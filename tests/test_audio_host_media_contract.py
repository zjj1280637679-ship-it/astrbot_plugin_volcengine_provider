from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = ROOT / "AstrBot" / "data" / "plugins" / "astrbot_plugin_volcengine_provider"
ASTRBOT_ROOT = ROOT / "AstrBot"
sys.path.insert(0, str(ASTRBOT_ROOT))
sys.path.insert(0, str(PLUGIN_ROOT.parent))

from astrbot.core.message.message_event_result import MessageChain
from astrbot.core.provider.entities import ProviderRequest
from astrbot.core.provider.provider import Provider
from astrbot.core.utils.media_utils import MediaResolver
from astrbot_plugin_volcengine_provider.adapters.audio import AudioNormalizationError
from astrbot_plugin_volcengine_provider.providers import ProviderVolcengineArk

ASTRBOT_VERSION = os.environ.get("ASTRBOT_E2E_HOST_VERSION", "")


def version_tuple(version: str) -> tuple[int, int, int]:
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)", version.strip())
    if not match:
        return (0, 0, 0)
    return tuple(int(part) for part in match.groups())  # type: ignore[return-value]


def encode_amr(wav_path: Path, output_path: Path) -> bool:
    result = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(wav_path),
            "-ar",
            "8000",
            "-ac",
            "1",
            "-c:a",
            "libopencore_amrnb",
            "-b:a",
            "12.20k",
            str(output_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return True
    print(f"AMR_HOST_ENCODER_SKIPPED: {result.stderr.strip()}")
    return False


def encode_silk(wav_path: Path, output_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pysilk",
            "encode",
            str(wav_path),
            str(output_path),
        ],
        check=False,
        capture_output=True,
        text=True,
        cwd=ASTRBOT_ROOT,
    )
    if result.returncode != 0:
        raise AssertionError(
            f"pysilk encode failed: {result.stdout}\n{result.stderr}"
        )


def assert_media_resolver_contract(wav_path: Path, encoded_path: Path) -> None:
    resolver = MediaResolver(MessageChain())
    encoded_bytes = encoded_path.read_bytes()
    if not encoded_bytes:
        raise AssertionError(f"encoded media is empty: {encoded_path}")

    fake_wav = encoded_path.with_suffix(".wav")
    fake_wav.write_bytes(encoded_bytes)

    resolved = resolver._resolve_audio_data(str(fake_wav))
    if not resolved:
        raise AssertionError(
            f"AstrBot MediaResolver returned no audio for misnamed {encoded_path.suffix}"
        )
    path = Path(resolved)
    if path.suffix.lower() != ".wav":
        raise AssertionError(f"MediaResolver did not normalize to .wav: {path}")
    if not path.read_bytes().startswith(b"RIFF"):
        raise AssertionError(f"MediaResolver output is not RIFF/WAVE: {path}")

    ProviderVolcengineArk.__abstractmethods__ = frozenset()
    provider = ProviderVolcengineArk(
        provider_config={"id": "audio-contract", "key": ["dummy"]},
        provider_settings={},
    )
    try:
        normalized = provider._prepare_audio_file(path)
    except AudioNormalizationError as exc:
        raise AssertionError(f"plugin rejected host-normalized WAV: {exc}") from exc
    if not normalized.startswith(b"RIFF"):
        raise AssertionError("plugin audio adapter did not produce RIFF/WAVE")


def main() -> None:
    if version_tuple(ASTRBOT_VERSION) < (4, 27, 4):
        print(f"AUDIO_HOST_CONTRACT_SKIPPED host={ASTRBOT_VERSION or 'unknown'}")
        return

    fixture_dir = ROOT / ".tmp-audio-host-contract"
    fixture_dir.mkdir(exist_ok=True)
    wav_path = fixture_dir / "source.wav"

    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=0.4",
            "-ar",
            "16000",
            "-ac",
            "1",
            str(wav_path),
        ],
        check=True,
    )

    silk_path = fixture_dir / "voice.silk"
    encode_silk(wav_path, silk_path)
    assert_media_resolver_contract(wav_path, silk_path)

    amr_path = fixture_dir / "voice.amr"
    if encode_amr(wav_path, amr_path):
        assert_media_resolver_contract(wav_path, amr_path)

    print(f"AUDIO_HOST_CONTRACT_OK host={ASTRBOT_VERSION}")


if __name__ == "__main__":
    main()
