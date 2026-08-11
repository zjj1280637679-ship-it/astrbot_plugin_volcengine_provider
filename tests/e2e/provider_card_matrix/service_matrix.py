"""Service-level provider-card lifecycle matrix.

Runs the actual AstrBot ProviderConfigService create/update methods after the
plugin Dashboard bridge is installed. This verifies that both Volcengine Source
types and a foreign reference cross the same host save boundary correctly.
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
    VIDEO_INPUT_ENABLED_KEY,
)

from assertions import (
    assert_foreign_config_is_clean,
    assert_no_temporary_ui_keys_persisted,
    assert_owned_model_card_saved,
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
                {"id": "plan-A", "type": AGENT_PLAN_PROVIDER_TYPE},
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
        self.provider_manager = FakeManager(self.config["provider"])


async def _exercise_owned(service: FakeService, source_id: str) -> dict:
    ui_key = registry._video_ui_key(source_id)

    await ProviderConfigService.create_provider(
        service,
        {"id": f"{source_id}/new", "model": "new", ui_key: True},
        source_id,
    )
    created = service.provider_manager.created[-1]
    assert created["provider_source_id"] == source_id
    assert_owned_model_card_saved(created, expected_video_enabled=True)

    await ProviderConfigService.create_provider(
        service,
        {"id": f"{source_id}/default", "model": "default"},
        source_id,
    )
    created_default = service.provider_manager.created[-1]
    assert_owned_model_card_saved(created_default, expected_video_enabled=False)

    existing_id = f"{source_id}/existing"
    existing_model = "agentplan/existing" if source_id == "plan-A" else "existing"
    await ProviderConfigService.update_provider(
        service,
        existing_id,
        {
            "id": existing_id,
            "provider_source_id": source_id,
            "model": existing_model,
            VIDEO_INPUT_ENABLED_KEY: False,
            ui_key: True,
        },
    )
    _, updated = service.provider_manager.updated[-1]
    assert_owned_model_card_saved(updated, expected_video_enabled=True)

    return {
        "source_id": source_id,
        "create_enabled": True,
        "create_default": False,
        "update_enabled": True,
    }


async def _exercise_foreign(service: FakeService) -> dict:
    forged = registry._video_ui_key("foreign-A")
    await ProviderConfigService.create_provider(
        service,
        {
            "id": "foreign-A/new",
            "model": "new",
            forged: True,
            "custom_extra_body": {"foreign": "kept"},
        },
        "foreign-A",
    )
    created = service.provider_manager.created[-1]
    assert_no_temporary_ui_keys_persisted(created)
    assert_foreign_config_is_clean(created)
    assert created["custom_extra_body"] == {"foreign": "kept"}

    return {
        "source_id": "foreign-A",
        "volcengine_state": "absent",
        "foreign_extra_body": "preserved",
    }


async def exercise() -> dict:
    while registry._DASHBOARD_LEASE_COUNT > 0:
        registry.release_owned_dashboard_bridge()

    if registry.acquire_owned_dashboard_bridge() is not True:
        raise AssertionError("expected Dashboard bridge to install in supported host")

    try:
        service = FakeService()
        return {
            "ark": await _exercise_owned(service, "ark-A"),
            "agent_plan": await _exercise_owned(service, "plan-A"),
            "foreign": await _exercise_foreign(service),
        }
    finally:
        while registry._DASHBOARD_LEASE_COUNT > 0:
            registry.release_owned_dashboard_bridge()


def main() -> None:
    result = asyncio.run(exercise())
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    print("PROVIDER_CARD_SERVICE_MATRIX=OK")


if __name__ == "__main__":
    main()
