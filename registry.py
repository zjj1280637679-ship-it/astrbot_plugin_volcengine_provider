"""Plugin-owned Provider registration and narrow AstrBot Dashboard bridge.

Dashboard integration is capability-detected at runtime. Missing optional
Dashboard APIs may reduce UI/feedback integration, but must never prevent the
Provider adapters themselves from registering or loading.
"""

from __future__ import annotations

import copy
from collections.abc import Callable
from typing import Any

from astrbot.core.provider.register import (
    provider_cls_map,
    provider_registry,
    register_provider_adapter,
)

from .capabilities import (
    AGENT_PLAN_PROVIDER_TYPE,
    ARK_PROVIDER_TYPE,
    LEGACY_MODEL_VIDEO_INPUT_KEY,
    LEGACY_MODEL_VIDEO_UI_KEY_PREFIX,
    LEGACY_SOURCE_VIDEO_KEYS,
    OWNED_SOURCE_TYPES,
    SOURCE_VIDEO_SELECTOR_UI_KEY_PREFIX,
    VIDEO_CONTROLS_VISIBLE_KEY,
    VIDEO_INPUT_ENABLED_KEY,
    cleanup_owned_settings_on_source_change,
    consume_source_model_hints,
    normalize_owned_model_card_for_save,
    source_types,
    video_input_enabled,
)

PLUGIN_MODULE_MARKER = "astrbot_plugin_volcengine_provider"

# AstrBot 4.26/4.27 exposes one shared Provider schema. Canonical per-card state
# must not be rendered there. The first prefix remains accepted only for stale
# 0.1.17 model dialogs; the second projects one Source-owned checkbox list. Both
# are Dashboard-only and are stripped at their respective save boundaries.
_VIDEO_UI_KEY_PREFIX = LEGACY_MODEL_VIDEO_UI_KEY_PREFIX
_SOURCE_VIDEO_SELECTOR_UI_KEY_PREFIX = SOURCE_VIDEO_SELECTOR_UI_KEY_PREFIX
_SOURCE_TRANSPORT_UI_HINT = (
    "视频请求通道是当前火山 Source 内的逐模型请求转发设置，不是模型能力结论。"
    "打开“显示逐模型视频选项”可集中勾选；关闭只隐藏选择区，"
    "不会清除已保存选择，也不会停用已勾选模型的视频转发。"
)

_DASHBOARD_LEASE_COUNT = 0
_SCHEMA_WRAPPER: Callable[..., Any] | None = None
_SCHEMA_ORIGINAL: Callable[..., Any] | None = None
_MODELS_WRAPPER: Callable[..., Any] | None = None
_MODELS_ORIGINAL: Callable[..., Any] | None = None
_CREATE_WRAPPER: Callable[..., Any] | None = None
_CREATE_ORIGINAL: Callable[..., Any] | None = None
_UPDATE_WRAPPER: Callable[..., Any] | None = None
_UPDATE_ORIGINAL: Callable[..., Any] | None = None
_SOURCE_UPSERT_WRAPPER: Callable[..., Any] | None = None
_SOURCE_UPSERT_ORIGINAL: Callable[..., Any] | None = None


def _video_ui_key(source_id: str) -> str:
    """Return a reversible non-persistent UI key for one Source ID.

    UTF-8 hex is injective for Python strings after UTF-8 encoding, unlike a
    truncated hash.  The longer key exists only in a Dashboard response and is
    removed before persistence.
    """

    encoded = source_id.encode("utf-8").hex()
    return f"{_VIDEO_UI_KEY_PREFIX}{encoded}"


def _source_video_selector_ui_key(source_id: str) -> str:
    """Return the non-persistent Source-page selector key for one Source."""

    encoded = source_id.encode("utf-8").hex()
    return f"{_SOURCE_VIDEO_SELECTOR_UI_KEY_PREFIX}{encoded}"


def _strip_video_ui_keys(provider_config: dict[str, Any]) -> None:
    """Remove every Dashboard-only transport field before host persistence."""

    for key in [
        key
        for key in provider_config
        if isinstance(key, str) and key.startswith(_VIDEO_UI_KEY_PREFIX)
    ]:
        provider_config.pop(key, None)


def _strip_source_video_selector_ui_keys(source_config: dict[str, Any]) -> None:
    """Remove Source-page model selectors before host persistence."""

    for key in [
        key
        for key in source_config
        if isinstance(key, str) and key.startswith(_SOURCE_VIDEO_SELECTOR_UI_KEY_PREFIX)
    ]:
        source_config.pop(key, None)


