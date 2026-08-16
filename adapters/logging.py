"""OpenAI SDK request-log redaction owned by this plugin.

This module changes only observability output; it must never own retry,
request routing, key selection or Provider recovery.
"""

from __future__ import annotations

import logging
import re

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

