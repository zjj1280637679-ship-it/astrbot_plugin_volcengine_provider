"""Two isolated Volcengine Ark chat providers built on AstrBot.

Both upstreams implement the OpenAI Chat Completions protocol, so this plugin
inherits AstrBot's native OpenAI adapter.  That keeps streaming, multimodal
message assembly, function calling, retries and response normalization on the
framework's normal path.
"""

from __future__ import annotations

import asyncio
import base64
import copy
import io
import re
import subprocess
import uuid
import wave
from pathlib import Path
from typing import Any

from astrbot import logger
from astrbot.core.agent.message import ContentPart, TextPart
from astrbot.core.provider.entities import ProviderType
from astrbot.core.provider.sources.openai_source import ProviderOpenAIOfficial
from astrbot.core.provider.sources.request_retry import retry_provider_request
from astrbot.core.utils.astrbot_path import get_astrbot_temp_path
from astrbot.core.utils.media_utils import MediaResolver, describe_media_ref
from openai._exceptions import NotFoundError

from .compatibility.astrbot import _ApiKeyLogView
from .metadata.agent_plan import (
    KNOWN_AGENT_PLAN_MODELS,
    publish_agent_plan_metadata,
)
from .metadata.ark import publish_ark_model_metadata
from .metadata.common import _dedupe_nonempty

from .registry import (
    AGENT_PLAN_PROVIDER_TYPE,
    AGENT_PLAN_VIDEO_INPUT_KEY,
    ARK_PROVIDER_TYPE,
    ARK_VIDEO_INPUT_KEY,
    register_owned_provider,
)

VOLCENGINE_BRAND_KEY = "volcengine"

ARK_API_BASE = "https://ark.cn-beijing.volces.com/api/v3"
AGENT_PLAN_API_BASE = "https://ark.cn-beijing.volces.com/api/plan/v3"
AGENT_PLAN_PREFIX = "agentplan/"
ARK_DEFAULT_MODEL = "doubao-seed-2-1-pro-260628"
AGENT_PLAN_DEFAULT_MODEL = "doubao-seed-2.1-turbo"

ARK_CHAT_AUDIO_MAX_BYTES = 25 * 1024 * 1024
ARK_CHAT_AUDIO_SAMPLE_RATE = 16_000
ARK_CHAT_AUDIO_CHANNELS = 1
ARK_CHAT_AUDIO_SAMPLE_WIDTH = 2
ARK_CHAT_AUDIO_TRANSCODE_TIMEOUT_SECONDS = 120

# AstrBot currently represents an incoming video as a framework-generated
# TextPart because ProviderRequest has no video_urls field. Match only the
# exact framework envelope, and only when the same TextPart is present in
# extra_user_content_parts for the current request.  This prevents ordinary
# chat text that happens to look like a local path from becoming file access.
VIDEO_ATTACHMENT_PATTERN = re.compile(
    r"^\[Video Attachment(?: in quoted message)?: "
    r"name (?P<name>.*?), (?P<source_kind>path|ref) "
    r"(?P<source>.+)\]$"
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
    ARK_VIDEO_INPUT_KEY: False,
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
    AGENT_PLAN_VIDEO_INPUT_KEY: False,
}






def _video_attachments_from_current_request(
    extra_user_content_parts: list[ContentPart] | None,
) -> list[tuple[str, str]]:
    """Return trusted ``(marker_text, media_ref)`` pairs for this request.

    The trust boundary is the ContentPart list assembled by AstrBot and passed
    separately from the user's prompt.  Context history alone is deliberately
    insufficient because a user can type arbitrary text that resembles an
    attachment marker.
    """

    attachments: list[tuple[str, str]] = []
    for part in extra_user_content_parts or []:
        if not isinstance(part, TextPart):
            continue
        match = VIDEO_ATTACHMENT_PATTERN.fullmatch(part.text)
        if not match:
            continue
        media_ref = match.group("source").strip()
        if media_ref:
            attachments.append((part.text, media_ref))
    return attachments


def _replace_last_text_block(
    messages: list[dict],
    marker_text: str,
    replacement: dict[str, Any],
) -> bool:
    """Replace the newest exact marker, preserving earlier conversation text."""

    for message in reversed(messages):
        content = message.get("content")
        if not isinstance(content, list):
            continue
        for index in range(len(content) - 1, -1, -1):
            block = content[index]
            if not isinstance(block, dict):
                continue
            if block.get("type") == "text" and block.get("text") == marker_text:
                content[index] = replacement
                return True
    return False


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


