from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "AstrBot" / "data" / "plugins"))

from astrbot_plugin_volcengine_provider.metadata.ark import normalize_ark_model_metadata
from astrbot_plugin_volcengine_provider.registry import _merge_source_feedback


def main() -> None:
    # Missing field: no plugin claim at all.
    model_id, missing = normalize_ark_model_metadata({"id": "missing"})
    assert model_id == "missing"
    assert missing == {"id": "missing"}

    # Explicit empty list: this *is* current feedback. It must survive
    # normalization even though [] is falsey in Python.
    model_id, empty = normalize_ark_model_metadata(
        {
            "id": "empty",
            "modalities": {
                "input_modalities": [],
            },
        }
    )
    assert model_id == "empty"
    assert empty == {
        "id": "empty",
        "modalities": {"input": []},
    }

    # Current explicit empty input replaces the same display direction for this
    # response, while an unreported output direction remains host-owned.
    host = {
        "id": "empty",
        "modalities": {
            "input": ["image", "audio"],
            "output": ["text"],
        },
        "tool_call": True,
    }
    merged = _merge_source_feedback(host, empty)
    assert merged["modalities"] == {
        "input": [],
        "output": ["text"],
    }
    assert merged["tool_call"] is True

    # Copy-on-write: live display feedback never edits AstrBot's source object.
    assert host["modalities"]["input"] == ["image", "audio"]
    assert host["modalities"]["output"] == ["text"]

    # Unknown/future modality tokens are information, not something the current
    # adapter is entitled to erase. AstrBot 4.26/4.27 can simply ignore names it
    # does not understand while a future host may consume them.
    _, future_only = normalize_ark_model_metadata(
        {
            "id": "future",
            "modalities": {
                "input_modalities": ["future_modality", "image", "future_modality"],
            },
        }
    )
    assert future_only == {
        "id": "future",
        "modalities": {"input": ["future_modality", "image"]},
    }

    future_host = {
        "id": "future",
        "modalities": {"input": ["audio"], "output": ["text"]},
    }
    future_merged = _merge_source_feedback(future_host, future_only)
    assert future_merged["modalities"] == {
        "input": ["future_modality", "image"],
        "output": ["text"],
    }

    print("LIVE_FEEDBACK_PRESENCE=OK")


if __name__ == "__main__":
    main()
