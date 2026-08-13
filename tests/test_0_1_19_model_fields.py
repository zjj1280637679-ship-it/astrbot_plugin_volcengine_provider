from __future__ import annotations

import copy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "AstrBot" / "data" / "plugins"))

from astrbot_plugin_volcengine_provider.capabilities import (
    FREQUENCY_PENALTY_KEY,
    MAX_OUTPUT_TOKENS_KEY,
    PRESENCE_PENALTY_KEY,
    REASONING_EFFORT_KEY,
    REASONING_MODE_KEY,
    STOP_SEQUENCES_KEY,
    TEMPERATURE_KEY,
    TOP_P_KEY,
    VIDEO_INPUT_ENABLED_KEY,
    VIDEO_INPUT_ENABLED_UI_KEY,
    VIDEO_INPUT_MODE_UI_KEY,
    VIDEO_INPUT_PROFILE_KEY,
    apply_request_overrides,
    normalize_model_fields_for_save,
    project_model_fields,
    strip_model_fields,
    video_input_mode,
)


def _expect_value_error(fn) -> None:
    try:
        fn()
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def main() -> None:
    # 0.1.18 compatibility: a legacy true has no profile and therefore becomes
    # Original Quality, while false remains Off.
    assert video_input_mode({VIDEO_INPUT_ENABLED_KEY: True}) == "original"
    assert video_input_mode({VIDEO_INPUT_ENABLED_KEY: False}) == "off"

    # A saved profile survives the Source-page shortcut being switched off.
    saved = {
        VIDEO_INPUT_ENABLED_KEY: False,
        VIDEO_INPUT_PROFILE_KEY: "compressed",
    }
    assert video_input_mode(saved) == "off"
    projected = project_model_fields({"modalities": ["text", "image"]}, saved)
    assert projected["modalities"] == ["text", "image"]
    assert VIDEO_INPUT_ENABLED_UI_KEY not in projected
    assert VIDEO_INPUT_MODE_UI_KEY not in projected
    assert projected[VIDEO_INPUT_PROFILE_KEY] == "compressed"

    # The canonical AstrBot checklist is the current switch. The retired key
    # remains accepted only for an already-open old Dashboard tab.
    canonical = normalize_model_fields_for_save(
        {
            "modalities": ["text", "image", "video"],
            VIDEO_INPUT_ENABLED_KEY: False,
            VIDEO_INPUT_PROFILE_KEY: "compressed",
        }
    )
    assert canonical[VIDEO_INPUT_ENABLED_KEY] is True
    assert canonical["modalities"] == ["text", "image", "video"]
    canonical_wins = normalize_model_fields_for_save(
        {
            "modalities": ["text", "video"],
            VIDEO_INPUT_ENABLED_UI_KEY: False,
            VIDEO_INPUT_MODE_UI_KEY: "off",
        }
    )
    assert canonical_wins[VIDEO_INPUT_ENABLED_KEY] is True

    # Turning the old checkbox back on remains backward compatible.
    normalized = normalize_model_fields_for_save(
        {
            VIDEO_INPUT_ENABLED_KEY: False,
            VIDEO_INPUT_PROFILE_KEY: "compressed",
            VIDEO_INPUT_ENABLED_UI_KEY: True,
        }
    )
    assert normalized[VIDEO_INPUT_ENABLED_KEY] is True
    assert normalized[VIDEO_INPUT_PROFILE_KEY] == "compressed"
    assert VIDEO_INPUT_MODE_UI_KEY not in normalized

    # Off is a checkbox toggle: the last profile is deliberately retained.
    normalized = normalize_model_fields_for_save(
        {
            VIDEO_INPUT_ENABLED_KEY: True,
            VIDEO_INPUT_PROFILE_KEY: "compressed",
            VIDEO_INPUT_ENABLED_UI_KEY: False,
        }
    )
    assert normalized[VIDEO_INPUT_ENABLED_KEY] is False
    assert normalized[VIDEO_INPUT_PROFILE_KEY] == "compressed"

    # An already-open 0.1.19 tab remains readable, but the current checkbox wins
    # when both generations are submitted together.
    legacy = normalize_model_fields_for_save(
        {VIDEO_INPUT_MODE_UI_KEY: "compressed"}
    )
    assert legacy[VIDEO_INPUT_ENABLED_KEY] is True
    assert legacy[VIDEO_INPUT_PROFILE_KEY] == "compressed"
    current_wins = normalize_model_fields_for_save(
        {
            VIDEO_INPUT_ENABLED_UI_KEY: False,
            VIDEO_INPUT_MODE_UI_KEY: "compressed",
        }
    )
    assert current_wins[VIDEO_INPUT_ENABLED_KEY] is False

    # Optional rows distinguish empty from the real numeric value 0.
    empty = normalize_model_fields_for_save(
        {
            TEMPERATURE_KEY: "",
            TOP_P_KEY: "",
            MAX_OUTPUT_TOKENS_KEY: "",
            FREQUENCY_PENALTY_KEY: "",
            PRESENCE_PENALTY_KEY: "",
            STOP_SEQUENCES_KEY: [],
            REASONING_MODE_KEY: "",
            REASONING_EFFORT_KEY: "",
        }
    )
    for key in (
        TEMPERATURE_KEY,
        TOP_P_KEY,
        MAX_OUTPUT_TOKENS_KEY,
        FREQUENCY_PENALTY_KEY,
        PRESENCE_PENALTY_KEY,
        STOP_SEQUENCES_KEY,
        REASONING_MODE_KEY,
        REASONING_EFFORT_KEY,
    ):
        assert key not in empty

    zeros = normalize_model_fields_for_save(
        {
            TEMPERATURE_KEY: "0",
            TOP_P_KEY: "0",
            FREQUENCY_PENALTY_KEY: "0",
            PRESENCE_PENALTY_KEY: "0",
        }
    )
    assert zeros[TEMPERATURE_KEY] == 0.0
    assert zeros[TOP_P_KEY] == 0.0
    assert zeros[FREQUENCY_PENALTY_KEY] == 0.0
    assert zeros[PRESENCE_PENALTY_KEY] == 0.0

    normalized = normalize_model_fields_for_save(
        {
            TEMPERATURE_KEY: "0.7",
            TOP_P_KEY: "0.95",
            MAX_OUTPUT_TOKENS_KEY: "32768",
            STOP_SEQUENCES_KEY: ["STOP", "  END  ", ""],
            FREQUENCY_PENALTY_KEY: "-0.25",
            PRESENCE_PENALTY_KEY: "0.5",
            REASONING_MODE_KEY: "auto",
            REASONING_EFFORT_KEY: "high",
        }
    )
    assert normalized[TEMPERATURE_KEY] == 0.7
    assert normalized[TOP_P_KEY] == 0.95
    assert normalized[MAX_OUTPUT_TOKENS_KEY] == 32768
    assert normalized[STOP_SEQUENCES_KEY] == ["STOP", "END"]
    assert normalized[FREQUENCY_PENALTY_KEY] == -0.25
    assert normalized[PRESENCE_PENALTY_KEY] == 0.5
    assert normalized[REASONING_MODE_KEY] == "auto"
    assert normalized[REASONING_EFFORT_KEY] == "high"

    _expect_value_error(
        lambda: normalize_model_fields_for_save({TEMPERATURE_KEY: "2.1"})
    )
    _expect_value_error(lambda: normalize_model_fields_for_save({TOP_P_KEY: "1.1"}))
    _expect_value_error(
        lambda: normalize_model_fields_for_save({MAX_OUTPUT_TOKENS_KEY: "0"})
    )
    _expect_value_error(
        lambda: normalize_model_fields_for_save(
            {STOP_SEQUENCES_KEY: ["1", "2", "3", "4", "5"]}
        )
    )
    _expect_value_error(
        lambda: normalize_model_fields_for_save({REASONING_MODE_KEY: "magic"})
    )
    for key in (
        TEMPERATURE_KEY,
        TOP_P_KEY,
        FREQUENCY_PENALTY_KEY,
        PRESENCE_PENALTY_KEY,
    ):
        for non_finite in ("nan", "NaN", "inf", "-inf", "Infinity", "1e309"):
            _expect_value_error(
                lambda key=key, value=non_finite: normalize_model_fields_for_save(
                    {key: value}
                )
            )

    # Explicit horizontal rows outrank the same JSON keys, while missing rows do
    # nothing and therefore preserve custom_extra_body values.
    extra = {
        "temperature": 1.1,
        "top_p": 0.2,
        "max_tokens": 4096,
        "stop": ["CUSTOM"],
        "frequency_penalty": 0.1,
        "presence_penalty": 0.2,
        "reasoning_effort": "low",
        "thinking": {"type": "disabled", "vendor_extra": "kept"},
        "foreign": "kept",
    }
    provider = normalize_model_fields_for_save(
        {
            TEMPERATURE_KEY: "0.6",
            TOP_P_KEY: "0.9",
            MAX_OUTPUT_TOKENS_KEY: "8192",
            STOP_SEQUENCES_KEY: ["ROW"],
            FREQUENCY_PENALTY_KEY: "-0.5",
            PRESENCE_PENALTY_KEY: "0.75",
            REASONING_MODE_KEY: "auto",
            REASONING_EFFORT_KEY: "high",
        }
    )
    apply_request_overrides(provider, {}, extra)
    assert extra["temperature"] == 0.6
    assert extra["top_p"] == 0.9
    assert extra["max_tokens"] == 8192
    assert extra["stop"] == ["ROW"]
    assert extra["frequency_penalty"] == -0.5
    assert extra["presence_penalty"] == 0.75
    assert extra["reasoning_effort"] == "high"
    assert extra["thinking"] == {"type": "auto", "vendor_extra": "kept"}
    assert extra["foreign"] == "kept"

    untouched = {"temperature": 1.25, "custom": True}
    apply_request_overrides({}, {}, untouched)
    assert untouched == {"temperature": 1.25, "custom": True}

    # Foreign/ownership cleanup can remove every 0.1.19 field without touching
    # unrelated host/user configuration.
    card = copy.deepcopy(provider)
    card[VIDEO_INPUT_PROFILE_KEY] = "compressed"
    card[VIDEO_INPUT_ENABLED_UI_KEY] = True
    card[VIDEO_INPUT_MODE_UI_KEY] = "compressed"
    card["custom_extra_body"] = {"keep": True}
    assert strip_model_fields(card) is True
    assert card == {"custom_extra_body": {"keep": True}}

    print("MODEL_FIELDS_0_1_19=OK")


if __name__ == "__main__":
    main()
