"""Volcengine-owned per-model fields for the model-card UI.

The video switch reuses AstrBot's canonical ``modalities`` checklist.  The
remaining fields are ordinary model-card configuration. Dashboard projection
may add empty values so AstrBot renders horizontal rows; the save boundary
removes empty values again so unused fields do not pollute persisted cards.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

from .model_scope import VIDEO_INPUT_ENABLED_KEY, video_input_enabled

VIDEO_INPUT_PROFILE_KEY = "volcengine_video_input_profile"
# 0.1.20 visible checkbox. The 0.1.19 three-state key remains accepted only at
# the save boundary so an already-open old Dashboard tab cannot lose intent.
VIDEO_INPUT_ENABLED_UI_KEY = "_volcengine_video_input_enabled_ui"
VIDEO_INPUT_MODE_UI_KEY = "_volcengine_video_input_mode_ui"

REASONING_MODE_KEY = "volcengine_reasoning_mode"
REASONING_EFFORT_KEY = "volcengine_reasoning_effort"
TEMPERATURE_KEY = "volcengine_temperature"
TOP_P_KEY = "volcengine_top_p"
MAX_OUTPUT_TOKENS_KEY = "volcengine_max_output_tokens"
STOP_SEQUENCES_KEY = "volcengine_stop_sequences"
FREQUENCY_PENALTY_KEY = "volcengine_frequency_penalty"
PRESENCE_PENALTY_KEY = "volcengine_presence_penalty"

VIDEO_PROFILE_VALUES = frozenset({"original", "compressed"})
VIDEO_MODE_VALUES = frozenset({"off", "original", "compressed"})
REASONING_MODE_VALUES = frozenset({"disabled", "enabled", "auto"})
REASONING_EFFORT_VALUES = frozenset({"low", "medium", "high"})

MODEL_SETTING_KEYS = frozenset(
    {
        VIDEO_INPUT_PROFILE_KEY,
        REASONING_MODE_KEY,
        REASONING_EFFORT_KEY,
        TEMPERATURE_KEY,
        TOP_P_KEY,
        MAX_OUTPUT_TOKENS_KEY,
        STOP_SEQUENCES_KEY,
        FREQUENCY_PENALTY_KEY,
        PRESENCE_PENALTY_KEY,
    }
)
MODEL_UI_KEYS = frozenset({VIDEO_INPUT_ENABLED_UI_KEY, VIDEO_INPUT_MODE_UI_KEY})
ALL_MODEL_FIELD_KEYS = frozenset((*MODEL_SETTING_KEYS, *MODEL_UI_KEYS))

# AstrBot returns one shared schema. ``dashboard_asset_bridge`` applies these
# rows only to Volcengine Source dialogs after the frontend makes its per-dialog
# schema clone; foreign dialogs mark every row invisible.
MODEL_FIELD_SCHEMA: dict[str, dict[str, Any]] = {
    VIDEO_INPUT_PROFILE_KEY: {
        "description": "视频质量 / Video Quality",
        "type": "string",
        "options": ["compressed", "original"],
        "labels": [
            "压缩 / Compressed",
            "原画 / Original Quality",
        ],
        "hint": (
            "仅在当前模型卡启用视频输入时生效；关闭视频输入不会删除这里的偏好。 / "
            "Used only while Video Input is enabled; disabling video keeps this preference."
        ),
    },
    REASONING_MODE_KEY: {
        "description": "思考模式 / Thinking Mode",
        "type": "string",
        "options": ["", "disabled", "enabled", "auto"],
        "labels": [
            "默认 / Default",
            "关闭 / Disabled",
            "开启 / Enabled",
            "自动 / Auto",
        ],
        "hint": (
            "映射到 Ark Chat 的 thinking.type。默认表示不额外注入该参数；模型是否支持由上游决定。 / "
            "Maps to Ark Chat thinking.type. Default means the plugin does not "
            "inject this parameter; upstream model support still applies."
        ),
    },
    REASONING_EFFORT_KEY: {
        "description": "思考强度 / Reasoning Effort",
        "type": "string",
        "options": ["", "low", "medium", "high"],
        "labels": [
            "默认 / Default",
            "低 / Low",
            "中 / Medium",
            "高 / High",
        ],
        "hint": (
            "映射到 reasoning_effort。仅深度推理模型支持；默认表示不额外注入。 / "
            "Maps to reasoning_effort. Only reasoning models support it; Default "
            "means no extra parameter is injected."
        ),
    },
    TEMPERATURE_KEY: {
        "description": "温度 / Temperature",
        "type": "string",
        "hint": (
            "可选，范围 0-2。留空不覆盖 custom_extra_body 或平台默认值；通常不要与 Top P 同时调整。 / "
            "Optional, range 0-2. Empty does not override custom_extra_body or the "
            "platform default; normally adjust either Temperature or Top P, not both."
        ),
    },
    TOP_P_KEY: {
        "description": "核采样 / Top P",
        "type": "string",
        "hint": (
            "可选，范围 0-1。留空不覆盖 custom_extra_body 或平台默认值。 / "
            "Optional, range 0-1. Empty does not override custom_extra_body or the "
            "platform default."
        ),
    },
    MAX_OUTPUT_TOKENS_KEY: {
        "description": "最大输出 Token / Max Output Tokens",
        "type": "string",
        "hint": (
            "可选正整数。当前 Chat 通道映射为 max_tokens；留空不覆盖已有请求参数。 / "
            "Optional positive integer. The current Chat path maps it to max_tokens; "
            "empty leaves existing request parameters untouched."
        ),
    },
    STOP_SEQUENCES_KEY: {
        "description": "停止序列 / Stop Sequences",
        "type": "list",
        "items": {"type": "string"},
        "hint": (
            "最多 4 个非空字符串；留空不发送 stop。 / "
            "Up to four non-empty strings; an empty list does not send stop."
        ),
    },
    FREQUENCY_PENALTY_KEY: {
        "description": "频率惩罚 / Frequency Penalty",
        "type": "string",
        "hint": (
            "可选，范围 -2 到 2。留空不覆盖已有请求参数。 / "
            "Optional, range -2 to 2. Empty leaves existing request parameters untouched."
        ),
    },
    PRESENCE_PENALTY_KEY: {
        "description": "存在惩罚 / Presence Penalty",
        "type": "string",
        "hint": (
            "可选，范围 -2 到 2。留空不覆盖已有请求参数。 / "
            "Optional, range -2 to 2. Empty leaves existing request parameters untouched."
        ),
    },
}


def video_input_profile(provider_config: Mapping[str, Any]) -> str:
    """Return the saved non-off video profile, defaulting legacy true to original."""

    value = str(provider_config.get(VIDEO_INPUT_PROFILE_KEY) or "").strip().lower()
    return value if value in VIDEO_PROFILE_VALUES else "original"


def video_input_mode(provider_config: Mapping[str, Any]) -> str:
    """Return the three-state UI mode without changing 0.1.18 runtime truth."""

    if not video_input_enabled(provider_config):
        return "off"
    return video_input_profile(provider_config)


def project_model_fields(
    target: dict[str, Any],
    persisted: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Project editable rows onto one owned Dashboard model-card copy."""

    source = persisted if isinstance(persisted, Mapping) else target
    target.pop(VIDEO_INPUT_ENABLED_UI_KEY, None)
    target.pop(VIDEO_INPUT_MODE_UI_KEY, None)
    modalities = target.get("modalities")
    if isinstance(modalities, list):
        projected_modalities = [value for value in modalities if value != "video"]
        explicit = source.get(VIDEO_INPUT_ENABLED_KEY)
        if explicit is True or (not isinstance(explicit, bool) and video_input_enabled(source)):
            projected_modalities.append("video")
        target["modalities"] = projected_modalities
    target[VIDEO_INPUT_PROFILE_KEY] = video_input_profile(source)

    for key in (REASONING_MODE_KEY, REASONING_EFFORT_KEY):
        value = source.get(key)
        target[key] = str(value).strip() if value is not None else ""

    for key in (
        TEMPERATURE_KEY,
        TOP_P_KEY,
        MAX_OUTPUT_TOKENS_KEY,
        FREQUENCY_PENALTY_KEY,
        PRESENCE_PENALTY_KEY,
    ):
        value = source.get(key)
        target[key] = "" if value is None else str(value)

    stop = source.get(STOP_SEQUENCES_KEY)
    target[STOP_SEQUENCES_KEY] = list(stop) if isinstance(stop, list) else []
    return target


