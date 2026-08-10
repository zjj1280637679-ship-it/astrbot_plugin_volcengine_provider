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
import logging
import re
import subprocess
import uuid
import wave
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from astrbot import logger
from astrbot.core.agent.message import ContentPart, TextPart
from astrbot.core.provider.entities import ProviderType
from astrbot.core.provider.sources.openai_source import ProviderOpenAIOfficial
from astrbot.core.provider.sources.request_retry import retry_provider_request
from astrbot.core.utils.astrbot_path import get_astrbot_temp_path
from astrbot.core.utils.media_utils import MediaResolver, describe_media_ref
from astrbot.core.utils.llm_metadata import LLM_METADATAS
from openai._exceptions import NotFoundError

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

OPENAI_BASE_CLIENT_LOGGER = "openai._base_client"
VIDEO_URL_LOG_PATTERN = re.compile(
    r"(?P<prefix>['\"]video_url['\"]\s*:\s*\{\s*"
    r"['\"]url['\"]\s*:\s*['\"])(?P<value>.*?)(?P<suffix>['\"])",
    re.DOTALL,
)
VIDEO_LOG_REDACTION = "[REDACTED_VIDEO_URL]"
AUDIO_DATA_LOG_PATTERN = re.compile(
    r"(?P<prefix>['\"]input_audio['\"]\s*:\s*\{\s*"
    r"['\"]data['\"]\s*:\s*['\"])(?P<value>.*?)(?P<suffix>['\"])",
    re.DOTALL,
)
AUDIO_LOG_REDACTION = "[REDACTED_AUDIO_BASE64]"


class _ApiKeyLogView(str):
    """Preserve a real API key while redacting the slice AstrBot logs on 429.

    This object is passed only into AstrBot's native error-recovery method.
    Equality and hashing stay identical to ``str``, so the framework still owns
    key-pool membership, removal, selection and retry policy.  Only indexing is
    redacted because AstrBot currently logs ``chosen_key[:12]`` on rate limits.
    """

    def __getitem__(self, key):
        if isinstance(key, slice):
            return "[REDACTED_API_KEY]"
        return "*"

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

# Agent Plan's inference-key plane has no documented /models route. Keep only
# active language models shown by the official Agent Plan console on
# 2026-08-09; users can still type a newer official model name manually.
# Models marked "即将下线" are deliberately omitted.
KNOWN_AGENT_PLAN_MODELS = (
    "doubao-seed-2.1-turbo",
    "doubao-seed-evolving",
    "doubao-seed-2.0-lite",
    "doubao-seed-2.0-mini",
    "deepseek-v4-flash",
    "deepseek-v4-pro",
    "glm-5.2",
    "glm-latest",
    "kimi-k3",
    "kimi-k2.7-code",
    "minimax-m3",
    "ark-code-latest",
)

# The Plan control plane exposes only ModelID values. These limits and input
# modalities therefore follow the public package/model tables and the live
# console, rather than pretending the inference key returns a capability map.
# k-values in the public table are binary token units except the official
# ark-code-latest client example, which uses literal 256000/32000 limits.
AGENT_PLAN_MODEL_SPECS: dict[str, dict[str, Any]] = {
    "doubao-seed-2.0-mini": {
        "input": ["text", "image", "video", "audio"],
        "context": 262_144,
        "output": 131_072,
    },
    "doubao-seed-2.0-lite": {
        "input": ["text", "image", "video", "audio"],
        "context": 262_144,
        "output": 131_072,
    },
    "deepseek-v4-flash": {
        "input": ["text"],
        "context": 1_048_576,
        "output": 393_216,
    },
    "doubao-seed-2.1-turbo": {
        "input": ["text", "image", "video"],
        "context": 262_144,
        "output": 262_144,
    },
    "doubao-seed-evolving": {
        "input": ["text", "image", "video"],
        "context": 1_048_576,
        "output": 262_144,
    },
    "minimax-m3": {
        "input": ["text", "image"],
        "context": 1_048_576,
        "output": 131_072,
    },
    "glm-5.2": {
        "input": ["text"],
        "context": 1_048_576,
        "output": 131_072,
    },
    "glm-latest": {
        "input": ["text"],
        "context": 1_048_576,
        "output": 131_072,
    },
    "kimi-k2.7-code": {
        "input": ["text", "image", "video"],
        "context": 262_144,
        "output": 32_768,
    },
    "deepseek-v4-pro": {
        "input": ["text"],
        "context": 1_048_576,
        "output": 393_216,
    },
    "kimi-k3": {
        "input": ["text", "image"],
        "context": 1_048_576,
        "output": 131_072,
    },
    "ark-code-latest": {
        "input": ["text", "image"],
        "context": 256_000,
        "output": 32_000,
    },
}

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