def _strip_source_only_video_keys_from_model_card(
    provider_config: dict[str, Any],
) -> None:
    """Remove Source-page state that is invalid on every model card."""

    provider_config.pop(VIDEO_CONTROLS_VISIBLE_KEY, None)
    for legacy_source_key in LEGACY_SOURCE_VIDEO_KEYS.values():
        provider_config.pop(legacy_source_key, None)
    _strip_source_video_selector_ui_keys(provider_config)


def _strip_all_plugin_video_fields_from_model_card(
    provider_config: dict[str, Any],
) -> None:
    """Remove every plugin video field from a foreign/UI model projection."""

    provider_config.pop(VIDEO_INPUT_ENABLED_KEY, None)
    provider_config.pop(LEGACY_MODEL_VIDEO_INPUT_KEY, None)
    _strip_video_ui_keys(provider_config)
    _strip_source_only_video_keys_from_model_card(provider_config)


def _strip_wrong_layer_video_fields_from_source(source_config: dict[str, Any]) -> None:
    """Remove model-card and retired Source fields from a Source payload."""

    source_config.pop(VIDEO_INPUT_ENABLED_KEY, None)
    source_config.pop(LEGACY_MODEL_VIDEO_INPUT_KEY, None)
    for legacy_source_key in LEGACY_SOURCE_VIDEO_KEYS.values():
        source_config.pop(legacy_source_key, None)
    _strip_video_ui_keys(source_config)


def _inject_owned_source_transport_hint(payload: dict[str, Any]) -> dict[str, Any]:
    """Project a current UI-path hint onto owned Sources only.

    AstrBot V4 builds new Sources from ``config_schema.provider.config_template``
    and existing Sources from ``provider_sources``. Both collections are copied
    before mutation. Existing host/user hints are preserved rather than overwritten.
    """

    # New Sources are built from config_schema.provider.config_template.
    config_schema = payload.get("config_schema")
    provider_schema = (
        config_schema.get("provider") if isinstance(config_schema, dict) else None
    )
    templates = (
        provider_schema.get("config_template")
        if isinstance(provider_schema, dict)
        else None
    )
    if isinstance(templates, dict):
        copied_templates = copy.deepcopy(templates)
        provider_schema["config_template"] = copied_templates
        for template in copied_templates.values():
            if not isinstance(template, dict):
                continue
            source_type = str(template.get("type") or "").strip()
            if source_type not in OWNED_SOURCE_TYPES:
                continue
            if not template.get("hint"):
                template["hint"] = _SOURCE_TRANSPORT_UI_HINT

    provider_sources = payload.get("provider_sources")
    if not isinstance(provider_sources, list):
        return payload

    copied_sources = copy.deepcopy(provider_sources)
    payload["provider_sources"] = copied_sources
    types = source_types({"provider_sources": copied_sources})
    for source in copied_sources:
        if not isinstance(source, dict):
            continue
        source_id = str(source.get("id") or "").strip()
        if not source_id or types.get(source_id) not in OWNED_SOURCE_TYPES:
            continue
        if not source.get("hint"):
            source["hint"] = _SOURCE_TRANSPORT_UI_HINT
    return payload


def _strip_source_transport_hint(source_config: dict[str, Any]) -> None:
    """Remove only this plugin's short-lived explanatory Source hint."""

    if source_config.get("hint") == _SOURCE_TRANSPORT_UI_HINT:
        source_config.pop("hint", None)


def _apply_video_ui_transport_setting(
    provider_config: dict[str, Any],
    provider_sources: list[dict[str, Any]] | object,
) -> None:
    """Translate the current Source's short-lived UI value to the canonical key.

    This is user configuration transport, not model-capability discovery.  UI
    values from foreign Sources are discarded rather than being promoted into
    plugin state.
    """

    source_id = str(provider_config.get("provider_source_id") or "").strip()
    types = (
        source_types({"provider_sources": provider_sources})
        if isinstance(provider_sources, list)
        else {}
    )
    if source_id and types.get(source_id) in OWNED_SOURCE_TYPES:
        ui_value = provider_config.get(_video_ui_key(source_id))
        if isinstance(ui_value, bool):
            # The visible UI value is the user's newest edit, so it intentionally
            # outranks the hidden canonical value copied into an edit response.
            provider_config[VIDEO_INPUT_ENABLED_KEY] = ui_value
    _strip_video_ui_keys(provider_config)


