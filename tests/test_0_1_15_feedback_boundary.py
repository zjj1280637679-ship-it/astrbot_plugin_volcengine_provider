from __future__ import annotations

import asyncio
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "AstrBot" / "data" / "plugins"))

from astrbot.core.agent.message import TextPart
from astrbot_plugin_volcengine_provider.adapters.errors import (
    AdapterInputTransportError,
)
from astrbot_plugin_volcengine_provider.capabilities import (
    AGENT_PLAN_PROVIDER_TYPE,
    ARK_PROVIDER_TYPE,
    LEGACY_MODEL_VIDEO_INPUT_KEY,
    LEGACY_MODEL_VIDEO_UI_KEY_PREFIX,
    SOURCE_VIDEO_SELECTOR_UI_KEY_PREFIX,
    VIDEO_CONTROLS_VISIBLE_KEY,
    VIDEO_INPUT_ENABLED_KEY,
    cleanup_owned_settings_on_source_change,
    clear_source_model_hints,
    consume_source_model_hints,
    legacy_model_video_ui_key,
    migrate_legacy_video_settings,
    normalize_owned_model_card_for_save,
    remember_source_model_hint,
    video_input_enabled,
)
from astrbot_plugin_volcengine_provider.metadata.agent_plan import (
    KNOWN_AGENT_PLAN_MODELS,
)
from astrbot_plugin_volcengine_provider.metadata.ark import normalize_ark_model_metadata
from astrbot_plugin_volcengine_provider.providers import ProviderVolcengineArk
from astrbot_plugin_volcengine_provider.registry import (
    _inject_model_card_video_control,
    _merge_source_feedback,
    _source_video_selector_ui_key,
)


