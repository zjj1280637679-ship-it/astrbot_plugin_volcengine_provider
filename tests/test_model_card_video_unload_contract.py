from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "AstrBot" / "data" / "plugins"))

from astrbot.dashboard.services.config_service import ProviderConfigService
from astrbot_plugin_volcengine_provider import registry
from astrbot_plugin_volcengine_provider.capabilities import dashboard_asset_bridge
from astrbot_plugin_volcengine_provider.capabilities import model_fields_bridge


def _release_everything() -> None:
    while dashboard_asset_bridge._DASHBOARD_ASSET_LEASE_COUNT > 0:
        dashboard_asset_bridge.release_dashboard_asset_bridge()
    while model_fields_bridge._FIELD_BRIDGE_LEASE_COUNT > 0:
        model_fields_bridge.release_model_fields_bridge()
    while registry._DASHBOARD_LEASE_COUNT > 0:
        registry.release_owned_dashboard_bridge()


def main() -> None:
    _release_everything()

    schema_original = ProviderConfigService.get_provider_schema
    create_original = ProviderConfigService.create_provider
    update_original = ProviderConfigService.update_provider

    try:
        from astrbot.dashboard.services.static_file_service import StaticFileService
    except (ImportError, ModuleNotFoundError):
        StaticFileService = None  # type: ignore[assignment,misc]
        static_original = None
    else:
        static_original = StaticFileService.resolve_static_file

    try:
        # Match plugin startup order. The asset bridge is the frontend half of
        # the source-scoped native Video option; the model-fields bridge is
        # installed only when that private-dialog adaptation is available.
        assert registry.acquire_owned_dashboard_bridge() is True
        asset_acquired = dashboard_asset_bridge.acquire_dashboard_asset_bridge()
        if asset_acquired:
            assert model_fields_bridge.acquire_model_fields_bridge() is True

        assert ProviderConfigService.get_provider_schema is not schema_original
        assert ProviderConfigService.create_provider is not create_original
        assert ProviderConfigService.update_provider is not update_original

        if asset_acquired:
            assert StaticFileService is not None
            assert StaticFileService.resolve_static_file is not static_original
            assert getattr(
                StaticFileService.resolve_static_file,
                "_volcengine_dashboard_asset_wrapper",
                False,
            )

        # Match plugin termination order. Every public host method must return
        # to the exact callable that existed before the plugin acquired it.
        if asset_acquired:
            dashboard_asset_bridge.release_dashboard_asset_bridge()
            model_fields_bridge.release_model_fields_bridge()
        registry.release_owned_dashboard_bridge()

        assert ProviderConfigService.get_provider_schema is schema_original
        assert ProviderConfigService.create_provider is create_original
        assert ProviderConfigService.update_provider is update_original
        assert dashboard_asset_bridge._DASHBOARD_ASSET_LEASE_COUNT == 0
        assert model_fields_bridge._FIELD_BRIDGE_LEASE_COUNT == 0
        assert registry._DASHBOARD_LEASE_COUNT == 0

        if asset_acquired:
            assert StaticFileService is not None
            assert StaticFileService.resolve_static_file is static_original
            assert dashboard_asset_bridge._CACHE_ROOT is None
            assert dashboard_asset_bridge._CACHE == {}
            assert dashboard_asset_bridge._MISSES == set()
            assert dashboard_asset_bridge._STATIC_FOLDER_ASSETS == {}

        print(
            "MODEL_CARD_VIDEO_UNLOAD_CONTRACT=OK "
            f"asset_bridge={'active' if asset_acquired else 'host-unavailable'}"
        )
    finally:
        _release_everything()
        # A failing assertion must not leave the test runner's imported host
        # mutated. Restore exact originals as a final safety net.
        ProviderConfigService.get_provider_schema = schema_original
        ProviderConfigService.create_provider = create_original
        ProviderConfigService.update_provider = update_original
        if StaticFileService is not None and static_original is not None:
            StaticFileService.resolve_static_file = static_original


if __name__ == "__main__":
    main()
