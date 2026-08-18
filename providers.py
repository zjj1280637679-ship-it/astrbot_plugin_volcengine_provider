"""Two isolated Volcengine Ark chat providers built on AstrBot.

Both upstreams implement the OpenAI Chat Completions protocol, so streaming,
function calling, retries and response normalization stay on AstrBot's normal
provider path.  This plugin adds only Volcengine-specific last-mile media
handling, cache observability, fixed billing endpoints and the Agent Plan local
namespace.

Context-window authority stays with AstrBot/model-card configuration.  Dynamic
routing aliases and future model revisions make a plugin-owned static model
family context table unsafe.
"""

from __future__ import annotations

import copy
import time
from contextvars import ContextVar

from astrbot import logger
from astrbot.core.provider.entities import ProviderType
from astrbot.core.provider.sources.openai_source import ProviderOpenAIOfficial
from astrbot.core.provider.sources.request_retry import retry_provider_request
from openai._exceptions import NotFoundError

from .adapters.audio import build_ark_input_audio
from .adapters.errors import AdapterInputTransportError
from .adapters.image import build_ark_image_part
from .adapters.limits import get_limits
from .adapters.video import inject_current_request_videos
from .compatibility.astrbot import _ApiKeyLogView
from .capabilities import (
    apply_request_overrides,
    cache_log_settings,
    channel_name,
    clear_source_model_hints,
    configured_context_limit,
    is_context_length_error,
    log_cache_usage,
    remember_source_model_hint,
    source_scope_id,
    video_input_mode,
)
from .metadata.agent_plan import KNOWN_AGENT_PLAN_MODELS
from .metadata.ark import normalize_ark_model_metadata
from .registry import (
    AGENT_PLAN_PROVIDER_TYPE,
    ARK_PROVIDER_TYPE,
    register_owned_provider,
)

VOLCENGINE_BRAND_KEY = "volcengine"

ARK_API_BASE = "https://ark.cn-beijing.volces.com/api/v3"
AGENT_PLAN_API_BASE = "https://ark.cn-beijing.volces.com/api/plan/v3"
AGENT_PLAN_PREFIX = "agentplan/"
ARK_DEFAULT_MODEL = "doubao-seed-2-1-pro-260628"
AGENT_PLAN_DEFAULT_MODEL = "doubao-seed-2.1-turbo"

_REQUEST_STARTED_AT: ContextVar[float | None] = ContextVar(
    "volcengine_request_started_at",
    default=None,
)

AZURE_ONLY_CONFIG_KEYS = frozenset(
    {
        "api_version",
        "api_type",
        "azure_endpoint",
        "azure_deployment",
        "azure_ad_token",
        "azure_ad_token_provider",
    }
)


ARK_DEFAULT_CONFIG = {
    "id": "volcengine-ark",
    "provider": VOLCENGINE_BRAND_KEY,
    "type": ARK_PROVIDER_TYPE,
    "provider_type": "chat_completion",
    "enable": True,
    "key": [],
    "api_base": ARK_API_BASE,
    "timeout": 120,
    "proxy": "",
    "custom_headers": {},
}

AGENT_PLAN_DEFAULT_CONFIG = {
    "id": "volcengine-agent-plan",
    "provider": VOLCENGINE_BRAND_KEY,
    "type": AGENT_PLAN_PROVIDER_TYPE,
    "provider_type": "chat_completion",
    "enable": True,
    "key": [],
    "api_base": AGENT_PLAN_API_BASE,
    "timeout": 120,
    "proxy": "",
    "custom_headers": {},
}


def _dedupe_nonempty(values) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def to_agent_plan_public_model(model: object) -> str:
    value = str(model or "").strip()
    if not value:
        raise ValueError("Agent Plan model name cannot be empty")
    if value.startswith(AGENT_PLAN_PREFIX):
        upstream = value[len(AGENT_PLAN_PREFIX) :].strip()
        if not upstream:
            raise ValueError("Agent Plan model name cannot be empty after agentplan/")
        return f"{AGENT_PLAN_PREFIX}{upstream}"
    return f"{AGENT_PLAN_PREFIX}{value}"


def to_agent_plan_upstream_model(model: object) -> str:
    public = to_agent_plan_public_model(model)
    return public[len(AGENT_PLAN_PREFIX) :]