def strip_model_fields(provider_config: dict[str, Any]) -> bool:
    """Remove every 0.1.19 Volcengine model setting/UI field from one card."""

    changed = False
    for key in ALL_MODEL_FIELD_KEYS:
        if key in provider_config:
            provider_config.pop(key, None)
            changed = True
    return changed


def _normalize_enum(
    provider_config: dict[str, Any],
    key: str,
    allowed: frozenset[str],
) -> None:
    if key not in provider_config:
        return
    value = str(provider_config.get(key) or "").strip().lower()
    if not value:
        provider_config.pop(key, None)
        return
    if value not in allowed:
        raise ValueError(f"Invalid {key}: {value!r}")
    provider_config[key] = value


def _normalize_float(
    provider_config: dict[str, Any],
    key: str,
    *,
    minimum: float,
    maximum: float,
) -> None:
    if key not in provider_config:
        return
    raw = provider_config.get(key)
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        provider_config.pop(key, None)
        return
    try:
        value = float(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid numeric value for {key}: {raw!r}") from exc
    if not math.isfinite(value):
        raise ValueError(f"{key} must be a finite number")
    if value < minimum or value > maximum:
        raise ValueError(f"{key} must be between {minimum} and {maximum}")
    provider_config[key] = value


def _normalize_positive_int(provider_config: dict[str, Any], key: str) -> None:
    if key not in provider_config:
        return
    raw = provider_config.get(key)
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        provider_config.pop(key, None)
        return
    try:
        value = int(str(raw).strip())
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid integer value for {key}: {raw!r}") from exc
    if value <= 0:
        raise ValueError(f"{key} must be greater than 0")
    provider_config[key] = value


def _normalize_stop_sequences(provider_config: dict[str, Any]) -> None:
    if STOP_SEQUENCES_KEY not in provider_config:
        return
    raw = provider_config.get(STOP_SEQUENCES_KEY)
    if raw in (None, ""):
        provider_config.pop(STOP_SEQUENCES_KEY, None)
        return
    if not isinstance(raw, list):
        raise ValueError(f"{STOP_SEQUENCES_KEY} must be a list")
    values = [str(value).strip() for value in raw if str(value).strip()]
    if not values:
        provider_config.pop(STOP_SEQUENCES_KEY, None)
        return
    if len(values) > 4:
        raise ValueError(f"{STOP_SEQUENCES_KEY} accepts at most 4 strings")
    provider_config[STOP_SEQUENCES_KEY] = values


def normalize_model_fields_for_save(provider_config: dict[str, Any]) -> dict[str, Any]:
    """Translate UI-only values and validate persisted 0.1.19 model settings."""

    if VIDEO_INPUT_ENABLED_UI_KEY in provider_config:
        enabled = provider_config.pop(VIDEO_INPUT_ENABLED_UI_KEY)
        if not isinstance(enabled, bool):
            raise ValueError(
                f"Invalid video input checkbox value: {enabled!r}"
            )
        provider_config[VIDEO_INPUT_ENABLED_KEY] = enabled

    # Compatibility with an already-open 0.1.19 model dialog. The current
    # checkbox value, when present, deliberately outranks this retired field.
    if VIDEO_INPUT_MODE_UI_KEY in provider_config:
        mode = str(provider_config.pop(VIDEO_INPUT_MODE_UI_KEY) or "").strip().lower()
        if mode not in VIDEO_MODE_VALUES:
            raise ValueError(f"Invalid video input mode: {mode!r}")
        if VIDEO_INPUT_ENABLED_KEY not in provider_config:
            if mode == "off":
                provider_config[VIDEO_INPUT_ENABLED_KEY] = False
            else:
                provider_config[VIDEO_INPUT_ENABLED_KEY] = True
                provider_config[VIDEO_INPUT_PROFILE_KEY] = mode

    # The standard AstrBot checklist is the current UI and therefore outranks
    # compatibility values submitted by an already-open older Dashboard tab.
    modalities = provider_config.get("modalities")
    if isinstance(modalities, list):
        provider_config[VIDEO_INPUT_ENABLED_KEY] = "video" in modalities

    if VIDEO_INPUT_PROFILE_KEY in provider_config:
        profile = str(provider_config.get(VIDEO_INPUT_PROFILE_KEY) or "").strip().lower()
        if not profile:
            provider_config.pop(VIDEO_INPUT_PROFILE_KEY, None)
        elif profile not in VIDEO_PROFILE_VALUES:
            raise ValueError(f"Invalid {VIDEO_INPUT_PROFILE_KEY}: {profile!r}")
        else:
            provider_config[VIDEO_INPUT_PROFILE_KEY] = profile

    _normalize_enum(provider_config, REASONING_MODE_KEY, REASONING_MODE_VALUES)
    _normalize_enum(provider_config, REASONING_EFFORT_KEY, REASONING_EFFORT_VALUES)
    _normalize_float(provider_config, TEMPERATURE_KEY, minimum=0.0, maximum=2.0)
    _normalize_float(provider_config, TOP_P_KEY, minimum=0.0, maximum=1.0)
    _normalize_positive_int(provider_config, MAX_OUTPUT_TOKENS_KEY)
    _normalize_stop_sequences(provider_config)
    _normalize_float(
        provider_config,
        FREQUENCY_PENALTY_KEY,
        minimum=-2.0,
        maximum=2.0,
    )
    _normalize_float(
        provider_config,
        PRESENCE_PENALTY_KEY,
        minimum=-2.0,
        maximum=2.0,
    )
    return provider_config


def apply_request_overrides(
    provider_config: Mapping[str, Any],
    payloads: dict[str, Any],
    extra_body: dict[str, Any],
) -> None:
    """Apply explicit 0.1.19 rows after custom_extra_body has been merged.

    This ordering intentionally makes an explicit horizontal model-card field
    outrank the same key inside ``custom_extra_body``. Missing 0.1.19 fields do
    nothing, so the pre-existing JSON escape hatch and AstrBot defaults remain
    unchanged.
    """

    reasoning_mode = str(provider_config.get(REASONING_MODE_KEY) or "").strip().lower()
    if reasoning_mode in REASONING_MODE_VALUES:
        thinking = extra_body.get("thinking")
        merged_thinking = dict(thinking) if isinstance(thinking, dict) else {}
        merged_thinking["type"] = reasoning_mode
        extra_body["thinking"] = merged_thinking

    reasoning_effort = str(
        provider_config.get(REASONING_EFFORT_KEY) or ""
    ).strip().lower()
    if reasoning_effort in REASONING_EFFORT_VALUES:
        extra_body["reasoning_effort"] = reasoning_effort

    direct_map = {
        TEMPERATURE_KEY: "temperature",
        TOP_P_KEY: "top_p",
        MAX_OUTPUT_TOKENS_KEY: "max_tokens",
        STOP_SEQUENCES_KEY: "stop",
        FREQUENCY_PENALTY_KEY: "frequency_penalty",
        PRESENCE_PENALTY_KEY: "presence_penalty",
    }
    for config_key, request_key in direct_map.items():
        if config_key in provider_config:
            extra_body[request_key] = provider_config[config_key]
