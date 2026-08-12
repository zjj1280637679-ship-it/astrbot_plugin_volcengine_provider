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
    LEGACY_MODEL_VIDEO_INPUT_KEY,
    LEGACY_SOURCE_VIDEO_KEYS,
    VIDEO_CONTROLS_VISIBLE_KEY,
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
                {
                    "id": "ark-A",
                    "provider": "volcengine",
                    "type": ARK_PROVIDER_TYPE,
                },
                {
                    "id": "plan-A",
                    "provider": "volcengine",
                    "type": AGENT_PLAN_PROVIDER_TYPE,
                },
                {
                    "id": "foreign-A",
                    "provider": "openai",
                    "type": "openai_chat_completion",
                },
            ],
            "provider": [
                {
                    "id": "ark-A/a",
                    "provider_source_id": "ark-A",
                    "model": "same-model",
                    VIDEO_INPUT_ENABLED_KEY: True,
                },
                {
                    "id": "ark-A/b",
                    "provider_source_id": "ark-A",
                    "model": "same-model",
                    VIDEO_INPUT_ENABLED_KEY: False,
                },
                {
                    "id": "plan-A/a",
                    "provider_source_id": "plan-A",
                    "model": "same-model",
                    VIDEO_INPUT_ENABLED_KEY: False,
                },
                {
                    "id": "foreign-A/a",
                    "provider_source_id": "foreign-A",
                    "model": "same-model",
                },
            ],
        }
        self.provider_manager = FakeManager(self.config["provider"])
        self.source_upserts: list[tuple[str, dict]] = []
        self.fail_source_upsert = False


def _has_temporary_ui_key(config: dict) -> bool:
    return any(
        isinstance(key, str)
        and (
            key.startswith(registry._VIDEO_UI_KEY_PREFIX)
            or key.startswith(registry._SOURCE_VIDEO_SELECTOR_UI_KEY_PREFIX)
        )
        for key in config
    )


def _cards(service: FakeService) -> dict[str, dict]:
    return {str(card["id"]): card for card in service.config["provider"]}