def _validate_ark_chat_wav(wav_data: bytes) -> None:
    """Enforce the exact audio invariant sent to Ark Chat Completions."""

    if len(wav_data) > ARK_CHAT_AUDIO_MAX_BYTES:
        raise ValueError(
            "音频归一化后超过火山方舟 Base64 音频输入的 25 MB 上限，未发送请求。"
        )
    if not wav_data.startswith(b"RIFF") or wav_data[8:12] != b"WAVE":
        raise ValueError("音频归一化结果不是有效的 RIFF/WAVE 文件，未发送请求。")

    try:
        with wave.open(io.BytesIO(wav_data), "rb") as wav_file:
            if wav_file.getnchannels() != ARK_CHAT_AUDIO_CHANNELS:
                raise ValueError("音频归一化结果不是单声道 WAV，未发送请求。")
            if wav_file.getsampwidth() != ARK_CHAT_AUDIO_SAMPLE_WIDTH:
                raise ValueError("音频归一化结果不是 16-bit PCM WAV，未发送请求。")
            if wav_file.getframerate() != ARK_CHAT_AUDIO_SAMPLE_RATE:
                raise ValueError("音频归一化结果不是 16 kHz WAV，未发送请求。")
            if wav_file.getcomptype() != "NONE":
                raise ValueError("音频归一化结果不是未压缩 PCM WAV，未发送请求。")
            if wav_file.getnframes() <= 0:
                raise ValueError("音频归一化结果没有可用音频帧，未发送请求。")
    except (EOFError, wave.Error) as exc:
        raise ValueError("音频归一化结果的 WAV 结构无效，未发送请求。") from exc


async def _ffmpeg_to_ark_chat_wav(source_path: Path, output_path: Path) -> None:
    """Convert one materialized audio file to the provider's canonical WAV."""

    args = [
        "ffmpeg",
        "-nostdin",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(source_path),
        "-vn",
        "-ac",
        str(ARK_CHAT_AUDIO_CHANNELS),
        "-ar",
        str(ARK_CHAT_AUDIO_SAMPLE_RATE),
        "-c:a",
        "pcm_s16le",
        "-f",
        "wav",
        str(output_path),
    ]

    try:
        process = await asyncio.create_subprocess_exec(
            *args,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
    except FileNotFoundError as exc:
        raise ValueError("找不到 ffmpeg，无法把音频附件转换为火山方舟可读格式。") from exc

    try:
        _, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=ARK_CHAT_AUDIO_TRANSCODE_TIMEOUT_SECONDS,
        )
    except TimeoutError as exc:
        process.kill()
        await process.communicate()
        raise ValueError("音频附件转换超时，未向火山方舟发送请求。") from exc

    if process.returncode != 0:
        # Do not expose a signed source URL, local path or raw ffmpeg command in
        # user-visible errors. The exit code is sufficient for diagnosis.
        stderr_size = len(stderr or b"")
        raise ValueError(
            "音频附件无法解码为标准 WAV，未向火山方舟发送请求"
            f"（ffmpeg exit={process.returncode}, stderr_bytes={stderr_size}）。"
        )


async def normalize_ark_chat_audio(audio_ref: str) -> bytes:
    """Use AstrBot for audio resolution and enforce only Ark's final WAV invariant."""

    temp_dir = Path(get_astrbot_temp_path())
    temp_dir.mkdir(parents=True, exist_ok=True)
    output_path = temp_dir / f"volcengine_audio_{uuid.uuid4().hex}.wav"

    try:
        async with MediaResolver(
            audio_ref,
            media_type="audio",
            default_suffix=".wav",
        ).as_path(target_format="wav") as resolved:
            source_path = resolved.path

            wav_data: bytes | None = None
            source_stat = await asyncio.to_thread(source_path.stat)
            if source_stat.st_size <= ARK_CHAT_AUDIO_MAX_BYTES:
                candidate = await asyncio.to_thread(source_path.read_bytes)
                try:
                    _validate_ark_chat_wav(candidate)
                except ValueError:
                    pass
                else:
                    wav_data = candidate

            if wav_data is None:
                await _ffmpeg_to_ark_chat_wav(source_path, output_path)
                wav_data = await asyncio.to_thread(output_path.read_bytes)

        _validate_ark_chat_wav(wav_data)
        logger.debug(
            "Normalized Ark audio attachment: source=%s format=wav "
            "pcm_s16le=%dHz mono bytes=%d",
            describe_media_ref(audio_ref),
            ARK_CHAT_AUDIO_SAMPLE_RATE,
            len(wav_data),
        )
        return wav_data
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(
            "无法把本次音频附件归一化为火山方舟可读格式，未发送请求。"
        ) from exc
    finally:
        try:
            output_path.unlink(missing_ok=True)
        except OSError:
            logger.warning("Failed to clean provider-owned audio temp file")