def _inject_model_card_video_control(payload: dict[str, Any]) -> dict[str, Any]:
    """Project per-model video choices into each owned Source page.

    The historical function name is retained for import compatibility, but the
    visible control now lives on the current Provider Source.  AstrBot's Source
    form owns real ``type``/``provider`` identity and evaluates conditions on the
    same object, so it does not suffer the generic model-card all-or-none leak.

    The Source selector is only a Dashboard projection.  Each model card's
    ``volcengine_video_input_enabled`` remains the sole persistent/runtime truth.
    """

    try:
        items = payload["config_schema"]["provider"]["items"]
    except (KeyError, TypeError):
        return payload
    if not isinstance(items, dict):
        return payload

    # Remove schema remnants from an already wrapped/customized response. The
    # model-card UI is intentionally retired; configuration now lives on Source.
    forbidden_schema_keys = {
        VIDEO_INPUT_ENABLED_KEY,
        LEGACY_MODEL_VIDEO_INPUT_KEY,
        VIDEO_CONTROLS_VISIBLE_KEY,
        *LEGACY_SOURCE_VIDEO_KEYS.values(),
    }
    for key in list(items):
        if key in forbidden_schema_keys or (
            isinstance(key, str)
            and (
                key.startswith(_VIDEO_UI_KEY_PREFIX)
                or key.startswith(_SOURCE_VIDEO_SELECTOR_UI_KEY_PREFIX)
            )
        ):
            items.pop(key, None)

    items[VIDEO_CONTROLS_VISIBLE_KEY] = {
        "description": "显示逐模型视频选项",
        "type": "bool",
        "hint": (
            "仅控制下方逐模型选择区的显示。关闭不会清除已经保存的选择，"
            "也不会停用已勾选模型的视频请求转发。"
        ),
    }

    types = source_types(payload)
    providers_input = payload.get("providers", [])
    providers = (
        copy.deepcopy(providers_input) if isinstance(providers_input, list) else []
    )
    payload["providers"] = providers

    providers_by_source: dict[str, list[dict[str, Any]]] = {}
    selected_card_ids = {
        str(provider.get("id") or "").strip()
        for provider in providers_input
        if isinstance(provider, dict) and video_input_enabled(provider)
    }
    for provider in providers:
        if not isinstance(provider, dict):
            continue
        source_id = str(provider.get("provider_source_id") or "").strip()
        # No plugin video field has a legitimate generic model-card UI
        # representation. Strip stale, forged and wrong-layer fields alike.
        _strip_all_plugin_video_fields_from_model_card(provider)
        if types.get(source_id) not in OWNED_SOURCE_TYPES:
            continue
        providers_by_source.setdefault(source_id, []).append(provider)

    provider_sources_input = payload.get("provider_sources", [])
    provider_sources = (
        copy.deepcopy(provider_sources_input)
        if isinstance(provider_sources_input, list)
        else []
    )
    payload["provider_sources"] = provider_sources

    def project_source(source: dict[str, Any], source_type: str) -> None:
        source_id = str(source.get("id") or "").strip()
        _strip_wrong_layer_video_fields_from_source(source)
        _strip_source_video_selector_ui_keys(source)
        if not source_id or source_type not in OWNED_SOURCE_TYPES:
            # Defensive projection cleanup: even a forged/stale foreign field
            # must not become a fallback-rendered Volcengine control.
            source.pop(VIDEO_CONTROLS_VISIBLE_KEY, None)
            return

        source.setdefault(VIDEO_CONTROLS_VISIBLE_KEY, False)
        cards = sorted(
            providers_by_source.get(source_id, []),
            key=lambda card: str(card.get("id") or ""),
        )
        options: list[str] = []
        labels: list[str] = []
        selected: list[str] = []
        for card in cards:
            card_id = str(card.get("id") or "").strip()
            if not card_id:
                continue
            model = str(card.get("model") or "").strip()
            options.append(card_id)
            labels.append(f"{model or card_id}（{card_id}）")
            if card_id in selected_card_ids:
                selected.append(card_id)

        selector_key = _source_video_selector_ui_key(source_id)
        items[selector_key] = {
            "description": "启用视频请求通道的模型",
            "type": "list",
            "items": {"type": "string"},
            "options": options,
            "labels": labels,
            "render_type": "checkbox",
            "hint": (
                "勾选表示允许该模型卡按 Ark video_url 协议尝试发送本轮视频；"
                "它是用户请求转发设置，不是模型能力结论。"
            ),
            "condition": {VIDEO_CONTROLS_VISIBLE_KEY: True},
        }
        source[selector_key] = selected

    for source in provider_sources:
        if not isinstance(source, dict):
            continue
        source_id = str(source.get("id") or "").strip()
        project_source(source, types.get(source_id, ""))

    config_schema = payload.get("config_schema")
    provider_schema = (
        config_schema.get("provider") if isinstance(config_schema, dict) else None
    )
    templates_input = (
        provider_schema.get("config_template")
        if isinstance(provider_schema, dict)
        else None
    )
    if isinstance(templates_input, dict):
        templates = copy.deepcopy(templates_input)
        provider_schema["config_template"] = templates
        for template in templates.values():
            if not isinstance(template, dict):
                continue
            _strip_wrong_layer_video_fields_from_source(template)
            _strip_source_video_selector_ui_keys(template)
            if str(template.get("type") or "").strip() in OWNED_SOURCE_TYPES:
                # A new Source has no configured model cards yet. Its master
                # switch is immediately visible; the selector is projected on
                # the next schema load after model cards exist.
                template.setdefault(VIDEO_CONTROLS_VISIBLE_KEY, False)
            else:
                template.pop(VIDEO_CONTROLS_VISIBLE_KEY, None)
    return payload