async def exercise() -> None:
    while registry._DASHBOARD_LEASE_COUNT > 0:
        registry.release_owned_dashboard_bridge()

    original_source_upsert = ProviderConfigService.upsert_provider_source

    async def record_source_upsert(self, source_id: str, config: dict) -> None:
        if self.fail_source_upsert:
            raise RuntimeError("simulated host source save failure")
        saved = copy.deepcopy(config)
        self.source_upserts.append((source_id, saved))
        for index, source in enumerate(self.config["provider_sources"]):
            if source.get("id") == source_id:
                self.config["provider_sources"][index] = saved
                break

    ProviderConfigService.upsert_provider_source = record_source_upsert
    assert registry.acquire_owned_dashboard_bridge() is True
    try:
        service = FakeService()
        ark_selector = registry._source_video_selector_ui_key("ark-A")
        plan_selector = registry._source_video_selector_ui_key("plan-A")
        foreign_selector = registry._source_video_selector_ui_key("foreign-A")

        # Closing the master switch hides the selector only. Even a stale hidden
        # payload must not change a=true,b=false, and transient fields never save.
        await ProviderConfigService.upsert_provider_source(
            service,
            "ark-A",
            {
                "id": "ark-A",
                "provider": "volcengine",
                "type": ARK_PROVIDER_TYPE,
                VIDEO_CONTROLS_VISIBLE_KEY: False,
                ark_selector: ["ark-A/b"],
                VIDEO_INPUT_ENABLED_KEY: True,
                LEGACY_MODEL_VIDEO_INPUT_KEY: True,
                registry._video_ui_key("ark-A"): True,
                LEGACY_SOURCE_VIDEO_KEYS[ARK_PROVIDER_TYPE]: True,
                "hint": registry._SOURCE_TRANSPORT_UI_HINT,
            },
        )
        cards = _cards(service)
        assert cards["ark-A/a"][VIDEO_INPUT_ENABLED_KEY] is True
        assert cards["ark-A/b"][VIDEO_INPUT_ENABLED_KEY] is False
        _, saved_closed = service.source_upserts[-1]
        assert saved_closed[VIDEO_CONTROLS_VISIBLE_KEY] is False
        assert VIDEO_INPUT_ENABLED_KEY not in saved_closed
        assert LEGACY_MODEL_VIDEO_INPUT_KEY not in saved_closed
        assert all(key not in saved_closed for key in LEGACY_SOURCE_VIDEO_KEYS.values())
        assert "hint" not in saved_closed
        assert not _has_temporary_ui_key(saved_closed)

        # Opening the Source selector applies only this Source's card IDs. Same
        # model names on Plan/foreign Sources and forged IDs cannot cross scope.
        await ProviderConfigService.upsert_provider_source(
            service,
            "ark-A",
            {
                "id": "ark-A",
                "provider": "volcengine",
                "type": ARK_PROVIDER_TYPE,
                VIDEO_CONTROLS_VISIBLE_KEY: True,
                ark_selector: ["ark-A/b", "plan-A/a", "foreign-A/a"],
            },
        )
        cards = _cards(service)
        assert cards["ark-A/a"][VIDEO_INPUT_ENABLED_KEY] is False
        assert cards["ark-A/b"][VIDEO_INPUT_ENABLED_KEY] is True
        assert cards["plan-A/a"][VIDEO_INPUT_ENABLED_KEY] is False
        assert VIDEO_INPUT_ENABLED_KEY not in cards["foreign-A/a"]
        _, saved_open = service.source_upserts[-1]
        assert saved_open[VIDEO_CONTROLS_VISIBLE_KEY] is True
        assert not _has_temporary_ui_key(saved_open)

        # Closing again, this time with the hidden selector omitted entirely,
        # preserves b=true. Re-projection keeps b selected for the next reopen.
        await ProviderConfigService.upsert_provider_source(
            service,
            "ark-A",
            {
                "id": "ark-A",
                "provider": "volcengine",
                "type": ARK_PROVIDER_TYPE,
                VIDEO_CONTROLS_VISIBLE_KEY: False,
            },
        )
        cards = _cards(service)
        assert cards["ark-A/a"][VIDEO_INPUT_ENABLED_KEY] is False
        assert cards["ark-A/b"][VIDEO_INPUT_ENABLED_KEY] is True

        projected = registry._inject_model_card_video_control(
            {
                "config_schema": {"provider": {"items": {}, "config_template": {}}},
                "provider_sources": service.config["provider_sources"],
                "providers": service.config["provider"],
            }
        )
        projected_ark = next(
            source
            for source in projected["provider_sources"]
            if source.get("id") == "ark-A"
        )
        assert projected_ark[VIDEO_CONTROLS_VISIBLE_KEY] is False
        assert projected_ark[ark_selector] == ["ark-A/b"]

        # Agent Plan has the same owned behavior through its own exact Source ID.
        await ProviderConfigService.upsert_provider_source(
            service,
            "plan-A",
            {
                "id": "plan-A",
                "provider": "volcengine",
                "type": AGENT_PLAN_PROVIDER_TYPE,
                VIDEO_CONTROLS_VISIBLE_KEY: True,
                plan_selector: ["plan-A/a"],
            },
        )
        assert _cards(service)["plan-A/a"][VIDEO_INPUT_ENABLED_KEY] is True

        # A foreign Source cannot persist forged presentation fields or mutate
        # any model-card Volcengine state.
        await ProviderConfigService.upsert_provider_source(
            service,
            "foreign-A",
            {
                "id": "foreign-A",
                "provider": "openai",
                "type": "openai_chat_completion",
                VIDEO_CONTROLS_VISIBLE_KEY: True,
                foreign_selector: ["ark-A/a"],
                "hint": "host-or-user-hint",
            },
        )
        _, foreign_saved = service.source_upserts[-1]
        assert VIDEO_CONTROLS_VISIBLE_KEY not in foreign_saved
        assert not _has_temporary_ui_key(foreign_saved)
        assert foreign_saved["hint"] == "host-or-user-hint"
        assert _cards(service)["ark-A/a"][VIDEO_INPUT_ENABLED_KEY] is False

        # Rejected Source renames are checked before any per-card mutation.
        snapshot = copy.deepcopy(service.config["provider"])
        try:
            await ProviderConfigService.upsert_provider_source(
                service,
                "ark-A",
                {
                    "id": "plan-A",
                    "provider": "volcengine",
                    "type": ARK_PROVIDER_TYPE,
                    VIDEO_CONTROLS_VISIBLE_KEY: True,
                    ark_selector: ["ark-A/a"],
                },
            )
        except ValueError:
            pass
        else:
            raise AssertionError("duplicate Source rename should fail")
        assert service.config["provider"] == snapshot

        # If the host Source save itself raises after the plugin has translated
        # the selection, restore the entire per-card list to its pre-call state.
        snapshot = copy.deepcopy(service.config["provider"])
        service.fail_source_upsert = True
        try:
            await ProviderConfigService.upsert_provider_source(
                service,
                "ark-A",
                {
                    "id": "ark-A",
                    "provider": "volcengine",
                    "type": ARK_PROVIDER_TYPE,
                    VIDEO_CONTROLS_VISIBLE_KEY: True,
                    ark_selector: ["ark-A/a"],
                },
            )
        except RuntimeError as exc:
            assert "simulated host source save failure" in str(exc)
        else:
            raise AssertionError("host Source save failure should propagate")
        service.fail_source_upsert = False
        assert service.config["provider"] == snapshot

        # Compatibility for a stale already-open 0.1.17 model dialog: its old
        # temporary bool is still translated and stripped at save.
        legacy_model_ui = registry._video_ui_key("ark-A")
        await ProviderConfigService.create_provider(
            service,
            {"id": "ark-A/new", "model": "new", legacy_model_ui: True},
            "ark-A",
        )
        created = service.provider_manager.created[-1]
        assert created[VIDEO_INPUT_ENABLED_KEY] is True
        assert not _has_temporary_ui_key(created)

        # A foreign model save cannot persist any canonical, legacy, Source-only
        # or temporary Volcengine video state, even when a client forges it.
        await ProviderConfigService.create_provider(
            service,
            {
                "id": "foreign-A/new",
                "model": "new",
                VIDEO_INPUT_ENABLED_KEY: True,
                LEGACY_MODEL_VIDEO_INPUT_KEY: True,
                VIDEO_CONTROLS_VISIBLE_KEY: True,
                foreign_selector: ["ark-A/a"],
                registry._video_ui_key("foreign-A"): True,
                LEGACY_SOURCE_VIDEO_KEYS[AGENT_PLAN_PROVIDER_TYPE]: True,
            },
            "foreign-A",
        )
        foreign_created = service.provider_manager.created[-1]
        assert VIDEO_INPUT_ENABLED_KEY not in foreign_created
        assert LEGACY_MODEL_VIDEO_INPUT_KEY not in foreign_created
        assert VIDEO_CONTROLS_VISIBLE_KEY not in foreign_created
        assert all(
            key not in foreign_created for key in LEGACY_SOURCE_VIDEO_KEYS.values()
        )
        assert not _has_temporary_ui_key(foreign_created)

        await ProviderConfigService.update_provider(
            service,
            "ark-A/a",
            {
                "id": "ark-A/a",
                "provider_source_id": "foreign-A",
                "model": "same-model",
                VIDEO_INPUT_ENABLED_KEY: True,
                LEGACY_MODEL_VIDEO_INPUT_KEY: True,
                VIDEO_CONTROLS_VISIBLE_KEY: True,
                foreign_selector: ["ark-A/a"],
                LEGACY_SOURCE_VIDEO_KEYS[ARK_PROVIDER_TYPE]: True,
                legacy_model_ui: True,
                "modalities": ["text", "video"],
            },
        )
        _, moved = service.provider_manager.updated[-1]
        assert VIDEO_INPUT_ENABLED_KEY not in moved
        assert LEGACY_MODEL_VIDEO_INPUT_KEY not in moved
        assert VIDEO_CONTROLS_VISIBLE_KEY not in moved
        assert all(key not in moved for key in LEGACY_SOURCE_VIDEO_KEYS.values())
        assert not _has_temporary_ui_key(moved)
        assert moved["modalities"] == ["text", "video"]
    finally:
        while registry._DASHBOARD_LEASE_COUNT > 0:
            registry.release_owned_dashboard_bridge()
        ProviderConfigService.upsert_provider_source = original_source_upsert


if __name__ == "__main__":
    asyncio.run(exercise())
    print("DASHBOARD_SAVE_BOUNDARY=OK")
