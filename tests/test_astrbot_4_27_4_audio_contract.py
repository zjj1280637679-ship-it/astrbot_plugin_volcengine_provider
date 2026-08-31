"""AstrBot 4.27.4 MediaResolver to Ark WAV integration contract."""

from __future__ import annotations

import asyncio
import base64
import io
import math
import struct
import sys
import tempfile
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "AstrBot" / "data" / "plugins"))

from astrbot import __version__ as ASTRBOT_VERSION
from astrbot.core.utils.media_utils import convert_audio_to_amr
from astrbot.core.utils.tencent_record_helper import wav_to_tencent_silk
from astrbot_plugin_volcengine_provider.adapters.audio import build_ark_input_audio


def _write_tone(path: Path) -> None:
    sample_rate = 24_000
    frame_count = sample_rate // 5
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        for index in range(frame_count):
            sample = int(12_000 * math.sin(2 * math.pi * 440 * index / sample_rate))
            output.writeframesraw(struct.pack("<h", sample))


def _assert_canonical_ark_wav(block: dict) -> None:
    assert block["type"] == "input_audio"
    assert block["input_audio"]["format"] == "wav"
    wav_bytes = base64.b64decode(block["input_audio"]["data"], validate=True)
    assert wav_bytes.startswith(b"RIFF") and wav_bytes[8:12] == b"WAVE"
    with wave.open(io.BytesIO(wav_bytes), "rb") as resolved:
        assert resolved.getnchannels() == 1
        assert resolved.getsampwidth() == 2
        assert resolved.getframerate() == 16_000
        assert resolved.getcomptype() == "NONE"
        assert resolved.getnframes() > 0


async def test_misnamed_amr_reaches_canonical_ark_wav() -> None:
    with tempfile.TemporaryDirectory(prefix="volcengine-amr-4274-") as temp:
        root = Path(temp)
        tone = root / "tone.wav"
        amr = root / "tone.amr"
        misnamed = root / "qq-voice.wav"
        _write_tone(tone)
        await convert_audio_to_amr(str(tone), str(amr))
        amr_bytes = amr.read_bytes()
        assert amr_bytes.startswith(b"#!AMR\n")
        misnamed.write_bytes(amr_bytes)

        _assert_canonical_ark_wav(await build_ark_input_audio(str(misnamed)))


async def test_misnamed_tencent_silk_reaches_canonical_ark_wav() -> None:
    with tempfile.TemporaryDirectory(prefix="volcengine-silk-4274-") as temp:
        root = Path(temp)
        tone = root / "tone.wav"
        silk = root / "tone.silk"
        misnamed = root / "qq-voice.wav"
        _write_tone(tone)
        await wav_to_tencent_silk(str(tone), str(silk))
        silk_bytes = silk.read_bytes()
        assert silk_bytes.startswith(b"\x02#!SILK_V3")
        misnamed.write_bytes(silk_bytes)

        _assert_canonical_ark_wav(await build_ark_input_audio(str(misnamed)))


def main() -> None:
    host_version = tuple(int(part) for part in ASTRBOT_VERSION.split(".")[:3])
    if host_version >= (4, 27, 4):
        asyncio.run(test_misnamed_amr_reaches_canonical_ark_wav())
        sources = "amr,tencent_silk"
    else:
        print("ASTRBOT_4_27_4_AMR_CONTRACT=SKIP_HOST_VERSION")
        sources = "tencent_silk"
    asyncio.run(test_misnamed_tencent_silk_reaches_canonical_ark_wav())
    print(f"ASTRBOT_4_27_4_AUDIO_CONTRACT=OK sources={sources} misnamed=wav")


if __name__ == "__main__":
    main()