class _FixedArkEndpointProvider(ProviderOpenAIOfficial):
    """OpenAI-compatible provider whose billing endpoint cannot drift."""

    _fixed_api_base = ""
    _video_input_config_key = ""
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

    async def _resolve_video_reference(self, media_ref: str) -> str:
        """Resolve one AstrBot video reference for Ark Chat Completions.

        Ark's official Chat schema accepts an HTTP(S) URL or base64 video data
        in ``video_url.url``.  Remote URLs stay remote; local/file/base64
        references go through AstrBot's own MediaResolver so this plugin does
        not create a second download or temporary-file subsystem.
        """

        normalized = media_ref.strip()
        if normalized.startswith(("http://", "https://", "data:video/")):
            return normalized

        try:
            media = await MediaResolver(
                normalized,
                media_type="video",
                default_suffix=".mp4",
            ).to_base64_data(
                strict=True,
                default_mime_type="video/mp4",
            )
        except Exception as exc:
            raise ValueError(
                "无法读取本次视频附件，未向火山方舟发送降级后的纯文本请求。"
            ) from exc

        if media is None or not media.mime_type.startswith("video/"):
            raise ValueError(
                "视频附件没有可识别的视频 MIME 类型，未向火山方舟发送请求。"
            )
        return media.to_data_url()

    async def _resolve_audio_part(self, audio_ref: str) -> dict:
        """Build Ark Chat's input_audio block from byte-validated WAV data."""

        wav_data = await normalize_ark_chat_audio(audio_ref)
        audio_base64 = await asyncio.to_thread(
            lambda: base64.b64encode(wav_data).decode("ascii")
        )
        return {
            "type": "input_audio",
            "input_audio": {
                "data": audio_base64,
                "format": "wav",
            },
        }

    def _supports_video_input(self) -> bool:
        """Resolve only the plugin-owned video switch, with legacy fallback.

        AstrBot does not yet model video in its native modality axis. New
        Volcengine sources therefore use a provider-specific boolean. Existing
        0.1.7-0.1.12 model cards that already saved ``video`` in ``modalities``
        keep working until the host gains a native video capability.
        """

        explicit = self.provider_config.get(self._video_input_config_key)
        if isinstance(explicit, bool):
            return explicit
        modalities = self.provider_config.get("modalities")
        return isinstance(modalities, list) and "video" in modalities

    async def _inject_current_request_videos(
        self,
        messages: list[dict],
        extra_user_content_parts: list[ContentPart] | None,
    ) -> None:
        attachments = _video_attachments_from_current_request(
            extra_user_content_parts,
        )
        if not attachments:
            return

        supports_video = self._supports_video_input()
        if not supports_video:
            for marker_text, _ in reversed(attachments):
                if not _replace_last_text_block(
                    messages,
                    marker_text,
                    {"type": "text", "text": "[Video]"},
                ):
                    raise ValueError(
                        "AstrBot 已声明视频附件，但当前请求中找不到对应内容块；"
                        "本次请求已停止。"
                    )
            return

        replacements: list[tuple[str, dict[str, Any]]] = []
        for marker_text, media_ref in attachments:
            video_url = await self._resolve_video_reference(media_ref)
            replacements.append(
                (
                    marker_text,
                    {
                        "type": "video_url",
                        "video_url": {"url": video_url},
                    },
                )
            )

        # The prompt text precedes extra parts in AstrBot's message assembly.
        # Replacing from the tail ensures a user-typed lookalike remains text
        # even when it is identical to the trusted attachment envelope.
        for marker_text, replacement in reversed(replacements):
            if not _replace_last_text_block(messages, marker_text, replacement):
                raise ValueError(
                    "AstrBot 已声明视频附件，但当前请求中找不到对应内容块；"
                    "为避免静默丢视频，本次请求已停止。"
                )

    async def _prepare_chat_payload(self, *args, **kwargs):
        """Extend AstrBot's native Chat payload with Ark's video_url block."""

        extra_user_content_parts = kwargs.get("extra_user_content_parts")
        if extra_user_content_parts is None and len(args) >= 8:
            extra_user_content_parts = args[7]

        payloads, context_query = await super()._prepare_chat_payload(
            *args,
            **kwargs,
        )
        await self._inject_current_request_videos(
            context_query,
            extra_user_content_parts,
        )
        return payloads, context_query

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
        if isinstance(result, tuple) and len(result) > 1 and isinstance(
            result[1], _ApiKeyLogView
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
    _video_input_config_key = ARK_VIDEO_INPUT_KEY
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
        """Enumerate every visible ordinary Ark model and publish its facts."""

        try:
            response = await retry_provider_request(
                "Volcengine Ark",
                lambda: self.client.models.list(),
            )
            model_objects = sorted(
                response.data,
                key=lambda model: str(getattr(model, "id", "")),
            )
            return _dedupe_nonempty(
                publish_ark_model_metadata(model) for model in model_objects
            )
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
    _video_input_config_key = AGENT_PLAN_VIDEO_INPUT_KEY
    _volcengine_provider_plugin_owned = True

    def __init__(self, provider_config: dict, provider_settings: dict) -> None:
        config = copy.deepcopy(provider_config)
        config["model"] = to_agent_plan_public_model(
            config.get("model") or AGENT_PLAN_DEFAULT_MODEL
        )
        publish_agent_plan_metadata(to_agent_plan_public_model)
        super().__init__(config, provider_settings)

    async def get_models(self) -> list[str]:
        # Do not probe an undocumented /models route with the Plan inference key.
        publish_agent_plan_metadata(to_agent_plan_public_model)
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
