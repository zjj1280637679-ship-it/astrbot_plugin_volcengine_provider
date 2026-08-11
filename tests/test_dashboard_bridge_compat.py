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

    # Official supported hosts should install whatever bridge APIs they expose.
    acquired = registry.acquire_owned_dashboard_bridge()
    assert acquired is True
    registry.release_owned_dashboard_bridge()

    originals = {
        name: getattr(ProviderConfigService, name, None)
        for name in OPTIONAL_METHODS
    }

    try:
        # A host that lacks the newer model-list/save hooks must still load.
        for name in (
            "list_provider_source_models",
            "create_provider",
            "update_provider",
        ):
            if hasattr(ProviderConfigService, name):
                delattr(ProviderConfigService, name)

        acquired = registry.acquire_owned_dashboard_bridge()
        assert acquired is True  # get_provider_schema is enough for a partial bridge.
        assert getattr(
            ProviderConfigService.get_provider_schema,
            "_volcengine_provider_schema_wrapper",
            False,
        )
        registry.release_owned_dashboard_bridge()

        # Even a build with no recognized Dashboard hook must degrade to no-op,
        # not raise during plugin construction.
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