def _is_owned_source(service: Any, source_id: str) -> bool:
    config = getattr(service, "config", {})
    types = source_types(config if hasattr(config, "get") else {})
    return types.get(source_id) in OWNED_SOURCE_TYPES


def _merge_source_feedback(base: object, hint: object) -> dict[str, Any]:
    """Overlay one *current* Ark receipt onto one Dashboard response only.

    This function does not mutate AstrBot's process-global metadata.  Fields
    absent from the current receipt remain AstrBot-owned.  Fields explicitly
    present in the current receipt replace the same display field for this
    Source response, including explicit ``False`` and current modality lists;
    otherwise stale information would outrank a newer receipt.
    """

    merged = copy.deepcopy(base) if isinstance(base, dict) else {}
    if not isinstance(hint, dict):
        return merged

    for key, value in hint.items():
        if key == "modalities" and isinstance(value, dict):
            current = merged.get("modalities")
            if not isinstance(current, dict):
                current = {}
            else:
                current = copy.deepcopy(current)
            for direction in ("input", "output"):
                if direction in value and isinstance(value[direction], list):
                    current[direction] = copy.deepcopy(value[direction])
            merged["modalities"] = current
            continue

        if key == "limit" and isinstance(value, dict):
            current = merged.get("limit")
            if not isinstance(current, dict):
                current = {}
            else:
                current = copy.deepcopy(current)
            for name, incoming in value.items():
                current[name] = copy.deepcopy(incoming)
            merged["limit"] = current
            continue

        # ``False`` is still a live feedback value.  Do not use truthiness or
        # preserve an older host/display value over an explicit current receipt.
        merged[key] = copy.deepcopy(value)
    return merged


def _overlay_source_scoped_model_hints(
    service: Any,
    source_id: str,
    result: dict[str, Any],
) -> dict[str, Any]:
    models = [str(model) for model in result.get("models", []) or []]

    # Consume first even when the Source changed ownership between get_models()
    # and this wrapper.  The mailbox is current-call data, never reusable history.
    hints = consume_source_model_hints(source_id, models)
    if not _is_owned_source(service, source_id) or not hints:
        return result

    metadata = result.setdefault("model_metadata", {})
    if not isinstance(metadata, dict):
        return result
    for model_id, hint in hints.items():
        metadata[model_id] = _merge_source_feedback(metadata.get(model_id), hint)
    return result


def _unwrap_owned_wrapper(
    candidate: object,
    *,
    marker: str,
    original: str,
) -> Callable[..., Any] | None:
    """Return an unwrapped host method, or None when that API is unavailable."""

    if not callable(candidate):
        return None
    if getattr(candidate, marker, False):
        unwrapped = getattr(candidate, original, None)
        return unwrapped if callable(unwrapped) else None
    return candidate


def _provider_sources_for_service(service: Any) -> list[dict[str, Any]]:
    config = getattr(service, "config", {})
    if not hasattr(config, "get"):
        return []
    sources = config.get("provider_sources", [])
    return sources if isinstance(sources, list) else []


def _existing_provider_config(service: Any, provider_id: str) -> dict[str, Any]:
    """Read one persisted model card without requiring a specific manager API."""

    manager = getattr(service, "provider_manager", None)
    getter = getattr(manager, "get_provider_config_by_id", None)
    if callable(getter):
        existing = getter(provider_id)
        if isinstance(existing, dict):
            return existing

    config = getattr(service, "config", {})
    providers = config.get("provider", []) if hasattr(config, "get") else []
    if isinstance(providers, list):
        for provider in providers:
            if not isinstance(provider, dict):
                continue
            if str(provider.get("id") or "") == provider_id:
                return provider
    return {}


