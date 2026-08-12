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
    legacy_model_video_ui_key,
)
from astrbot_plugin_volcengine_provider.registry import (
    _SOURCE_TRANSPORT_UI_HINT,
    _SOURCE_VIDEO_SELECTOR_UI_KEY_PREFIX,
    _VIDEO_UI_KEY_PREFIX,
    _inject_model_card_video_control,
    _inject_owned_source_transport_hint,
    _source_video_selector_ui_key,
    _strip_source_transport_hint,
)


def _has_key_prefix(config: dict, prefix: str) -> bool:
    return any(isinstance(key, str) and key.startswith(prefix) for key in config)


def _assert_no_model_video_ui_fields(config: dict) -> None:
    assert VIDEO_INPUT_ENABLED_KEY not in config
    assert LEGACY_MODEL_VIDEO_INPUT_KEY not in config
    assert VIDEO_CONTROLS_VISIBLE_KEY not in config
    assert all(key not in config for key in LEGACY_SOURCE_VIDEO_KEYS.values())
    assert not _has_key_prefix(config, _VIDEO_UI_KEY_PREFIX)
    assert not _has_key_prefix(config, _SOURCE_VIDEO_SELECTOR_UI_KEY_PREFIX)


def _assert_no_wrong_layer_source_video_fields(config: dict) -> None:
    assert VIDEO_INPUT_ENABLED_KEY not in config
    assert LEGACY_MODEL_VIDEO_INPUT_KEY not in config
    assert all(key not in config for key in LEGACY_SOURCE_VIDEO_KEYS.values())
    assert not _has_key_prefix(config, _VIDEO_UI_KEY_PREFIX)


