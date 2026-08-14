from __future__ import annotations

import copy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "AstrBot" / "data" / "plugins"))

from astrbot_plugin_volcengine_provider.capabilities import (
    AGENT_PLAN_PROVIDER_TYPE,
    ARK_PROVIDER_TYPE,
    LEGACY_MODEL_VIDEO_INPUT_KEY,
    LEGACY_SOURCE_VIDEO_KEYS,
    VIDEO_CONTROLS_VISIBLE_KEY,
    VIDEO_INPUT_ENABLED_KEY,
)
from astrbot_plugin_volcengine_provider.registry import (
    _SOURCE_VIDEO_SELECTOR_UI_KEY_PREFIX,
    _VIDEO_UI_KEY_PREFIX,
    _apply_video_ui_transport_setting,
    _inject_model_card_video_control,
    _source_video_selector_ui_key,
    _video_ui_key,
)


def _has_prefix(config: dict, prefix: str) -> bool:
    return any(isinstance(key, str) and key.startswith(prefix) for key in config)


def _assert_no_persistent_or_source_video_fields(config: dict) -> None:
    assert VIDEO_INPUT_ENABLED_KEY not in config
    assert LEGACY_MODEL_VIDEO_INPUT_KEY not in config
    assert VIDEO_CONTROLS_VISIBLE_KEY not in config
    assert all(key not in config for key in LEGACY_SOURCE_VIDEO_KEYS.values())
    assert not _has_prefix(config, _SOURCE_VIDEO_SELECTOR_UI_KEY_PREFIX)


def main() -> None:
    sources = [
        {"id": "ark-A", "provider": "volcengine", "type": ARK_PROVIDER_TYPE},
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
    ]
    ark_ui = _video_ui_key("ark-A")
    plan_ui = _video_ui_key("plan-A")
    foreign_ui = _video_ui_key("foreign-A")
    foreign_selector = _source_video_selector_ui_key("foreign-A")

    payload = {
        "config_schema": {
            "provider": {
                "items": {
                    "modalities": {
                        "type": "list",
                        "options": ["text", "image", "audio", "tool_use"],
                    },
                    VIDEO_INPUT_ENABLED_KEY: {"type": "bool"},
                    VIDEO_CONTROLS_VISIBLE_KEY: {"type": "bool"},
                    foreign_ui: {"type": "bool"},
                    foreign_selector: {"type": "list"},
                },
                "config_template": {
                    "ark": {
                        **sources[0],
                        VIDEO_CONTROLS_VISIBLE_KEY: True,
                        foreign_selector: ["foreign-A/card"],
                    },
                    "plan": {**sources[1], VIDEO_CONTROLS_VISIBLE_KEY: False},
                    "foreign": {
                        **sources[2],
                        VIDEO_CONTROLS_VISIBLE_KEY: True,
                        VIDEO_INPUT_ENABLED_KEY: True,
                    },
                },
            }
        },
        "provider_sources": [
            {**sources[0], VIDEO_CONTROLS_VISIBLE_KEY: True},
            {**sources[1], VIDEO_CONTROLS_VISIBLE_KEY: False},
            {
                **sources[2],
                VIDEO_CONTROLS_VISIBLE_KEY: True,
                foreign_selector: ["foreign-A/card"],
            },
        ],
        "providers": [
            {
                "id": "ark-A/card-on",
                "provider_source_id": "ark-A",
                "model": "same-model",
                VIDEO_INPUT_ENABLED_KEY: True,
            },
            {
                "id": "ark-A/card-off",
                "provider_source_id": "ark-A",
                "model": "same-model",
                VIDEO_INPUT_ENABLED_KEY: False,
            },
            {
                "id": "plan-A/card",
                "provider_source_id": "plan-A",
                "model": "same-model",
                VIDEO_INPUT_ENABLED_KEY: True,
            },
            {
                "id": "foreign-A/card",
                "provider_source_id": "foreign-A",
                "model": "same-model",
                VIDEO_INPUT_ENABLED_KEY: True,
                foreign_ui: True,
                VIDEO_CONTROLS_VISIBLE_KEY: True,
            },
        ],
    }
    before = copy.deepcopy(payload)
    out = _inject_model_card_video_control(copy.deepcopy(payload))

    # Projection never mutates the caller or the host-owned modality enum.
    assert payload == before
    items = out["config_schema"]["provider"]["items"]
    assert items["modalities"]["options"] == ["text", "image", "audio", "tool_use"]
    assert "video" not in items["modalities"]["options"]

    # The old global modality and both retired UI generations remain absent.
    # The current checkbox is projected later by model_fields_bridge only onto
    # owned concrete card copies.
    assert ark_ui not in items
    assert plan_ui not in items
    assert foreign_ui not in items
    assert VIDEO_INPUT_ENABLED_KEY not in items
    assert VIDEO_CONTROLS_VISIBLE_KEY not in items
    assert not _has_prefix(items, _SOURCE_VIDEO_SELECTOR_UI_KEY_PREFIX)

    ark_on, ark_off, plan, foreign = out["providers"]
    for card in (ark_on, ark_off, plan, foreign):
        _assert_no_persistent_or_source_video_fields(card)
        assert not _has_prefix(card, _VIDEO_UI_KEY_PREFIX)

    # The retired Source-level gate is absent on owned and foreign projections.
    for source in out["provider_sources"]:
        _assert_no_persistent_or_source_video_fields(source)
        assert not _has_prefix(source, _VIDEO_UI_KEY_PREFIX)
    for template in out["config_schema"]["provider"]["config_template"].values():
        _assert_no_persistent_or_source_video_fields(template)
        assert not _has_prefix(template, _VIDEO_UI_KEY_PREFIX)

    # The temporary checkbox is translated at the ordinary card save boundary.
    edited = {
        "id": "ark-A/new",
        "provider_source_id": "ark-A",
        ark_ui: True,
        foreign_ui: True,
    }
    _apply_video_ui_transport_setting(edited, sources)
    assert edited[VIDEO_INPUT_ENABLED_KEY] is True
    assert not _has_prefix(edited, _VIDEO_UI_KEY_PREFIX)

    forged_foreign = {
        "id": "foreign-A/card",
        "provider_source_id": "foreign-A",
        foreign_ui: True,
    }
    _apply_video_ui_transport_setting(forged_foreign, sources)
    assert VIDEO_INPUT_ENABLED_KEY not in forged_foreign
    assert not _has_prefix(forged_foreign, _VIDEO_UI_KEY_PREFIX)

    print("MODEL_CARD_UI_SCOPE=OK")


if __name__ == "__main__":
    main()
