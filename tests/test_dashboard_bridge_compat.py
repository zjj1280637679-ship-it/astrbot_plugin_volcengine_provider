from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "AstrBot" / "data" / "plugins"))

from astrbot.dashboard.services.config_service import ProviderConfigService
from astrbot_plugin_volcengine_provider import registry


OPTIONAL_METHODS = (
    "get_provider_schema",
    "list_provider_source_models",
    "create_provider",
    "update_provider",
)


def _release_all() -> None:
    while registry._DASHBOARD_LEASE_COUNT > 0:
        registry.release_owned_dashboard_bridge()


def main() -> None:
    _release_all()

    # Official supported hosts should install their available bridge set.
    acquired = registry.acquire_owned_dashboard_bridge()
    assert acquired is True
    registry.release_owned_dashboard_bridge()

    originals = {
        name: getattr(ProviderConfigService, name, None)
        for name in OPTIONAL_METHODS
    }

    try:
        # If create/update are unavailable, do NOT expose the transport UI:
        # showing a setting whose save semantics cannot be completed is worse
        # than a local UI degradation.  The independent live-feedback bridge
        # may still operate if the model-list API exists.
        for name in ("create_provider", "update_provider"):
            if hasattr(ProviderConfigService, name):
                delattr(ProviderConfigService, name)

        acquired = registry.acquire_owned_dashboard_bridge()
        assert acquired is True  # list_provider_source_models remains useful.
        assert not getattr(
            ProviderConfigService.get_provider_schema,
            "_volcengine_provider_schema_wrapper",
            False,
        )
        assert getattr(
            ProviderConfigService.list_provider_source_models,
            "_volcengine_source_models_wrapper",
            False,
        )
        registry.release_owned_dashboard_bridge()

        # With only get_provider_schema left, there is no safe/useful bridge:
        # the Provider itself must still load and plugin construction must not
        # raise, but the Dashboard enhancement becomes a no-op.
        if hasattr(ProviderConfigService, "list_provider_source_models"):
            delattr(ProviderConfigService, "list_provider_source_models")
        assert registry.acquire_owned_dashboard_bridge() is False
        assert registry._DASHBOARD_LEASE_COUNT == 0
        assert not getattr(
            ProviderConfigService.get_provider_schema,
            "_volcengine_provider_schema_wrapper",
            False,
        )

        # Even a build with no recognized Dashboard hook must also be a no-op.
        if hasattr(ProviderConfigService, "get_provider_schema"):
            delattr(ProviderConfigService, "get_provider_schema")
        assert registry.acquire_owned_dashboard_bridge() is False
        assert registry._DASHBOARD_LEASE_COUNT == 0
    finally:
        _release_all()
        for name, method in originals.items():
            if method is not None:
                setattr(ProviderConfigService, name, method)
            elif hasattr(ProviderConfigService, name):
                delattr(ProviderConfigService, name)

    print("DASHBOARD_BRIDGE_COMPAT=OK")


if __name__ == "__main__":
    main()
