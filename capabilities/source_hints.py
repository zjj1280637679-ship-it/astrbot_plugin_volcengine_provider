"""Transient Source-scoped sparse feedback for model discovery.

Missing fields mean unknown, never unsupported. Feedback is scoped by
``(source_id, model_id)`` and must never become a process-global model
capability table or a routing policy.
"""

from __future__ import annotations

import copy
from typing import Any

_SOURCE_MODEL_HINTS: dict[tuple[str, str], dict[str, Any]] = {}


def clear_source_model_hints(source_id: str) -> None:
    if not source_id:
        return
    for key in [key for key in _SOURCE_MODEL_HINTS if key[0] == source_id]:
        _SOURCE_MODEL_HINTS.pop(key, None)


def remember_source_model_hint(
    source_id: str,
    model_id: str,
    metadata: dict[str, Any],
) -> None:
    if source_id and model_id:
        _SOURCE_MODEL_HINTS[(source_id, model_id)] = copy.deepcopy(metadata)


def get_source_model_hints(
    source_id: str,
    model_ids: list[str] | None = None,
) -> dict[str, dict[str, Any]]:
    allowed = set(model_ids) if model_ids is not None else None
    result: dict[str, dict[str, Any]] = {}
    for (scope, model_id), metadata in _SOURCE_MODEL_HINTS.items():
        if scope != source_id:
            continue
        if allowed is not None and model_id not in allowed:
            continue
        result[model_id] = copy.deepcopy(metadata)
    return result