def main() -> None:
    # Selector identity is reversible/injective, including punctuation and UTF-8.
    for source_id in ("ark-A", "a/b", "a?b", "火山 方舟", "emoji-🚀"):
        ui_key = _source_video_selector_ui_key(source_id)
        encoded = ui_key.removeprefix(_SOURCE_VIDEO_SELECTOR_UI_KEY_PREFIX)
        assert bytes.fromhex(encoded).decode("utf-8") == source_id
    assert _source_video_selector_ui_key("a/b") != _source_video_selector_ui_key("a?b")

    forged_foreign_selector = _source_video_selector_ui_key("foreign-A")
    forged_old_model_ui = legacy_model_video_ui_key("foreign-A")
    payload = {
        "config_schema": {
            "provider": {
                "items": {
                    "modalities": {
                        "type": "list",
                        "options": ["text", "image", "audio", "tool_use"],
                    },
                    VIDEO_INPUT_ENABLED_KEY: {"type": "bool"},
                    LEGACY_MODEL_VIDEO_INPUT_KEY: {"type": "bool"},
                    forged_old_model_ui: {"type": "bool"},
                    forged_foreign_selector: {"type": "list"},
                    LEGACY_SOURCE_VIDEO_KEYS[ARK_PROVIDER_TYPE]: {"type": "bool"},
                },
                "config_template": {
                    "ark-template": {
                        "id": "volcengine-ark",
                        "provider": "volcengine",
                        "type": ARK_PROVIDER_TYPE,
                        VIDEO_INPUT_ENABLED_KEY: True,
                        LEGACY_MODEL_VIDEO_INPUT_KEY: True,
                        forged_old_model_ui: True,
                        forged_foreign_selector: ["foreign-A/card"],
                        LEGACY_SOURCE_VIDEO_KEYS[ARK_PROVIDER_TYPE]: True,
                    },
                    "plan-template": {
                        "id": "volcengine-agent-plan",
                        "provider": "volcengine",
                        "type": AGENT_PLAN_PROVIDER_TYPE,
                    },
                    "foreign-template": {
                        "id": "openai",
                        "provider": "openai",
                        "type": "openai_chat_completion",
                        VIDEO_CONTROLS_VISIBLE_KEY: True,
                        forged_foreign_selector: ["foreign-A/card"],
                    },
                },
            },
        },
        "provider_sources": [
            {"id": "ark-A", "provider": "volcengine", "type": ARK_PROVIDER_TYPE},
            {
                "id": "plan-A",
                "provider": "volcengine",
                "type": AGENT_PLAN_PROVIDER_TYPE,
                VIDEO_CONTROLS_VISIBLE_KEY: True,
                VIDEO_INPUT_ENABLED_KEY: True,
                LEGACY_MODEL_VIDEO_INPUT_KEY: True,
                forged_old_model_ui: True,
                LEGACY_SOURCE_VIDEO_KEYS[AGENT_PLAN_PROVIDER_TYPE]: True,
            },
            {
                "id": "foreign-A",
                "provider": "openai",
                "type": "openai_chat_completion",
                VIDEO_CONTROLS_VISIBLE_KEY: True,
                forged_foreign_selector: ["foreign-A/card"],
                VIDEO_INPUT_ENABLED_KEY: True,
                LEGACY_MODEL_VIDEO_INPUT_KEY: True,
                forged_old_model_ui: True,
                LEGACY_SOURCE_VIDEO_KEYS[ARK_PROVIDER_TYPE]: True,
            },
        ],
        "providers": [
            {
                "id": "ark-A/card-1",
                "provider_source_id": "ark-A",
                "model": "same-model",
                VIDEO_INPUT_ENABLED_KEY: True,
                VIDEO_CONTROLS_VISIBLE_KEY: True,
                LEGACY_MODEL_VIDEO_INPUT_KEY: False,
                forged_foreign_selector: ["ark-A/card-1"],
                LEGACY_SOURCE_VIDEO_KEYS[ARK_PROVIDER_TYPE]: True,
            },
            {
                "id": "ark-A/card-2",
                "provider_source_id": "ark-A",
                "model": "same-model",
                VIDEO_INPUT_ENABLED_KEY: False,
                forged_old_model_ui: True,
            },
            {
                "id": "plan-A/card",
                "provider_source_id": "plan-A",
                "model": "same-model",
                VIDEO_INPUT_ENABLED_KEY: True,
                VIDEO_CONTROLS_VISIBLE_KEY: True,
                forged_foreign_selector: ["plan-A/card"],
            },
            {
                "id": "foreign-A/card",
                "provider_source_id": "foreign-A",
                "model": "same-model",
                VIDEO_INPUT_ENABLED_KEY: True,
                LEGACY_MODEL_VIDEO_INPUT_KEY: True,
                VIDEO_CONTROLS_VISIBLE_KEY: True,
                forged_old_model_ui: True,
                forged_foreign_selector: ["ark-A/card-1"],
                LEGACY_SOURCE_VIDEO_KEYS[AGENT_PLAN_PROVIDER_TYPE]: True,
            },
        ],
    }
    before = copy.deepcopy(payload)

    out = _inject_owned_source_transport_hint(copy.deepcopy(payload))
    out = _inject_model_card_video_control(out)
    items = out["config_schema"]["provider"]["items"]

    # Projection is copy-on-write and never restores the 0.1.12 global video
    # option in AstrBot-owned modalities.
    assert payload == before
    assert items["modalities"]["options"] == ["text", "image", "audio", "tool_use"]
    assert "video" not in items["modalities"]["options"]
    assert VIDEO_INPUT_ENABLED_KEY not in items
    assert LEGACY_MODEL_VIDEO_INPUT_KEY not in items
    assert all(key not in items for key in LEGACY_SOURCE_VIDEO_KEYS.values())
    assert not any(str(key).startswith(_VIDEO_UI_KEY_PREFIX) for key in items)

    assert items[VIDEO_CONTROLS_VISIBLE_KEY]["type"] == "bool"
    ark_selector = _source_video_selector_ui_key("ark-A")
    plan_selector = _source_video_selector_ui_key("plan-A")
    assert items[ark_selector]["condition"] == {VIDEO_CONTROLS_VISIBLE_KEY: True}
    assert items[ark_selector]["render_type"] == "checkbox"
    assert items[ark_selector]["options"] == ["ark-A/card-1", "ark-A/card-2"]
    assert items[plan_selector]["options"] == ["plan-A/card"]
    assert forged_foreign_selector not in items

    ark_source, plan_source, foreign_source = out["provider_sources"]
    assert ark_source[VIDEO_CONTROLS_VISIBLE_KEY] is False
    assert ark_source[ark_selector] == ["ark-A/card-1"]
    assert plan_source[VIDEO_CONTROLS_VISIBLE_KEY] is True
    assert plan_source[plan_selector] == ["plan-A/card"]
    assert VIDEO_CONTROLS_VISIBLE_KEY not in foreign_source
    assert not _has_key_prefix(foreign_source, _SOURCE_VIDEO_SELECTOR_UI_KEY_PREFIX)
    for source in (ark_source, plan_source, foreign_source):
        _assert_no_wrong_layer_source_video_fields(source)

    # Source guidance and concrete controls are owned-only. New Source templates
    # get the master switch immediately; they have no model list until cards exist.
    assert ark_source["hint"] == _SOURCE_TRANSPORT_UI_HINT
    assert plan_source["hint"] == _SOURCE_TRANSPORT_UI_HINT
    assert "hint" not in foreign_source
    templates = out["config_schema"]["provider"]["config_template"]
    for name in ("ark-template", "plan-template"):
        assert templates[name][VIDEO_CONTROLS_VISIBLE_KEY] is False
        assert templates[name]["hint"] == _SOURCE_TRANSPORT_UI_HINT
        assert not _has_key_prefix(
            templates[name], _SOURCE_VIDEO_SELECTOR_UI_KEY_PREFIX
        )
    assert VIDEO_CONTROLS_VISIBLE_KEY not in templates["foreign-template"]
    assert not _has_key_prefix(
        templates["foreign-template"], _SOURCE_VIDEO_SELECTOR_UI_KEY_PREFIX
    )
    for template in templates.values():
        _assert_no_wrong_layer_source_video_fields(template)

    # Generic model-card projections contain neither the canonical value nor the
    # retired temporary switch. The Source page is the only visible entry point.
    ark_card, ark_card_2, plan_card, foreign_card = out["providers"]
    for card in (ark_card, ark_card_2, plan_card, foreign_card):
        _assert_no_model_video_ui_fields(card)

    to_save = dict(ark_source)
    _strip_source_transport_hint(to_save)
    assert "hint" not in to_save
    custom_hint = {"hint": "host-or-user-hint"}
    _strip_source_transport_hint(custom_hint)
    assert custom_hint["hint"] == "host-or-user-hint"

    print("MODEL_CARD_UI_SCOPE=OK")


if __name__ == "__main__":
    main()
