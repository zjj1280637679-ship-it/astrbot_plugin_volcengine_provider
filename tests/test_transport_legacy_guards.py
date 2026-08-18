"""Legacy media-transport invariants that must survive later releases.

These are the 0.1.25 negative-path guarantees, rewritten to use the runtime
``MediaLimits`` policy introduced later.  New tests may extend this suite but
must not replace these lifecycle checks.
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
from astrbot_plugin_volcengine_provider.adapters.limits import (
    MediaLimits,
    get_limits,
    set_limits,
)


class FakeTranscodeProcess:
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


class _NullContext:
    def __init__(self, value):
        self.value = value

    async def __aenter__(self):
        return self.value

    async def __aexit__(self, *exc_info):
        return False


@contextlib.asynccontextmanager
async def _fake_video_resolver(
    path: Path,
    *,
    mime: str = "video/mp4",
    forbid_read: bool = False,
):
    class _FakeResolver:
        def __init__(self, *args, **kwargs):
            pass

        def as_path(self, *args, **kwargs):
            resolved = SimpleNamespace(path=path, mime_type=mime)

            def read_bytes():
                if forbid_read:
                    raise AssertionError("oversized input was read before rejection")
                return path.read_bytes()

            resolved.read_bytes = read_bytes
            return _NullContext(resolved)

    original = video_adapter.MediaResolver
    video_adapter.MediaResolver = _FakeResolver
    try:
        yield
    finally:
        video_adapter.MediaResolver = original


def _install_fake_spawn(adapter_module, fake_process):
    original = adapter_module.asyncio.create_subprocess_exec

    async def fake_spawn(*args, **kwargs):
        return fake_process

    adapter_module.asyncio.create_subprocess_exec = fake_spawn
    return original


def test_data_url_payload_ceiling() -> None:
    within = video_adapter._data_url_payload_within_limit
    assert within("data:video/mp4;base64,AAAA", max_bytes=3) is True
    assert within("data:video/mp4;base64,AAAAA", max_bytes=3) is False
    assert within("data:video/mp4;base64,", max_bytes=3) is True


async def test_original_mode_passes_small_data_url_through() -> None:
    original = get_limits()
    set_limits(MediaLimits(video_max_bytes=16))
    try:
        result = await video_adapter.resolve_video_reference(
            "data:video/mp4;base64,AAAA"
        )
        assert result == "data:video/mp4;base64,AAAA"
    finally:
        set_limits(original)


async def test_original_mode_rejects_oversized_data_url() -> None:
    original = get_limits()
    set_limits(MediaLimits(video_max_bytes=4))
    try:
        try:
            await video_adapter.resolve_video_reference(
                "data:video/mp4;base64," + "A" * 12
            )
        except AdapterInputTransportError as exc:
            assert exc.stage == "validate_media"
            assert exc.reached_model is False
        else:
            raise AssertionError("oversized data URL must be rejected")
    finally:
        set_limits(original)


async def test_original_mode_rejects_oversized_local_before_read_base64() -> None:
    with tempfile.TemporaryDirectory(prefix="volcengine-legacy-guard-") as tmp:
        source = Path(tmp) / "clip.mp4"
        source.write_bytes(b"v" * 2048)
        original = get_limits()
        set_limits(MediaLimits(video_max_bytes=1024))
        try:
            async with _fake_video_resolver(source, forbid_read=True):
                try:
                    await video_adapter.resolve_video_reference(str(source))
                except AdapterInputTransportError as exc:
                    assert exc.stage == "validate_media"
                    assert exc.reached_model is False
                else:
                    raise AssertionError("oversized local video must be rejected")
        finally:
            set_limits(original)


async def test_original_mode_rejects_empty_local_file() -> None:
    with tempfile.TemporaryDirectory(prefix="volcengine-legacy-guard-") as tmp:
        source = Path(tmp) / "clip.mp4"
        source.write_bytes(b"")
        async with _fake_video_resolver(source):
            try:
                await video_adapter.resolve_video_reference(str(source))
            except AdapterInputTransportError as exc:
                assert exc.stage == "validate_media"
            else:
                raise AssertionError("empty local video must be rejected")


async def test_original_mode_materializes_small_local_file() -> None:
    with tempfile.TemporaryDirectory(prefix="volcengine-legacy-guard-") as tmp:
        source = Path(tmp) / "clip.mp4"
        source.write_bytes(b"v" * 64)
        async with _fake_video_resolver(source):
            result = await video_adapter.resolve_video_reference(str(source))
        assert result.startswith("data:video/mp4;base64,")


async def test_compressed_timeout_kills_ffmpeg() -> None:
    with tempfile.TemporaryDirectory(prefix="volcengine-legacy-guard-") as tmp:
        source = Path(tmp) / "clip.mp4"
        source.write_bytes(b"v" * 64)
        fake = FakeTranscodeProcess()
        original_limits = get_limits()
        original_which = video_adapter.shutil.which
        original_spawn = _install_fake_spawn(video_adapter, fake)
        video_adapter.shutil.which = lambda _: "/fake/ffmpeg"
        set_limits(MediaLimits(video_transcode_timeout_seconds=0.05))
        try:
            async with _fake_video_resolver(source):
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
            set_limits(original_limits)
            video_adapter.shutil.which = original_which
            video_adapter.asyncio.create_subprocess_exec = original_spawn


async def test_compressed_cancellation_kills_ffmpeg() -> None:
    with tempfile.TemporaryDirectory(prefix="volcengine-legacy-guard-") as tmp:
        source = Path(tmp) / "clip.mp4"
        source.write_bytes(b"v" * 64)
        fake = FakeTranscodeProcess()
        original_which = video_adapter.shutil.which
        original_spawn = _install_fake_spawn(video_adapter, fake)
        video_adapter.shutil.which = lambda _: "/fake/ffmpeg"
        try:
            async with _fake_video_resolver(source):
                task = asyncio.create_task(
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
                    raise AssertionError("cancelled video transcode must propagate")
            assert fake.killed is True
        finally:
            video_adapter.shutil.which = original_which
            video_adapter.asyncio.create_subprocess_exec = original_spawn


async def test_audio_cancellation_kills_ffmpeg() -> None:
    fake = FakeTranscodeProcess()
    original_spawn = _install_fake_spawn(audio_adapter, fake)
    try:
        task = asyncio.create_task(
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
            raise AssertionError("cancelled audio transcode must propagate")
        assert fake.killed is True
    finally:
        audio_adapter.asyncio.create_subprocess_exec = original_spawn


def main() -> None:
    test_data_url_payload_ceiling()
    asyncio.run(test_original_mode_passes_small_data_url_through())
    asyncio.run(test_original_mode_rejects_oversized_data_url())
    asyncio.run(test_original_mode_rejects_oversized_local_before_read_base64())
    asyncio.run(test_original_mode_rejects_empty_local_file())
    asyncio.run(test_original_mode_materializes_small_local_file())
    asyncio.run(test_compressed_timeout_kills_ffmpeg())
    asyncio.run(test_compressed_cancellation_kills_ffmpeg())
    asyncio.run(test_audio_cancellation_kills_ffmpeg())
    print("LEGACY_TRANSPORT_GUARDS=OK")


if __name__ == "__main__":
    main()
