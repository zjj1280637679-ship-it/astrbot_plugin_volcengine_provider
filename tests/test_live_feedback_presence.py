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

    # Explicit empty list: this *is* current feedback.  It must survive
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

    # A list containing only an unknown/future modality is still an explicitly
    # supplied list.  The current adapter cannot advertise the unknown symbol,
    # but it must not resurrect stale known icons either.
    _, future_only = normalize_ark_model_metadata(
        {
            "id": "future",
            "modalities": {
                "input_modalities": ["future_modality"],
            },
        }
    )
    assert future_only == {
        "id": "future",
        "modalities": {"input": []},
    }

    print("LIVE_FEEDBACK_PRESENCE=OK")


if __name__ == "__main__":
    main()