class _FixedArkEndpointProvider(ProviderOpenAIOfficial):
    """OpenAI-compatible provider whose billing endpoint cannot drift."""

    _fixed_api_base = ""
    _volcengine_provider_plugin_owned = True

    def __init__(self, provider_config: dict, provider_settings: dict) -> None:
        config = copy.deepcopy(provider_config)
        for name in AZURE_ONLY_CONFIG_KEYS:
            config.pop(name, None)

        configured_base = str(config.get("api_base") or "").rstrip("/")
        fixed_base = self._fixed_api_base.rstrip("/")
        if configured_base and configured_base != fixed_base:
            logger.warning(
                "%s ignores a customized api_base and uses its fixed billing endpoint=%s",
                self.__class__.__name__,
                fixed_base,
            )
        config["api_base"] = fixed_base
        super().__init__(config, provider_settings)

        limits = get_limits()
        cache_enabled, cache_every = cache_log_settings()
        logger.info(
            "[VolcenginePolicy] provider-bound id=%s type=%s model=%s "
            "audio=%dMiB video=%dMiB image=%dMiB cache=%s/every=%d",
            str(self.provider_config.get("id") or ""),
            str(self.provider_config.get("type") or ""),
            str(self.get_model() or ""),
            limits.audio_max_bytes // (1024 * 1024),
            limits.video_max_bytes // (1024 * 1024),
            limits.image_max_bytes // (1024 * 1024),
            cache_enabled,
            cache_every,
        )

    async def _resolve_audio_part(self, audio_ref: str) -> dict:
        return await build_ark_input_audio(audio_ref)

    async def _resolve_image_part(
        self,
        image_url: str,
        *,
        image_detail: str | None = None,
    ) -> dict:
        """Resolve/compress an Ark image before raw bytes become Base64."""
        return await build_ark_image_part(
            image_url,
            image_detail=image_detail,
        )

    async def _transform_content_part(self, part: dict) -> dict:
        """Keep image transport failures fail-closed on AstrBot 4.26/4.27.

        AstrBot's generic OpenAI adapter intentionally catches image preprocessing
        exceptions and preserves the original image block.  That is unsafe for
        this plugin's explicit size guard because an oversized/invalid image would
        otherwise bypass the guard.  Only image blocks are specialized here;
        all other content parts remain host-owned.
        """
        if isinstance(part, dict) and part.get("type") == "image_url":
            image_url, image_detail = self._extract_image_part_info(part)
            if not image_url:
                return part
            try:
                return await self._resolve_image_part(
                    image_url,
                    image_detail=image_detail,
                )
            except AdapterInputTransportError:
                raise
            except Exception as exc:
                raise AdapterInputTransportError(
                    "图片预处理失败，未向火山方舟发送请求。",
                    media_type="image",
                    stage="resolve_media",
                ) from exc
        return await super()._transform_content_part(part)

    async def _prepare_chat_payload(self, *args, **kwargs):
        extra_user_content_parts = kwargs.get("extra_user_content_parts")
        if extra_user_content_parts is None and len(args) >= 8:
            extra_user_content_parts = args[7]

        payloads, context_query = await super()._prepare_chat_payload(*args, **kwargs)

        mode = video_input_mode(self.provider_config)
        await inject_current_request_videos(
            context_query,
            extra_user_content_parts,
            enabled=mode != "off",
            mode="original" if mode == "off" else mode,
        )
        return payloads, context_query

    async def _query(
        self,
        payloads: dict,
        tools,
        *,
        request_max_retries: int | None = None,
    ):
        token = _REQUEST_STARTED_AT.set(time.perf_counter())
        try:
            return await super()._query(
                payloads,
                tools,
                request_max_retries=request_max_retries,
            )
        finally:
            _REQUEST_STARTED_AT.reset(token)

    async def _query_stream(
        self,
        payloads: dict,
        tools,
        *,
        request_max_retries: int | None = None,
    ):
        token = _REQUEST_STARTED_AT.set(time.perf_counter())
        try:
            async for item in super()._query_stream(
                payloads,
                tools,
                request_max_retries=request_max_retries,
            ):
                yield item
        finally:
            _REQUEST_STARTED_AT.reset(token)

    async def _parse_openai_completion(self, completion, tools):
        llm_response = await super()._parse_openai_completion(completion, tools)

        usage = getattr(completion, "usage", None)
        if usage is None:
            return llm_response

        started = _REQUEST_STARTED_AT.get()
        elapsed_ms = (
            max(0, int((time.perf_counter() - started) * 1000))
            if started is not None
            else 0
        )
        prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
        completion_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
        ptd = getattr(usage, "prompt_tokens_details", None)
        cached = int(getattr(ptd, "cached_tokens", 0) or 0) if ptd else 0
        ctd = getattr(usage, "completion_tokens_details", None)
        reasoning = int(getattr(ctd, "reasoning_tokens", 0) or 0) if ctd else 0

        resolved_model = str(getattr(completion, "model", "") or "")
        log_cache_usage(
            channel=channel_name(self._fixed_api_base),
            model=resolved_model or str(self.get_model() or ""),
            prompt_tokens=prompt_tokens,
            cached_tokens=cached,
            completion_tokens=completion_tokens,
            reasoning_tokens=reasoning,
            ms=elapsed_ms,
        )
        return llm_response

    def _apply_provider_specific_extra_body_overrides(self, extra_body: dict) -> None:
        parent = getattr(super(), "_apply_provider_specific_extra_body_overrides", None)
        if callable(parent):
            parent(extra_body)
        apply_request_overrides(self.provider_config, {}, extra_body)

    def _apply_provider_specific_request_overrides(
        self,
        payloads: dict,
        extra_body: dict,
    ) -> None:
        parent = getattr(super(), "_apply_provider_specific_request_overrides", None)
        if callable(parent):
            parent(payloads, extra_body)
        apply_request_overrides(self.provider_config, payloads, extra_body)

    async def _handle_api_error(
        self,
        error: Exception,
        payloads: dict,
        context_query: list,
        func_tool,
        chosen_key: str,
        available_api_keys: list[str],
        retry_cnt: int,
        max_retries: int,
        image_fallback_used: bool = False,
    ) -> tuple:
        if is_context_length_error(error):
            resolved = str(payloads.get("model", "") or self.get_model() or "")
            guard = configured_context_limit(self.provider_config)
            if guard is None:
                logger.warning(
                    "[VolcengineCache] context-length error for model=%s; "
                    "plugin has no explicit context guard and does not invent one; "
                    "AstrBot/model metadata owns compression and retry",
                    resolved,
                )
            else:
                logger.warning(
                    "[VolcengineCache] context-length error for model=%s; "
                    "explicit max_context_tokens=%d was still rejected; "
                    "delegating history reduction/retry to AstrBot",
                    resolved,
                    guard,
                )

        result = await super()._handle_api_error(
            error,
            payloads,
            context_query,
            func_tool,
            _ApiKeyLogView(chosen_key),
            available_api_keys,
            retry_cnt,
            max_retries,
            image_fallback_used=image_fallback_used,
        )
        if (
            isinstance(result, tuple)
            and len(result) > 1
            and isinstance(result[1], _ApiKeyLogView)
        ):
            result = list(result)
            result[1] = str(result[1])
            return tuple(result)
        return result


