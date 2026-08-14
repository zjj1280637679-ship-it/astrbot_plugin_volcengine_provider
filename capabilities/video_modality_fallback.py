"""Reversible backend fallback for the model-card Video modality.

AstrBot exposes one shared model-card schema.  The preferred UI path remains
``dashboard_asset_bridge`` which edits each dialog's private schema clone after
its Provider Source type is known.  This module adds a deliberately small
fallback to the shared ``modalities`` metadata so an already-cached or otherwise
unpatched Dashboard bundle still receives a fifth Video checkbox.

The fallback is marked in schema metadata.  A compatible frontend bridge removes
that marked option from foreign Source dialogs.  If the frontend bridge does not
run, the only intended UI side effect is a temporary Video checkbox on foreign
cards; create/update wrappers strip that option again at the persistence boundary.
"""

from __future__ import annotations

import copy
from collections.abc import Callable
from typing import Any

from .model_scope import OWNED_SOURCE_TYPES, source_types

VIDEO_MODALITY_FALLBACK_MARKER = "_volcengine_video_modality_fallback"

_FALLBACK_LABELS = {
    "text": "文本 / Text",
    "image": "图像 / Image",
    "audio": "音频 / Audio",
    "tool_use": "工具使用 / Tool use",
    "video": "视频 / Video",
}

_FALLBACK_LEASE_COUNT = 0
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
            if not isinstance(provider, dict):
                continue
            if str(provider.get("id") or "") == provider_id:
                return provider
    return {}


def _owned_source_type(service: Any, source_id: str) -> str:
    types = source_types({"provider_sources": _provider_sources_for_service(service)})
    source_type = types.get(str(source_id or "").strip(), "")
    return source_type if source_type in OWNED_SOURCE_TYPES else ""


def _fallback_labels(options: list[object]) -> list[str]:
    return [_FALLBACK_LABELS.get(str(option), str(option)) for option in options]


def inject_video_modality_fallback(payload: dict[str, Any]) -> dict[str, Any]:
    """Add a marked fifth Video option without mutating the host response.

    If AstrBot already exposes ``video`` natively, no marker is added and the
    host metadata is left untouched.  This distinction lets the frontend avoid
    deleting a future host-native Video capability from foreign providers.
    """

    if not isinstance(payload, dict):
        return payload
    result = copy.deepcopy(payload)
    try:
        items = result["config_schema"]["provider"]["items"]
    except (KeyError, TypeError):
        return result
    if not isinstance(items, dict):
        return result

    modalities = items.get("modalities")
    if not isinstance(modalities, dict):
        return result
    options = modalities.get("options")
    if not isinstance(options, list):
        return result

    if "video" in options:
        # Native/future host support must never be reclassified as plugin fallback.
        modalities.pop(VIDEO_MODALITY_FALLBACK_MARKER, None)
        return result

    next_options = [*options, "video"]
    modalities["options"] = next_options
    labels = modalities.get("labels")
    if isinstance(labels, list):
        next_labels = list(labels[: len(options)])
        while len(next_labels) < len(options):
            next_labels.append(str(options[len(next_labels)]))
        next_labels.append(_FALLBACK_LABELS["video"])
        modalities["labels"] = next_labels
    else:
        # AstrBot 4.27 normally stores an i18n key string here.  A cached frontend
        # cannot extend that translation array, so the fallback uses stable
        # bilingual labels.  The preferred source-scoped JS bridge restores normal
        # locale-specific labels on its private dialog clone.
        modalities["labels"] = _fallback_labels(next_options)
    modalities[VIDEO_MODALITY_FALLBACK_MARKER] = True
    return result


def strip_video_modality(provider_config: dict[str, Any]) -> bool:
    """Remove only ``video`` from a concrete card's modalities list."""

    modalities = provider_config.get("modalities")
    if not isinstance(modalities, list) or "video" not in modalities:
        return False
    provider_config["modalities"] = [value for value in modalities if value != "video"]
    return True


