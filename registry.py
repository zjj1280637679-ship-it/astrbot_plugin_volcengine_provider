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
# AstrBot does not yet expose video as a native provider modality. Keep the
# provider-owned switch scoped to each Volcengine source; old model cards that
# saved ``video`` in ``modalities`` remain readable as a compatibility fallback.
ARK_VIDEO_INPUT_KEY = "volcengine_ark_video_input"
AGENT_PLAN_VIDEO_INPUT_KEY = "volcengine_agent_plan_video_input"

_SCHEMA_LEASE_COUNT = 0
_SCHEMA_WRAPPER: Callable[..., dict[str, Any]] | None = None
_SCHEMA_ORIGINAL: Callable[..., dict[str, Any]] | None = None


def _inject_volcengine_video_control_fields(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Expose only Volcengine-owned video switches in AstrBot's shared schema.

    AstrBot 4.27 has no provider-specific schema-extension registry and its
    native ``modalities`` axis stops at text/image/audio/tool_use. Injecting a
    fifth common modality would affect every provider card. Instead, add two
    boolean field definitions; AstrBotConfig renders them only on Volcengine
    source templates that actually contain the corresponding key.
    """

    try:
        items = payload["config_schema"]["provider"]["items"]
    except (KeyError, TypeError):
        return payload
    if not isinstance(items, dict):
        return payload

    items.setdefault(
        ARK_VIDEO_INPUT_KEY,
        {
            "description": "视频输入",
            "type": "bool",
            "hint": "仅控制火山方舟普通 API 的视频附件输入；关闭时视频会保留为 [Video] 文本占位。",
            "condition": {"type": ARK_PROVIDER_TYPE},
        },
    )
    items.setdefault(
        AGENT_PLAN_VIDEO_INPUT_KEY,
        {
            "description": "视频输入",
            "type": "bool",
            "hint": "仅控制火山方舟 Agent Plan 的视频附件输入；关闭时视频会保留为 [Video] 文本占位。",
            "condition": {"type": AGENT_PLAN_PROVIDER_TYPE},
        },
    )
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

    def get_provider_schema_with_volcengine_controls(self) -> dict[str, Any]:
        payload = current(self)
        return _inject_volcengine_video_control_fields(payload)

    get_provider_schema_with_volcengine_controls._volcengine_provider_schema_wrapper = (  # type: ignore[attr-defined]
        True
    )
    get_provider_schema_with_volcengine_controls._volcengine_provider_schema_original = (  # type: ignore[attr-defined]
        current
    )
    ProviderConfigService.get_provider_schema = (  # type: ignore[method-assign]
        get_provider_schema_with_volcengine_controls
    )
    _SCHEMA_ORIGINAL = current
    _SCHEMA_WRAPPER = get_provider_schema_with_volcengine_controls
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
