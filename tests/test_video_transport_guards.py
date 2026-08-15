"""Transport guard contracts for the video/audio last-mile adapters.

These guards are the 0.1.25 robustness boundary:

* local video materialization rejects empty and oversized input *before*
  base64-encoding (Original mode), and again for the transcoded output
  (Compressed mode);
* compressed transcoding is bounded by a wall-clock timeout and the ffmpeg
  subprocess is killed on timeout;
* a cancelled chat request always kills a running ffmpeg subprocess for both
  the video compressed path and the audio WAV normalization path;
* base64 data URLs are size-checked without decoding their payload.

No network or paid Volcengine API call is used. Subprocess behavior is faked
through ``asyncio.create_subprocess_exec`` monkeypatches, so the contracts run
deterministically everywhere.
"""

from __future__ import annotations

import asyncio
import contextlib
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "AstrBot" / "data" / "plugins"))

from astrbot_plugin_volcengine_provider.adapters import audio as audio_adapter
from astrbot_plugin_volcengine_provider.adapters import video as video_adapter
from astrbot_plugin_volcengine_provider.adapters.errors import AdapterInputTransportError


class FakeTranscodeProcess:
    """A subprocess stand-in whose communicate() never returns on its own."""

    def __init__(self) -> None:
        self.killed = False
        self._returncode: int | None = None

    async def communicate(self) -> tuple[bytes, bytes]:
        await asyncio.sleep(30)
        return b"", b""

    def kill(self) -> None:
        self.killed = True
        self._returncode = -9

    @property
    def returncode(self) -> int | None:
        return self._returncode

    async def wait(self) -> None:
        await asyncio.sleep(0)


@contextlib.asynccontextmanager
async def _fake_resolver(tmp_path: Path, *, size: int | None = None, mime: str = "video/mp4"):
    class _FakeResolver:
        def __init__(self, *args, **kwargs):
            pass

        def as_path(self, *args, **kwargs):
            resolved = SimpleNamespace(
                path=tmp_path,
                mime_type=mime,
            )
            resolved.read_bytes = lambda: tmp_path.read_bytes()
            return _NullContext(resolved)

    class _NullContext:
        def __init__(self, value):
            self.value = value

        async def __aenter__(self):
            return self.value

        async def __aexit__(self, *exc_info):
            return False

    original = video_adapter.MediaResolver
    video_adapter.MediaResolver = _FakeResolver
    try:
        yield
    finally:
        video_adapter.MediaResolver = original


def _write_bytes(path: Path, size: int) -> None:
    path.write_bytes(b"v" * size)


def test_data_url_payload_ceiling() -> None:
    within = video_adapter._data_url_payload_within_limit
    # max_bytes=3 -> capacity ceil(3/3)*4 = 4 base64 chars.
    assert within("data:video/mp4;base64,AAAA", max_bytes=3) is True
    assert within("data:video/mp4;base64,AAAAA", max_bytes=3) is False
    assert within("data:video/mp4;base64,", max_bytes=3) is True


async def test_original_mode_passes_small_data_url_through() -> None:
    result = await video_adapter.resolve_video_reference(
        "data:video/mp4;base64,AAAA"
    )
    assert result == "data:video/mp4;base64,AAAA"


async def test_original_mode_rejects_oversized_data_url() -> None:
    original_max = video_adapter.ARK_CHAT_VIDEO_MAX_BYTES
    video_adapter.ARK_CHAT_VIDEO_MAX_BYTES = 4
    try:
        try:
            await video_adapter.resolve_video_reference(
                "data:video/mp4;base64," + "A" * 12  # decodes to 9 bytes > 4
            )
        except AdapterInputTransportError as exc:
            assert exc.stage == "validate_media"
            assert exc.reached_model is False
        else:
            raise AssertionError("oversized data URL must be rejected")
    finally:
        video_adapter.ARK_CHAT_VIDEO_MAX_BYTES = original_max


async def test_original_mode_rejects_oversized_local_file_before_base64() -> None:
    with tempfile.TemporaryDirectory(prefix="volcengine-guard-test-") as tmp:
        source = Path(tmp) / "clip.mp4"
        _write_bytes(source, 2048)
        original_max = video_adapter.ARK_CHAT_VIDEO_MAX_BYTES
        video_adapter.ARK_CHAT_VIDEO_MAX_BYTES = 1024
        try:
            async with _fake_resolver(source):
                try:
                    await video_adapter.resolve_video_reference(str(source))
                except AdapterInputTransportError as exc:
                    assert exc.stage == "validate_media"
                    assert exc.reached_model is False
                else:
                    raise AssertionError("oversized local video must be rejected")
        finally:
            video_adapter.ARK_CHAT_VIDEO_MAX_BYTES = original_max


