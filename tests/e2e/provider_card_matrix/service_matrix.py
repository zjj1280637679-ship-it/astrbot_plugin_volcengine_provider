"""Service-level provider-card lifecycle matrix.

Runs the actual AstrBot ProviderConfigService create/update methods after the
plugin Dashboard bridges are installed. This verifies that both Volcengine
Source types and a foreign reference cross the same host save boundary correctly.
"""

from __future__ import annotations

import asyncio
import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PLUGIN_PARENT = ROOT / "AstrBot" / "data" / "plugins"
sys.path.insert(0, str(PLUGIN_PARENT))

from astrbot.dashboard.services.config_service import ProviderConfigService
from astrbot_plugin_volcengine_provider import registry
from astrbot_plugin_volcengine_provider.capabilities import (
    AGENT_PLAN_PROVIDER_TYPE,
    ARK_PROVIDER_TYPE,
    REASONING_EFFORT_KEY,
    REASONING_MODE_KEY,
    STOP_SEQUENCES_KEY,
    TEMPERATURE_KEY,
    VIDEO_INPUT_ENABLED_KEY,
    VIDEO_INPUT_MODE_UI_KEY,
    VIDEO_INPUT_PROFILE_KEY,
    acquire_model_fields_bridge,
    release_model_fields_bridge,
)
from astrbot_plugin_volcengine_provider.capabilities import model_fields_bridge

from assertions import (
    assert_foreign_config_is_clean,
    assert_no_temporary_ui_keys_persisted,
    assert_owned_model_card_saved,
)


class FakeManager:
    def __init__(self, providers: list[dict]) -> None:
        self.providers = providers
        self.providers_config = providers
        self.provider_sources_config: list[dict] = []
        self.created: list[dict] = []
        self.updated: list[tuple[str, dict]] = []
        self.reloaded: list[dict] = []

    async def create_provider(self, config: dict) -> None:
        self.created.append(copy.deepcopy(config))

    async def update_provider(self, provider_id: str, config: dict) -> None:
        self.updated.append((provider_id, copy.deepcopy(config)))

    async def reload(self, config: dict) -> None:
        self.reloaded.append(copy.deepcopy(config))

    def get_provider_config_by_id(self, provider_id: str, **_: object) -> dict | None:
        for provider in self.providers:
            if provider.get("id") == provider_id:
                return copy.deepcopy(provider)
        return None


class FakeConfig(dict):
    def save_config(self, replace_config: dict | None = None, **_: object) -> None:
        # ProviderConfigService already mutated this in-memory object. Validation
        # still runs through the real host helper; disk persistence is the only
        # side effect omitted by this service matrix.
        return None


def make_service() -> ProviderConfigService:
    service = object.__new__(ProviderConfigService)
    service.config = FakeConfig(
        {
            "provider_sources": [
                {
                    "id": "ark-A",
                    "provider": "volcengine",
                    "type": ARK_PROVIDER_TYPE,
                    "provider_type": "chat_completion",
                    "enable": True,
                },
                {
                    "id": "plan-A",
                    "provider": "volcengine",
                    "type": AGENT_PLAN_PROVIDER_TYPE,
                    "provider_type": "chat_completion",
                    "enable": True,
                },
                {
                    "id": "foreign-A",
                    "provider": "openai",
                    "type": "openai_chat_completion",
                    "provider_type": "chat_completion",
                    "enable": True,
                },
            ],
            "provider": [
                {
                    "id": "ark-A/existing",
                    "provider_source_id": "ark-A",
                    "model": "existing",
                    VIDEO_INPUT_ENABLED_KEY: False,
                    VIDEO_INPUT_PROFILE_KEY: "compressed",
                },
                {
                    "id": "plan-A/existing",
                    "provider_source_id": "plan-A",
                    "model": "agentplan/existing",
                    VIDEO_INPUT_ENABLED_KEY: False,
                },
                {
                    "id": "foreign-A/existing",
                    "provider_source_id": "foreign-A",
                    "model": "existing",
                },
            ],
        }
    )
    service.provider_manager = FakeManager(service.config["provider"])
    service.provider_manager.provider_sources_config = service.config[
        "provider_sources"
    ]
    return service