def redact_video_urls_from_log(message: str) -> str:
    """Remove Ark video URLs and audio data from an SDK debug message.

    The OpenAI SDK logs request JSON at DEBUG level.  Local videos are data
    URLs and remote videos may use signed URLs, so neither value belongs in a
    persistent log. Audio is sent as bare Base64, so the value nested under an
    ``input_audio.data`` key is protected by the same plugin-owned filter.
    Unrelated SDK diagnostics remain intact.
    """

    redacted = VIDEO_URL_LOG_PATTERN.sub(
        lambda match: (
            f"{match.group('prefix')}{VIDEO_LOG_REDACTION}"
            f"{match.group('suffix')}"
        ),
        message,
    )
    return AUDIO_DATA_LOG_PATTERN.sub(
        lambda match: (
            f"{match.group('prefix')}{AUDIO_LOG_REDACTION}"
            f"{match.group('suffix')}"
        ),
        redacted,
    )


def _redact_sdk_log_structure(value: object) -> tuple[object, bool]:
    """Redact SDK request structures copy-on-write before logging renders them."""

    if isinstance(value, dict):
        result: dict | None = None
        for key, item in value.items():
            replacement = item
            changed = False
            if key == "video_url" and isinstance(item, dict) and "url" in item:
                replacement = item.copy()
                replacement["url"] = VIDEO_LOG_REDACTION
                changed = True
            elif key == "input_audio" and isinstance(item, dict) and "data" in item:
                replacement = item.copy()
                replacement["data"] = AUDIO_LOG_REDACTION
                changed = True
            else:
                replacement, changed = _redact_sdk_log_structure(item)

            if changed:
                if result is None:
                    result = value.copy()
                result[key] = replacement
        return (value, False) if result is None else (result, True)

    if isinstance(value, list):
        result: list | None = None
        for index, item in enumerate(value):
            replacement, changed = _redact_sdk_log_structure(item)
            if changed:
                if result is None:
                    result = value.copy()
                result[index] = replacement
        return (value, False) if result is None else (result, True)

    if isinstance(value, tuple):
        result: list | None = None
        for index, item in enumerate(value):
            replacement, changed = _redact_sdk_log_structure(item)
            if changed:
                if result is None:
                    result = list(value)
                result[index] = replacement
        return (value, False) if result is None else (tuple(result), True)

    if isinstance(value, str) and (
        "video_url" in value or "input_audio" in value
    ):
        redacted = redact_video_urls_from_log(value)
        if redacted != value:
            return redacted, True

    return value, False


class VideoRequestLogFilter(logging.Filter):
    """Redact media payloads without eagerly rendering large SDK log records."""

    _volcengine_provider_video_redaction = True
    _volcengine_provider_video_redaction_leases = 0

    def filter(self, record: logging.LogRecord) -> bool:
        redacted_args, args_changed = _redact_sdk_log_structure(record.args)
        if args_changed:
            record.args = redacted_args

        redacted_msg, msg_changed = _redact_sdk_log_structure(record.msg)
        if msg_changed:
            record.msg = redacted_msg
        return True


def install_video_log_redaction() -> VideoRequestLogFilter:
    """Acquire one lease on the SDK request-log redaction filter.

    The lease count lives on the filter instance rather than in module globals,
    so it survives AstrBot plugin-module reload overlap.  An older plugin
    instance can then release only its own lease without removing protection
    still owned by the newly loaded instance.
    """

    sdk_logger = logging.getLogger(OPENAI_BASE_CLIENT_LOGGER)
    for existing in sdk_logger.filters:
        if getattr(existing, "_volcengine_provider_video_redaction", False):
            leases = int(
                getattr(
                    existing,
                    "_volcengine_provider_video_redaction_leases",
                    0,
                )
            )
            existing._volcengine_provider_video_redaction_leases = leases + 1
            return existing
    log_filter = VideoRequestLogFilter()
    log_filter._volcengine_provider_video_redaction_leases = 1
    sdk_logger.addFilter(log_filter)
    return log_filter


def remove_video_log_redaction(log_filter: logging.Filter | None) -> None:
    """Release one lease and remove only the exact unowned filter instance."""

    if log_filter is None:
        return
    leases = int(
        getattr(log_filter, "_volcengine_provider_video_redaction_leases", 1)
    )
    if leases > 1:
        log_filter._volcengine_provider_video_redaction_leases = leases - 1
        return
    log_filter._volcengine_provider_video_redaction_leases = 0
    logging.getLogger(OPENAI_BASE_CLIENT_LOGGER).removeFilter(log_filter)


def _dedupe_nonempty(values: Iterable[object]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


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


def _as_mapping(value: object) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump()
        return dumped if isinstance(dumped, dict) else {}
    return {}


def _positive_int(value: object) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 0
    return parsed if parsed > 0 else 0


def _feature_flag(value: object) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, dict):
        for name in ("supported", "enabled", "available", "function_calling"):
            if isinstance(value.get(name), bool):
                return value[name]
    return None


