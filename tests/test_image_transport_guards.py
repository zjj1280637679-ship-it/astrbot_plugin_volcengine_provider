"""Deterministic image compression contracts for the Ark Chat adapter."""

from __future__ import annotations

import asyncio
import base64
import io
import sys
from dataclasses import replace
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "AstrBot" / "data" / "plugins"))

from astrbot_plugin_volcengine_provider.adapters.image import enforce_image_limits
from astrbot_plugin_volcengine_provider.adapters.limits import get_limits, set_limits


def _bmp_data_url(size: tuple[int, int]) -> str:
    output = io.BytesIO()
    Image.new("RGB", size, (42, 108, 196)).save(output, format="BMP")
    return "data:image/bmp;base64," + base64.b64encode(output.getvalue()).decode("ascii")


def _decode_image(data_url: str) -> tuple[bytes, tuple[int, int]]:
    encoded = data_url.split(",", 1)[1]
    payload = base64.b64decode(encoded, validate=True)
    with Image.open(io.BytesIO(payload)) as image:
        return payload, image.size


async def test_oversized_image_honors_byte_and_longest_edge_limits() -> None:
    original_limits = get_limits()
    source_url = _bmp_data_url((3000, 2000))
    detail = "high"
    payloads = {
        "messages": [
            {
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": source_url, "detail": detail},
                    }
                ]
            }
        ]
    }
    byte_ceiling = 1024 * 1024
    longest_edge = 1280

    try:
        set_limits(
            replace(
                original_limits,
                image_max_bytes=byte_ceiling,
                image_compress_max_size=longest_edge,
            )
        )
        await enforce_image_limits(payloads)
    finally:
        set_limits(original_limits)

    image_url = payloads["messages"][0]["content"][0]["image_url"]
    assert image_url["url"].startswith("data:image/jpeg;base64,")
    assert image_url["detail"] == detail
    compressed, size = _decode_image(image_url["url"])
    assert len(compressed) <= byte_ceiling
    assert max(size) <= longest_edge


async def test_below_byte_ceiling_is_not_reencoded_or_resized() -> None:
    original_limits = get_limits()
    source_url = _bmp_data_url((64, 32))
    payloads = {
        "messages": [
            {"content": [{"type": "image_url", "image_url": {"url": source_url}}]}
        ]
    }

    try:
        set_limits(replace(original_limits, image_max_bytes=1024 * 1024))
        await enforce_image_limits(payloads)
    finally:
        set_limits(original_limits)

    assert payloads["messages"][0]["content"][0]["image_url"]["url"] == source_url


def main() -> None:
    asyncio.run(test_oversized_image_honors_byte_and_longest_edge_limits())
    asyncio.run(test_below_byte_ceiling_is_not_reencoded_or_resized())
    print("IMAGE_TRANSPORT_GUARDS_0_1_34=OK")


if __name__ == "__main__":
    main()
