"""Cache observability and conservative context diagnostics for Volcengine providers.

Lifecycle rule: an observation is only valid for the state in which it was made.
Changing cache-log policy resets rolling evidence instead of mixing samples across
policy generations.

Context-window ownership deliberately stays with AstrBot/model-card configuration.
The plugin does not author a second static model-family capability table: dynamic
routing aliases and future model revisions make such a table unsafe. Explicit
positive ``max_context_tokens`` values can still be observed for diagnostics, but
are never invented here.
"""

from __future__ import annotations

import json
import threading
from typing import Any

from astrbot import logger

DEFAULT_CACHE_LOG_ENABLED = True
DEFAULT_CACHE_LOG_EVERY = 10


def configured_context_limit(provider_config: dict[str, Any] | object) -> int | None:
    """Return an explicit positive host/model-card context guard, if present."""
    if not isinstance(provider_config, dict):
        return None
    raw = provider_config.get("max_context_tokens")
    if isinstance(raw, bool):
        return None
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


class _CacheAccumulator:
    """Thread-safe per-channel/model rolling counters."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._buckets: dict[tuple[str, str], list[int]] = {}

    def note(
        self,
        key: tuple[str, str],
        *,
        in_tokens: int,
        cached_tokens: int,
        out_tokens: int,
        ms: int,
        every: int,
    ) -> tuple[int, int, int, int, int] | None:
        """Record one call and atomically return/reset a completed bucket."""
        with self._lock:
            bucket = self._buckets.setdefault(key, [0, 0, 0, 0, 0])
            bucket[0] += 1
            bucket[1] += in_tokens
            bucket[2] += cached_tokens
            bucket[3] += out_tokens
            bucket[4] += ms
            if bucket[0] < every:
                return None
            snapshot = tuple(bucket)
            self._buckets[key] = [0, 0, 0, 0, 0]
            return snapshot

    def reset(self) -> None:
        """Invalidate rolling evidence after an observability-policy transition."""
        with self._lock:
            self._buckets.clear()


_accumulator = _CacheAccumulator()
_current_cache_log_enabled = DEFAULT_CACHE_LOG_ENABLED
_current_cache_log_every = DEFAULT_CACHE_LOG_EVERY


def configure_cache_log(enabled: bool | None = None, every: int | None = None) -> None:
    """Apply plugin-config overrides and invalidate old-policy rollups."""
    global _current_cache_log_enabled, _current_cache_log_every

    next_enabled = _current_cache_log_enabled if enabled is None else bool(enabled)
    next_every = _current_cache_log_every
    if every is not None:
        parsed = int(every)
        if parsed > 0:
            next_every = parsed

    changed = (
        next_enabled != _current_cache_log_enabled
        or next_every != _current_cache_log_every
    )
    _current_cache_log_enabled = next_enabled
    _current_cache_log_every = next_every
    if changed:
        _accumulator.reset()


def cache_log_enabled() -> bool:
    return _current_cache_log_enabled


def cache_log_every() -> int:
    return _current_cache_log_every


def cache_log_settings() -> tuple[bool, int]:
    return _current_cache_log_enabled, _current_cache_log_every


def log_cache_usage(
    *,
    channel: str,
    model: str,
    prompt_tokens: int,
    cached_tokens: int,
    completion_tokens: int,
    reasoning_tokens: int = 0,
    ms: int = 0,
) -> None:
    """Log one completion and a per-channel/model rolling summary."""
    if not _current_cache_log_enabled:
        return

    prompt_tokens = int(prompt_tokens or 0)
    cached_tokens = int(cached_tokens or 0)
    completion_tokens = int(completion_tokens or 0)
    reasoning_tokens = int(reasoning_tokens or 0)
    ms = int(ms or 0)
    uncached = max(prompt_tokens - cached_tokens, 0)
    ratio = cached_tokens / prompt_tokens * 100.0 if prompt_tokens > 0 else 0.0

    logger.info(
        "[VolcengineCache] channel=%s model=%s in=%d cached=%d (%.1f%%) "
        "uncached=%d out=%d rsn=%d ms=%d",
        channel,
        model,
        prompt_tokens,
        cached_tokens,
        ratio,
        uncached,
        completion_tokens,
        reasoning_tokens,
        ms,
    )

    snapshot = _accumulator.note(
        (str(channel), str(model)),
        in_tokens=prompt_tokens,
        cached_tokens=cached_tokens,
        out_tokens=completion_tokens,
        ms=ms,
        every=_current_cache_log_every,
    )
    if snapshot is None:
        return

    count, total_in, total_cached, total_out, total_ms = snapshot
    sum_ratio = total_cached / total_in * 100.0 if total_in > 0 else 0.0
    logger.info(
        "[VolcengineCache:SUM] channel=%s model=%s calls=%d in=%d "
        "cached=%d (%.1f%%) out=%d ms=%d",
        channel,
        model,
        count,
        total_in,
        total_cached,
        sum_ratio,
        total_out,
        total_ms,
    )


def _error_text_candidates(error: Exception) -> list[str]:
    candidates: list[str] = [str(error)]

    body = getattr(error, "body", None)
    if isinstance(body, dict):
        try:
            candidates.append(json.dumps(body, ensure_ascii=False, default=str))
        except Exception:
            pass
        nested = body.get("error")
        if isinstance(nested, dict):
            for key in ("message", "type", "code", "param"):
                value = nested.get(key)
                if value is not None:
                    candidates.append(str(value))
    elif isinstance(body, str):
        candidates.append(body)

    response = getattr(error, "response", None)
    text = getattr(response, "text", None) if response is not None else None
    if isinstance(text, str):
        candidates.append(text)

    return candidates


def is_context_length_error(error: Exception) -> bool:
    """Return whether an exception resembles an upstream context rejection."""
    lowered = "\n".join(_error_text_candidates(error)).lower()
    return any(
        marker in lowered
        for marker in (
            "context length",
            "maximum context",
            "context_length",
            "context window",
            "token limit",
            "too many tokens",
            "max context",
        )
    )


def channel_name(api_base: str) -> str:
    """Derive ``v3`` or ``plan/v3`` from a fixed Ark endpoint."""
    base = str(api_base or "").strip().rstrip("/")
    marker = "/api/"
    if marker in base:
        return base.split(marker, 1)[1]
    return base.rsplit("/", 1)[-1] or "unknown"
