"""Single-use Source-scoped feedback handoff for model discovery.

This module is deliberately *not* a capability cache.  Ordinary Ark ``/models``
feedback exists only to bridge one live ``get_models()`` receipt into the
Dashboard response that immediately consumes it.

Missing fields mean "not reported".  Stored entries have no authority beyond
that one handoff and must never become routing state, model truth, or history.
"""

from __future__ import annotations

import copy
from typing import Any

# A tiny in-process mailbox between Provider.get_models() and AstrBot's
# list_provider_source_models() service call.  Entries are cleared before a new
# upstream request and consumed (removed) by the Dashboard bridge.
_SOURCE_MODEL_HINTS: dict[tuple[str, str], dict[str, Any]] = {}


def clear_source_model_hints(source_id: str) -> None:
    """Discard every unconsumed receipt for one Source."""

    if not source_id:
        return
    for key in [key for key in _SOURCE_MODEL_HINTS if key[0] == source_id]:
        _SOURCE_MODEL_HINTS.pop(key, None)


def remember_source_model_hint(
    source_id: str,
    model_id: str,
    metadata: dict[str, Any],
) -> None:
    """Place one current-receipt feedback fragment into the handoff mailbox."""

    if source_id and model_id:
        _SOURCE_MODEL_HINTS[(source_id, model_id)] = copy.deepcopy(metadata)


def consume_source_model_hints(
    source_id: str,
    model_ids: list[str] | None = None,
) -> dict[str, dict[str, Any]]:
    """Return current feedback once, then erase the whole Source mailbox.

    ``model_ids`` only filters what is returned; all entries for ``source_id``
    are removed so an unrequested model from this receipt cannot leak into a
    later Dashboard request.
    """

    allowed = set(model_ids) if model_ids is not None else None
    result: dict[str, dict[str, Any]] = {}
    keys = [key for key in _SOURCE_MODEL_HINTS if key[0] == source_id]
    for key in keys:
        _, model_id = key
        metadata = _SOURCE_MODEL_HINTS.pop(key, None)
        if metadata is None:
            continue
        if allowed is not None and model_id not in allowed:
            continue
        result[model_id] = copy.deepcopy(metadata)
    return result
