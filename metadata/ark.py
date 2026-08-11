"""Normalize ordinary Ark `/models` receipts into sparse feedback."""

from __future__ import annotations

from typing import Any


def _dedupe_nonempty(values: object) -> list[str]:
    if not isinstance(values, (list, tuple)):
        return []
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


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
    """Preserve every non-empty upstream modality token from this receipt.

    AstrBot 4.26/4.27 currently acts only on the modality names it understands.
    Filtering here would let today's adapter vocabulary delete information from
    a future Ark/AstrBot vocabulary, so normalization only deduplicates/cleans
    strings and leaves interpretation to the current host/UI.
    """

    return _dedupe_nonempty(values)


def normalize_ark_model_metadata(model: object) -> tuple[str, dict[str, Any]]:
    """Return only information explicitly present in this live receipt.

    Presence and truthiness are deliberately separate. An explicitly returned
    empty modality list is still current feedback and must not be collapsed into
    "field missing", otherwise a stale display value could survive a newer
    receipt. Unknown/future modality tokens are retained rather than interpreted
    or discarded. This remains feedback, not a model-capability truth claim.
    """

    data = _as_mapping(model)
    model_id = str(data.get("id") or getattr(model, "id", "") or "").strip()
    if not model_id:
        return "", {}

    hint: dict[str, Any] = {"id": model_id}
    modalities = _as_mapping(data.get("modalities"))
    raw_input = modalities.get("input_modalities")
    raw_output = modalities.get("output_modalities")
    has_input = "input_modalities" in modalities and isinstance(raw_input, (list, tuple))
    has_output = "output_modalities" in modalities and isinstance(raw_output, (list, tuple))
    if has_input or has_output:
        hint["modalities"] = {}
        if has_input:
            hint["modalities"]["input"] = _normalized_modalities(raw_input)
        if has_output:
            hint["modalities"]["output"] = _normalized_modalities(raw_output)

    limits = _as_mapping(data.get("token_limits"))
    context = _positive_int(limits.get("context_window"))
    output = _positive_int(limits.get("max_output_token_length"))
    if context or output:
        hint["limit"] = {}
        if context:
            hint["limit"]["context"] = context
        if output:
            hint["limit"]["output"] = output

    features = _as_mapping(data.get("features"))
    tools = _as_mapping(features.get("tools"))
    tool_call = _feature_flag(tools.get("function_calling"))
    if tool_call is None:
        tool_call = _feature_flag(features.get("function_calling"))
    if tool_call is not None:
        hint["tool_call"] = tool_call

    reasoning = _feature_flag(features.get("reasoning"))
    if reasoning is not None:
        hint["reasoning"] = reasoning

    return model_id, hint
