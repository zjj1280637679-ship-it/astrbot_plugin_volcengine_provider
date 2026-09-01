"""Ark Chat image last-mile adapter.

Volcengine Ark rejects oversized image inputs (the ordinary Chat Completions
path caps a single image around 5 MB). This adapter walks the assembled
OpenAI payload, measures local/data-URL images, and transparently compresses
those over the configured ceiling into a compact JPEG data URL. Remote URLs
pass through untouched because Ark fetches them server-side.

The byte ceiling, longest-edge bound and JPEG quality are runtime-configurable
through the plugin's ``_conf_schema.json``.
"""

from __future__ import annotations

import asyncio
import base64
import io
import logging
from pathlib import Path
from urllib.parse import unquote, urlparse

from .limits import get_limits

logger = logging.getLogger(__name__)


def _image_urls_from_payload(payloads: dict) -> list[tuple[list, int, dict]]:
    """Return ``(content_list, index, block)`` for every image_url block."""
    hits: list[tuple[list, int, dict]] = []
    messages = payloads.get("messages")
    if not isinstance(messages, list):
        return hits
    for message in messages:
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, list):
            continue
        for index, block in enumerate(content):
            if not isinstance(block, dict):
                continue
            image_url = block.get("image_url")
            if isinstance(image_url, dict) and isinstance(image_url.get("url"), str):
                hits.append((content, index, image_url))
    return hits


def _data_url_byte_size(data_url: str) -> int | None:
    payload = data_url.rsplit(",", 1)[-1]
    try:
        return len(base64.b64decode(payload, validate=True))
    except Exception:
        return None


def _file_url_path(file_url: str) -> Path | None:
    parsed = urlparse(file_url)
    if parsed.scheme != "file":
        return None
    try:
        return Path(unquote(parsed.path))
    except Exception:
        return None


def _compress_image_sync(source: bytes, max_bytes: int, max_size: int, quality: int) -> bytes | None:
    """Iteratively downscale an in-memory image until it fits ``max_bytes``."""
    from PIL import Image

    try:
        image = Image.open(io.BytesIO(source))
        image.load()
    except Exception:
        return None
    if image.mode not in ("RGB", "L"):
        image = image.convert("RGB")

    width, height = image.size
    longest = max(width, height)
    if max_size > 0 and longest > max_size:
        if width >= height:
            target_size = (max_size, max(1, int(height * max_size / width)))
        else:
            target_size = (max(1, int(width * max_size / height)), max_size)
        image = image.resize(target_size, Image.LANCZOS)

    for attempt in range(6):
        out = io.BytesIO()
        image.save(out, format="JPEG", quality=quality, optimize=True)
        data = out.getvalue()
        if len(data) <= max_bytes:
            return data
        width, height = image.size
        longest = max(width, height)
        if longest <= 128:
            return data  # give up: already tiny, stop shrinking
        scale = min(0.75, (max_bytes / max(len(data), 1)) ** 0.5)
        new_longest = max(128, int(longest * scale))
        if width >= height:
            new_size = (new_longest, max(1, int(height * new_longest / width)))
        else:
            new_size = (max(1, int(width * new_longest / height)), new_longest)
        image = image.resize(new_size, Image.LANCZOS)
        quality = max(quality - 8, 55)
    return None


async def enforce_image_limits(payloads: dict) -> None:
    """Compress oversized local/data-URL images in-place under the configured ceiling."""
    limits = get_limits()
    if not limits.image_compress_enabled:
        return
    for content, index, image_url in _image_urls_from_payload(payloads):
        url = image_url["url"].strip()
        try:
            if url.startswith(("http://", "https://")):
                continue
            source: bytes | None = None
            if url.startswith("data:image"):
                size = _data_url_byte_size(url)
                if size is None or size <= limits.image_max_bytes:
                    continue
                source = base64.b64decode(url.rsplit(",", 1)[-1], validate=True)
            elif url.startswith("file:"):
                path = _file_url_path(url)
                if path is None:
                    continue
                stat = await asyncio.to_thread(path.stat)
                if stat.st_size <= limits.image_max_bytes:
                    continue
                source = await asyncio.to_thread(path.read_bytes)
            else:
                # Bare local path (AstrBot sometimes passes these through).
                path = Path(url)
                if not path.is_absolute() or not path.exists():
                    continue
                stat = await asyncio.to_thread(path.stat)
                if stat.st_size <= limits.image_max_bytes:
                    continue
                source = await asyncio.to_thread(path.read_bytes)
            if not source:
                continue
            compressed = await asyncio.to_thread(
                _compress_image_sync,
                source,
                limits.image_max_bytes,
                limits.image_compress_max_size,
                limits.image_compress_quality,
            )
            if not compressed:
                logger.warning("volcengine: image compression failed; leaving original image url")
                continue
            image_url["url"] = "data:image/jpeg;base64," + base64.b64encode(compressed).decode("ascii")
            logger.info("volcengine: compressed oversized image to %d bytes", len(compressed))
        except Exception:
            logger.warning("volcengine: image limit enforcement failed for one image", exc_info=True)