def _existing_source_config(service: Any, source_id: str) -> dict[str, Any]:
    """Read one persisted Provider Source without requiring a host helper."""

    for source in _provider_sources_for_service(service):
        if not isinstance(source, dict):
            continue
        if str(source.get("id") or "").strip() == source_id:
            return source
    return {}


def _apply_source_video_ui_settings(
    service: Any,
    source_id: str,
    source_config: dict[str, Any],
) -> list[str]:
    """Apply one owned Source-page selection to its model-card truth values.

    The master switch is presentation state only. When it is false, or when a
    hidden selector is absent, model-card values are deliberately untouched.
    When true, only cards belonging to this exact Source are updated; selected
    values use card IDs rather than model names so equal names cannot cross
    Source/card identity boundaries.

    Returns the IDs whose canonical value changed. Dashboard-only selector keys
    are always stripped before the host persistence boundary.
    """

    original_source_id = str(source_id or "").strip()
    next_source_id = str(source_config.get("id") or original_source_id).strip()
    existing = _existing_source_config(service, original_source_id)
    old_source_type = str(existing.get("type") or "").strip()
    source_type = str(source_config.get("type") or old_source_type or "").strip()
    config = getattr(service, "config", {})
    providers = config.get("provider", []) if hasattr(config, "get") else []

    if source_type not in OWNED_SOURCE_TYPES:
        if old_source_type in OWNED_SOURCE_TYPES:
            if isinstance(providers, list):
                for provider in providers:
                    if not isinstance(provider, dict):
                        continue
                    if (
                        str(provider.get("provider_source_id") or "").strip()
                        != original_source_id
                    ):
                        continue
                    cleanup_owned_settings_on_source_change(
                        provider,
                        old_source_type=old_source_type,
                        new_source_type=source_type,
                    )
                    _strip_all_plugin_video_fields_from_model_card(provider)
        _strip_wrong_layer_video_fields_from_source(source_config)
        source_config.pop(VIDEO_CONTROLS_VISIBLE_KEY, None)
        _strip_source_video_selector_ui_keys(source_config)
        return []

    # Heal any 0.1.17 AstrBot 4.26 live-schema projection debris before this
    # Source save. This is a migration/cleanup step only and does not manufacture
    # a default choice when the card has no prior video setting.
    if isinstance(providers, list):
        sources = _provider_sources_for_service(service)
        for provider in providers:
            if not isinstance(provider, dict):
                continue
            if (
                str(provider.get("provider_source_id") or "").strip()
                != original_source_id
            ):
                continue
            normalize_owned_model_card_for_save(
                provider,
                sources,
                default_enabled=None,
            )

    visible = source_config.get(VIDEO_CONTROLS_VISIBLE_KEY)
    if not isinstance(visible, bool):
        previous = existing.get(VIDEO_CONTROLS_VISIBLE_KEY)
        source_config[VIDEO_CONTROLS_VISIBLE_KEY] = (
            previous if isinstance(previous, bool) else False
        )
        visible = source_config[VIDEO_CONTROLS_VISIBLE_KEY]

    selector_present = False
    selector_value: object = None
    for candidate_id in (original_source_id, next_source_id):
        if not candidate_id:
            continue
        key = _source_video_selector_ui_key(candidate_id)
        if key in source_config:
            selector_present = True
            selector_value = source_config.get(key)
            break

    changed: list[str] = []
    if visible is True and selector_present and isinstance(selector_value, list):
        selected_ids = {
            str(value).strip() for value in selector_value if str(value).strip()
        }
        if isinstance(providers, list):
            for provider in providers:
                if not isinstance(provider, dict):
                    continue
                if (
                    str(provider.get("provider_source_id") or "").strip()
                    != original_source_id
                ):
                    continue
                provider_id = str(provider.get("id") or "").strip()
                if not provider_id:
                    continue
                next_enabled = provider_id in selected_ids
                if provider.get(VIDEO_INPUT_ENABLED_KEY) is not next_enabled:
                    provider[VIDEO_INPUT_ENABLED_KEY] = next_enabled
                    changed.append(provider_id)

    _strip_source_video_selector_ui_keys(source_config)
    _strip_wrong_layer_video_fields_from_source(source_config)
    return changed


