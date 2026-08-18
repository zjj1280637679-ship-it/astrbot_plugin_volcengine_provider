"""Cache insight and context-limit governance for Volcengine Ark providers.

This module is the plugin-owned home for two behaviours that were previously
scattered as standalone debugging scripts:

1. **Cache hit observability** — after every chat completion the provider logs
   ``[VolcengineCache]`` with the input/cached/uncached/output token counts and
   the hit ratio, plus a rolling ``[VolcengineCache:SUM]`` every N calls.  This
   is the Volcengine equivalent of DeepSeek Harness' cache-hit diagnostics: it
   makes it possible to verify that a stable request prefix (same model, same
   channel, stable conversation head) is actually being billed as cache hits.

2. **Context limit governance** — the Ark endpoints accept much larger
   contexts than AstrBot's conservative defaults.  When a request fails with a
   context-length error we raise the effective ceiling to the known per-model
   capacity instead of popping records blindly, so long conversations keep
   their prefix stable (which is also what keeps cache hits high).

Both are configurable through ``_conf_schema.json`` and live inside the plugin
instead of as unmanaged scripts.
"""

from __future__ import annotations

import threading
import time

from astrbot import logger

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DEFAULT_CACHE_LOG_ENABLED = True
DEFAULT_CACHE_LOG_EVERY = 10

# ---------------------------------------------------------------------------
# Per-model context ceilings (tokens).  These are the capacities the Ark
# billing channels actually accept; AstrBot's default max_tokens can be much
# lower and would truncate long conversations.
# ---------------------------------------------------------------------------

# deepseek-v4 / deepseek-v4-pro / deepseek-v4-flash -> 1M context
_CONTEXT_1M_PREFIXES = (
    "deepseek-v4",
    "glm-5",
    "glm-4",
)
# doubao / kimi / minimax family -> 256K context
_CONTEXT_256K_PREFIXES = (
    "doubao",
    "kimi",
    "minimax",
)

_DEFAULT_CONTEXT_LIMIT = 262144


def resolve_context_limit(model: str) -> int:
    """Return the known context ceiling for an Ark model id."""
    name = str(model or "").strip()
    lowered = name.lower()
    for prefix in _CONTEXT_1M_PREFIXES:
        if lowered.startswith(prefix):
            return 1048576
    for prefix in _CONTEXT_256K_PREFIXES:
        if lowered.startswith(prefix):
            return 262144
    return _DEFAULT_CONTEXT_LIMIT


def downgrade_context_limit(current_limit: int) -> int:
    """Halve an unknown/unverified ceiling on a context-length error.

    Used only when the model is not in the known table and the request still
    exceeds the guessed ceiling.
    """
    if current_limit <= 0:
        return _DEFAULT_CONTEXT_LIMIT
    return max(current_limit // 2, 65536)


# ---------------------------------------------------------------------------
# Cache-hit logging
# ---------------------------------------------------------------------------

class _CacheAccumulator:
    """Rolling counter for the periodic ``[VolcengineCache:SUM]`` line."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.count = 0
        self.total_in = 0
        self.total_cached = 0
        self.total_out = 0
        self.total_ms = 0

    def note(self, in_tokens: int, cached_tokens: int, out_tokens: int, ms: int) -> None:
        with self._lock:
            self.count += 1
            self.total_in += in_tokens
            self.total_cached += cached_tokens
            self.total_out += out_tokens
            self.total_ms += ms

    def snapshot(self) -> tuple[int, int, int, int, int]:
        with self._lock:
            return (
                self.count,
                self.total_in,
                self.total_cached,
                self.total_out,
                self.total_ms,
            )

    def reset(self) -> None:
        with self._lock:
            self.count = 0
            self.total_in = 0
            self.total_cached = 0
            self.total_out = 0
            self.total_ms = 0


_accumulator = _CacheAccumulator()

_current_cache_log_enabled = DEFAULT_CACHE_LOG_ENABLED
_current_cache_log_every = DEFAULT_CACHE_LOG_EVERY


def configure_cache_log(enabled: bool | None = None, every: int | None = None) -> None:
    """Apply plugin-config overrides (called from the plugin entrypoint)."""
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
    ms: int = 0,
) -> None:
    """Log one completion's cache-hit breakdown.

    Mirrors the format that was validated against live Ark responses:
    ``[VolcengineCache] channel=%s model=%s in=%d cached=%d (%.1f%%) uncached=%d
    out=%d rsn=%d ms=%d`` plus a rolling sum every N calls.
    """
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

    _accumulator.note(prompt_tokens, cached_tokens, completion_tokens, ms)
    count, total_in, total_cached, total_out, total_ms = _accumulator.snapshot()
    if count >= _current_cache_log_every:
        sum_ratio = (total_cached / total_in * 100.0) if total_in > 0 else 0.0
        logger.info(
            "[VolcengineCache:SUM] calls=%d in=%d cached=%d (%.1f%%) "
            "out=%d ms=%d",
            count,
            total_in,
            total_cached,
            sum_ratio,
            total_out,
            total_ms,
        )
        _accumulator.reset()


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def is_context_length_error(error: Exception) -> bool:
    """True when the error looks like a context-length rejection."""
    text = str(error)
    lowered = text.lower()
    return (
        "context length" in lowered
        or "maximum context" in lowered
        or "context_length" in lowered
        or "token limit" in lowered
        or "context window" in lowered
    )


def channel_name(api_base: str) -> str:
    """Derive a short channel label from the fixed Ark endpoint.

    ``https://ark.cn-beijing.volces.com/api/v3`` -> ``v3``
    ``https://ark.cn-beijing.volces.com/api/plan/v3`` -> ``plan/v3``
    """
    base = str(api_base or "").strip().rstrip("/")
    marker = "/api/"
    if marker in base:
        return base.split(marker, 1)[1]
    return base.rsplit("/", 1)[-1] or "unknown"
