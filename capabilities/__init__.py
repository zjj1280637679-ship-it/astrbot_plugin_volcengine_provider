"""Stable entry point for Volcengine model-card settings and feedback."""

from .model_scope import (
    AGENT_PLAN_PROVIDER_TYPE,
    ARK_PROVIDER_TYPE,
    LEGACY_MODEL_VIDEO_INPUT_KEY,
    LEGACY_SOURCE_VIDEO_KEYS,
    OWNED_SOURCE_TYPES,
    VIDEO_INPUT_ENABLED_KEY,
    migrate_legacy_video_settings,
    normalize_owned_model_card_for_save,
    owned_source_type_for_card,
    source_scope_id,
    source_types,
    video_input_enabled,
)
from .source_hints import (
    clear_source_model_hints,
    consume_source_model_hints,
    remember_source_model_hint,
)
from .source_migration import cleanup_owned_settings_on_source_change

__all__ = [
    "AGENT_PLAN_PROVIDER_TYPE",
    "ARK_PROVIDER_TYPE",
    "LEGACY_MODEL_VIDEO_INPUT_KEY",
    "LEGACY_SOURCE_VIDEO_KEYS",
    "OWNED_SOURCE_TYPES",
    "VIDEO_INPUT_ENABLED_KEY",
    "cleanup_owned_settings_on_source_change",
    "clear_source_model_hints",
    "consume_source_model_hints",
    "migrate_legacy_video_settings",
    "normalize_owned_model_card_for_save",
    "owned_source_type_for_card",
    "remember_source_model_hint",
    "source_scope_id",
    "source_types",
    "video_input_enabled",
]
