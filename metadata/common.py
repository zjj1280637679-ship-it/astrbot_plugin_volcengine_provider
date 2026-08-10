"""Shared helpers for publishing facts into AstrBot metadata."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from astrbot.core.utils.llm_metadata import LLM_METADATAS


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