def acquire_owned_dashboard_bridge() -> bool:
    """Install only Dashboard wrappers supported by this AstrBot build.

    The Provider adapters are the required feature. Dashboard model feedback is
    independent. The Source-page video UI requires both schema projection and a
    Source save boundary, so the plugin never exposes a control whose save
    semantics it cannot complete. Legacy model-card save translation remains a
    separate compatibility bridge for already-open/stale 0.1.17 clients.
    """

    global _DASHBOARD_LEASE_COUNT
    global _SCHEMA_WRAPPER, _SCHEMA_ORIGINAL, _MODELS_WRAPPER, _MODELS_ORIGINAL
    global _CREATE_WRAPPER, _CREATE_ORIGINAL, _UPDATE_WRAPPER, _UPDATE_ORIGINAL
    global _SOURCE_UPSERT_WRAPPER, _SOURCE_UPSERT_ORIGINAL

    if _DASHBOARD_LEASE_COUNT:
        _DASHBOARD_LEASE_COUNT += 1
        return True

    try:
        from astrbot.dashboard.services.config_service import ProviderConfigService
    except (ImportError, ModuleNotFoundError):
        return False

    schema_current = _unwrap_owned_wrapper(
        getattr(ProviderConfigService, "get_provider_schema", None),
        marker="_volcengine_provider_schema_wrapper",
        original="_volcengine_provider_schema_original",
    )
    models_current = _unwrap_owned_wrapper(
        getattr(ProviderConfigService, "list_provider_source_models", None),
        marker="_volcengine_source_models_wrapper",
        original="_volcengine_source_models_original",
    )
    create_current = _unwrap_owned_wrapper(
        getattr(ProviderConfigService, "create_provider", None),
        marker="_volcengine_model_save_wrapper",
        original="_volcengine_model_save_original",
    )
    update_current = _unwrap_owned_wrapper(
        getattr(ProviderConfigService, "update_provider", None),
        marker="_volcengine_model_save_wrapper",
        original="_volcengine_model_save_original",
    )
    source_upsert_current = _unwrap_owned_wrapper(
        getattr(ProviderConfigService, "upsert_provider_source", None),
        marker="_volcengine_source_save_wrapper",
        original="_volcengine_source_save_original",
    )

    installed = False
    can_install_legacy_model_save_bridge = (
        schema_current is not None
        and create_current is not None
        and update_current is not None
    )
    can_install_source_video_ui = (
        schema_current is not None and source_upsert_current is not None
    )

    if can_install_source_video_ui:

        def schema_wrapper(self) -> dict[str, Any]:
            result = _inject_owned_source_transport_hint(schema_current(self))
            result = _inject_model_card_video_control(result)
            return result

        schema_wrapper._volcengine_provider_schema_wrapper = True  # type: ignore[attr-defined]
        schema_wrapper._volcengine_provider_schema_original = schema_current  # type: ignore[attr-defined]
        ProviderConfigService.get_provider_schema = schema_wrapper  # type: ignore[method-assign]
        _SCHEMA_ORIGINAL, _SCHEMA_WRAPPER = schema_current, schema_wrapper
        installed = True

    if models_current is not None:

        async def models_wrapper(self, source_id: str) -> dict[str, Any]:
            result = await models_current(self, source_id)
            if not isinstance(result, dict):
                # Consume any current-call handoff even if a custom AstrBot build
                # returns an unexpected shape; never leave it as future history.
                consume_source_model_hints(source_id)
                return result
            return _overlay_source_scoped_model_hints(self, source_id, result)

        models_wrapper._volcengine_source_models_wrapper = True  # type: ignore[attr-defined]
        models_wrapper._volcengine_source_models_original = models_current  # type: ignore[attr-defined]
        ProviderConfigService.list_provider_source_models = models_wrapper  # type: ignore[method-assign]
        _MODELS_ORIGINAL, _MODELS_WRAPPER = models_current, models_wrapper
        installed = True

    if can_install_legacy_model_save_bridge:

        async def create_wrapper(
            self,
            config: dict[str, Any],
            source_id: str | None = None,
        ) -> None:
            normalized = dict(config)
            if source_id:
                normalized["provider_source_id"] = source_id
            sources = _provider_sources_for_service(self)
            _apply_video_ui_transport_setting(normalized, sources)
            types = source_types({"provider_sources": sources})
            source_type = types.get(
                str(normalized.get("provider_source_id") or "").strip(),
                "",
            )
            if source_type in OWNED_SOURCE_TYPES:
                _strip_source_only_video_keys_from_model_card(normalized)
                normalize_owned_model_card_for_save(
                    normalized,
                    sources,
                    default_enabled=False,
                )
            else:
                _strip_all_plugin_video_fields_from_model_card(normalized)
            await create_current(self, normalized, source_id)

        create_wrapper._volcengine_model_save_wrapper = True  # type: ignore[attr-defined]
        create_wrapper._volcengine_model_save_original = create_current  # type: ignore[attr-defined]
        ProviderConfigService.create_provider = create_wrapper  # type: ignore[method-assign]
        _CREATE_ORIGINAL, _CREATE_WRAPPER = create_current, create_wrapper
        installed = True

        async def update_wrapper(
            self,
            provider_id: str,
            config: dict[str, Any],
        ) -> None:
            normalized = dict(config)
            existing = _existing_provider_config(self, provider_id)
            if not normalized.get("provider_source_id") and existing.get(
                "provider_source_id"
            ):
                normalized["provider_source_id"] = existing["provider_source_id"]

            sources = _provider_sources_for_service(self)
            types = source_types({"provider_sources": sources})
            old_source_id = str(existing.get("provider_source_id") or "").strip()
            new_source_id = str(normalized.get("provider_source_id") or "").strip()
            old_type = types.get(old_source_id, "")
            new_type = types.get(new_source_id, "")

            cleanup_owned_settings_on_source_change(
                normalized,
                old_source_type=old_type,
                new_source_type=new_type,
            )

            _apply_video_ui_transport_setting(normalized, sources)

            existing_value: bool | None = None
            for candidate in (
                existing.get(VIDEO_INPUT_ENABLED_KEY),
                existing.get(_video_ui_key(old_source_id)) if old_source_id else None,
                existing.get(LEGACY_MODEL_VIDEO_INPUT_KEY),
            ):
                if isinstance(candidate, bool):
                    existing_value = candidate
                    break
            if (
                new_type in OWNED_SOURCE_TYPES
                and VIDEO_INPUT_ENABLED_KEY not in normalized
                and old_type in OWNED_SOURCE_TYPES
                and existing_value is not None
            ):
                normalized[VIDEO_INPUT_ENABLED_KEY] = existing_value

            if new_type in OWNED_SOURCE_TYPES:
                _strip_source_only_video_keys_from_model_card(normalized)
                normalize_owned_model_card_for_save(
                    normalized,
                    sources,
                    default_enabled=False,
                )
                _strip_video_ui_keys(normalized)
            else:
                _strip_all_plugin_video_fields_from_model_card(normalized)
            await update_current(self, provider_id, normalized)

        update_wrapper._volcengine_model_save_wrapper = True  # type: ignore[attr-defined]
        update_wrapper._volcengine_model_save_original = update_current  # type: ignore[attr-defined]
        ProviderConfigService.update_provider = update_wrapper  # type: ignore[method-assign]
        _UPDATE_ORIGINAL, _UPDATE_WRAPPER = update_current, update_wrapper
        installed = True

    if can_install_source_video_ui:

        async def source_upsert_wrapper(
            self,
            source_id: str,
            config: dict[str, Any],
        ) -> Any:
            normalized = dict(config)
            next_source_id = str(normalized.get("id") or source_id).strip()
            if not next_source_id:
                raise ValueError("Provider source config must have an 'id' field")

            # Mirror AstrBot's only Source identity preflight before touching
            # per-card settings. A rejected rename must have no side effects.
            for source in _provider_sources_for_service(self):
                if not isinstance(source, dict):
                    continue
                if (
                    str(source.get("id") or "").strip() == next_source_id
                    and next_source_id != str(source_id).strip()
                ):
                    raise ValueError(
                        f"Provider source ID '{next_source_id}' exists already, "
                        "please try another ID."
                    )

            normalized["id"] = next_source_id
            service_config = getattr(self, "config", {})
            providers = (
                service_config.get("provider", [])
                if hasattr(service_config, "get")
                else []
            )
            provider_snapshot = copy.deepcopy(providers)
            _apply_source_video_ui_settings(self, source_id, normalized)
            _strip_source_transport_hint(normalized)
            try:
                return await source_upsert_current(self, source_id, normalized)
            except Exception:
                # The Source selector is a projection over per-card persistent
                # truth. If the host rejects/fails the Source save, restore the
                # pre-call card list so a failed UI action has no plugin-created
                # in-memory side effect.
                if isinstance(providers, list):
                    providers[:] = provider_snapshot
                raise

        source_upsert_wrapper._volcengine_source_save_wrapper = True  # type: ignore[attr-defined]
        source_upsert_wrapper._volcengine_source_save_original = source_upsert_current  # type: ignore[attr-defined]
        ProviderConfigService.upsert_provider_source = source_upsert_wrapper  # type: ignore[method-assign]
        _SOURCE_UPSERT_ORIGINAL, _SOURCE_UPSERT_WRAPPER = (
            source_upsert_current,
            source_upsert_wrapper,
        )
        installed = True

    if installed:
        _DASHBOARD_LEASE_COUNT = 1
    return installed


