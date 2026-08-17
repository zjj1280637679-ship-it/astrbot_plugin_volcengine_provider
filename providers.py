"""Two isolated Volcengine Ark chat providers built on AstrBot.

Both upstreams implement the OpenAI Chat Completions protocol, so this plugin
inherits AstrBot's native OpenAI adapter.  That keeps streaming, multimodal
message assembly, function calling, retries and response normalization on the
framework's normal path.
"""

from __future__ import annotations

import copy

from astrbot import logger
from astrbot.core.provider.entities import ProviderType
from astrbot.core.provider.sources.openai_source import ProviderOpenAIOfficial
from astrbot.core.provider.sources.request_retry import retry_provider_request
from openai._exceptions import NotFoundError

from .adapters.audio import build_ark_input_audio
from .adapters.image import enforce_image_limits
from .adapters.video import inject_current_request_videos
from .compatibility.astrbot import _ApiKeyLogView
from .capabilities import (
    apply_request_overrides,
    clear_source_model_hints,
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
    # AstrBot's WebUI resolves company logos from this brand key.  Channel
    # identity belongs to ``type``/``id``/``api_base`` instead.
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
    """Return the AstrBot-facing Agent Plan model identifier."""

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
    """Strip the local namespace before a request reaches Volcengine."""

    public = to_agent_plan_public_model(model)
    return public[len(AGENT_PLAN_PREFIX) :]


class _FixedArkEndpointProvider(ProviderOpenAIOfficial):
    """OpenAI-compatible provider whose billing endpoint cannot drift."""

    _fixed_api_base = ""
    _volcengine_provider_plugin_owned = True

    def __init__(self, provider_config: dict, provider_settings: dict) -> None:
        config = copy.deepcopy(provider_config)
        # These cards always use the ordinary OpenAI client. Ignore stale
        # Azure-only fields instead of inventing a second validation policy.
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

    async def _resolve_audio_part(self, audio_ref: str) -> dict:
        """Serialize AstrBot-resolved audio using Ark's final input_audio contract."""

        return await build_ark_input_audio(audio_ref)

    async def _prepare_chat_payload(self, *args, **kwargs):
        """Extend AstrBot's native Chat payload with Ark's video_url block."""

        extra_user_content_parts = kwargs.get("extra_user_content_parts")
        if extra_user_content_parts is None and len(args) >= 8:
            extra_user_content_parts = args[7]

        payloads, context_query = await super()._prepare_chat_payload(
            *args,
            **kwargs,
        )
        await enforce_image_limits(payloads)
        mode = video_input_mode(self.provider_config)
        await inject_current_request_videos(
            context_query,
            extra_user_content_parts,
            enabled=mode != "off",
            mode="original" if mode == "off" else mode,
        )
        return payloads, context_query

    def _apply_provider_specific_extra_body_overrides(
        self,
        extra_body: dict,
    ) -> None:
        """AstrBot 4.26.x hook: apply 0.1.19 rows after custom_extra_body."""

        parent = getattr(super(), "_apply_provider_specific_extra_body_overrides", None)
        if callable(parent):
            parent(extra_body)
        apply_request_overrides(self.provider_config, {}, extra_body)

    def _apply_provider_specific_request_overrides(
        self,
        payloads: dict,
        extra_body: dict,
    ) -> None:
        """AstrBot 4.27.x+ hook: apply 0.1.19 rows after custom_extra_body."""

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
        """Delegate recovery to AstrBot while keeping its key-prefix log redacted."""

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
    """Ordinary pay-as-you-go/free-quota Volcengine Ark chat provider."""

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
        """Enumerate visible Ark models and hand off only this live receipt."""

        scope = source_scope_id(self.provider_config)
        # Erase the previous receipt *before* network I/O.  A failed refresh must
        # not leave yesterday's feedback available for a later Dashboard call.
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
    """Agent Plan provider with a local-only ``agentplan/`` namespace."""

    _fixed_api_base = AGENT_PLAN_API_BASE
    _volcengine_provider_plugin_owned = True

    def __init__(self, provider_config: dict, provider_settings: dict) -> None:
        config = copy.deepcopy(provider_config)
        config["model"] = to_agent_plan_public_model(
            config.get("model") or AGENT_PLAN_DEFAULT_MODEL
        )
        super().__init__(config, provider_settings)

    async def get_models(self) -> list[str]:
        # Do not probe an undocumented /models route with the Plan inference key.
        models = (self.get_model(), *KNOWN_AGENT_PLAN_MODELS)
        return _dedupe_nonempty(to_agent_plan_public_model(model) for model in models)

    async def _prepare_chat_payload(self, *args, **kwargs):
        """Normalize only the request model; keep meta/config names prefixed."""

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