def main() -> None:
    assert video_input_enabled({}) is False
    assert video_input_enabled({VIDEO_INPUT_ENABLED_KEY: True}) is True
    assert (
        video_input_enabled(
            {
                VIDEO_INPUT_ENABLED_KEY: True,
                VIDEO_CONTROLS_VISIBLE_KEY: False,
            }
        )
        is True
    )
    assert video_input_enabled({"modalities": ["text", "video"]}) is False
    assert (
        video_input_enabled(
            {
                "provider_source_id": "ark",
                legacy_model_video_ui_key("ark"): True,
                LEGACY_MODEL_VIDEO_INPUT_KEY: False,
            }
        )
        is True
    )
    assert (
        video_input_enabled(
            {
                "provider_source_id": "ark",
                legacy_model_video_ui_key("other"): True,
            }
        )
        is False
    )

    sources = [
        {"id": "ark", "type": ARK_PROVIDER_TYPE},
        {"id": "foreign", "type": "openai_chat_completion"},
    ]
    card = {
        "id": "ark/a",
        "provider_source_id": "ark",
        "modalities": ["text", "image"],
    }
    before = copy.deepcopy(card["modalities"])
    normalize_owned_model_card_for_save(card, sources, default_enabled=False)
    assert card[VIDEO_INPUT_ENABLED_KEY] is False
    assert card["modalities"] == before

    cfg = {
        "provider_sources": [
            {
                "id": "ark",
                "type": ARK_PROVIDER_TYPE,
                "volcengine_ark_video_input": True,
            },
            {"id": "foreign", "type": "openai_chat_completion"},
        ],
        "provider": [
            {
                "id": "ark/legacy",
                "provider_source_id": "ark",
                "modalities": ["text", "video"],
            },
            {
                "id": "foreign/a",
                "provider_source_id": "foreign",
                "modalities": ["text"],
            },
        ],
    }
    migrate_legacy_video_settings(cfg)
    assert cfg["provider"][0][VIDEO_INPUT_ENABLED_KEY] is True
    assert cfg["provider"][0]["modalities"] == ["text", "video"]
    assert VIDEO_INPUT_ENABLED_KEY not in cfg["provider"][1]
    assert "volcengine_ark_video_input" not in cfg["provider_sources"][0]

    # Migration precedence is user-state preservation, not a capability guess:
    # canonical > matching retired 0.1.17 UI > older per-card > explicit Source
    # bool > modalities clue.
    precedence_cfg = {
        "provider_sources": [
            {
                "id": "ark-off",
                "type": ARK_PROVIDER_TYPE,
                "volcengine_ark_video_input": False,
            },
            {
                "id": "ark-on",
                "type": ARK_PROVIDER_TYPE,
                "volcengine_ark_video_input": True,
            },
            {
                "id": "plan-off",
                "type": AGENT_PLAN_PROVIDER_TYPE,
                "volcengine_agent_plan_video_input": False,
            },
        ],
        "provider": [
            {
                "id": "ark/source-disabled",
                "provider_source_id": "ark-off",
                "modalities": ["text", "video"],
            },
            {
                "id": "ark/model-override",
                "provider_source_id": "ark-off",
                "volcengine_model_video_input": True,
                "modalities": ["text", "video"],
            },
            {
                "id": "ark/new-override",
                "provider_source_id": "ark-on",
                VIDEO_INPUT_ENABLED_KEY: False,
                "modalities": ["text", "video"],
            },
            {
                "id": "plan/source-disabled",
                "provider_source_id": "plan-off",
                "modalities": ["text", "video"],
            },
        ],
    }
    migrate_legacy_video_settings(precedence_cfg)
    cards = {card["id"]: card for card in precedence_cfg["provider"]}
    assert cards["ark/source-disabled"][VIDEO_INPUT_ENABLED_KEY] is False
    assert cards["ark/source-disabled"]["modalities"] == ["text", "video"]
    assert cards["ark/model-override"][VIDEO_INPUT_ENABLED_KEY] is True
    assert "volcengine_model_video_input" not in cards["ark/model-override"]
    assert cards["ark/new-override"][VIDEO_INPUT_ENABLED_KEY] is False
    assert cards["plan/source-disabled"][VIDEO_INPUT_ENABLED_KEY] is False
    assert all(
        "volcengine_ark_video_input" not in source
        and "volcengine_agent_plan_video_input" not in source
        for source in precedence_cfg["provider_sources"]
    )

    # AstrBot 4.26.1 returned live model-card dictionaries from the schema
    # service. The 0.1.17 projection could therefore leave its intended
    # temporary key in memory before another save. Preserve only the exact
    # current-Source key, then remove every presentation/wrong-layer field.
    ark_retired_ui = legacy_model_video_ui_key("ark")
    wrong_retired_ui = legacy_model_video_ui_key("other")
    ark_selector = f"{SOURCE_VIDEO_SELECTOR_UI_KEY_PREFIX}61726b"
    polluted_cfg = {
        "provider_sources": [
            {
                "id": "ark",
                "type": ARK_PROVIDER_TYPE,
                VIDEO_CONTROLS_VISIBLE_KEY: True,
                VIDEO_INPUT_ENABLED_KEY: True,
                LEGACY_MODEL_VIDEO_INPUT_KEY: True,
                ark_retired_ui: True,
                ark_selector: ["ark/ui-current"],
            },
            {
                "id": "foreign",
                "type": "openai_chat_completion",
                VIDEO_CONTROLS_VISIBLE_KEY: True,
                ark_selector: ["foreign/forged"],
            },
        ],
        "provider": [
            {
                "id": "ark/ui-current",
                "provider_source_id": "ark",
                ark_retired_ui: True,
                wrong_retired_ui: False,
                LEGACY_MODEL_VIDEO_INPUT_KEY: False,
                VIDEO_CONTROLS_VISIBLE_KEY: True,
                ark_selector: ["ark/ui-current"],
            },
            {
                "id": "ark/canonical",
                "provider_source_id": "ark",
                VIDEO_INPUT_ENABLED_KEY: False,
                ark_retired_ui: True,
            },
            {
                "id": "ark/wrong-only",
                "provider_source_id": "ark",
                wrong_retired_ui: True,
            },
            {
                "id": "foreign/forged",
                "provider_source_id": "foreign",
                VIDEO_INPUT_ENABLED_KEY: True,
                LEGACY_MODEL_VIDEO_INPUT_KEY: True,
                legacy_model_video_ui_key("foreign"): True,
                VIDEO_CONTROLS_VISIBLE_KEY: True,
                ark_selector: ["ark/ui-current"],
                "modalities": ["text", "video"],
            },
        ],
    }
    migrated = migrate_legacy_video_settings(polluted_cfg)
    polluted_cards = {card["id"]: card for card in polluted_cfg["provider"]}
    assert polluted_cards["ark/ui-current"][VIDEO_INPUT_ENABLED_KEY] is True
    assert polluted_cards["ark/canonical"][VIDEO_INPUT_ENABLED_KEY] is False
    assert VIDEO_INPUT_ENABLED_KEY not in polluted_cards["ark/wrong-only"]
    assert polluted_cards["foreign/forged"]["modalities"] == ["text", "video"]
    assert all(
        VIDEO_CONTROLS_VISIBLE_KEY not in card
        and LEGACY_MODEL_VIDEO_INPUT_KEY not in card
        and not any(
            str(key).startswith(LEGACY_MODEL_VIDEO_UI_KEY_PREFIX)
            or str(key).startswith(SOURCE_VIDEO_SELECTOR_UI_KEY_PREFIX)
            for key in card
        )
        for card in polluted_cards.values()
    )
    assert VIDEO_INPUT_ENABLED_KEY not in polluted_cards["foreign/forged"]
    ark_source, foreign_source = polluted_cfg["provider_sources"]
    assert ark_source[VIDEO_CONTROLS_VISIBLE_KEY] is True
    assert VIDEO_CONTROLS_VISIBLE_KEY not in foreign_source
    assert all(
        VIDEO_INPUT_ENABLED_KEY not in source
        and LEGACY_MODEL_VIDEO_INPUT_KEY not in source
        and not any(
            str(key).startswith(LEGACY_MODEL_VIDEO_UI_KEY_PREFIX)
            or str(key).startswith(SOURCE_VIDEO_SELECTOR_UI_KEY_PREFIX)
            for key in source
        )
        for source in polluted_cfg["provider_sources"]
    )
    assert set(migrated) >= {
        "ark/ui-current",
        "ark/canonical",
        "ark/wrong-only",
        "foreign/forged",
    }

    anonymous_debris = {
        "provider_sources": [],
        "provider": [{VIDEO_CONTROLS_VISIBLE_KEY: True}],
    }
    assert migrate_legacy_video_settings(anonymous_debris) == [""]
    assert VIDEO_CONTROLS_VISIBLE_KEY not in anonymous_debris["provider"][0]

    moving = {
        "provider_source_id": "foreign",
        VIDEO_INPUT_ENABLED_KEY: True,
        "modalities": ["text", "video"],
    }
    cleanup_owned_settings_on_source_change(
        moving,
        old_source_type=ARK_PROVIDER_TYPE,
        new_source_type="openai_chat_completion",
    )
    assert VIDEO_INPUT_ENABLED_KEY not in moving
    assert moving["modalities"] == ["text", "video"]

    # Sparse receipt: missing fields stay absent; no capability default is authored.
    mid, hint = normalize_ark_model_metadata({"id": "unknown"})
    assert mid == "unknown"
    assert hint == {"id": "unknown"}
    _, rich = normalize_ark_model_metadata(
        {
            "id": "rich",
            "modalities": {"input_modalities": ["image", "audio"]},
            "features": {"reasoning": {"supported": True}},
            "token_limits": {"context_window": 65536},
        }
    )
    assert rich["modalities"]["input"] == ["image", "audio"]
    assert rich["reasoning"] is True
    assert rich["limit"] == {"context": 65536}
    assert "tool_call" not in rich

    # A live receipt wins for the same display field *for this response only*.
    # Missing directions/fields remain host-owned rather than being invented.
    base = {
        "id": "same",
        "tool_call": True,
        "modalities": {"input": ["image"], "output": ["text"]},
        "limit": {"context": 131072, "output": 0},
    }
    incoming = {
        "id": "same",
        "tool_call": False,
        "modalities": {"input": ["audio"]},
        "limit": {"context": 65536, "output": 4096},
    }
    merged = _merge_source_feedback(base, incoming)
    assert merged["tool_call"] is False
    assert merged["modalities"] == {"input": ["audio"], "output": ["text"]}
    assert merged["limit"] == {"context": 65536, "output": 4096}
    # The source object is copy-on-write; AstrBot's base feedback is untouched.
    assert base["tool_call"] is True
    assert base["modalities"]["input"] == ["image"]
    assert base["limit"]["context"] == 131072

    # Dynamic feedback is a single-use current-call handoff, never history.
    clear_source_model_hints("live")
    remember_source_model_hint("live", "m", {"id": "m", "tool_call": False})
    assert consume_source_model_hints("live", ["m"]) == {
        "m": {"id": "m", "tool_call": False}
    }
    assert consume_source_model_hints("live", ["m"]) == {}

    # ContextVar isolation: concurrent model-list calls cannot consume each
    # other's Source feedback even when their Source/model identifiers match.
    async def isolated_feedback(value: bool) -> bool:
        clear_source_model_hints("same-source")
        remember_source_model_hint(
            "same-source",
            "same-model",
            {"id": "same-model", "tool_call": value},
        )
        await asyncio.sleep(0)
        result = consume_source_model_hints("same-source", ["same-model"])
        return result["same-model"]["tool_call"]

    async def run_isolation() -> list[bool]:
        return list(
            await asyncio.gather(
                isolated_feedback(True),
                isolated_feedback(False),
            )
        )

    assert asyncio.run(run_isolation()) == [True, False]

    payload = {
        "config_schema": {"provider": {"items": {}}},
        "provider_sources": sources,
        "providers": [
            {"id": "ark/a", "provider_source_id": "ark", "model": "same"},
            {"id": "foreign/a", "provider_source_id": "foreign", "model": "same"},
        ],
    }
    out = _inject_model_card_video_control(payload)
    assert VIDEO_INPUT_ENABLED_KEY not in out["providers"][0]
    assert out["provider_sources"][0][VIDEO_CONTROLS_VISIBLE_KEY] is False
    assert out["provider_sources"][0][_source_video_selector_ui_key("ark")] == []
    assert VIDEO_INPUT_ENABLED_KEY not in out["providers"][1]
    assert _source_video_selector_ui_key("foreign") not in out["provider_sources"][1]

    # Agent Plan list remains discovery-only and includes third parties.
    assert "deepseek-v4-pro" in KNOWN_AGENT_PLAN_MODELS
    assert "glm-5.2" in KNOWN_AGENT_PLAN_MODELS

    provider = ProviderVolcengineArk(
        {
            "id": "video-test",
            "provider": "volcengine",
            "type": ARK_PROVIDER_TYPE,
            "provider_type": "chat_completion",
            "enable": True,
            "key": ["dummy-key"],
            "api_base": "https://ark.cn-beijing.volces.com/api/v3",
            "model": "dummy-model",
            VIDEO_INPUT_ENABLED_KEY: True,
        },
        {"request_max_retries": 1},
    )
    assert provider is not None

    async def fake_resolve(ref: str) -> str:
        assert ref == "/tmp/test.mp4"
        return "data:video/mp4;base64,AAAA"

    import astrbot_plugin_volcengine_provider.adapters.video as video_adapter

    original = video_adapter.resolve_video_reference
    video_adapter.resolve_video_reference = fake_resolve
    try:
        marker = "[Video Attachment: name test.mp4, path /tmp/test.mp4]"
        messages = [{"role": "user", "content": [{"type": "text", "text": marker}]}]
        asyncio.run(
            video_adapter.inject_current_request_videos(
                messages,
                [TextPart(text=marker)],
                enabled=True,
            )
        )
        assert messages[0]["content"][0]["type"] == "video_url"

        messages_off = [{"role": "user", "content": [{"type": "text", "text": marker}]}]
        asyncio.run(
            video_adapter.inject_current_request_videos(
                messages_off,
                [TextPart(text=marker)],
                enabled=False,
            )
        )
        assert messages_off[0]["content"] == [{"type": "text", "text": "[Video]"}]

        # Trusted attachment exists but assembled content is missing: transport
        # failure, not model rejection/capability evidence.
        try:
            asyncio.run(
                video_adapter.inject_current_request_videos(
                    [{"role": "user", "content": [{"type": "text", "text": "other"}]}],
                    [TextPart(text=marker)],
                    enabled=False,
                )
            )
            raise AssertionError("expected AdapterInputTransportError")
        except AdapterInputTransportError as exc:
            assert exc.reached_model is False
            assert exc.capability_observed is None
            assert not hasattr(exc, "fallback_recommended")
            assert exc.media_type == "video"
            assert exc.stage == "assemble_payload"
    finally:
        video_adapter.resolve_video_reference = original

    # Audio normalization errors are wrapped with the same provenance contract.
    import astrbot_plugin_volcengine_provider.adapters.audio as audio_adapter

    original_audio_normalize = audio_adapter.normalize_ark_chat_audio

    async def fail_audio(_: str) -> bytes:
        raise ValueError("synthetic local audio failure")

    audio_adapter.normalize_ark_chat_audio = fail_audio
    try:
        try:
            asyncio.run(audio_adapter.build_ark_input_audio("dummy"))
            raise AssertionError("expected AdapterInputTransportError")
        except AdapterInputTransportError as exc:
            assert exc.reached_model is False
            assert exc.capability_observed is None
            assert not hasattr(exc, "fallback_recommended")
            assert exc.media_type == "audio"
            assert exc.stage == "normalize_for_ark"
    finally:
        audio_adapter.normalize_ark_chat_audio = original_audio_normalize

    semantics = json.loads(
        (ROOT / "docs" / "contracts" / "SEMANTICS.json").read_text("utf-8")
    )
    assert semantics["epistemic_contract"]["feedback_is_truth"] is False
    assert (
        semantics["epistemic_contract"]["missing_feedback_means_unsupported"] is False
    )
    assert (
        semantics["live_model_feedback"]["ordinary_ark_models_receipt"]["persistent"]
        is False
    )
    assert semantics["failure_domains"]["input_transport"]["reached_model"] is False
    assert semantics["failure_domains"]["input_transport"]["routing_advice"] is None
    assert (
        semantics["future_extension_policy"]["preserve_unknown_future_feedback_tokens"]
        is True
    )
    assert (
        semantics["fields"][VIDEO_INPUT_ENABLED_KEY]["kind"]
        == "request_transport_switch"
    )

    print("FEEDBACK_BOUNDARY_0_1_15=OK")


if __name__ == "__main__":
    main()
