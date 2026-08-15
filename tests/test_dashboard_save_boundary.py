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
    AGENT_PLAN_PROVIDER_TYPE,
    ARK_PROVIDER_TYPE,
    MODEL_FIELD_SCHEMA,
    VIDEO_INPUT_ENABLED_KEY,
    VIDEO_INPUT_ENABLED_UI_KEY,
    VIDEO_INPUT_PROFILE_KEY,
    acquire_model_fields_bridge,
    release_model_fields_bridge,
)
from astrbot_plugin_volcengine_provider.capabilities import model_fields_bridge


class FakeManager:
    def __init__(self, providers: list[dict]) -> None:
        self.providers = providers

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
                {"id": "plan-A", "type": AGENT_PLAN_PROVIDER_TYPE},
                {"id": "foreign-A", "type": "openai_chat_completion"},
            ],
            "provider": [
                {
                    "id": "ark-A/card",
                    "provider_source_id": "ark-A",
                    "model": "same-model",
                    "modalities": ["text", "image"],
                    VIDEO_INPUT_ENABLED_KEY: True,
                    VIDEO_INPUT_PROFILE_KEY: "compressed",
                },
                {
                    "id": "foreign-A/card",
                    "provider_source_id": "foreign-A",
                    "model": "same-model",
                },
            ],
        }
        self.provider_manager = FakeManager(self.config["provider"])
        self.created: list[dict] = []
        self.updated: list[tuple[str, dict]] = []


def _release_all() -> None:
    while model_fields_bridge._FIELD_BRIDGE_LEASE_COUNT > 0:
        release_model_fields_bridge()
    while registry._DASHBOARD_LEASE_COUNT > 0:
        registry.release_owned_dashboard_bridge()


async def exercise() -> None:
    _release_all()
    originals = {
        "get_provider_schema": ProviderConfigService.get_provider_schema,
        "create_provider": ProviderConfigService.create_provider,
        "update_provider": ProviderConfigService.update_provider,
    }

    def base_schema(self) -> dict:
        return {
            "config_schema": {
                "provider": {
                    "items": {
                        "modalities": {
                            "type": "list",
                            "options": ["text", "image", "audio", "tool_use"],
                        }
                    },
                    "config_template": {},
                }
            },
            "provider_sources": copy.deepcopy(self.config["provider_sources"]),
            "providers": copy.deepcopy(self.config["provider"]),
        }

    async def record_create(self, config: dict, source_id: str | None = None) -> None:
        saved = copy.deepcopy(config)
        if source_id:
            saved["provider_source_id"] = source_id
        self.created.append(saved)

    async def record_update(self, provider_id: str, config: dict) -> None:
        self.updated.append((provider_id, copy.deepcopy(config)))

    ProviderConfigService.get_provider_schema = base_schema
    ProviderConfigService.create_provider = record_create
    ProviderConfigService.update_provider = record_update

    try:
        # Match plugin startup order: compatibility/feedback bridge first, then
        # the per-card value/persistence bridge around it.  The frontend asset
        # bridge is intentionally not part of this save-boundary unit: it acts on
        # a later private model-dialog clone and is a different concrete object.
        assert registry.acquire_owned_dashboard_bridge() is True
        assert acquire_model_fields_bridge() is True
        service = FakeService()

        projected = ProviderConfigService.get_provider_schema(service)
        items = projected["config_schema"]["provider"]["items"]
        assert items["modalities"]["options"] == [
            "text",
            "image",
            "audio",
            "tool_use",
        ]
        assert "video" not in items["modalities"]["options"]

        # ``items`` here is still the host-shared metadata-definition object.  It
        # must contain the complete 0.1.19 definitions so an owned private clone
        # can later render them, but its safe visibility state is hidden because
        # this shared object has no concrete model-card Source identity.  Do not
        # equate this state with the later Ark/Plan private-clone visibility.
        for key, metadata in MODEL_FIELD_SCHEMA.items():
            actual = copy.deepcopy(items[key])
            assert actual.pop("invisible") is True
            assert actual == metadata, (key, actual, metadata)

        # These are concrete existing model-card value copies.  The owned card
        # gets its saved Volcengine values projected; the foreign card gets none.
        owned, foreign = projected["providers"]
        assert owned["modalities"] == ["text", "image", "video"]
        assert owned[VIDEO_INPUT_PROFILE_KEY] == "compressed"
        for key in MODEL_FIELD_SCHEMA:
            assert key not in foreign

        # The create/save boundary is where the upper native model-card Video
        # selection becomes normal persisted ``modalities`` state plus the
        # runtime mirror.  This is independent from whether the frontend checkbox
        # renderer was involved in constructing the test payload.
        await ProviderConfigService.create_provider(
            service,
            {
                "id": "ark-A/new",
                "provider_source_id": "ark-A",
                "modalities": ["text", "video"],
                VIDEO_INPUT_PROFILE_KEY: "original",
            },
            "ark-A",
        )
        saved_owned = service.created[-1]
        assert saved_owned[VIDEO_INPUT_ENABLED_KEY] is True
        assert saved_owned["modalities"] == ["text", "video"]
        assert saved_owned[VIDEO_INPUT_PROFILE_KEY] == "original"
        assert VIDEO_INPUT_ENABLED_UI_KEY not in saved_owned

        # A forged plugin UI/runtime state on a foreign card is erased at the
        # save wrapper boundary and cannot become persistent foreign state.
        await ProviderConfigService.create_provider(
            service,
            {
                "id": "foreign-A/new",
                "provider_source_id": "foreign-A",
                VIDEO_INPUT_ENABLED_UI_KEY: True,
                VIDEO_INPUT_ENABLED_KEY: True,
                VIDEO_INPUT_PROFILE_KEY: "compressed",
            },
            "foreign-A",
        )
        saved_foreign = service.created[-1]
        assert VIDEO_INPUT_ENABLED_UI_KEY not in saved_foreign
        assert VIDEO_INPUT_ENABLED_KEY not in saved_foreign
        assert VIDEO_INPUT_PROFILE_KEY not in saved_foreign

        await ProviderConfigService.update_provider(
            service,
            "ark-A/card",
            {
                "id": "ark-A/card",
                "provider_source_id": "ark-A",
                "modalities": ["text", "image"],
                VIDEO_INPUT_PROFILE_KEY: "compressed",
            },
        )
        _, saved_update = service.updated[-1]
        assert saved_update[VIDEO_INPUT_ENABLED_KEY] is False
        assert saved_update["modalities"] == ["text", "image"]
        assert saved_update[VIDEO_INPUT_PROFILE_KEY] == "compressed"
        assert VIDEO_INPUT_ENABLED_UI_KEY not in saved_update

        print("DASHBOARD_SAVE_BOUNDARY=OK")
    finally:
        _release_all()
        for name, method in originals.items():
            setattr(ProviderConfigService, name, method)


if __name__ == "__main__":
    asyncio.run(exercise())
