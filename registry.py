"""Plugin-owned Provider registration and scoped AstrBot Dashboard persistence bridge.

The visible Video checkbox itself is delivered only on a concrete owned model
card by the model-field/asset/runtime bridges. This module owns the backend
schema cleanup, current Source feedback overlay, and create/update persistence
boundary. Retired Source-page Video controls are intentionally absent.
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
)

PLUGIN_MODULE_MARKER = "astrbot_plugin_volcengine_provider"

# These prefixes are recognized only so stale 0.1.x debris can be stripped at
# current persistence/schema boundaries. There is no active UI that generates
# either key family.
_VIDEO_UI_KEY_PREFIX = LEGACY_MODEL_VIDEO_UI_KEY_PREFIX
_SOURCE_VIDEO_SELECTOR_UI_KEY_PREFIX = SOURCE_VIDEO_SELECTOR_UI_KEY_PREFIX

_DASHBOARD_LEASE_COUNT = 0
_SCHEMA_WRAPPER: Callable[..., Any] | None = None
_SCHEMA_ORIGINAL: Callable[..., Any] | None = None
_MODELS_WRAPPER: Callable[..., Any] | None = None
_MODELS_ORIGINAL: Callable[..., Any] | None = None
_CREATE_WRAPPER: Callable[..., Any] | None = None
_CREATE_ORIGINAL: Callable[..., Any] | None = None
_UPDATE_WRAPPER: Callable[..., Any] | None = None
_UPDATE_ORIGINAL: Callable[..., Any] | None = None


def _strip_video_ui_keys(provider_config: dict[str, Any]) -> None:
    for key in list(provider_config):
        if isinstance(key, str) and key.startswith(_VIDEO_UI_KEY_PREFIX):
            provider_config.pop(key, None)


def _strip_source_video_selector_ui_keys(config: dict[str, Any]) -> None:
    for key in list(config):
        if isinstance(key, str) and key.startswith(_SOURCE_VIDEO_SELECTOR_UI_KEY_PREFIX):
            config.pop(key, None)


def _strip_source_only_video_keys_from_model_card(
    provider_config: dict[str, Any],
) -> None:
    provider_config.pop(VIDEO_CONTROLS_VISIBLE_KEY, None)
    for legacy_source_key in LEGACY_SOURCE_VIDEO_KEYS.values():
        provider_config.pop(legacy_source_key, None)
    _strip_source_video_selector_ui_keys(provider_config)


def _strip_all_plugin_video_fields_from_model_card(
    provider_config: dict[str, Any],
) -> None:
    provider_config.pop(VIDEO_INPUT_ENABLED_KEY, None)
    provider_config.pop(LEGACY_MODEL_VIDEO_INPUT_KEY, None)
    _strip_video_ui_keys(provider_config)
    _strip_source_only_video_keys_from_model_card(provider_config)


def _strip_wrong_layer_video_fields_from_source(source_config: dict[str, Any]) -> None:
    source_config.pop(VIDEO_INPUT_ENABLED_KEY, None)
    source_config.pop(LEGACY_MODEL_VIDEO_INPUT_KEY, None)
    source_config.pop(VIDEO_CONTROLS_VISIBLE_KEY, None)
    for legacy_source_key in LEGACY_SOURCE_VIDEO_KEYS.values():
        source_config.pop(legacy_source_key, None)
    _strip_video_ui_keys(source_config)
    _strip_source_video_selector_ui_keys(source_config)


def _inject_model_card_video_control(payload: dict[str, Any]) -> dict[str, Any]:
    """Sanitize the shared schema and concrete saved objects before projection.

    The shared AstrBot schema must never receive a globally visible Video or a
    persistent Volcengine model field. Later scoped bridges operate on a private
    concrete owned card. This function only removes stale/global plugin debris.
    """

    try:
        items = payload["config_schema"]["provider"]["items"]
    except (KeyError, TypeError):
        return payload
    if not isinstance(items, dict):
        return payload

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

    providers_input = payload.get("providers", [])
    providers = (
        copy.deepcopy(providers_input) if isinstance(providers_input, list) else []
    )
    payload["providers"] = providers
    for provider in providers:
        if isinstance(provider, dict):
            _strip_all_plugin_video_fields_from_model_card(provider)

    provider_sources_input = payload.get("provider_sources", [])
    provider_sources = (
        copy.deepcopy(provider_sources_input)
        if isinstance(provider_sources_input, list)
        else []
    )
    payload["provider_sources"] = provider_sources
    for source in provider_sources:
        if isinstance(source, dict):
            _strip_wrong_layer_video_fields_from_source(source)

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
            if isinstance(template, dict):
                _strip_wrong_layer_video_fields_from_source(template)
    return payload


def _is_owned_source(service: Any, source_id: str) -> bool:
    config = getattr(service, "config", {})
    types = source_types(config if hasattr(config, "get") else {})
    return types.get(source_id) in OWNED_SOURCE_TYPES


def _merge_source_feedback(base: object, hint: object) -> dict[str, Any]:
    """Overlay one current Ark receipt onto one Dashboard response only."""

    merged = copy.deepcopy(base) if isinstance(base, dict) else {}
    if not isinstance(hint, dict):
        return merged

    for key, value in hint.items():
        if key == "modalities" and isinstance(value, dict):
            current = merged.get("modalities")
            current = copy.deepcopy(current) if isinstance(current, dict) else {}
            for direction in ("input", "output"):
                if direction in value and isinstance(value[direction], list):
                    current[direction] = copy.deepcopy(value[direction])
            merged["modalities"] = current
            continue

        if key == "limit" and isinstance(value, dict):
            current = merged.get("limit")
            current = copy.deepcopy(current) if isinstance(current, dict) else {}
            for name, incoming in value.items():
                current[name] = copy.deepcopy(incoming)
            merged["limit"] = current
            continue

        # Explicit False/0/empty is still current feedback; never use truthiness.
        merged[key] = copy.deepcopy(value)
    return merged


def _overlay_source_scoped_model_hints(
    service: Any,
    source_id: str,
    result: dict[str, Any],
) -> dict[str, Any]:
    models = [str(model) for model in result.get("models", []) or []]
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
            if isinstance(provider, dict) and str(provider.get("id") or "") == provider_id:
                return provider
    return {}


def acquire_owned_dashboard_bridge() -> bool:
    """Install current backend schema/feedback/save wrappers when supported."""

    global _DASHBOARD_LEASE_COUNT
    global _SCHEMA_WRAPPER, _SCHEMA_ORIGINAL, _MODELS_WRAPPER, _MODELS_ORIGINAL
    global _CREATE_WRAPPER, _CREATE_ORIGINAL, _UPDATE_WRAPPER, _UPDATE_ORIGINAL

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

    can_install_model_card_boundary = (
        schema_current is not None
        and create_current is not None
        and update_current is not None
    )
    installed = False

    if can_install_model_card_boundary:

        def schema_wrapper(self) -> dict[str, Any]:
            return _inject_model_card_video_control(schema_current(self))

        schema_wrapper._volcengine_provider_schema_wrapper = True  # type: ignore[attr-defined]
        schema_wrapper._volcengine_provider_schema_original = schema_current  # type: ignore[attr-defined]
        ProviderConfigService.get_provider_schema = schema_wrapper  # type: ignore[method-assign]
        _SCHEMA_ORIGINAL, _SCHEMA_WRAPPER = schema_current, schema_wrapper
        installed = True

    if models_current is not None:

        async def models_wrapper(self, source_id: str) -> dict[str, Any]:
            result = await models_current(self, source_id)
            if not isinstance(result, dict):
                consume_source_model_hints(source_id)
                return result
            return _overlay_source_scoped_model_hints(self, source_id, result)

        models_wrapper._volcengine_source_models_wrapper = True  # type: ignore[attr-defined]
        models_wrapper._volcengine_source_models_original = models_current  # type: ignore[attr-defined]
        ProviderConfigService.list_provider_source_models = models_wrapper  # type: ignore[method-assign]
        _MODELS_ORIGINAL, _MODELS_WRAPPER = models_current, models_wrapper
        installed = True

    if can_install_model_card_boundary:

        async def create_wrapper(
            self,
            config: dict[str, Any],
            source_id: str | None = None,
        ) -> None:
            normalized = dict(config)
            if source_id:
                normalized["provider_source_id"] = source_id
            sources = _provider_sources_for_service(self)
            types = source_types({"provider_sources": sources})
            source_type = types.get(
                str(normalized.get("provider_source_id") or "").strip(),
                "",
            )
            if source_type in OWNED_SOURCE_TYPES:
                _strip_source_only_video_keys_from_model_card(normalized)
                _strip_video_ui_keys(normalized)
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

            if new_type in OWNED_SOURCE_TYPES:
                _strip_source_only_video_keys_from_model_card(normalized)
                _strip_video_ui_keys(normalized)
                # Some host edit paths may omit modalities when unchanged. In
                # that case preserve only the already-persisted current mirror.
                if not isinstance(normalized.get("modalities"), list) and not isinstance(
                    normalized.get(VIDEO_INPUT_ENABLED_KEY), bool
                ):
                    previous = existing.get(VIDEO_INPUT_ENABLED_KEY)
                    if isinstance(previous, bool):
                        normalized[VIDEO_INPUT_ENABLED_KEY] = previous
                normalize_owned_model_card_for_save(
                    normalized,
                    sources,
                    default_enabled=False,
                )
            else:
                _strip_all_plugin_video_fields_from_model_card(normalized)
            await update_current(self, provider_id, normalized)

        update_wrapper._volcengine_model_save_wrapper = True  # type: ignore[attr-defined]
        update_wrapper._volcengine_model_save_original = update_current  # type: ignore[attr-defined]
        ProviderConfigService.update_provider = update_wrapper  # type: ignore[method-assign]
        _UPDATE_ORIGINAL, _UPDATE_WRAPPER = update_current, update_wrapper
        installed = True

    if installed:
        _DASHBOARD_LEASE_COUNT = 1
    return installed


def release_owned_dashboard_bridge() -> None:
    global _DASHBOARD_LEASE_COUNT
    global _SCHEMA_WRAPPER, _SCHEMA_ORIGINAL, _MODELS_WRAPPER, _MODELS_ORIGINAL
    global _CREATE_WRAPPER, _CREATE_ORIGINAL, _UPDATE_WRAPPER, _UPDATE_ORIGINAL

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

    _SCHEMA_WRAPPER = _SCHEMA_ORIGINAL = None
    _MODELS_WRAPPER = _MODELS_ORIGINAL = None
    _CREATE_WRAPPER = _CREATE_ORIGINAL = None
    _UPDATE_WRAPPER = _UPDATE_ORIGINAL = None


# Import-compatibility aliases used by existing installations/tests.
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
        provider_registry[:] = [item for item in provider_registry if item is not existing]
        provider_cls_map.pop(provider_type_name, None)

    return register_provider_adapter(
        provider_type_name,
        desc,
        provider_type=provider_type,
        default_config_tmpl=default_config_tmpl,
        provider_display_name=provider_display_name,
    )
