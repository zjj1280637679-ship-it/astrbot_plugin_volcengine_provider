"""Translate ordinary Ark /models receipts into AstrBot model facts."""

from __future__ import annotations

from typing import Any

from .common import _dedupe_nonempty, _publish_metadata


def _as_mapping(value: object) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump()
        return dumped if isinstance(dumped, dict) else {}
    return {}


def _positive_int(value: object) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 0
    return parsed if parsed > 0 else 0


def _feature_flag(value: object) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, dict):
        for name in ("supported", "enabled", "available", "function_calling"):
            if isinstance(value.get(name), bool):
                return value[name]
    return None


def _normalized_modalities(values: object) -> list[str]:
    if not isinstance(values, (list, tuple)):
        return []
    allowed = {"text", "image", "audio", "video"}
    return [value for value in _dedupe_nonempty(values) if value in allowed]



def publish_ark_model_metadata(model: object) -> str:
    """Translate ordinary Ark model facts using conservative card defaults.

    AstrBot treats a missing metadata entry as a legacy provider and enables
    image, audio and tool use by default.  That is unsafe for Ark's mixed model
    catalogue: some entries omit capability fields entirely, and the absence of
    a field is not evidence that every optional input is accepted.  Publish an
    entry for every returned model, always keep text available, and add optional
    capabilities only when this specific ``/models`` receipt says so.

    The result is only a default for a newly-created model card.  Users remain
    free to edit ``modalities`` afterwards; request-time handling continues to
    respect the saved card without a second capability policy here.
    """

    data = _as_mapping(model)
    model_id = str(data.get("id") or getattr(model, "id", "") or "").strip()
    if not model_id:
        return ""

    modalities = _as_mapping(data.get("modalities"))
    input_modalities = _dedupe_nonempty(
        ["text", *_normalized_modalities(modalities.get("input_modalities"))]
    )
    output_modalities = _normalized_modalities(modalities.get("output_modalities"))

    limits = _as_mapping(data.get("token_limits"))
    context_limit = _positive_int(limits.get("context_window"))
    output_limit = _positive_int(limits.get("max_output_token_length"))
    reasoning_limit = _positive_int(limits.get("max_reasoning_token_length"))

    features = _as_mapping(data.get("features"))
    tools = _as_mapping(features.get("tools"))
    tool_call = _feature_flag(tools.get("function_calling"))
    if tool_call is None:
        tool_call = _feature_flag(features.get("function_calling"))
    reasoning = _feature_flag(features.get("reasoning"))
    if reasoning is None and "max_reasoning_token_length" in limits:
        reasoning = reasoning_limit > 0

    _publish_metadata(
        model_id,
        {
            "reasoning": False if reasoning is None else reasoning,
            "tool_call": False if tool_call is None else tool_call,
            "modalities": {
                "input": input_modalities,
                "output": output_modalities,
            },
            "limit": {
                "context": context_limit,
                "output": output_limit,
            },
        },
    )
    return model_id



