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
VIDEO_CONTROLS_VISIBLE_KEY = "volcengine_video_controls_visible"
LEGACY_MODEL_VIDEO_INPUT_KEY = "volcengine_model_video_input"
LEGACY_MODEL_VIDEO_UI_KEY_PREFIX = "_volcengine_video_transport_ui_"
SOURCE_VIDEO_SELECTOR_UI_KEY_PREFIX = "_volcengine_video_models_ui_"
LEGACY_SOURCE_VIDEO_KEYS = {
    ARK_PROVIDER_TYPE: "volcengine_ark_video_input",
    AGENT_PLAN_PROVIDER_TYPE: "volcengine_agent_plan_video_input",
}


def legacy_model_video_ui_key(source_id: str) -> str:
    """Return the retired 0.1.17 model-dialog key for one exact Source ID."""

    return f"{LEGACY_MODEL_VIDEO_UI_KEY_PREFIX}{source_id.encode('utf-8').hex()}"


def _strip_model_card_dashboard_video_keys(provider_config: dict[str, Any]) -> bool:
    """Remove Source/presentation fields that must never persist on a model card."""

    changed = False
    for key in list(provider_config):
        if (
            key == VIDEO_CONTROLS_VISIBLE_KEY
            or key in LEGACY_SOURCE_VIDEO_KEYS.values()
            or (
                isinstance(key, str)
                and (
                    key.startswith(LEGACY_MODEL_VIDEO_UI_KEY_PREFIX)
                    or key.startswith(SOURCE_VIDEO_SELECTOR_UI_KEY_PREFIX)
                )
            )
        ):
            provider_config.pop(key, None)
            changed = True
    return changed


def source_scope_id(provider_config: Mapping[str, Any]) -> str:
    return str(
        provider_config.get("provider_source_id") or provider_config.get("id") or ""
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
    source_id = str(provider_config.get("provider_source_id") or "").strip()
    if source_id:
        retired_ui = provider_config.get(legacy_model_video_ui_key(source_id))
        if isinstance(retired_ui, bool):
            # AstrBot 4.26.1 returned live provider dictionaries from the schema
            # service. The 0.1.17 projection could therefore leave this intended
            # temporary key in memory before another config save. Accept only the
            # key derived from this exact card Source until startup migration
            # converts and removes it.
            return retired_ui
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
    source_id = str(provider_config.get("provider_source_id") or "").strip()
    retired_ui = (
        provider_config.get(legacy_model_video_ui_key(source_id)) if source_id else None
    )
    legacy = provider_config.get(LEGACY_MODEL_VIDEO_INPUT_KEY)
    if not isinstance(explicit, bool):
        if isinstance(retired_ui, bool):
            provider_config[VIDEO_INPUT_ENABLED_KEY] = retired_ui
        elif isinstance(legacy, bool):
            provider_config[VIDEO_INPUT_ENABLED_KEY] = legacy
        elif isinstance(default_enabled, bool):
            provider_config[VIDEO_INPUT_ENABLED_KEY] = default_enabled
    provider_config.pop(LEGACY_MODEL_VIDEO_INPUT_KEY, None)
    _strip_model_card_dashboard_video_keys(provider_config)
    return provider_config


def migrate_legacy_video_settings(config: dict[str, Any]) -> list[str]:
    """Migrate pre-0.1.15 plugin video settings without touching modalities.

    Migration preserves the old resolver's precedence exactly:

    1. already-saved 0.1.15 per-card transport setting;
    2. exact-Source retired 0.1.17 Dashboard model key;
    3. older per-card plugin setting;
    4. older explicit Provider Source boolean (``True`` *or* ``False``);
    5. historical ``video`` entry in AstrBot ``modalities`` as a final clue.

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
        source_type = types.get(source_id, "")
        legacy_key = LEGACY_SOURCE_VIDEO_KEYS.get(source_type)
        if source_id and legacy_key and legacy_key in source:
            value = source.get(legacy_key)
            if isinstance(value, bool):
                legacy_defaults[source_id] = value
        for old_source_key in LEGACY_SOURCE_VIDEO_KEYS.values():
            if old_source_key in source:
                source.pop(old_source_key, None)
                source_changed = True
        # Defensive wrong-layer cleanup. The visibility preference is the only
        # plugin video field allowed to persist on an owned Source.
        for key in list(source):
            if key in {VIDEO_INPUT_ENABLED_KEY, LEGACY_MODEL_VIDEO_INPUT_KEY} or (
                isinstance(key, str)
                and (
                    key.startswith(LEGACY_MODEL_VIDEO_UI_KEY_PREFIX)
                    or key.startswith(SOURCE_VIDEO_SELECTOR_UI_KEY_PREFIX)
                )
            ):
                source.pop(key, None)
                source_changed = True
        if (
            source_type not in OWNED_SOURCE_TYPES
            and VIDEO_CONTROLS_VISIBLE_KEY in source
        ):
            source.pop(VIDEO_CONTROLS_VISIBLE_KEY, None)
            source_changed = True

    changed_ids: list[str] = []
    any_changed = source_changed
    for provider in providers:
        if not isinstance(provider, dict):
            continue
        source_id = str(provider.get("provider_source_id") or "").strip()
        if types.get(source_id) not in OWNED_SOURCE_TYPES:
            continue

        before = dict(provider)
        explicit = provider.get(VIDEO_INPUT_ENABLED_KEY)
        legacy_model = provider.get(LEGACY_MODEL_VIDEO_INPUT_KEY)
        retired_ui = provider.get(legacy_model_video_ui_key(source_id))
        modalities = provider.get("modalities")

        if not isinstance(explicit, bool):
            if isinstance(retired_ui, bool):
                provider[VIDEO_INPUT_ENABLED_KEY] = retired_ui
            elif isinstance(legacy_model, bool):
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
        _strip_model_card_dashboard_video_keys(provider)
        if provider != before:
            any_changed = True
            provider_id = str(provider.get("id") or "").strip()
            if provider_id:
                changed_ids.append(provider_id)

    # Presentation-only fields on foreign cards are never eligible for
    # promotion, but they are still plugin debris and must be removed.
    for provider in providers:
        if not isinstance(provider, dict):
            continue
        source_id = str(provider.get("provider_source_id") or "").strip()
        if types.get(source_id) in OWNED_SOURCE_TYPES:
            continue
        before = dict(provider)
        provider.pop(VIDEO_INPUT_ENABLED_KEY, None)
        provider.pop(LEGACY_MODEL_VIDEO_INPUT_KEY, None)
        for legacy_key in LEGACY_SOURCE_VIDEO_KEYS.values():
            provider.pop(legacy_key, None)
        _strip_model_card_dashboard_video_keys(provider)
        if provider != before:
            any_changed = True
            provider_id = str(provider.get("id") or "").strip()
            if provider_id and provider_id not in changed_ids:
                changed_ids.append(provider_id)

    if any_changed and not changed_ids:
        changed_ids.append("")
    return changed_ids
