"""Single-use Source-scoped feedback handoff for model discovery.

This module is deliberately *not* a capability cache. Ordinary Ark ``/models``
feedback exists only to bridge one live ``get_models()`` receipt into the
Dashboard response that immediately consumes it.

Missing fields mean "not reported". Stored entries have no authority beyond
that one handoff and must never become routing state, model truth, or history.
"""

from __future__ import annotations

import copy
from contextvars import ContextVar
from typing import Any

# Provider.get_models() and the Dashboard service wrapper execute in the same
# async context. A ContextVar therefore gives each concurrent request its own
# tiny mailbox without creating a process-global history store.
_SOURCE_MODEL_HINTS: ContextVar[dict[tuple[str, str], dict[str, Any]]] = ContextVar(
    "volcengine_source_model_feedback",
    default={},
)


def _snapshot() -> dict[tuple[str, str], dict[str, Any]]:
    # Never mutate the ContextVar's default/current mapping in place.
    return copy.deepcopy(_SOURCE_MODEL_HINTS.get())


def clear_source_model_hints(source_id: str) -> None:
    """Discard every unconsumed receipt for one Source in this async context."""

    if not source_id:
        return
    current = _snapshot()
    for key in [key for key in current if key[0] == source_id]:
        current.pop(key, None)
    _SOURCE_MODEL_HINTS.set(current)


def remember_source_model_hint(
    source_id: str,
    model_id: str,
    metadata: dict[str, Any],
) -> None:
    """Place one current-receipt feedback fragment into the request-local mailbox."""

    if not source_id or not model_id:
        return
    current = _snapshot()
    current[(source_id, model_id)] = copy.deepcopy(metadata)
    _SOURCE_MODEL_HINTS.set(current)


def consume_source_model_hints(
    source_id: str,
    model_ids: list[str] | None = None,
) -> dict[str, dict[str, Any]]:
    """Return current feedback once, then erase the whole Source mailbox.

    ``model_ids`` only filters what is returned; all entries for ``source_id``
    are removed so an unrequested model from this receipt cannot leak into a
    later Dashboard operation in the same task.
    """

    allowed = set(model_ids) if model_ids is not None else None
    current = _snapshot()
    result: dict[str, dict[str, Any]] = {}
    keys = [key for key in current if key[0] == source_id]
    for key in keys:
        _, model_id = key
        metadata = current.pop(key, None)
        if metadata is None:
            continue
        if allowed is not None and model_id not in allowed:
            continue
        result[model_id] = copy.deepcopy(metadata)
    _SOURCE_MODEL_HINTS.set(current)
    return result
