"""Cache observability for Volcengine Ark providers.

After each completion the provider can log the upstream usage counters exposed
by Ark, including cached and uncached prompt tokens. Context-length failures
are only identified for diagnostics; retry and conversation-history recovery
remain owned by AstrBot.
"""

from __future__ import annotations

import threading

from astrbot import logger

DEFAULT_CACHE_LOG_ENABLED = True
DEFAULT_CACHE_LOG_EVERY = 10


class _CacheAccumulator:
    """Rolling counter for the periodic ``[VolcengineCache:SUM]`` line."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.count = 0
        self.total_in = 0
        self.total_cached = 0
        self.total_out = 0

    def note(self, in_tokens: int, cached_tokens: int, out_tokens: int) -> None:
        with self._lock:
            self.count += 1
            self.total_in += in_tokens
            self.total_cached += cached_tokens
            self.total_out += out_tokens

    def snapshot(self) -> tuple[int, int, int, int]:
        with self._lock:
            return (
                self.count,
                self.total_in,
                self.total_cached,
                self.total_out,
            )

    def reset(self) -> None:
        with self._lock:
            self.count = 0
            self.total_in = 0
            self.total_cached = 0
            self.total_out = 0


_accumulator = _CacheAccumulator()

_current_cache_log_enabled = DEFAULT_CACHE_LOG_ENABLED
_current_cache_log_every = DEFAULT_CACHE_LOG_EVERY


def configure_cache_log(enabled: bool | None = None, every: int | None = None) -> None:
    """Apply plugin-config overrides from the plugin entrypoint."""
    global _current_cache_log_enabled, _current_cache_log_every
    if enabled is not None:
        _current_cache_log_enabled = bool(enabled)
    if every is not None and int(every) > 0:
        _current_cache_log_every = int(every)


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
) -> None:
    """Log one completion's upstream cache-hit counters."""
    if not _current_cache_log_enabled:
        return
    prompt_tokens = int(prompt_tokens or 0)
    cached_tokens = int(cached_tokens or 0)
    completion_tokens = int(completion_tokens or 0)
    reasoning_tokens = int(reasoning_tokens or 0)
    uncached = max(prompt_tokens - cached_tokens, 0)
    ratio = (cached_tokens / prompt_tokens * 100.0) if prompt_tokens > 0 else 0.0

    logger.info(
        "[VolcengineCache] channel=%s model=%s in=%d cached=%d (%.1f%%) "
        "uncached=%d out=%d rsn=%d",
        channel,
        model,
        prompt_tokens,
        cached_tokens,
        ratio,
        uncached,
        completion_tokens,
        reasoning_tokens,
    )

    _accumulator.note(prompt_tokens, cached_tokens, completion_tokens)
    count, total_in, total_cached, total_out = _accumulator.snapshot()
    if count >= _current_cache_log_every:
        sum_ratio = (total_cached / total_in * 100.0) if total_in > 0 else 0.0
        logger.info(
            "[VolcengineCache:SUM] calls=%d in=%d cached=%d (%.1f%%) out=%d",
            count,
            total_in,
            total_cached,
            sum_ratio,
            total_out,
        )
        _accumulator.reset()


def is_context_length_error(error: Exception) -> bool:
    """True when an error looks like a context-length rejection."""
    lowered = str(error).lower()
    return (
        "context length" in lowered
        or "maximum context" in lowered
        or "context_length" in lowered
        or "token limit" in lowered
        or "context window" in lowered
    )


def channel_name(api_base: str) -> str:
    """Derive a short channel label from a fixed Ark endpoint."""
    base = str(api_base or "").strip().rstrip("/")
    marker = "/api/"
    if marker in base:
        return base.split(marker, 1)[1]
    return base.rsplit("/", 1)[-1] or "unknown"