async def test_original_mode_rejects_empty_local_file() -> None:
    with tempfile.TemporaryDirectory(prefix="volcengine-guard-test-") as tmp:
        source = Path(tmp) / "clip.mp4"
        _write_bytes(source, 0)
        async with _fake_resolver(source):
            try:
                await video_adapter.resolve_video_reference(str(source))
            except AdapterInputTransportError as exc:
                assert exc.stage == "validate_media"
            else:
                raise AssertionError("empty local video must be rejected")


async def test_original_mode_materializes_small_local_file() -> None:
    with tempfile.TemporaryDirectory(prefix="volcengine-guard-test-") as tmp:
        source = Path(tmp) / "clip.mp4"
        _write_bytes(source, 64)
        async with _fake_resolver(source):
            result = await video_adapter.resolve_video_reference(str(source))
        assert result.startswith("data:video/mp4;base64,")


def _install_fake_spawn(adapter_module, fake_process) -> None:
    async def fake_spawn(*args, **kwargs):
        return fake_process

    adapter_module._fake_spawn_original = getattr(
        adapter_module, "_fake_spawn_original", None
    )
    adapter_module.asyncio.create_subprocess_exec = fake_spawn


def _restore_spawn(adapter_module) -> None:
    if adapter_module._fake_spawn_original is not None:
        adapter_module.asyncio.create_subprocess_exec = (
            adapter_module._fake_spawn_original
        )


async def test_compressed_timeout_kills_ffmpeg() -> None:
    with tempfile.TemporaryDirectory(prefix="volcengine-guard-test-") as tmp:
        source = Path(tmp) / "clip.mp4"
        _write_bytes(source, 64)
        fake = FakeTranscodeProcess()
        original_which = video_adapter.shutil.which
        original_timeout = video_adapter.ARK_CHAT_VIDEO_TRANSCODE_TIMEOUT_SECONDS
        video_adapter.shutil.which = lambda _: "/fake/ffmpeg"
        video_adapter.ARK_CHAT_VIDEO_TRANSCODE_TIMEOUT_SECONDS = 0.05
        _install_fake_spawn(video_adapter, fake)
        try:
            async with _fake_resolver(source):
                try:
                    await video_adapter.resolve_video_reference(
                        str(source), mode=video_adapter.VIDEO_MODE_COMPRESSED
                    )
                except AdapterInputTransportError as exc:
                    assert exc.stage == "compress_media"
                    assert "超时" in str(exc)
                else:
                    raise AssertionError("stuck ffmpeg must time out")
            assert fake.killed is True
        finally:
            video_adapter.shutil.which = original_which
            video_adapter.ARK_CHAT_VIDEO_TRANSCODE_TIMEOUT_SECONDS = original_timeout
            _restore_spawn(video_adapter)


async def test_compressed_cancellation_kills_ffmpeg() -> None:
    with tempfile.TemporaryDirectory(prefix="volcengine-guard-test-") as tmp:
        source = Path(tmp) / "clip.mp4"
        _write_bytes(source, 64)
        fake = FakeTranscodeProcess()
        original_which = video_adapter.shutil.which
        video_adapter.shutil.which = lambda _: "/fake/ffmpeg"
        _install_fake_spawn(video_adapter, fake)
        try:
            async with _fake_resolver(source):
                task = asyncio.ensure_future(
                    video_adapter.resolve_video_reference(
                        str(source), mode=video_adapter.VIDEO_MODE_COMPRESSED
                    )
                )
                await asyncio.sleep(0.05)
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                else:
                    raise AssertionError("cancelled transcode must propagate CancelledError")
            assert fake.killed is True
        finally:
            video_adapter.shutil.which = original_which
            _restore_spawn(video_adapter)


async def test_audio_cancellation_kills_ffmpeg() -> None:
    fake = FakeTranscodeProcess()
    _install_fake_spawn(audio_adapter, fake)
    try:
        task = asyncio.ensure_future(
            audio_adapter._ffmpeg_to_ark_chat_wav(
                Path("unused-source.wav"),
                Path("unused-output.wav"),
            )
        )
        await asyncio.sleep(0.05)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        else:
            raise AssertionError("cancelled audio transcode must propagate CancelledError")
        assert fake.killed is True
    finally:
        _restore_spawn(audio_adapter)


def main() -> None:
    test_data_url_payload_ceiling()
    asyncio.run(test_original_mode_passes_small_data_url_through())
    asyncio.run(test_original_mode_rejects_oversized_data_url())
    asyncio.run(test_original_mode_rejects_oversized_local_file_before_base64())
    asyncio.run(test_original_mode_rejects_empty_local_file())
    asyncio.run(test_original_mode_materializes_small_local_file())
    asyncio.run(test_compressed_timeout_kills_ffmpeg())
    asyncio.run(test_compressed_cancellation_kills_ffmpeg())
    asyncio.run(test_audio_cancellation_kills_ffmpeg())
    print("VIDEO_TRANSPORT_GUARDS_0_1_25=OK")


if __name__ == "__main__":
    main()
