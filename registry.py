"""Plugin-owned registration and provider-schema extensions."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from astrbot.core.provider.register import (
    provider_cls_map,
    provider_registry,
    register_provider_adapter,
)

PLUGIN_MODULE_MARKER = "astrbot_plugin_volcengine_provider"

ARK_PROVIDER_TYPE = "volcengine_ark_chat_completion"
AGENT_PLAN_PROVIDER_TYPE = "volcengine_agent_plan_chat_completion"
# Kept only to read any configuration saved by the short-lived 0.1.6 build.
# From 0.1.7 onward, ``modalities`` is the single authoritative model-level
# capability set, matching AstrBot's native image/audio/tool switches.
ARK_VIDEO_INPUT_KEY = "volcengine_ark_video_input"
AGENT_PLAN_VIDEO_INPUT_KEY = "volcengine_agent_plan_video_input"

_SCHEMA_LEASE_COUNT = 0
_SCHEMA_WRAPPER: Callable[..., dict[str, Any]] | None = None
_SCHEMA_ORIGINAL: Callable[..., dict[str, Any]] | None = None


def _inject_volcengine_video_fields(payload: dict[str, Any]) -> dict[str, Any]:
    """Complete AstrBot's native model-capability selector with video.

    AstrBot 4.26 already models text/image/audio/tool support in one per-model
    ``modalities`` list.  Video belongs to that same axis.  The Dashboard's
    translated label list is compiled with only four entries, so appending an
    option alone renders a blank checkbox.  This response adapter appends the
    option and its visible label together after AstrBot has completed i18n
    conversion.  It does not modify AstrBot or Dashboard files.
    """

    try:
        items = payload["config_schema"]["provider"]["items"]
    except (KeyError, TypeError):
        return payload
    if not isinstance(items, dict):
        return payload

    modalities = items.get("modalities")
    if not isinstance(modalities, dict):
        return payload

    options = modalities.get("options")
    if not isinstance(options, list):
        return payload
    # ConfigMetadataI18n keeps nested lists by reference.  Mutating ``options``
    # in place would therefore alter process-global CONFIG_METADATA_2 and leave
    # a ghost fifth option after this plugin releases its method wrapper.
    options = list(options)
    modalities["options"] = options
    if "video" not in options:
        options.append("video")

    # ConfigMetadataI18n replaces the original labels list with a translation
    # key.  The Dashboard can therefore translate only the four labels compiled
    # into AstrBot 4.26.  Supply the complete visible list together so index 4
    # cannot become an unlabeled checkbox.
    label_by_option = {
        "text": "文本",
        "image": "图像",
        "audio": "音频",
        "tool_use": "工具使用",
        "video": "视频",
    }
    modalities["labels"] = [label_by_option.get(option, option) for option in options]
    return payload


def acquire_owned_provider_schema() -> None:
    """Install one reversible adapter on AstrBot's provider-schema service."""

    global _SCHEMA_LEASE_COUNT, _SCHEMA_WRAPPER, _SCHEMA_ORIGINAL
    if _SCHEMA_LEASE_COUNT:
        _SCHEMA_LEASE_COUNT += 1
        return

    from astrbot.dashboard.services.config_service import ProviderConfigService

    current = ProviderConfigService.get_provider_schema
    if getattr(current, "_volcengine_provider_schema_wrapper", False):
        current = getattr(current, "_volcengine_provider_schema_original")

    def get_provider_schema_with_volcengine_video(self) -> dict[str, Any]:
        payload = current(self)
        return _inject_volcengine_video_fields(payload)

    get_provider_schema_with_volcengine_video._volcengine_provider_schema_wrapper = (  # type: ignore[attr-defined]
        True
    )
    get_provider_schema_with_volcengine_video._volcengine_provider_schema_original = (  # type: ignore[attr-defined]
        current
    )
    ProviderConfigService.get_provider_schema = (  # type: ignore[method-assign]
        get_provider_schema_with_volcengine_video
    )
    _SCHEMA_ORIGINAL = current
    _SCHEMA_WRAPPER = get_provider_schema_with_volcengine_video
    _SCHEMA_LEASE_COUNT = 1


def release_owned_provider_schema() -> None:
    """Release one lease and remove only this plugin's active adapter."""

    global _SCHEMA_LEASE_COUNT, _SCHEMA_WRAPPER, _SCHEMA_ORIGINAL
    if _SCHEMA_LEASE_COUNT <= 0:
        return
    _SCHEMA_LEASE_COUNT -= 1
    if _SCHEMA_LEASE_COUNT:
        return

    from astrbot.dashboard.services.config_service import ProviderConfigService

    if (
        _SCHEMA_WRAPPER is not None
        and _SCHEMA_ORIGINAL is not None
        and ProviderConfigService.get_provider_schema is _SCHEMA_WRAPPER
    ):
        ProviderConfigService.get_provider_schema = _SCHEMA_ORIGINAL  # type: ignore[method-assign]
    _SCHEMA_WRAPPER = None
    _SCHEMA_ORIGINAL = None


def register_owned_provider(
    provider_type_name: str,
    desc: str,
    *,
    provider_type,
    default_config_tmpl: dict,
    provider_display_name: str,
):
    """Register once and replace only an older class owned by this plugin.

    AstrBot 4.26 has a process-global registry without plugin ownership or an
    unregister hook.  A plugin reload must therefore remove its own previous
    metadata before registering the new class.  A foreign collision fails
    closed instead of silently hijacking another adapter.
    """

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
