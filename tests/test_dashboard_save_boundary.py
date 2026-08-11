from __future__ import annotations

import asyncio
import copy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "AstrBot" / "data" / "plugins"))

from astrbot.dashboard.services.config_service import ProviderConfigService
from astrbot_plugin_volcengine_provider import registry
from astrbot_plugin_volcengine_provider.capabilities import (
    ARK_PROVIDER_TYPE,
    VIDEO_INPUT_ENABLED_KEY,
)


class FakeManager:
    def __init__(self, providers: list[dict]) -> None:
        self.providers = providers
        self.created: list[dict] = []
        self.updated: list[tuple[str, dict]] = []

    async def create_provider(self, config: dict) -> None:
        self.created.append(copy.deepcopy(config))

    async def update_provider(self, provider_id: str, config: dict) -> None:
        self.updated.append((provider_id, copy.deepcopy(config)))

    def get_provider_config_by_id(self, provider_id: str, **_: object) -> dict | None:
        for provider in self.providers:
            if provider.get("id") == provider_id:
                return copy.deepcopy(provider)
        return None


class FakeService:
    def __init__(self) -> None:
        self.config = {
            "provider_sources": [
                {"id": "ark-A", "type": ARK_PROVIDER_TYPE},
                {"id": "foreign-A", "type": "openai_chat_completion"},
            ],
            "provider": [
                {
                    "id": "ark-A/existing",
                    "provider_source_id": "ark-A",
                    "model": "existing",
                    VIDEO_INPUT_ENABLED_KEY: False,
                },
                {
                    "id": "foreign-A/existing",
                    "provider_source_id": "foreign-A",
                    "model": "existing",
                },
            ],
        }
        self.provider_manager = FakeManager(self.config["provider"])


def _has_ui_key(config: dict) -> bool:
    return any(
        isinstance(key, str) and key.startswith(registry._VIDEO_UI_KEY_PREFIX)
        for key in config
    )


async def exercise() -> None:
    while registry._DASHBOARD_LEASE_COUNT > 0:
        registry.release_owned_dashboard_bridge()

    assert registry.acquire_owned_dashboard_bridge() is True
    try:
        service = FakeService()
        ark_ui = registry._video_ui_key("ark-A")
        foreign_ui = registry._video_ui_key("foreign-A")

        # New owned card: Dashboard-only True becomes the canonical transport
        # setting before ProviderManager sees the config; the UI key disappears.
        await ProviderConfigService.create_provider(
            service,
            {
                "id": "ark-A/new",
                "model": "new",
                ark_ui: True,
            },
            "ark-A",
        )
        created = service.provider_manager.created[-1]
        assert created["provider_source_id"] == "ark-A"
        assert created[VIDEO_INPUT_ENABLED_KEY] is True
        assert not _has_ui_key(created)

        # New owned card with no UI interaction gets only the transport default.
        await ProviderConfigService.create_provider(
            service,
            {"id": "ark-A/default", "model": "default"},
            "ark-A",
        )
        created_default = service.provider_manager.created[-1]
        assert created_default[VIDEO_INPUT_ENABLED_KEY] is False
        assert not _has_ui_key(created_default)

        # A foreign Source cannot turn a forged Dashboard UI key into Volcengine
        # state.  The ephemeral key is stripped and the rest passes through.
        await ProviderConfigService.create_provider(
            service,
            {
                "id": "foreign-A/new",
                "model": "new",
                foreign_ui: True,
                "custom_extra_body": {"foreign": "kept"},
            },
            "foreign-A",
        )
        foreign_created = service.provider_manager.created[-1]
        assert VIDEO_INPUT_ENABLED_KEY not in foreign_created
        assert not _has_ui_key(foreign_created)
        assert foreign_created["custom_extra_body"] == {"foreign": "kept"}

        # Existing owned card: the visible UI edit is newer than the hidden
        # canonical value copied into the edit payload, so True must win.
        await ProviderConfigService.update_provider(
            service,
            "ark-A/existing",
            {
                "id": "ark-A/existing",
                "provider_source_id": "ark-A",
                "model": "existing",
                VIDEO_INPUT_ENABLED_KEY: False,
                ark_ui: True,
            },
        )
        _, updated = service.provider_manager.updated[-1]
        assert updated[VIDEO_INPUT_ENABLED_KEY] is True
        assert not _has_ui_key(updated)

        # Moving an owned card to a foreign Source removes plugin-owned state;
        # AstrBot/native/foreign fields remain untouched.
        await ProviderConfigService.update_provider(
            service,
            "ark-A/existing",
            {
                "id": "ark-A/existing",
                "provider_source_id": "foreign-A",
                "model": "existing",
                VIDEO_INPUT_ENABLED_KEY: True,
                ark_ui: True,
                "modalities": ["text", "video"],
                "custom_extra_body": {"foreign": "kept"},
            },
        )
        _, moved = service.provider_manager.updated[-1]
        assert VIDEO_INPUT_ENABLED_KEY not in moved
        assert not _has_ui_key(moved)
        assert moved["modalities"] == ["text", "video"]
        assert moved["custom_extra_body"] == {"foreign": "kept"}
    finally:
        while registry._DASHBOARD_LEASE_COUNT > 0:
            registry.release_owned_dashboard_bridge()


if __name__ == "__main__":
    asyncio.run(exercise())
    print("DASHBOARD_SAVE_BOUNDARY=OK")
