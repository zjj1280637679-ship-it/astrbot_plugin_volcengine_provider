"""Cache observability and context-limit hints for Volcengine Ark providers.

This module owns two narrow responsibilities:

1. Report upstream cache-hit accounting from ``usage.cached_tokens``.
2. Apply a model-specific ``max_context_tokens`` hint before AstrBot builds
   the main-agent context guard. Explicit user/provider values always win.

It does not rewrite chat history itself. If the upstream still rejects a
request for context length, AstrBot keeps ownership of its normal retry /
history-shrinking policy.
"""

from __future__ import annotations

import threading

from astrbot import logger

DEFAULT_CACHE_LOG_ENABLED = True
DEFAULT_CACHE_LOG_EVERY = 10

_AGENT_PLAN_PREFIX = "agentplan/"
_CONTEXT_LIMITS = (
    (("deepseek-v4", "glm-5", "glm-4"), 1_048_576),
    (("doubao", "kimi", "minimax"), 262_144),
)


def _normalize_model_name(model: object) -> str:
    name = str(model or "").strip().lower()
    if name.startswith(_AGENT_PLAN_PREFIX):
        name = name[len(_AGENT_PLAN_PREFIX) :].strip()
    return name


def resolve_context_limit(model: object) -> int | None:
    """Return a verified model-family context hint, otherwise ``None``."""
    name = _normalize_model_name(model)
    for prefixes, limit in _CONTEXT_LIMITS:
        if any(name.startswith(prefix) for prefix in prefixes):
            return limit
    return None


def apply_context_limit_hint(provider_config: dict) -> int | None:
    """Apply a known ceiling only when no positive explicit value exists.

    AstrBot's main-agent builder only injects its fallback context ceiling when
    ``provider_config['max_context_tokens'] <= 0``. Setting the known value here
    therefore changes the real guard used by AstrBot instead of merely logging
    a larger number after a failure.
    """
    raw_current = provider_config.get("max_context_tokens", 0)
    try:
        current = int(raw_current or 0)
    except (TypeError, ValueError):
        current = 0
    if current > 0:
        return current

    limit = resolve_context_limit(provider_config.get("model"))
    if limit is not None:
        provider_config["max_context_tokens"] = limit
    return limit


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


_accumulator = _CacheAccumulator()
_current_cache_log_enabled = DEFAULT_CACHE_LOG_ENABLED
_current_cache_log_every = DEFAULT_CACHE_LOG_EVERY


def configure_cache_log(enabled: bool | None = None, every: int | None = None) -> None:
    """Apply plugin-config overrides."""
    global _current_cache_log_enabled, _current_cache_log_every
    if enabled is not None:
        _current_cache_log_enabled = bool(enabled)
    if every is not None:
        parsed = int(every)
        if parsed > 0:
            _current_cache_log_every = parsed


def cache_log_enabled() -> bool:
    return _current_cache_log_enabled


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


def is_context_length_error(error: Exception) -> bool:
    """Return whether an exception resembles an upstream context rejection."""
    lowered = str(error).lower()
    return any(
        marker in lowered
        for marker in (
            "context length",
            "maximum context",
            "context_length",
            "token limit",
            "context window",
        )
    )


def channel_name(api_base: str) -> str:
    """Derive ``v3`` or ``plan/v3`` from a fixed Ark endpoint."""
    base = str(api_base or "").strip().rstrip("/")
    marker = "/api/"
    if marker in base:
        return base.split(marker, 1)[1]
    return base.rsplit("/", 1)[-1] or "unknown"