def acquire_video_modality_fallback_bridge() -> bool:
    """Install schema fallback plus foreign-card save guards when APIs exist."""

    global _FALLBACK_LEASE_COUNT
    global _SCHEMA_WRAPPER, _SCHEMA_ORIGINAL
    global _CREATE_WRAPPER, _CREATE_ORIGINAL
    global _UPDATE_WRAPPER, _UPDATE_ORIGINAL

    if _FALLBACK_LEASE_COUNT:
        _FALLBACK_LEASE_COUNT += 1
        return True

    try:
        from astrbot.dashboard.services.config_service import ProviderConfigService
    except (ImportError, ModuleNotFoundError):
        return False

    schema_current = _unwrap_owned_wrapper(
        getattr(ProviderConfigService, "get_provider_schema", None),
        marker="_volcengine_video_fallback_schema_wrapper",
        original="_volcengine_video_fallback_schema_original",
    )
    create_current = _unwrap_owned_wrapper(
        getattr(ProviderConfigService, "create_provider", None),
        marker="_volcengine_video_fallback_save_wrapper",
        original="_volcengine_video_fallback_save_original",
    )
    update_current = _unwrap_owned_wrapper(
        getattr(ProviderConfigService, "update_provider", None),
        marker="_volcengine_video_fallback_save_wrapper",
        original="_volcengine_video_fallback_save_original",
    )
    if schema_current is None or create_current is None or update_current is None:
        return False

    def schema_wrapper(self) -> dict[str, Any]:
        return inject_video_modality_fallback(schema_current(self))

    schema_wrapper._volcengine_video_fallback_schema_wrapper = True  # type: ignore[attr-defined]
    schema_wrapper._volcengine_video_fallback_schema_original = schema_current  # type: ignore[attr-defined]
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
        if not _owned_source_type(
            self,
            str(normalized.get("provider_source_id") or ""),
        ):
            strip_video_modality(normalized)
        await create_current(self, normalized, source_id)

    create_wrapper._volcengine_video_fallback_save_wrapper = True  # type: ignore[attr-defined]
    create_wrapper._volcengine_video_fallback_save_original = create_current  # type: ignore[attr-defined]
    ProviderConfigService.create_provider = create_wrapper  # type: ignore[method-assign]
    _CREATE_ORIGINAL, _CREATE_WRAPPER = create_current, create_wrapper

    async def update_wrapper(
        self,
        provider_id: str,
        config: dict[str, Any],
    ) -> None:
        normalized = dict(config)
        existing = _existing_provider_config(self, provider_id)
        if not normalized.get("provider_source_id") and existing.get("provider_source_id"):
            normalized["provider_source_id"] = existing["provider_source_id"]
        if not _owned_source_type(
            self,
            str(normalized.get("provider_source_id") or ""),
        ):
            strip_video_modality(normalized)
        await update_current(self, provider_id, normalized)

    update_wrapper._volcengine_video_fallback_save_wrapper = True  # type: ignore[attr-defined]
    update_wrapper._volcengine_video_fallback_save_original = update_current  # type: ignore[attr-defined]
    ProviderConfigService.update_provider = update_wrapper  # type: ignore[method-assign]
    _UPDATE_ORIGINAL, _UPDATE_WRAPPER = update_current, update_wrapper

    _FALLBACK_LEASE_COUNT = 1
    return True


def release_video_modality_fallback_bridge() -> None:
    """Release one lease and restore exactly the host wrappers we replaced."""

    global _FALLBACK_LEASE_COUNT
    global _SCHEMA_WRAPPER, _SCHEMA_ORIGINAL
    global _CREATE_WRAPPER, _CREATE_ORIGINAL
    global _UPDATE_WRAPPER, _UPDATE_ORIGINAL

    if _FALLBACK_LEASE_COUNT <= 0:
        _FALLBACK_LEASE_COUNT = 0
        return
    _FALLBACK_LEASE_COUNT -= 1
    if _FALLBACK_LEASE_COUNT:
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
