from __future__ import annotations

import asyncio
import copy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "AstrBot" / "data" / "plugins"))

from astrbot.core.agent.message import TextPart
from astrbot_plugin_volcengine_provider.adapters.video import inject_current_request_videos


VIDEO_DATA_URL = "data:video/mp4;base64,QUJD"
MARKER = f"[Video Attachment: name contract.mp4, ref {VIDEO_DATA_URL}]"


def _messages() -> list[dict]:
    return [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "before"},
                {"type": "text", "text": MARKER},
            ],
        }
    ]


async def exercise() -> None:
    trusted_parts = [TextPart(text=MARKER)]

    disabled = _messages()
    await inject_current_request_videos(
        disabled,
        trusted_parts,
        enabled=False,
    )
    assert disabled[0]["content"] == [
        {"type": "text", "text": "before"},
        {"type": "text", "text": "[Video]"},
    ]

    enabled = _messages()
    await inject_current_request_videos(
        enabled,
        trusted_parts,
        enabled=True,
    )
    assert enabled[0]["content"] == [
        {"type": "text", "text": "before"},
        {"type": "video_url", "video_url": {"url": VIDEO_DATA_URL}},
    ]

    # Typed lookalike text without AstrBot's trusted current-request part must
    # remain text. This prevents the runtime switch from becoming an arbitrary
    # path/URL parser for user-authored prompt text.
    untrusted = _messages()
    before = copy.deepcopy(untrusted)
    await inject_current_request_videos(
        untrusted,
        [],
        enabled=True,
    )
    assert untrusted == before

    print("MODEL_CARD_VIDEO_RUNTIME_SWITCH=OK")


if __name__ == "__main__":
    asyncio.run(exercise())