@register_owned_provider(
    ARK_PROVIDER_TYPE,
    "Volcengine Ark ordinary API (OpenAI Chat Completions)",
    provider_type=ProviderType.CHAT_COMPLETION,
    default_config_tmpl=copy.deepcopy(ARK_DEFAULT_CONFIG),
    provider_display_name="火山方舟普通 API",
)
class ProviderVolcengineArk(_FixedArkEndpointProvider):
    _fixed_api_base = ARK_API_BASE
    _volcengine_provider_plugin_owned = True

    def __init__(self, provider_config: dict, provider_settings: dict) -> None:
        model = str(provider_config.get("model") or ARK_DEFAULT_MODEL).strip()
        if model.startswith(AGENT_PLAN_PREFIX):
            raise ValueError(
                "agentplan/ models must use the dedicated Volcengine Agent Plan provider"
            )
        config = copy.deepcopy(provider_config)
        config["model"] = model
        super().__init__(config, provider_settings)

    async def get_models(self) -> list[str]:
        scope = source_scope_id(self.provider_config)
        clear_source_model_hints(scope)
        try:
            response = await retry_provider_request(
                "Volcengine Ark",
                lambda: self.client.models.list(),
            )
            model_ids: list[str] = []
            for model in sorted(
                response.data,
                key=lambda item: str(getattr(item, "id", "")),
            ):
                model_id, hint = normalize_ark_model_metadata(model)
                if not model_id:
                    continue
                model_ids.append(model_id)
                if len(hint) > 1:
                    remember_source_model_hint(scope, model_id, hint)
            return _dedupe_nonempty(model_ids)
        except NotFoundError as error:
            raise Exception(f"获取模型列表失败：{error}") from error


@register_owned_provider(
    AGENT_PLAN_PROVIDER_TYPE,
    "Volcengine Ark Agent Plan API with local agentplan/ model namespace",
    provider_type=ProviderType.CHAT_COMPLETION,
    default_config_tmpl=copy.deepcopy(AGENT_PLAN_DEFAULT_CONFIG),
    provider_display_name="火山方舟 Agent Plan API",
)
class ProviderVolcengineAgentPlan(_FixedArkEndpointProvider):
    _fixed_api_base = AGENT_PLAN_API_BASE
    _volcengine_provider_plugin_owned = True

    def __init__(self, provider_config: dict, provider_settings: dict) -> None:
        config = copy.deepcopy(provider_config)
        config["model"] = to_agent_plan_public_model(
            config.get("model") or AGENT_PLAN_DEFAULT_MODEL
        )
        super().__init__(config, provider_settings)

    async def get_models(self) -> list[str]:
        models = (self.get_model(), *KNOWN_AGENT_PLAN_MODELS)
        return _dedupe_nonempty(to_agent_plan_public_model(model) for model in models)

    async def _prepare_chat_payload(self, *args, **kwargs):
        positional = list(args)
        if "model" in kwargs:
            selected = kwargs.get("model") or self.get_model()
            kwargs["model"] = to_agent_plan_upstream_model(selected)
        elif len(positional) >= 7:
            selected = positional[6] or self.get_model()
            positional[6] = to_agent_plan_upstream_model(selected)
        else:
            kwargs["model"] = to_agent_plan_upstream_model(self.get_model())
        return await super()._prepare_chat_payload(*positional, **kwargs)