def _normalized_modalities(values: object) -> list[str]:
    if not isinstance(values, (list, tuple)):
        return []
    allowed = {"text", "image", "audio", "video"}
    return [value for value in _dedupe_nonempty(values) if value in allowed]


def _publish_metadata(model_id: str, metadata: dict[str, Any]) -> None:
    """Publish model facts through AstrBot's native model metadata cache."""

    existing = LLM_METADATAS.get(model_id, {})
    LLM_METADATAS[model_id] = {
        "id": model_id,
        "reasoning": bool(metadata.get("reasoning", existing.get("reasoning", False))),
        "tool_call": bool(metadata.get("tool_call", existing.get("tool_call", False))),
        "knowledge": str(existing.get("knowledge", "none")),
        "release_date": str(existing.get("release_date", "")),
        "modalities": metadata.get(
            "modalities",
            existing.get("modalities", {"input": [], "output": []}),
        ),
        "open_weights": bool(existing.get("open_weights", False)),
        "limit": metadata.get(
            "limit",
            existing.get("limit", {"context": 0, "output": 0}),
        ),
    }


def publish_agent_plan_metadata() -> None:
    """Publish the documented Plan model table under local prefixed IDs."""

    for upstream_id, spec in AGENT_PLAN_MODEL_SPECS.items():
        public_id = to_agent_plan_public_model(upstream_id)
        _publish_metadata(
            public_id,
            {
                "reasoning": spec.get("reasoning", True),
                "tool_call": spec.get("tool_call", True),
                "modalities": {
                    "input": list(spec["input"]),
                    "output": ["text"],
                },
                "limit": {
                    "context": int(spec["context"]),
                    "output": int(spec["output"]),
                },
            },
        )


def publish_ark_model_metadata(model: object) -> str:
    """Translate ordinary Ark model facts using conservative card defaults.

    AstrBot treats a missing metadata entry as a legacy provider and enables
    image, audio and tool use by default.  That is unsafe for Ark's mixed model
    catalogue: some entries omit capability fields entirely, and the absence of
    a field is not evidence that every optional input is accepted.  Publish an
    entry for every returned model, always keep text available, and add optional
    capabilities only when this specific ``/models`` receipt says so.

    The result is only a default for a newly-created model card.  Users remain
    free to edit ``modalities`` afterwards; request-time handling continues to
    respect the saved card without a second capability policy here.
    """

    data = _as_mapping(model)
    model_id = str(data.get("id") or getattr(model, "id", "") or "").strip()
    if not model_id:
        return ""

    modalities = _as_mapping(data.get("modalities"))
    input_modalities = _dedupe_nonempty(
        ["text", *_normalized_modalities(modalities.get("input_modalities"))]
    )
    output_modalities = _normalized_modalities(modalities.get("output_modalities"))

    limits = _as_mapping(data.get("token_limits"))
    context_limit = _positive_int(limits.get("context_window"))
    output_limit = _positive_int(limits.get("max_output_token_length"))
    reasoning_limit = _positive_int(limits.get("max_reasoning_token_length"))

    features = _as_mapping(data.get("features"))
    tools = _as_mapping(features.get("tools"))
    tool_call = _feature_flag(tools.get("function_calling"))
    if tool_call is None:
        tool_call = _feature_flag(features.get("function_calling"))
    reasoning = _feature_flag(features.get("reasoning"))
    if reasoning is None and "max_reasoning_token_length" in limits:
        reasoning = reasoning_limit > 0

    _publish_metadata(
        model_id,
        {
            "reasoning": False if reasoning is None else reasoning,
            "tool_call": False if tool_call is None else tool_call,
            "modalities": {
                "input": input_modalities,
                "output": output_modalities,
            },
            "limit": {
                "context": context_limit,
                "output": output_limit,
            },
        },
    )
    return model_id


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
        return {
            "type": "input_audio",
            "input_audio": {
                "data": base64.b64encode(wav_data).decode("ascii"),
                "format": "wav",
            },
        }

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

        modalities = self.provider_config.get("modalities")
        if isinstance(modalities, list):
            # One model capability set is authoritative, exactly like image,
            # audio and tool use.  This avoids two switches disagreeing.
            supports_video = "video" in modalities
        else:
            # Read a value saved by 0.1.6 only when the native capability list
            # is genuinely absent; all new/normal configurations use modalities.
            explicit_video_input = self.provider_config.get(
                self._video_input_config_key
            )
            supports_video = (
                explicit_video_input
                if isinstance(explicit_video_input, bool)
                else False
            )
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
        publish_agent_plan_metadata()
        super().__init__(config, provider_settings)

    async def get_models(self) -> list[str]:
        # Do not probe an undocumented /models route with the Plan inference key.
        publish_agent_plan_metadata()
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
