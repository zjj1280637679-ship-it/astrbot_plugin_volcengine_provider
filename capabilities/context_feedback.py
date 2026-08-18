"""Feedback-driven context governance for one live Volcengine Provider instance.

This module deliberately separates *identity* from *evidence*.

- Model names/aliases may be logged by callers, but they are never used to infer
  a context limit here.
- Pre-feedback is the explicit positive ``max_context_tokens`` value already on
  the live Provider card/host object before a request. That value may have come
  from a live Ark ``/models`` receipt, user configuration, AstrBot metadata, or
  AstrBot's own fallback; this module does not guess which model family produced it.
- Post-feedback is evidence from the request that actually reached upstream.
  A successful request proves only a lower bound. A context rejection may revise
  the next request's guard only when upstream explicitly reports a context ceiling.
- Learned post-feedback is scoped to the current Provider *instance*. Reloading
  the Provider, replacing the plugin, or restarting AstrBot creates a fresh loop
  from new pre-feedback instead of inheriting the old observation.

AstrBot's current ``ContextManager`` snapshots ``provider_config.max_context_tokens``
before the network call. Therefore a post-feedback revision naturally affects the
next request, while AstrBot's native retry path remains responsible for the current
failed request.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from astrbot import logger

from .cache_insight import configured_context_limit

_CONTEXT_LIMIT_KEYS = frozenset(
    {
        "context_window",
        "context_window_tokens",
        "max_context_length",
        "maximum_context_length",
        "max_context_window",
        "maximum_context_window",
        "context_limit",
        "context_token_limit",
        "max_context_tokens",
        "maximum_context_tokens",
        "max_model_len",
    }
)

_CONTEXT_LIMIT_PATTERNS = (
    re.compile(
        r"(?:maximum|max)\s+(?:model\s+)?context(?:\s+(?:length|window|tokens?))?"
        r"\s*(?:is|=|:|of)?\s*([0-9][0-9_,]*(?:\.[0-9]+)?\s*[kKmM]?)"
    ),
    re.compile(
        r"context\s+window\s*(?:is|=|:|of)?\s*"
        r"([0-9][0-9_,]*(?:\.[0-9]+)?\s*[kKmM]?)\s*tokens?"
    ),
)


def _positive_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    if isinstance(value, float):
        if value.is_integer() and value > 0:
            return int(value)
        return None
    if not isinstance(value, str):
        return None
    text = value.strip().replace(",", "").replace("_", "")
    if not text:
        return None
    multiplier = 1
    suffix = text[-1:].lower()
    if suffix in {"k", "m"}:
        multiplier = 1_000 if suffix == "k" else 1_000_000
        text = text[:-1].strip()
    try:
        numeric = float(text)
    except ValueError:
        return None
    result = int(numeric * multiplier)
    if result <= 0 or abs(result - numeric * multiplier) > 1e-9:
        return None
    return result


def _as_mapping(value: object) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        try:
            dumped = model_dump()
        except Exception:
            return {}
        return dumped if isinstance(dumped, dict) else {}
    return {}


def _structured_context_limits(value: object, *, depth: int = 0) -> list[int]:
    """Collect explicitly named context ceilings from a bounded structured body."""
    if depth > 5:
        return []
    if isinstance(value, (list, tuple)):
        result: list[int] = []
        for item in value[:32]:
            result.extend(_structured_context_limits(item, depth=depth + 1))
        return result

    mapping = _as_mapping(value)
    if not mapping:
        return []

    result: list[int] = []
    for key, item in list(mapping.items())[:64]:
        normalized_key = str(key or "").strip().lower().replace("-", "_")
        if normalized_key in _CONTEXT_LIMIT_KEYS:
            parsed = _positive_int(item)
            if parsed is not None:
                result.append(parsed)
        if isinstance(item, (dict, list, tuple)) or callable(
            getattr(item, "model_dump", None)
        ):
            result.extend(_structured_context_limits(item, depth=depth + 1))
    return result


def _error_text_candidates(error: Exception) -> list[str]:
    candidates: list[str] = []

    def append(value: object) -> None:
        if value is None:
            return
        text = str(value).strip()
        if text and text not in candidates:
            candidates.append(text[:8192])

    append(error)
    body = getattr(error, "body", None)
    if isinstance(body, dict):
        try:
            append(json.dumps(body, ensure_ascii=False, default=str))
        except Exception:
            pass
        nested = body.get("error")
        if isinstance(nested, dict):
            for key in ("message", "type", "code", "param"):
                append(nested.get(key))
    else:
        append(body)

    response = getattr(error, "response", None)
    if response is not None:
        append(getattr(response, "text", None))
    return candidates


def extract_reported_context_limit(error: Exception) -> int | None:
    """Return an explicit upstream context ceiling, never a model-name guess.

    When several explicit candidates exist, choose the smallest positive value.
    Contradictory upstream fields therefore fail conservatively rather than
    granting a larger context window.
    """
    limits: list[int] = []
    limits.extend(_structured_context_limits(getattr(error, "body", None)))

    response = getattr(error, "response", None)
    if response is not None:
        json_loader = getattr(response, "json", None)
        if callable(json_loader):
            try:
                response_json = json_loader()
            except Exception:
                response_json = None
            limits.extend(_structured_context_limits(response_json))

    for text in _error_text_candidates(error):
        lowered = text.lower()
        for pattern in _CONTEXT_LIMIT_PATTERNS:
            for match in pattern.finditer(lowered):
                parsed = _positive_int(match.group(1).replace(" ", ""))
                if parsed is not None:
                    limits.append(parsed)

    return min(limits) if limits else None


def requested_output_reserve(
    payloads: dict[str, Any] | object,
    provider_config: dict[str, Any] | object | None = None,
) -> int:
    """Return only explicitly requested output-token reservations.

    Evidence can come from the OpenAI payload, ``extra_body``, the user's
    ``custom_extra_body`` or this plugin's explicit horizontal
    ``volcengine_max_output_tokens`` field. The latter outranks custom extra-body
    at request construction time, but choosing the largest explicit value here is
    deliberately conservative when multiple compatible fields are present.

    An absent value is never guessed: zero means "no explicit reserve evidence".
    """
    candidates: list[int] = []

    def inspect_container(container: object) -> None:
        if not isinstance(container, dict):
            return
        for key in ("max_completion_tokens", "max_tokens"):
            parsed = _positive_int(container.get(key))
            if parsed is not None:
                candidates.append(parsed)

    if isinstance(payloads, dict):
        inspect_container(payloads)
        inspect_container(payloads.get("extra_body"))

    if isinstance(provider_config, dict):
        inspect_container(provider_config.get("custom_extra_body"))
        explicit_plugin_value = _positive_int(
            provider_config.get("volcengine_max_output_tokens")
        )
        if explicit_plugin_value is not None:
            candidates.append(explicit_plugin_value)

    return max(candidates) if candidates else 0


def context_guard_from_feedback(
    reported_context_limit: int,
    *,
    output_reserve: int = 0,
) -> int | None:
    """Translate a total-window ceiling into AstrBot's input-history guard.

    If the request explicitly reserved output tokens, leave those tokens outside
    the history guard. If no output reservation was explicit, keep the reported
    ceiling unchanged rather than inventing a reserve.
    """
    reported = _positive_int(reported_context_limit)
    reserve = _positive_int(output_reserve) or 0
    if reported is None or reserve >= reported:
        return None
    return reported - reserve


@dataclass(frozen=True, slots=True)
class ContextFeedbackSnapshot:
    phase: str
    guard: int | None
    source: str
    reported_context_limit: int | None = None
    output_reserve: int = 0
    accepted_input_high_water: int = 0
    accepted_total_high_water: int = 0


class ContextFeedbackLoop:
    """Per-Provider feedback loop: pre-feedback -> request -> post-feedback."""

    def __init__(self, provider_config: dict[str, Any] | object) -> None:
        initial = configured_context_limit(provider_config)
        self._active_guard = initial
        self._active_source = "pre_feedback" if initial is not None else "unreported"
        self._last_reported_context_limit: int | None = None
        self._accepted_input_high_water = 0
        self._accepted_total_high_water = 0

    def pre_request(
        self,
        provider_config: dict[str, Any],
        *,
        provider_id: str = "",
    ) -> ContextFeedbackSnapshot:
        """Re-confirm the guard immediately before the network request.

        A newer host/model-card value wins if it differs from our current
        post-feedback value. Otherwise the learned post-feedback remains the
        current runtime pre-feedback until this Provider instance is rebuilt or
        contradicted by another explicit upstream ceiling.
        """
        current = configured_context_limit(provider_config)
        if current != self._active_guard:
            self._active_guard = current
            self._active_source = "pre_feedback" if current is not None else "unreported"
            self._last_reported_context_limit = None

        logger.info(
            "[VolcengineContext:PRE] provider=%s guard=%s source=%s "
            "accepted_in_high=%d accepted_total_high=%d",
            provider_id or str(provider_config.get("id") or ""),
            self._active_guard if self._active_guard is not None else "unreported",
            self._active_source,
            self._accepted_input_high_water,
            self._accepted_total_high_water,
        )
        return ContextFeedbackSnapshot(
            phase="pre",
            guard=self._active_guard,
            source=self._active_source,
            reported_context_limit=self._last_reported_context_limit,
            accepted_input_high_water=self._accepted_input_high_water,
            accepted_total_high_water=self._accepted_total_high_water,
        )

    def post_success(
        self,
        *,
        prompt_tokens: int,
        completion_tokens: int,
        provider_id: str = "",
    ) -> ContextFeedbackSnapshot:
        """Record an accepted lower bound without pretending it is the ceiling."""
        prompt = max(int(prompt_tokens or 0), 0)
        completion = max(int(completion_tokens or 0), 0)
        total = prompt + completion
        self._accepted_input_high_water = max(self._accepted_input_high_water, prompt)
        self._accepted_total_high_water = max(self._accepted_total_high_water, total)
        logger.info(
            "[VolcengineContext:POST] provider=%s kind=accepted in=%d out=%d "
            "accepted_total_high=%d guard=%s source=%s",
            provider_id,
            prompt,
            completion,
            self._accepted_total_high_water,
            self._active_guard if self._active_guard is not None else "unreported",
            self._active_source,
        )
        return ContextFeedbackSnapshot(
            phase="post_success",
            guard=self._active_guard,
            source=self._active_source,
            reported_context_limit=self._last_reported_context_limit,
            accepted_input_high_water=self._accepted_input_high_water,
            accepted_total_high_water=self._accepted_total_high_water,
        )

    def post_context_rejection(
        self,
        provider_config: dict[str, Any],
        error: Exception,
        payloads: dict[str, Any] | object,
        *,
        provider_id: str = "",
    ) -> ContextFeedbackSnapshot:
        """Use only an explicit upstream ceiling to revise the next pre-feedback."""
        reported = extract_reported_context_limit(error)
        reserve = requested_output_reserve(payloads, provider_config)
        derived = (
            context_guard_from_feedback(reported, output_reserve=reserve)
            if reported is not None
            else None
        )

        if derived is not None:
            # Direct post-feedback is allowed to correct a stale host fallback in
            # either direction. This is the critical distinction from model-name
            # inference: the request actually reached upstream and upstream named
            # the ceiling explicitly.
            provider_config["max_context_tokens"] = derived
            self._active_guard = derived
            self._active_source = "post_feedback"
            self._last_reported_context_limit = reported

        logger.warning(
            "[VolcengineContext:POST] provider=%s kind=context_rejected "
            "reported_limit=%s output_reserve=%d next_guard=%s source=%s",
            provider_id or str(provider_config.get("id") or ""),
            reported if reported is not None else "unreported",
            reserve,
            self._active_guard if self._active_guard is not None else "unreported",
            self._active_source,
        )
        return ContextFeedbackSnapshot(
            phase="post_rejection",
            guard=self._active_guard,
            source=self._active_source,
            reported_context_limit=reported,
            output_reserve=reserve,
            accepted_input_high_water=self._accepted_input_high_water,
            accepted_total_high_water=self._accepted_total_high_water,
        )
