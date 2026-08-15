"""Backend half of Volcengine-owned model-card rows.

AstrBot exposes one shared schema, so this bridge contributes the definitions
for the lower Volcengine-only per-model request rows but marks those definitions
hidden in the shared schema by default. ``dashboard_asset_bridge`` may reveal
those rows only after AstrBot has cloned the schema for one concrete model-card
dialog and the selected Provider Source type is known to be owned by this plugin.
This module separately projects saved values only onto owned cards, strips forged
values from foreign cards, and normalizes create/update payloads.
"""

from __future__ import annotations

import copy
from collections.abc import Callable
from typing import Any

from .model_fields import (
    MODEL_FIELD_SCHEMA,
    MODEL_SETTING_KEYS,
    normalize_model_fields_for_save,
    project_model_fields,
    strip_model_fields,
)
from .model_scope import OWNED_SOURCE_TYPES, source_types

_FIELD_BRIDGE_LEASE_COUNT = 0
_SCHEMA_WRAPPER: Callable[..., Any] | None = None
_SCHEMA_ORIGINAL: Callable[..., Any] | None = None
_CREATE_WRAPPER: Callable[..., Any] | None = None
_CREATE_ORIGINAL: Callable[..., Any] | None = None
_UPDATE_WRAPPER: Callable[..., Any] | None = None
_UPDATE_ORIGINAL: Callable[..., Any] | None = None


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
    sources = config.get("provider_sources", []) if hasattr(config, "get") else []
    return sources if isinstance(sources, list) else []


def _providers_for_service(service: Any) -> list[dict[str, Any]]:
    config = getattr(service, "config", {})
    providers = config.get("provider", []) if hasattr(config, "get") else []
    return providers if isinstance(providers, list) else []


def _existing_provider_config(service: Any, provider_id: str) -> dict[str, Any]:
    manager = getattr(service, "provider_manager", None)
    getter = getattr(manager, "get_provider_config_by_id", None)
    if callable(getter):
        existing = getter(provider_id)
        if isinstance(existing, dict):
            return existing
    for provider in _providers_for_service(service):
        if str(provider.get("id") or "") == provider_id:
            return provider
    return {}


def _owned_source_type(service: Any, source_id: str) -> str:
    types = source_types({"provider_sources": _provider_sources_for_service(service)})
    source_type = types.get(str(source_id or "").strip(), "")
    return source_type if source_type in OWNED_SOURCE_TYPES else ""


def _inject_owned_model_fields(service: Any, payload: dict[str, Any]) -> dict[str, Any]:
    """Contribute hidden shared definitions and project values only to owned cards."""

    if not isinstance(payload, dict):
        return payload
    result = copy.deepcopy(payload)
    try:
        items = result["config_schema"]["provider"]["items"]
    except (KeyError, TypeError):
        return result
    if not isinstance(items, dict):
        return result

    # These metadata objects describe the *lower plugin request rows*, not the
    # native modalities checklist above them. Because this schema is shared by
    # every Provider Source, foreign dialogs must inherit the safe hidden state.
    # The frontend private-clone bridge is the only place allowed to reveal them
    # after the concrete dialog's Source type has been established.
    for key, metadata in MODEL_FIELD_SCHEMA.items():
        field = copy.deepcopy(metadata)
        field["invisible"] = True
        items[key] = field

    sources = result.get("provider_sources", [])
    types = source_types({"provider_sources": sources if isinstance(sources, list) else []})
    persisted_by_id = {
        str(provider.get("id") or ""): provider
        for provider in _providers_for_service(service)
        if isinstance(provider, dict) and provider.get("id")
    }

    providers = result.get("providers", [])
    if not isinstance(providers, list):
        return result
    for provider in providers:
        if not isinstance(provider, dict):
            continue
        source_id = str(provider.get("provider_source_id") or "").strip()
        provider_id = str(provider.get("id") or "")
        if types.get(source_id) in OWNED_SOURCE_TYPES:
            project_model_fields(provider, persisted_by_id.get(provider_id, provider))
        else:
            # Defensively remove forged/stale Volcengine values from foreign cards.
            strip_model_fields(provider)
    return result


