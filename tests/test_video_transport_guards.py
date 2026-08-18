"""0.1.31 negative-path and lifecycle-policy regression contracts.

This suite intentionally re-confirms invariants after state transitions instead
of treating one successful initialization as evidence for the whole lifecycle.
No network or paid Volcengine API call is used.
"""

from __future__ import annotations

import asyncio
import base64
import io
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "AstrBot" / "data" / "plugins"))

from astrbot_plugin_volcengine_provider import main as plugin_main
from astrbot_plugin_volcengine_provider.adapters import audio as audio_adapter
from astrbot_plugin_volcengine_provider.adapters import image as image_adapter
from astrbot_plugin_volcengine_provider.adapters.errors import AdapterInputTransportError
from astrbot_plugin_volcengine_provider.adapters.limits import (
    MediaLimits,
    get_limits,
    set_limits,
)
from astrbot_plugin_volcengine_provider.capabilities import cache_insight


class _NullContext:
    def __init__(self, value):
        self.value = value

    async def __aenter__(self):
        return self.value

    async def __aexit__(self, *exc_info):
        return False


def test_context_authority_is_not_replaced_by_static_family_guesses() -> None:
    """Known-looking names and dynamic aliases must remain host-owned."""
    for model in (
        "deepseek-v4-flash-ga-260731",
        "glm-5.2",
        "agentplan/doubao-seed-2.1-turbo",
        "agentplan/ark-code-latest",
        "ep-runtime-routed-model",
    ):
        cfg = {"model": model}
        assert cache_insight.configured_context_limit(cfg) is None
        assert "max_context_tokens" not in cfg

    explicit = {"model": "anything", "max_context_tokens": 777_777}
    assert cache_insight.configured_context_limit(explicit) == 777_777
    assert explicit["max_context_tokens"] == 777_777


def test_context_error_detection_reads_structured_body() -> None:
    class BodyOnlyError(Exception):
        body = {
            "error": {
                "code": "context_length_exceeded",
                "message": "request exceeds maximum context window",
            }
        }

        def __str__(self) -> str:
            return "bad request"

    assert cache_insight.is_context_length_error(BodyOnlyError()) is True


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


def test_cache_policy_transition_invalidates_old_rollup_evidence() -> None:
    original = cache_insight.cache_log_settings()
    try:
        cache_insight.configure_cache_log(enabled=True, every=10)
        cache_insight._accumulator.note(
            ("v3", "m"),
            in_tokens=100,
            cached_tokens=50,
            out_tokens=1,
            ms=10,
            every=10,
        )
        cache_insight.configure_cache_log(enabled=True, every=2)
        assert cache_insight.cache_log_settings() == (True, 2)
        assert cache_insight._accumulator.note(
            ("v3", "m"),
            in_tokens=1,
            cached_tokens=1,
            out_tokens=1,
            ms=1,
            every=2,
        ) is None
        snapshot = cache_insight._accumulator.note(
            ("v3", "m"),
            in_tokens=2,
            cached_tokens=2,
            out_tokens=2,
            ms=2,
            every=2,
        )
        assert snapshot == (2, 3, 3, 3, 3)
    finally:
        cache_insight.configure_cache_log(enabled=original[0], every=original[1])


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


def test_transparent_image_flattens_to_white_not_black() -> None:
    source_image = Image.new("RGBA", (32, 32), (255, 0, 0, 0))
    source = io.BytesIO()
    source_image.save(source, format="PNG")
    compressed = image_adapter._compress_image_sync(
        source.getvalue(),
        max_bytes=100_000,
        max_size=32,
        quality=95,
    )
    assert compressed is not None
    with Image.open(io.BytesIO(compressed)) as opened:
        result = opened.convert("RGB")
        r, g, b = result.getpixel((16, 16))
        assert r > 240 and g > 240 and b > 240, (r, g, b)


async def test_oversized_local_image_compresses_before_raw_read_base64() -> None:
    original_limits = get_limits()
    original_resolver = image_adapter.MediaResolver
    with tempfile.TemporaryDirectory(prefix="volcengine-image-prebase64-") as tmp:
        source = Path(tmp) / "large.bmp"
        Image.new("RGB", (256, 256), "white").save(source, format="BMP")
        assert source.stat().st_size > 2_000

        class _FakeResolver:
            def __init__(self, *args, **kwargs):
                pass

            def as_path(self, *args, **kwargs):
                resolved = SimpleNamespace(path=source, mime_type="image/bmp")

                def forbidden_read():
                    raise AssertionError(
                        "raw oversized bytes were read before compression"
                    )

                resolved.read_bytes = forbidden_read
                return _NullContext(resolved)

        image_adapter.MediaResolver = _FakeResolver
        set_limits(
            MediaLimits(
                image_compress_enabled=True,
                image_max_bytes=2_000,
                image_compress_max_size=128,
                image_compress_quality=85,
            )
        )
        try:
            part = await image_adapter.build_ark_image_part(str(source))
            url = part["image_url"]["url"]
            assert url.startswith("data:image/jpeg;base64,")
            encoded = url.split(",", 1)[1]
            assert len(base64.b64decode(encoded)) <= 2_000
        finally:
            image_adapter.MediaResolver = original_resolver
            set_limits(original_limits)


