from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "AstrBot" / "data" / "plugins"))

from astrbot_plugin_volcengine_provider.capabilities import (
    AGENT_PLAN_PROVIDER_TYPE,
    ARK_PROVIDER_TYPE,
    VIDEO_INPUT_ENABLED_KEY,
    normalize_owned_model_card_for_save,
)
from astrbot_plugin_volcengine_provider.registry import (
    _SOURCE_TRANSPORT_UI_HINT,
    _VIDEO_UI_KEY_PREFIX,
    _apply_video_ui_transport_setting,
    _inject_model_card_video_control,
    _inject_owned_source_transport_hint,
    _strip_source_transport_hint,
    _video_ui_key,
)


def main() -> None:
    # Dashboard key encoding is reversible/injective rather than probabilistic.
    for source_id in ("ark-A", "a/b", "a?b", "火山 方舟", "emoji-🚀"):
        ui_key = _video_ui_key(source_id)
        encoded = ui_key.removeprefix(_VIDEO_UI_KEY_PREFIX)
        assert bytes.fromhex(encoded).decode("utf-8") == source_id
    assert _video_ui_key("a/b") != _video_ui_key("a?b")

    sources = [
        {"id": "ark-A", "type": ARK_PROVIDER_TYPE},
        {"id": "plan-A", "type": AGENT_PLAN_PROVIDER_TYPE},
        {"id": "foreign-A", "type": "openai_chat_completion"},
    ]
    payload = {
        "config_schema": {"provider": {"items": {}}},
        "provider_sources": sources,
        "providers": [
            {
                "id": "ark-A/m",
                "provider_source_id": "ark-A",
                "model": "m",
                VIDEO_INPUT_ENABLED_KEY: True,
            },
            {
                "id": "plan-A/m",
                "provider_source_id": "plan-A",
                "model": "m",
                VIDEO_INPUT_ENABLED_KEY: False,
            },
            {"id": "foreign-A/m", "provider_source_id": "foreign-A", "model": "m"},
        ],
    }

    out = _inject_model_card_video_control(payload)
    out = _inject_owned_source_transport_hint(out)
    items = out["config_schema"]["provider"]["items"]

    ark_ui = _video_ui_key("ark-A")
    plan_ui = _video_ui_key("plan-A")
    foreign_ui = _video_ui_key("foreign-A")

    # Never add the canonical key to AstrBot's shared schema: without a
    # condition the V4 renderer would expose it on every Provider card.
    assert VIDEO_INPUT_ENABLED_KEY not in items

    # One short-lived UI key per owned Source, using AstrBot's native exact
    # condition on the model card's provider_source_id.
    assert items[ark_ui]["condition"] == {"provider_source_id": "ark-A"}
    assert items[plan_ui]["condition"] == {"provider_source_id": "plan-A"}
    assert foreign_ui not in items

    ark_card, plan_card, foreign_card = out["providers"]
    # Dashboard returns only the Source-scoped UI projection. The canonical
    # persistence key must not be present or AstrBot fallback-renders it as
    # a second raw field beside the intended switch.
    assert ark_card[ark_ui] is True
    assert plan_card[plan_ui] is False
    assert VIDEO_INPUT_ENABLED_KEY not in ark_card
    assert VIDEO_INPUT_ENABLED_KEY not in plan_card
    assert VIDEO_INPUT_ENABLED_KEY not in foreign_card
    assert not any(
        str(key).startswith(_VIDEO_UI_KEY_PREFIX)
        for key in foreign_card
    )

    # Source guidance is a Dashboard-only current UI-path hint. Owned
    # Sources receive it, foreign Sources do not, and the input list used to
    # build the projection remains unmodified.
    projected_sources = out["provider_sources"]
    assert projected_sources[0]["hint"] == _SOURCE_TRANSPORT_UI_HINT
    assert projected_sources[1]["hint"] == _SOURCE_TRANSPORT_UI_HINT
    assert "hint" not in projected_sources[2]
    assert all("hint" not in source for source in sources)

    to_save = dict(projected_sources[0])
    _strip_source_transport_hint(to_save)
    assert "hint" not in to_save
    custom_hint = {"hint": "host-or-user-hint"}
    _strip_source_transport_hint(custom_hint)
    assert custom_hint["hint"] == "host-or-user-hint"

    # The visible value is the user's newest edit and must beat the hidden
    # canonical value in the same Dashboard payload.  UI keys never persist.
    edited = {
        "id": "ark-A/m",
        "provider_source_id": "ark-A",
        VIDEO_INPUT_ENABLED_KEY: False,
        ark_ui: True,
        foreign_ui: True,  # malicious/stale foreign-looking UI key
    }
    _apply_video_ui_transport_setting(edited, sources)
    assert edited[VIDEO_INPUT_ENABLED_KEY] is True
    assert not any(
        str(key).startswith(_VIDEO_UI_KEY_PREFIX)
        for key in edited
    )

    # A new card that never touched the UI gets the transport default only at
    # the normal owned-card save boundary, not from a capability inference.
    new_card = {
        "id": "ark-A/new",
        "provider_source_id": "ark-A",
        "model": "new",
    }
    _apply_video_ui_transport_setting(new_card, sources)
    normalize_owned_model_card_for_save(new_card, sources, default_enabled=False)
    assert new_card[VIDEO_INPUT_ENABLED_KEY] is False

    # A foreign card cannot promote a forged UI key into plugin state; the
    # short-lived key is simply stripped.
    foreign_edit = {
        "id": "foreign-A/m",
        "provider_source_id": "foreign-A",
        foreign_ui: True,
    }
    _apply_video_ui_transport_setting(foreign_edit, sources)
    assert VIDEO_INPUT_ENABLED_KEY not in foreign_edit
    assert not any(
        str(key).startswith(_VIDEO_UI_KEY_PREFIX)
        for key in foreign_edit
    )

    print("MODEL_CARD_UI_SCOPE=OK")


if __name__ == "__main__":
    main()