def acquire_model_fields_bridge() -> bool:
    """Install reversible model-card projection/save wrappers when APIs exist."""

    global _FIELD_BRIDGE_LEASE_COUNT
    global _SCHEMA_WRAPPER, _SCHEMA_ORIGINAL
    global _CREATE_WRAPPER, _CREATE_ORIGINAL
    global _UPDATE_WRAPPER, _UPDATE_ORIGINAL

    if _FIELD_BRIDGE_LEASE_COUNT:
        _FIELD_BRIDGE_LEASE_COUNT += 1
        return True

    try:
        from astrbot.dashboard.services.config_service import ProviderConfigService
    except (ImportError, ModuleNotFoundError):
        return False

    schema_current = _unwrap_owned_wrapper(
        getattr(ProviderConfigService, "get_provider_schema", None),
        marker="_volcengine_model_fields_schema_wrapper",
        original="_volcengine_model_fields_schema_original",
    )
    create_current = _unwrap_owned_wrapper(
        getattr(ProviderConfigService, "create_provider", None),
        marker="_volcengine_model_fields_save_wrapper",
        original="_volcengine_model_fields_save_original",
    )
    update_current = _unwrap_owned_wrapper(
        getattr(ProviderConfigService, "update_provider", None),
        marker="_volcengine_model_fields_save_wrapper",
        original="_volcengine_model_fields_save_original",
    )
    if schema_current is None or create_current is None or update_current is None:
        return False

    def schema_wrapper(self) -> dict[str, Any]:
        result = schema_current(self)
        return _inject_owned_model_fields(self, result)

    schema_wrapper._volcengine_model_fields_schema_wrapper = True  # type: ignore[attr-defined]
    schema_wrapper._volcengine_model_fields_schema_original = schema_current  # type: ignore[attr-defined]
    ProviderConfigService.get_provider_schema = schema_wrapper  # type: ignore[method-assign]
    _SCHEMA_ORIGINAL, _SCHEMA_WRAPPER = schema_current, schema_wrapper

    async def create_wrapper(
        self,
        config: dict[str, Any],
        source_id: str | None = None,
    ) -> None:
        normalized = dict(config)
        if source_id:
            normalized["provider_source_id"] = source_id
        source_type = _owned_source_type(
            self,
            str(normalized.get("provider_source_id") or ""),
        )
        if source_type:
            normalize_model_fields_for_save(normalized)
        else:
            strip_model_fields(normalized)
        await create_current(self, normalized, source_id)

    create_wrapper._volcengine_model_fields_save_wrapper = True  # type: ignore[attr-defined]
    create_wrapper._volcengine_model_fields_save_original = create_current  # type: ignore[attr-defined]
    ProviderConfigService.create_provider = create_wrapper  # type: ignore[method-assign]
    _CREATE_ORIGINAL, _CREATE_WRAPPER = create_current, create_wrapper

    async def update_wrapper(
        self,
        provider_id: str,
        config: dict[str, Any],
    ) -> None:
        incoming_keys = set(config)
        normalized = dict(config)
        existing = _existing_provider_config(self, provider_id)
        if not normalized.get("provider_source_id") and existing.get("provider_source_id"):
            normalized["provider_source_id"] = existing["provider_source_id"]

        source_type = _owned_source_type(
            self,
            str(normalized.get("provider_source_id") or ""),
        )
        if source_type:
            # Non-Dashboard/older clients may omit the new fields entirely. Omission
            # means preserve; an explicitly empty row means clear and must not be
            # restored after normalization.
            for key in MODEL_SETTING_KEYS:
                if key not in incoming_keys and key in existing:
                    normalized[key] = copy.deepcopy(existing[key])
            normalize_model_fields_for_save(normalized)
        else:
            strip_model_fields(normalized)
        await update_current(self, provider_id, normalized)

    update_wrapper._volcengine_model_fields_save_wrapper = True  # type: ignore[attr-defined]
    update_wrapper._volcengine_model_fields_save_original = update_current  # type: ignore[attr-defined]
    ProviderConfigService.update_provider = update_wrapper  # type: ignore[method-assign]
    _UPDATE_ORIGINAL, _UPDATE_WRAPPER = update_current, update_wrapper

    _FIELD_BRIDGE_LEASE_COUNT = 1
    return True


def release_model_fields_bridge() -> None:
    """Release one lease and restore the previously wrapped host methods."""

    global _FIELD_BRIDGE_LEASE_COUNT
    global _SCHEMA_WRAPPER, _SCHEMA_ORIGINAL
    global _CREATE_WRAPPER, _CREATE_ORIGINAL
    global _UPDATE_WRAPPER, _UPDATE_ORIGINAL

    if _FIELD_BRIDGE_LEASE_COUNT <= 0:
        _FIELD_BRIDGE_LEASE_COUNT = 0
        return
    _FIELD_BRIDGE_LEASE_COUNT -= 1
    if _FIELD_BRIDGE_LEASE_COUNT:
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
            and _SCHEMA_ORIGINAL is not None
        ):
            ProviderConfigService.get_provider_schema = _SCHEMA_ORIGINAL  # type: ignore[method-assign]
        if (
            _CREATE_WRAPPER is not None
            and getattr(ProviderConfigService, "create_provider", None) is _CREATE_WRAPPER
            and _CREATE_ORIGINAL is not None
        ):
            ProviderConfigService.create_provider = _CREATE_ORIGINAL  # type: ignore[method-assign]
        if (
            _UPDATE_WRAPPER is not None
            and getattr(ProviderConfigService, "update_provider", None) is _UPDATE_WRAPPER
            and _UPDATE_ORIGINAL is not None
        ):
            ProviderConfigService.update_provider = _UPDATE_ORIGINAL  # type: ignore[method-assign]

    _SCHEMA_WRAPPER = _SCHEMA_ORIGINAL = None
    _CREATE_WRAPPER = _CREATE_ORIGINAL = None
    _UPDATE_WRAPPER = _UPDATE_ORIGINAL = None
