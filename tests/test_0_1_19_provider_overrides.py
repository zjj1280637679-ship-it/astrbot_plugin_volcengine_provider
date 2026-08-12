from __future__ import annotations

import asyncio
import base64
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "AstrBot" / "data" / "plugins"))

from astrbot_plugin_volcengine_provider.adapters import video as video_adapter
from astrbot_plugin_volcengine_provider.adapters.errors import AdapterInputTransportError
from astrbot_plugin_volcengine_provider.capabilities import (
    MAX_OUTPUT_TOKENS_KEY,
    REASONING_EFFORT_KEY,
    REASONING_MODE_KEY,
    STOP_SEQUENCES_KEY,
    TEMPERATURE_KEY,
    TOP_P_KEY,
)
from astrbot_plugin_volcengine_provider.providers import ProviderVolcengineArk


def _provider() -> ProviderVolcengineArk:
    provider = object.__new__(ProviderVolcengineArk)
    provider.provider_config = {
        "provider": "volcengine",
        "model": "test-model",
        TEMPERATURE_KEY: 0.6,
        TOP_P_KEY: 0.9,
        MAX_OUTPUT_TOKENS_KEY: 8192,
        STOP_SEQUENCES_KEY: ["STOP"],
        REASONING_MODE_KEY: "auto",
        REASONING_EFFORT_KEY: "high",
    }
    return provider


def test_old_hook() -> None:
    provider = _provider()
    # AstrBot 4.26.1 merges custom_extra_body first, then calls this hook.
    extra = {
        "temperature": 1.2,
        "top_p": 0.1,
        "max_tokens": 1024,
        "reasoning_effort": "low",
        "thinking": {"type": "disabled", "keep": True},
        "custom": "kept",
    }
    provider._apply_provider_specific_extra_body_overrides(extra)
    assert extra["temperature"] == 0.6
    assert extra["top_p"] == 0.9
    assert extra["max_tokens"] == 8192
    assert extra["stop"] == ["STOP"]
    assert extra["reasoning_effort"] == "high"
    assert extra["thinking"] == {"type": "auto", "keep": True}
    assert extra["custom"] == "kept"


def test_new_hook() -> None:
    provider = _provider()
    # AstrBot 4.27.2+ uses the payload-aware hook instead.
    payloads = {"model": "test-model"}
    extra = {"temperature": 1.3, "custom": "kept"}
    provider._apply_provider_specific_request_overrides(payloads, extra)
    assert payloads == {"model": "test-model"}
    assert extra["temperature"] == 0.6
    assert extra["top_p"] == 0.9
    assert extra["max_tokens"] == 8192
    assert extra["reasoning_effort"] == "high"
    assert extra["thinking"]["type"] == "auto"
    assert extra["custom"] == "kept"


async def test_compression_missing_ffmpeg_fails_closed() -> None:
    original_which = video_adapter.shutil.which
    video_adapter.shutil.which = lambda _: None
    try:
        try:
            await video_adapter.resolve_video_reference(
                "https://example.invalid/video.mp4",
                mode=video_adapter.VIDEO_MODE_COMPRESSED,
            )
        except AdapterInputTransportError as exc:
            assert exc.media_type == "video"
            assert exc.stage == "compress_media"
            assert exc.reached_model is False
        else:
            raise AssertionError("compressed mode should fail when ffmpeg is unavailable")
    finally:
        video_adapter.shutil.which = original_which


async def test_compression_emits_decodable_mp4_when_ffmpeg_exists() -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        print("COMPRESSED_VIDEO_POSITIVE=SKIP_NO_FFMPEG")
        return

    with tempfile.TemporaryDirectory(prefix="volcengine-video-test-") as tmp:
        tmpdir = Path(tmp)
        source = tmpdir / "source.mp4"
        subprocess.run(
            [
                ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "testsrc=size=640x360:rate=30",
                "-t",
                "1",
                "-c:v",
                "mpeg4",
                "-q:v",
                "4",
                str(source),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        result = await video_adapter.resolve_video_reference(
            str(source),
            mode=video_adapter.VIDEO_MODE_COMPRESSED,
        )
        prefix = "data:video/mp4;base64,"
        assert result.startswith(prefix)
        compressed = base64.b64decode(result[len(prefix) :])
        assert len(compressed) > 100
        assert b"ftyp" in compressed[:64]

        output = tmpdir / "compressed.mp4"
        output.write_bytes(compressed)
        # Decode the generated file with ffmpeg itself. This is stronger than
        # checking only an MP4 magic/header and still requires no network/API.
        subprocess.run(
            [
                ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                str(output),
                "-f",
                "null",
                "-",
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        print(
            "COMPRESSED_VIDEO_POSITIVE=OK "
            f"source_bytes={source.stat().st_size} compressed_bytes={len(compressed)}"
        )


def main() -> None:
    test_old_hook()
    test_new_hook()
    asyncio.run(test_compression_missing_ffmpeg_fails_closed())
    asyncio.run(test_compression_emits_decodable_mp4_when_ffmpeg_exists())
    print("PROVIDER_OVERRIDES_0_1_19=OK")


if __name__ == "__main__":
    main()