async def _exercise_owned(service: ProviderConfigService, source_id: str) -> dict:
    ui_key = registry._video_ui_key(source_id)
    selector_key = registry._source_video_selector_ui_key(source_id)

    # 0.1.20 retires the Source selector. A stale 0.1.18 Source payload must be
    # cleaned without changing the model card; the standard model-card
    # ``modalities`` list is now the only visible selection input.
    existing_id = f"{source_id}/existing"
    source_type = (
        AGENT_PLAN_PROVIDER_TYPE if source_id == "plan-A" else ARK_PROVIDER_TYPE
    )
    await ProviderConfigService.upsert_provider_source(
        service,
        source_id,
        {
            "id": source_id,
            "provider": "volcengine",
            "type": source_type,
            "provider_type": "chat_completion",
            "enable": True,
            selector_key: [existing_id],
        },
    )
    persisted = service.provider_manager.get_provider_config_by_id(existing_id)
    assert persisted is not None
    assert persisted[VIDEO_INPUT_ENABLED_KEY] is False
    if source_id == "ark-A":
        assert persisted[VIDEO_INPUT_PROFILE_KEY] == "compressed"

    await ProviderConfigService.upsert_provider_source(
        service,
        source_id,
        {
            "id": source_id,
            "provider": "volcengine",
            "type": source_type,
            "provider_type": "chat_completion",
            "enable": True,
            selector_key: [],
        },
    )
    persisted = service.provider_manager.get_provider_config_by_id(existing_id)
    assert persisted is not None
    assert persisted[VIDEO_INPUT_ENABLED_KEY] is False
    if source_id == "ark-A":
        assert persisted[VIDEO_INPUT_PROFILE_KEY] == "compressed"

    await ProviderConfigService.create_provider(
        service,
        {
            "id": f"{source_id}/new",
            "model": "new",
            "modalities": ["text", "video"],
            ui_key: False,
            VIDEO_INPUT_MODE_UI_KEY: "compressed",
            TEMPERATURE_KEY: "0.6",
            REASONING_MODE_KEY: "auto",
            REASONING_EFFORT_KEY: "high",
            STOP_SEQUENCES_KEY: ["STOP"],
        },
        source_id,
    )
    created = service.provider_manager.created[-1]
    assert created["provider_source_id"] == source_id
    assert_owned_model_card_saved(created, expected_video_enabled=True)
    assert created[VIDEO_INPUT_PROFILE_KEY] == "compressed"
    assert VIDEO_INPUT_MODE_UI_KEY not in created
    assert created[TEMPERATURE_KEY] == 0.6
    assert created[REASONING_MODE_KEY] == "auto"
    assert created[REASONING_EFFORT_KEY] == "high"
    assert created[STOP_SEQUENCES_KEY] == ["STOP"]

    await ProviderConfigService.create_provider(
        service,
        {
            "id": f"{source_id}/default",
            "model": "default",
            "modalities": ["text"],
        },
        source_id,
    )
    created_default = service.provider_manager.created[-1]
    assert_owned_model_card_saved(created_default, expected_video_enabled=False)
    assert TEMPERATURE_KEY not in created_default
    assert REASONING_MODE_KEY not in created_default
    assert VIDEO_INPUT_PROFILE_KEY not in created_default

    existing_model = "agentplan/existing" if source_id == "plan-A" else "existing"
    await ProviderConfigService.update_provider(
        service,
        existing_id,
        {
            "id": existing_id,
            "provider_source_id": source_id,
            "model": existing_model,
            "modalities": ["text", "video"],
            VIDEO_INPUT_ENABLED_KEY: False,
            ui_key: False,
            VIDEO_INPUT_MODE_UI_KEY: "original",
            TEMPERATURE_KEY: "0.4",
        },
    )
    _, updated = service.provider_manager.updated[-1]
    assert_owned_model_card_saved(updated, expected_video_enabled=True)
    # Current 0.1.20 modalities outrank the retired 0.1.19 UI field. Because no
    # current quality row was submitted, preserve the persisted compressed
    # preference rather than letting the stale old tab rewrite it.
    if source_id == "ark-A":
        assert updated[VIDEO_INPUT_PROFILE_KEY] == "compressed"
    else:
        assert VIDEO_INPUT_PROFILE_KEY not in updated
    assert updated[TEMPERATURE_KEY] == 0.4

    return {
        "source_id": source_id,
        "create_enabled": True,
        "create_default": False,
        "update_enabled": True,
        "retired_source_ui_ignored": True,
        "model_fields": "normalized",
    }


async def _exercise_foreign(service: ProviderConfigService) -> dict:
    forged = registry._video_ui_key("foreign-A")
    await ProviderConfigService.create_provider(
        service,
        {
            "id": "foreign-A/new",
            "model": "new",
            forged: True,
            VIDEO_INPUT_MODE_UI_KEY: "compressed",
            VIDEO_INPUT_PROFILE_KEY: "compressed",
            TEMPERATURE_KEY: "0.5",
            REASONING_MODE_KEY: "auto",
            REASONING_EFFORT_KEY: "high",
            STOP_SEQUENCES_KEY: ["FORGED"],
            "custom_extra_body": {"foreign": "kept"},
        },
        "foreign-A",
    )
    created = service.provider_manager.created[-1]
    assert_no_temporary_ui_keys_persisted(created)
    assert_foreign_config_is_clean(created)
    for key in (
        VIDEO_INPUT_MODE_UI_KEY,
        VIDEO_INPUT_PROFILE_KEY,
        TEMPERATURE_KEY,
        REASONING_MODE_KEY,
        REASONING_EFFORT_KEY,
        STOP_SEQUENCES_KEY,
    ):
        assert key not in created
    assert created["custom_extra_body"] == {"foreign": "kept"}

    return {
        "source_id": "foreign-A",
        "volcengine_state": "absent",
        "foreign_extra_body": "preserved",
    }


async def exercise() -> dict:
    while model_fields_bridge._FIELD_BRIDGE_LEASE_COUNT > 0:
        release_model_fields_bridge()
    while registry._DASHBOARD_LEASE_COUNT > 0:
        registry.release_owned_dashboard_bridge()

    if registry.acquire_owned_dashboard_bridge() is not True:
        raise AssertionError("expected 0.1.18 Dashboard bridge to install")
    if acquire_model_fields_bridge() is not True:
        raise AssertionError("expected 0.1.19 model-fields bridge to install")

    try:
        service = make_service()
        return {
            "ark": await _exercise_owned(service, "ark-A"),
            "agent_plan": await _exercise_owned(service, "plan-A"),
            "foreign": await _exercise_foreign(service),
        }
    finally:
        while model_fields_bridge._FIELD_BRIDGE_LEASE_COUNT > 0:
            release_model_fields_bridge()
        while registry._DASHBOARD_LEASE_COUNT > 0:
            registry.release_owned_dashboard_bridge()


def main() -> None:
    result = asyncio.run(exercise())
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    print("PROVIDER_CARD_SERVICE_MATRIX=OK")


if __name__ == "__main__":
    main()
