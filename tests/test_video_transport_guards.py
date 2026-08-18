"""0.1.31 transport/cache/context regression contracts.

Runs without network or paid API calls. The Runtime Distribution Gate installs
the packaged plugin into a clean AstrBot checkout before executing this file.
"""

from __future__ import annotations

import asyncio
import base64
import contextlib
import io
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "AstrBot" / "data" / "plugins"))

from astrbot_plugin_volcengine_provider.adapters import audio as audio_adapter
from astrbot_plugin_volcengine_provider.adapters import image as image_adapter
from astrbot_plugin_volcengine_provider.adapters import video as video_adapter
from astrbot_plugin_volcengine_provider.adapters.errors import AdapterInputTransportError
from astrbot_plugin_volcengine_provider.adapters.limits import (
    MediaLimits,
    get_limits,
    set_limits,
)
from astrbot_plugin_volcengine_provider.capabilities import cache_insight


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
async def _fake_video_resolver(path: Path, mime: str = "video/mp4"):
    class _FakeResolver:
        def __init__(self, *args, **kwargs):
            pass

        def as_path(self, *args, **kwargs):
            resolved = SimpleNamespace(path=path, mime_type=mime)
            resolved.read_bytes = lambda: path.read_bytes()
            return _NullContext(resolved)

    original = video_adapter.MediaResolver
    video_adapter.MediaResolver = _FakeResolver
    try:
        yield
    finally:
        video_adapter.MediaResolver = original


def _install_fake_spawn(adapter_module, fake_process) -> object:
    original = adapter_module.asyncio.create_subprocess_exec

    async def fake_spawn(*args, **kwargs):
        return fake_process

    adapter_module.asyncio.create_subprocess_exec = fake_spawn
    return original


def test_context_limit_hint_is_real_and_conservative() -> None:
    cfg = {"model": "deepseek-v4-flash-ga-260731"}
    assert cache_insight.apply_context_limit_hint(cfg) == 1_048_576
    assert cfg["max_context_tokens"] == 1_048_576

    plan_cfg = {"model": "agentplan/doubao-seed-2.1-turbo"}
    assert cache_insight.apply_context_limit_hint(plan_cfg) == 262_144
    assert plan_cfg["max_context_tokens"] == 262_144

    explicit = {"model": "deepseek-v4-pro", "max_context_tokens": 777_777}
    assert cache_insight.apply_context_limit_hint(explicit) == 777_777
    assert explicit["max_context_tokens"] == 777_777

    unknown = {"model": "ep-unknown"}
    assert cache_insight.apply_context_limit_hint(unknown) is None
    assert "max_context_tokens" not in unknown


def test_cache_rollups_are_bucketed_atomically() -> None:
    acc = cache_insight._CacheAccumulator()
    assert acc.note(
        ("v3", "m1"),
        in_tokens=10,
        cached_tokens=5,
        out_tokens=1,
        ms=100,
        every=2,
    ) is None
    assert acc.note(
        ("plan/v3", "m2"),
        in_tokens=20,
        cached_tokens=10,
        out_tokens=2,
        ms=200,
        every=2,
    ) is None
    snapshot = acc.note(
        ("v3", "m1"),
        in_tokens=30,
        cached_tokens=20,
        out_tokens=3,
        ms=300,
        every=2,
    )
    assert snapshot == (2, 40, 25, 4, 400)


def test_image_compressor_honors_longest_edge() -> None:
    source_image = Image.new("RGB", (2048, 1024), "white")
    source = io.BytesIO()
    source_image.save(source, format="PNG")

    compressed = image_adapter._compress_image_sync(
        source.getvalue(),
        max_bytes=1_000_000,
        max_size=256,
        quality=90,
    )
    assert compressed is not None
    with Image.open(io.BytesIO(compressed)) as result:
        assert max(result.size) <= 256


async def test_oversized_invalid_image_fails_closed() -> None:
    original = get_limits()
    set_limits(
        MediaLimits(
            image_compress_enabled=True,
            image_max_bytes=8,
            image_compress_max_size=256,
            image_compress_quality=85,
        )
    )
    try:
        payloads = {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": "data:image/png;base64,"
                                + base64.b64encode(b"not-an-image" * 4).decode("ascii")
                            },
                        }
                    ],
                }
            ]
        }
        try:
            await image_adapter.enforce_image_limits(payloads)
        except AdapterInputTransportError as exc:
            assert exc.stage == "compress_media"
            assert exc.reached_model is False
        else:
            raise AssertionError("oversized undecodable image must fail closed")
    finally:
        set_limits(original)


async def test_video_limit_reads_runtime_config() -> None:
    original = get_limits()
    set_limits(MediaLimits(video_max_bytes=4))
    try:
        try:
            await video_adapter.resolve_video_reference(
                "data:video/mp4;base64," + "A" * 12
            )
        except AdapterInputTransportError as exc:
            assert exc.stage == "validate_media"
        else:
            raise AssertionError("configured video ceiling must be enforced")
    finally:
        set_limits(original)


async def test_video_timeout_reads_runtime_config_and_kills_child() -> None:
    original_limits = get_limits()
    fake = FakeTranscodeProcess()
    original_which = video_adapter.shutil.which
    original_spawn = _install_fake_spawn(video_adapter, fake)
    video_adapter.shutil.which = lambda _: "/fake/ffmpeg"

    set_limits(MediaLimits(video_transcode_timeout_seconds=0.05))
    try:
        with tempfile.TemporaryDirectory(prefix="volcengine-guard-test-") as tmp:
            source = Path(tmp) / "clip.mp4"
            source.write_bytes(b"v" * 64)
            async with _fake_video_resolver(source):
                try:
                    await video_adapter.resolve_video_reference(
                        str(source),
                        mode=video_adapter.VIDEO_MODE_COMPRESSED,
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


async def test_audio_cancellation_kills_child() -> None:
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
            raise AssertionError("cancelled audio transcode must propagate cancellation")
        assert fake.killed is True
    finally:
        audio_adapter.asyncio.create_subprocess_exec = original_spawn


def test_request_timer_wraps_query_not_parser() -> None:
    provider_source = (
        Path(
            ROOT
            / "AstrBot"
            / "data"
            / "plugins"
            / "astrbot_plugin_volcengine_provider"
            / "providers.py"
        ).read_text("utf-8")
    )
    assert "_REQUEST_STARTED_AT.set(time.perf_counter())" in provider_source
    assert "started = time.perf_counter()" not in provider_source


def main() -> None:
    test_context_limit_hint_is_real_and_conservative()
    test_cache_rollups_are_bucketed_atomically()
    test_image_compressor_honors_longest_edge()
    test_request_timer_wraps_query_not_parser()
    asyncio.run(test_oversized_invalid_image_fails_closed())
    asyncio.run(test_video_limit_reads_runtime_config())
    asyncio.run(test_video_timeout_reads_runtime_config_and_kills_child())
    asyncio.run(test_audio_cancellation_kills_child())
    print("TRANSPORT_CACHE_CONTEXT_GUARDS_0_1_31=OK")


if __name__ == "__main__":
    main()
