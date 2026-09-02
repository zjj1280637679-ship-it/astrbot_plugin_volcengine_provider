from __future__ import annotations

import asyncio
import copy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "AstrBot" / "data" / "plugins"))

from astrbot_plugin_volcengine_provider.capabilities import (
    ARK_PROVIDER_TYPE,
    LEGACY_MODEL_VIDEO_INPUT_KEY,
    VIDEO_CONTROLS_VISIBLE_KEY,
    VIDEO_INPUT_ENABLED_KEY,
    clear_source_model_hints,
    consume_source_model_hints,
    legacy_model_video_ui_key,
    migrate_legacy_video_settings,
    normalize_owned_model_card_for_save,
    remember_source_model_hint,
    video_input_enabled,
)
from astrbot_plugin_volcengine_provider.registry import (
    _inject_model_card_video_control,
    _merge_source_feedback,
)


def main() -> None:
    sources = [
        {"id": "ark", "type": ARK_PROVIDER_TYPE},
        {"id": "foreign", "type": "openai_chat_completion"},
    ]

    enabled = {
        "id": "ark/on",
        "provider_source_id": "ark",
        "modalities": ["text", "video"],
    }
    normalize_owned_model_card_for_save(enabled, sources, default_enabled=False)
    assert enabled[VIDEO_INPUT_ENABLED_KEY] is True
    assert enabled["modalities"] == ["text", "video"]
    assert video_input_enabled(enabled) is True

    disabled = {
        "id": "ark/off",
        "provider_source_id": "ark",
        "modalities": ["text", "image"],
    }
    normalize_owned_model_card_for_save(disabled, sources, default_enabled=True)
    assert disabled[VIDEO_INPUT_ENABLED_KEY] is False
    assert disabled["modalities"] == ["text", "image"]
    assert video_input_enabled(disabled) is False

    retired_exact = legacy_model_video_ui_key("ark")
    cfg = {
        "provider_sources": [
            {
                "id": "ark",
                "type": ARK_PROVIDER_TYPE,
                "volcengine_ark_video_input": False,
                VIDEO_CONTROLS_VISIBLE_KEY: True,
            },
            {"id": "foreign", "type": "openai_chat_completion"},
        ],
        "provider": [
            {
                "id": "ark/exact-old-ui",
                "provider_source_id": "ark",
                retired_exact: True,
                LEGACY_MODEL_VIDEO_INPUT_KEY: False,
                "modalities": ["text"],
            },
            {
                "id": "ark/source-default",
                "provider_source_id": "ark",
                "modalities": ["text", "video"],
            },
            {
                "id": "foreign/debris",
                "provider_source_id": "foreign",
                VIDEO_INPUT_ENABLED_KEY: True,
                VIDEO_CONTROLS_VISIBLE_KEY: True,
                "modalities": ["text", "video"],
            },
        ],
    }
    before_modalities = {
        item["id"]: copy.deepcopy(item.get("modalities")) for item in cfg["provider"]
    }
    changed = migrate_legacy_video_settings(cfg)
    cards = {item["id"]: item for item in cfg["provider"]}
    assert cards["ark/exact-old-ui"][VIDEO_INPUT_ENABLED_KEY] is True
    assert cards["ark/source-default"][VIDEO_INPUT_ENABLED_KEY] is False
    assert VIDEO_INPUT_ENABLED_KEY not in cards["foreign/debris"]
    assert VIDEO_CONTROLS_VISIBLE_KEY not in cfg["provider_sources"][0]
    assert "volcengine_ark_video_input" not in cfg["provider_sources"][0]
    assert all(cards[name]["modalities"] == before_modalities[name] for name in cards)
    assert set(changed) >= {"ark/exact-old-ui", "ark/source-default", "foreign/debris"}

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
                },
                "config_template": {},
            }
        },
        "provider_sources": copy.deepcopy(sources),
        "providers": [
            {"id": "ark/a", "provider_source_id": "ark", VIDEO_INPUT_ENABLED_KEY: True},
            {"id": "foreign/a", "provider_source_id": "foreign", VIDEO_INPUT_ENABLED_KEY: True},
        ],
    }
    cleaned = _inject_model_card_video_control(payload)
    assert cleaned["config_schema"]["provider"]["items"]["modalities"]["options"] == [
        "text",
        "image",
        "audio",
        "tool_use",
    ]
    assert VIDEO_INPUT_ENABLED_KEY not in cleaned["config_schema"]["provider"]["items"]
    assert VIDEO_INPUT_ENABLED_KEY not in cleaned["providers"][0]
    assert VIDEO_INPUT_ENABLED_KEY not in cleaned["providers"][1]

    base = {
        "tool_call": True,
        "modalities": {"input": ["image"], "output": ["text"]},
        "limit": {"context": 131072, "output": 0},
    }
    incoming = {
        "tool_call": False,
        "modalities": {"input": ["audio"]},
        "limit": {"context": 65536},
    }
    merged = _merge_source_feedback(base, incoming)
    assert merged["tool_call"] is False
    assert merged["modalities"] == {"input": ["audio"], "output": ["text"]}
    assert merged["limit"] == {"context": 65536, "output": 0}
    assert base["tool_call"] is True

    clear_source_model_hints("live")
    remember_source_model_hint("live", "m", {"id": "m", "tool_call": False})
    assert consume_source_model_hints("live", ["m"])["m"]["tool_call"] is False
    assert consume_source_model_hints("live", ["m"]) == {}

    async def isolated(value: bool) -> bool:
        clear_source_model_hints("same")
        remember_source_model_hint("same", "m", {"id": "m", "tool_call": value})
        await asyncio.sleep(0)
        return bool(consume_source_model_hints("same", ["m"])["m"]["tool_call"])

    async def run_isolation() -> list[bool]:
        return list(await asyncio.gather(isolated(True), isolated(False)))

    assert asyncio.run(run_isolation()) == [True, False]
    print("CURRENT_FEEDBACK_AND_MIGRATION=OK")


if __name__ == "__main__":
    main()