async def test_oversized_invalid_data_image_fails_closed() -> None:
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
        ref = (
            "data:image/png;base64,"
            + base64.b64encode(b"not-an-image" * 4).decode("ascii")
        )
        try:
            await image_adapter.build_ark_image_part(ref)
        except AdapterInputTransportError as exc:
            assert exc.stage == "compress_media"
            assert exc.reached_model is False
        else:
            raise AssertionError("oversized undecodable image must fail closed")
    finally:
        set_limits(original)


async def test_audio_transcode_output_is_size_checked_before_read() -> None:
    original_limits = get_limits()
    original_resolver = audio_adapter.MediaResolver
    original_transcode = audio_adapter._ffmpeg_to_ark_chat_wav

    with tempfile.TemporaryDirectory(prefix="volcengine-audio-prebase64-") as tmp:
        source = Path(tmp) / "source.bin"
        source.write_bytes(b"x")

        class _FakeResolver:
            def __init__(self, *args, **kwargs):
                pass

            def as_path(self, *args, **kwargs):
                return _NullContext(SimpleNamespace(path=source))

        async def fake_transcode(_source: Path, output: Path) -> None:
            output.write_bytes(b"x" * 100)

        audio_adapter.MediaResolver = _FakeResolver
        audio_adapter._ffmpeg_to_ark_chat_wav = fake_transcode
        set_limits(MediaLimits(audio_max_bytes=10))
        try:
            try:
                await audio_adapter.normalize_ark_chat_audio(str(source))
            except ValueError as exc:
                assert "在读取/Base64 前已停止" in str(exc)
            else:
                raise AssertionError("oversized transcoded audio must fail before read")
        finally:
            audio_adapter.MediaResolver = original_resolver
            audio_adapter._ffmpeg_to_ark_chat_wav = original_transcode
            set_limits(original_limits)


async def test_plugin_initialize_rebinds_live_owned_providers_only() -> None:
    reloaded: list[str] = []

    class _Manager:
        inst_map = {
            "ark/card": object(),
            "plan/card": object(),
            "foreign/card": object(),
        }

        async def reload(self, provider):
            reloaded.append(provider["id"])

    class _Config(dict):
        def save_config(self):
            raise AssertionError("no migration should be persisted in this fixture")

    class _ConfigMgr:
        default_conf = _Config(
            provider=[
                {
                    "id": "ark/card",
                    "type": plugin_main.ARK_PROVIDER_TYPE,
                },
                {
                    "id": "plan/card",
                    "type": plugin_main.AGENT_PLAN_PROVIDER_TYPE,
                },
                {
                    "id": "foreign/card",
                    "type": "openai_chat_completion",
                },
            ],
            provider_sources=[],
        )

    context = SimpleNamespace(
        astrbot_config_mgr=_ConfigMgr(),
        provider_manager=_Manager(),
    )
    result = await plugin_main._reload_owned_provider_instances(context)
    assert result == ["ark/card", "plan/card"]
    assert reloaded == result


def test_request_timer_wraps_query_not_parser() -> None:
    provider_source = (
        ROOT
        / "AstrBot"
        / "data"
        / "plugins"
        / "astrbot_plugin_volcengine_provider"
        / "providers.py"
    ).read_text("utf-8")
    assert "_REQUEST_STARTED_AT.set(time.perf_counter())" in provider_source
    assert "started = time.perf_counter()" not in provider_source


def main() -> None:
    test_context_authority_is_not_replaced_by_static_family_guesses()
    test_context_error_detection_reads_structured_body()
    test_cache_rollups_are_bucketed_atomically()
    test_cache_policy_transition_invalidates_old_rollup_evidence()
    test_image_compressor_honors_longest_edge()
    test_transparent_image_flattens_to_white_not_black()
    test_request_timer_wraps_query_not_parser()
    asyncio.run(test_oversized_local_image_compresses_before_raw_read_base64())
    asyncio.run(test_oversized_invalid_data_image_fails_closed())
    asyncio.run(test_audio_transcode_output_is_size_checked_before_read())
    asyncio.run(test_plugin_initialize_rebinds_live_owned_providers_only())
    print("NEGATIVE_LIFECYCLE_GUARDS_0_1_31=OK")


if __name__ == "__main__":
    main()
