"""Clean only plugin-owned settings when a model card changes Source."""

from __future__ import annotations

from typing import Any

from .model_scope import (
    LEGACY_MODEL_VIDEO_INPUT_KEY,
    OWNED_SOURCE_TYPES,
    VIDEO_INPUT_ENABLED_KEY,
)


def cleanup_owned_settings_on_source_change(
    provider_config: dict[str, Any],
    *,
    old_source_type: str,
    new_source_type: str,
) -> bool:
    if (
        old_source_type not in OWNED_SOURCE_TYPES
        or new_source_type in OWNED_SOURCE_TYPES
    ):
        return False
    changed = False
    for key in (VIDEO_INPUT_ENABLED_KEY, LEGACY_MODEL_VIDEO_INPUT_KEY):
        if key in provider_config:
            provider_config.pop(key, None)
            changed = True
    # AstrBot-native feedback (including modalities) is host-owned.
    return changed
