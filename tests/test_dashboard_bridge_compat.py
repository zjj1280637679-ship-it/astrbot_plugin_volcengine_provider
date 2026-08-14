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
    "upsert_provider_source",
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
        name: getattr(ProviderConfigService, name, None) for name in OPTIONAL_METHODS
    }

    try:
        # The current card UI needs schema + card create/update only. Source
        # upsert is deliberately irrelevant because Source-level video controls
        # were retired.
        if hasattr(ProviderConfigService, "upsert_provider_source"):
            delattr(ProviderConfigService, "upsert_provider_source")
        acquired = registry.acquire_owned_dashboard_bridge()
        assert acquired is True
        assert getattr(
            ProviderConfigService.get_provider_schema,
            "_volcengine_provider_schema_wrapper",
            False,
        )
        assert getattr(
            ProviderConfigService.create_provider,
            "_volcengine_model_save_wrapper",
            False,
        )
        registry.release_owned_dashboard_bridge()
        if originals.get("upsert_provider_source") is not None:
            setattr(
                ProviderConfigService,
                "upsert_provider_source",
                originals["upsert_provider_source"],
            )

        # Without model create/update boundaries, no card UI schema may be
        # exposed; the independent live-feedback model-list hook remains useful.
        for name in ("create_provider", "update_provider"):
            if hasattr(ProviderConfigService, name):
                delattr(ProviderConfigService, name)

        acquired = registry.acquire_owned_dashboard_bridge()
        assert acquired is True
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

        # The model-card bridge does not depend on the independent model-list
        # feedback hook.
        for name in ("create_provider", "update_provider"):
            if originals.get(name) is not None:
                setattr(ProviderConfigService, name, originals[name])
        if hasattr(ProviderConfigService, "list_provider_source_models"):
            delattr(ProviderConfigService, "list_provider_source_models")
        assert registry.acquire_owned_dashboard_bridge() is True
        assert getattr(
            ProviderConfigService.get_provider_schema,
            "_volcengine_provider_schema_wrapper",
            False,
        )
        registry.release_owned_dashboard_bridge()

        # With only get_provider_schema left, there is no safe/useful bridge:
        # displaying card state without create/update boundaries is deceptive.
        for name in ("create_provider", "update_provider"):
            if hasattr(ProviderConfigService, name):
                delattr(ProviderConfigService, name)
        if hasattr(ProviderConfigService, "upsert_provider_source"):
            delattr(ProviderConfigService, "upsert_provider_source")
        assert registry.acquire_owned_dashboard_bridge() is False
        assert registry._DASHBOARD_LEASE_COUNT == 0

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
