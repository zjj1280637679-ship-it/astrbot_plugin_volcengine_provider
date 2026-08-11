"""Per-model-card Volcengine adapter settings and legacy migration.

This module never infers model capabilities. The video flag is only a
request-transport setting. AstrBot native capability feedback such as
``modalities`` remains host-owned and is never rewritten here.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

ARK_PROVIDER_TYPE = "volcengine_ark_chat_completion"
AGENT_PLAN_PROVIDER_TYPE = "volcengine_agent_plan_chat_completion"
OWNED_SOURCE_TYPES = frozenset({ARK_PROVIDER_TYPE, AGENT_PLAN_PROVIDER_TYPE})

VIDEO_INPUT_ENABLED_KEY = "volcengine_video_input_enabled"
LEGACY_MODEL_VIDEO_INPUT_KEY = "volcengine_model_video_input"
LEGACY_SOURCE_VIDEO_KEYS = {
    ARK_PROVIDER_TYPE: "volcengine_ark_video_input",
    AGENT_PLAN_PROVIDER_TYPE: "volcengine_agent_plan_video_input",
}


def source_scope_id(provider_config: Mapping[str, Any]) -> str:
    return str(
        provider_config.get("provider_source_id")
        or provider_config.get("id")
        or ""
    ).strip()


def video_input_enabled(provider_config: Mapping[str, Any]) -> bool:
    """Return the current card's video transport setting.

    Missing is the transport default (disabled), not a negative model
    capability claim. Users can enable the channel per model card;
    upstream accept/reject remains runtime feedback.
    """

    explicit = provider_config.get(VIDEO_INPUT_ENABLED_KEY)
    if isinstance(explicit, bool):
        return explicit
    legacy = provider_config.get(LEGACY_MODEL_VIDEO_INPUT_KEY)
    if isinstance(legacy, bool):
        return legacy
    return False


def source_types(config: Mapping[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    sources = config.get("provider_sources", [])
    if not isinstance(sources, list):
        return result
    for source in sources:
        if not isinstance(source, dict):
            continue
        source_id = str(source.get("id") or "").strip()
        if source_id:
            result[source_id] = str(source.get("type") or "").strip()
    return result


def owned_source_type_for_card(
    provider_config: Mapping[str, Any],
    provider_sources: list[dict[str, Any]] | object,
) -> str:
    source_id = str(provider_config.get("provider_source_id") or "").strip()
    if not source_id or not isinstance(provider_sources, list):
        return ""
    for source in provider_sources:
        if not isinstance(source, dict):
            continue
        if str(source.get("id") or "").strip() != source_id:
            continue
        source_type = str(source.get("type") or "").strip()
        return source_type if source_type in OWNED_SOURCE_TYPES else ""
    return ""


def normalize_owned_model_card_for_save(
    provider_config: dict[str, Any],
    provider_sources: list[dict[str, Any]] | object,
    *,
    default_enabled: bool | None = None,
) -> dict[str, Any]:
    """Normalize only plugin-owned transport keys on one owned card."""

    if not owned_source_type_for_card(provider_config, provider_sources):
        return provider_config

    explicit = provider_config.get(VIDEO_INPUT_ENABLED_KEY)
    legacy = provider_config.get(LEGACY_MODEL_VIDEO_INPUT_KEY)
    if not isinstance(explicit, bool):
        if isinstance(legacy, bool):
            provider_config[VIDEO_INPUT_ENABLED_KEY] = legacy
        elif isinstance(default_enabled, bool):
            provider_config[VIDEO_INPUT_ENABLED_KEY] = default_enabled
    provider_config.pop(LEGACY_MODEL_VIDEO_INPUT_KEY, None)
    return provider_config


def migrate_legacy_video_settings(config: dict[str, Any]) -> list[str]:
    """Migrate pre-0.1.15 plugin video settings without touching modalities.

    Migration preserves the old resolver's precedence exactly:

    1. already-saved 0.1.15 per-card transport setting;
    2. older per-card plugin setting;
    3. older explicit Provider Source boolean (``True`` *or* ``False``);
    4. historical ``video`` entry in AstrBot ``modalities`` as a final clue.

    The ``modalities`` field itself remains host-owned and is never rewritten.
    """

    sources = config.get("provider_sources", [])
    providers = config.get("provider", [])
    if not isinstance(sources, list) or not isinstance(providers, list):
        return []

    types = source_types(config)
    legacy_defaults: dict[str, bool] = {}
    source_changed = False
    for source in sources:
        if not isinstance(source, dict):
            continue
        source_id = str(source.get("id") or "").strip()
        legacy_key = LEGACY_SOURCE_VIDEO_KEYS.get(types.get(source_id, ""))
        if not source_id or not legacy_key:
            continue
        value = source.pop(legacy_key, None)
        if isinstance(value, bool):
            legacy_defaults[source_id] = value
            source_changed = True

    changed_ids: list[str] = []
    for provider in providers:
        if not isinstance(provider, dict):
            continue
        source_id = str(provider.get("provider_source_id") or "").strip()
        if types.get(source_id) not in OWNED_SOURCE_TYPES:
            continue

        before = dict(provider)
        explicit = provider.get(VIDEO_INPUT_ENABLED_KEY)
        legacy_model = provider.get(LEGACY_MODEL_VIDEO_INPUT_KEY)
        modalities = provider.get("modalities")

        if not isinstance(explicit, bool):
            if isinstance(legacy_model, bool):
                provider[VIDEO_INPUT_ENABLED_KEY] = legacy_model
            elif source_id in legacy_defaults:
                # Preserve the old Source-level user's explicit choice before
                # consulting the still older modalities encoding. Membership,
                # not truthiness, matters here: an explicit False is data.
                provider[VIDEO_INPUT_ENABLED_KEY] = legacy_defaults[source_id]
            elif isinstance(modalities, list) and "video" in modalities:
                # Known historical encoding used by this plugin only.
                provider[VIDEO_INPUT_ENABLED_KEY] = True

        provider.pop(LEGACY_MODEL_VIDEO_INPUT_KEY, None)
        if provider != before:
            provider_id = str(provider.get("id") or "").strip()
            if provider_id:
                changed_ids.append(provider_id)

    if source_changed and not changed_ids:
        changed_ids.append("")
    return changed_ids