def release_owned_dashboard_bridge() -> None:
    global _DASHBOARD_LEASE_COUNT
    global _SCHEMA_WRAPPER, _SCHEMA_ORIGINAL, _MODELS_WRAPPER, _MODELS_ORIGINAL
    global _CREATE_WRAPPER, _CREATE_ORIGINAL, _UPDATE_WRAPPER, _UPDATE_ORIGINAL
    global _SOURCE_UPSERT_WRAPPER, _SOURCE_UPSERT_ORIGINAL

    if _DASHBOARD_LEASE_COUNT <= 0:
        return
    _DASHBOARD_LEASE_COUNT -= 1
    if _DASHBOARD_LEASE_COUNT:
        return

    try:
        from astrbot.dashboard.services.config_service import ProviderConfigService
    except (ImportError, ModuleNotFoundError):
        ProviderConfigService = None  # type: ignore[assignment,misc]

    if ProviderConfigService is not None:
        if (
            _SCHEMA_WRAPPER is not None
            and getattr(ProviderConfigService, "get_provider_schema", None)
            is _SCHEMA_WRAPPER
        ):
            ProviderConfigService.get_provider_schema = _SCHEMA_ORIGINAL  # type: ignore[method-assign]
        if (
            _MODELS_WRAPPER is not None
            and getattr(ProviderConfigService, "list_provider_source_models", None)
            is _MODELS_WRAPPER
        ):
            ProviderConfigService.list_provider_source_models = _MODELS_ORIGINAL  # type: ignore[method-assign]
        if (
            _CREATE_WRAPPER is not None
            and getattr(ProviderConfigService, "create_provider", None)
            is _CREATE_WRAPPER
        ):
            ProviderConfigService.create_provider = _CREATE_ORIGINAL  # type: ignore[method-assign]
        if (
            _UPDATE_WRAPPER is not None
            and getattr(ProviderConfigService, "update_provider", None)
            is _UPDATE_WRAPPER
        ):
            ProviderConfigService.update_provider = _UPDATE_ORIGINAL  # type: ignore[method-assign]
        if (
            _SOURCE_UPSERT_WRAPPER is not None
            and getattr(ProviderConfigService, "upsert_provider_source", None)
            is _SOURCE_UPSERT_WRAPPER
        ):
            ProviderConfigService.upsert_provider_source = _SOURCE_UPSERT_ORIGINAL  # type: ignore[method-assign]

    _SCHEMA_WRAPPER = _SCHEMA_ORIGINAL = None
    _MODELS_WRAPPER = _MODELS_ORIGINAL = None
    _CREATE_WRAPPER = _CREATE_ORIGINAL = None
    _UPDATE_WRAPPER = _UPDATE_ORIGINAL = None
    _SOURCE_UPSERT_WRAPPER = _SOURCE_UPSERT_ORIGINAL = None


# 0.1.14 import compatibility.
acquire_owned_provider_schema = acquire_owned_dashboard_bridge
release_owned_provider_schema = release_owned_dashboard_bridge


def register_owned_provider(
    provider_type_name: str,
    desc: str,
    *,
    provider_type,
    default_config_tmpl: dict,
    provider_display_name: str,
):
    existing = provider_cls_map.get(provider_type_name)
    if existing is not None:
        existing_cls = getattr(existing, "cls_type", None)
        module = str(getattr(existing_cls, "__module__", ""))
        owned = bool(
            getattr(existing_cls, "_volcengine_provider_plugin_owned", False)
            or PLUGIN_MODULE_MARKER in module
        )
        if not owned:
            raise ValueError(
                f"Provider type {provider_type_name!r} is already owned by "
                f"{module or 'an unknown module'}"
            )
        provider_registry[:] = [
            item for item in provider_registry if item is not existing
        ]
        provider_cls_map.pop(provider_type_name, None)

    return register_provider_adapter(
        provider_type_name,
        desc,
        provider_type=provider_type,
        default_config_tmpl=default_config_tmpl,
        provider_display_name=provider_display_name,
    )
