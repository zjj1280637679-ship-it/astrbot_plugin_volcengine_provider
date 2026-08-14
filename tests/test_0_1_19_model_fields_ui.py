from __future__ import annotations

import copy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "AstrBot" / "data" / "plugins"))

from astrbot_plugin_volcengine_provider.capabilities import (
    ARK_PROVIDER_TYPE,
    MODEL_FIELD_SCHEMA,
    REASONING_EFFORT_KEY,
    REASONING_MODE_KEY,
    STOP_SEQUENCES_KEY,
    TEMPERATURE_KEY,
    VIDEO_INPUT_ENABLED_KEY,
    VIDEO_INPUT_MODE_UI_KEY,
    VIDEO_INPUT_PROFILE_KEY,
)
from astrbot_plugin_volcengine_provider.capabilities.model_fields_bridge import (
    _inject_owned_model_fields,
)


class FakeService:
    def __init__(self) -> None:
        self.config = {
            "provider_sources": [
                {"id": "ark-A", "provider": "volcengine", "type": ARK_PROVIDER_TYPE},
                {
                    "id": "foreign-A",
                    "provider": "openai",
                    "type": "openai_chat_completion",
                },
            ],
            "provider": [
                {
                    "id": "ark-A/model",
                    "provider_source_id": "ark-A",
                    "model": "model",
                    "modalities": ["text", "image"],
                    VIDEO_INPUT_ENABLED_KEY: True,
                    VIDEO_INPUT_PROFILE_KEY: "compressed",
                    TEMPERATURE_KEY: 0.6,
                    REASONING_MODE_KEY: "auto",
                    REASONING_EFFORT_KEY: "high",
                    STOP_SEQUENCES_KEY: ["STOP"],
                },
                {
                    "id": "foreign-A/model",
                    "provider_source_id": "foreign-A",
                    "model": "model",
                    # Forged fields must never reach the foreign edit dialog.
                    VIDEO_INPUT_PROFILE_KEY: "compressed",
                    TEMPERATURE_KEY: 0.1,
                    REASONING_MODE_KEY: "auto",
                },
            ],
        }


def main() -> None:
    service = FakeService()

    # Simulate the output of the existing 0.1.18 schema wrapper: generic model
    # card copies carry host fields only; persistent Volcengine video truth is
    # intentionally absent from the Dashboard projection.
    payload = {
        "config_schema": {
            "provider": {
                "items": {
                    "enable": {"type": "bool"},
                    "modalities": {"type": "list"},
                    "custom_extra_body": {"type": "dict"},
                },
                "config_template": {},
            }
        },
        "provider_sources": copy.deepcopy(service.config["provider_sources"]),
        "providers": [
            {
                "id": "ark-A/model",
                "provider_source_id": "ark-A",
                "model": "model",
                "modalities": ["text", "image"],
                "enable": True,
                "custom_extra_body": {},
            },
            {
                "id": "foreign-A/model",
                "provider_source_id": "foreign-A",
                "model": "model",
                "enable": True,
                "custom_extra_body": {"foreign": "kept"},
                VIDEO_INPUT_PROFILE_KEY: "forged",
                TEMPERATURE_KEY: "forged",
            },
        ],
    }
    before = copy.deepcopy(payload)
    out = _inject_owned_model_fields(service, payload)

    # Projection is copy-on-write so the 0.1.18 bridge response remains intact.
    assert payload == before

    items = out["config_schema"]["provider"]["items"]
    for key, expected in MODEL_FIELD_SCHEMA.items():
        assert items[key] == expected

    owned, foreign = out["providers"]
    assert owned["modalities"] == ["text", "image", "video"]
    assert VIDEO_INPUT_MODE_UI_KEY not in owned
    assert owned[VIDEO_INPUT_PROFILE_KEY] == "compressed"
    assert owned[TEMPERATURE_KEY] == "0.6"
    assert owned[REASONING_MODE_KEY] == "auto"
    assert owned[REASONING_EFFORT_KEY] == "high"
    assert owned[STOP_SEQUENCES_KEY] == ["STOP"]

    # Foreign model copies carry none of the Volcengine values; the frontend
    # bridge additionally marks their shared schema definitions invisible.
    for key in MODEL_FIELD_SCHEMA:
        assert key not in foreign
    assert foreign["custom_extra_body"] == {"foreign": "kept"}

    print("MODEL_FIELDS_UI_0_1_19=OK")


if __name__ == "__main__":
    main()
