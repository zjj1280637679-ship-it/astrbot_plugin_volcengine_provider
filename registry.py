"""Plugin-owned Provider registration and narrow AstrBot Dashboard bridge.

Dashboard integration is capability-detected at runtime. Missing optional
Dashboard APIs may reduce UI/feedback integration, but must never prevent the
Provider adapters themselves from registering or loading.
"""

from __future__ import annotations

import copy
import hashlib
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
    OWNED_SOURCE_TYPES,
    VIDEO_INPUT_ENABLED_KEY,
    cleanup_owned_settings_on_source_change,
    consume_source_model_hints,
    normalize_owned_model_card_for_save,
    source_types,
    video_input_enabled,
)

PLUGIN_MODULE_MARKER = "astrbot_plugin_volcengine_provider"

# AstrBot 4.26/4.27 exposes one shared model-card schema.  A canonical plugin
# field added there without a condition would be rendered on foreign Provider
# cards too.  These keys exist only in Dashboard payloads and are stripped at
# the save boundary; one condition-scoped key is generated per owned Source.
_VIDEO_UI_KEY_PREFIX = "_volcengine_video_transport_ui_"

_DASHBOARD_LEASE_COUNT = 0
_SCHEMA_WRAPPER: Callable[..., Any] | None = None
_SCHEMA_ORIGINAL: Callable[..., Any] | None = None
_MODELS_WRAPPER: Callable[..., Any] | None = None
_MODELS_ORIGINAL: Callable[..., Any] | None = None
_CREATE_WRAPPER: Callable[..., Any] | None = None
_CREATE_ORIGINAL: Callable[..., Any] | None = None
_UPDATE_WRAPPER: Callable[..., Any] | None = None
_UPDATE_ORIGINAL: Callable[..., Any] | None = None


def _video_ui_key(source_id: str) -> str:
    """Return a deterministic non-persistent UI key for one Source ID."""

    digest = hashlib.sha256(source_id.encode("utf-8")).hexdigest()[:16]
    return f"{_VIDEO_UI_KEY_PREFIX}{digest}"


def _strip_video_ui_keys(provider_config: dict[str, Any]) -> None:
    """Remove every Dashboard-only transport field before host persistence."""

    for key in [
        key
        for key in provider_config
        if isinstance(key, str) and key.startswith(_VIDEO_UI_KEY_PREFIX)
    ]:
        provider_config.pop(key, None)


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
    types = source_types({"provider_sources": provider_sources}) if isinstance(
        provider_sources, list
    ) else {}
    if source_id and types.get(source_id) in OWNED_SOURCE_TYPES:
        ui_value = provider_config.get(_video_ui_key(source_id))
        if isinstance(ui_value, bool):
            # The visible UI value is the user's newest edit, so it intentionally
            # outranks the hidden canonical value copied into an edit response.
            provider_config[VIDEO_INPUT_ENABLED_KEY] = ui_value
    _strip_video_ui_keys(provider_config)


def _inject_model_card_video_control(payload: dict[str, Any]) -> dict[str, Any]:
    """Expose Source-conditioned transport toggles only on owned model cards.

    AstrBot's V4 renderer shows every schema item without a ``condition``.  A
    single canonical field would therefore leak into unrelated Provider cards.
    Instead, create one Dashboard-only field per currently configured owned
    Source, conditioned on that card's ``provider_source_id``.  The save bridge
    converts it back to ``volcengine_video_input_enabled`` and strips the UI key.
    """

    try:
        items = payload["config_schema"]["provider"]["items"]
    except (KeyError, TypeError):
        return payload
    if not isinstance(items, dict):
        return payload

    types = source_types(payload)
    owned_source_ids = [
        source_id
        for source_id, source_type in types.items()
        if source_type in OWNED_SOURCE_TYPES
    ]

    for source_id in owned_source_ids:
        ui_key = _video_ui_key(source_id)
        items.setdefault(
            ui_key,
            {
                "description": "视频请求通道（当前模型卡）",
                "type": "bool",
                "hint": (
                    "仅控制火山适配器是否按 Ark video_url 协议尝试发送本轮视频；"
                    "不是模型能力结论。关闭时保留 [Video] 文本占位。"
                ),
                "condition": {"provider_source_id": source_id},
            },
        )

    providers = payload.get("providers", [])
    if not isinstance(providers, list):
        return payload
    for provider in providers:
        if not isinstance(provider, dict):
            continue
        source_id = str(provider.get("provider_source_id") or "").strip()
        if types.get(source_id) not in OWNED_SOURCE_TYPES:
            continue
        # The canonical value remains ordinary data but has no shared schema
        # item, so it is not rendered on foreign cards.
        provider.setdefault(VIDEO_INPUT_ENABLED_KEY, video_input_enabled(provider))
        provider[_video_ui_key(source_id)] = provider[VIDEO_INPUT_ENABLED_KEY]
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


def acquire_owned_dashboard_bridge() -> bool:
    """Install only Dashboard wrappers supported by this AstrBot build.

    The Provider adapters are the required feature. Dashboard model feedback is
    independent.  The per-model transport UI is installed only when schema,
    create and update hooks are all available, so the plugin never exposes a UI
    control whose save semantics it cannot complete.
    """

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

    installed = False
    can_install_transport_ui = (
        schema_current is not None
        and create_current is not None
        and update_current is not None
    )

    if can_install_transport_ui:
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

    if can_install_transport_ui:
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
            normalize_owned_model_card_for_save(
                normalized,
                sources,
                default_enabled=False,
            )
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
            if (
                not normalized.get("provider_source_id")
                and existing.get("provider_source_id")
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

            if (
                new_type in OWNED_SOURCE_TYPES
                and VIDEO_INPUT_ENABLED_KEY not in normalized
                and old_type in OWNED_SOURCE_TYPES
                and isinstance(existing.get(VIDEO_INPUT_ENABLED_KEY), bool)
            ):
                normalized[VIDEO_INPUT_ENABLED_KEY] = existing[
                    VIDEO_INPUT_ENABLED_KEY
                ]

            normalize_owned_model_card_for_save(
                normalized,
                sources,
                default_enabled=False,
            )
            _strip_video_ui_keys(normalized)
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
