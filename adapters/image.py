"""Ark Chat oversized-image guard.

Only images that exceed the configured byte ceiling are rewritten. Once that
path is entered, the output must satisfy both the byte ceiling and the configured
longest-edge target; otherwise the request fails closed before reaching Ark.
"""

from __future__ import annotations

import asyncio
import base64
import io
from pathlib import Path
from urllib.parse import unquote, urlparse

from PIL import Image, ImageOps

from .errors import AdapterInputTransportError
from .limits import get_limits


def _image_urls_from_payload(payloads: dict) -> list[dict]:
    hits: list[dict] = []
    messages = payloads.get("messages")
    if not isinstance(messages, list):
        return hits
    for message in messages:
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            image_url = block.get("image_url")
            if isinstance(image_url, dict) and isinstance(image_url.get("url"), str):
                hits.append(image_url)
    return hits


def _data_url_bytes(data_url: str) -> bytes | None:
    try:
        return base64.b64decode(data_url.rsplit(",", 1)[-1], validate=True)
    except Exception:
        return None


def _file_url_path(file_url: str) -> Path | None:
    parsed = urlparse(file_url)
    if parsed.scheme != "file":
        return None
    try:
        path = unquote(parsed.path)
        if parsed.netloc:
            path = f"//{parsed.netloc}{path}"
        return Path(path)
    except Exception:
        return None


def _resize_longest_edge(image: Image.Image, max_size: int) -> Image.Image:
    width, height = image.size
    longest = max(width, height)
    if longest <= max_size:
        return image
    scale = max_size / longest
    size = (max(1, round(width * scale)), max(1, round(height * scale)))
    return image.resize(size, Image.Resampling.LANCZOS)


def _compress_image_sync(
    source: bytes,
    max_bytes: int,
    max_size: int,
    quality: int,
) -> bytes | None:
    """Return JPEG bytes satisfying both configured limits, or ``None``."""
    try:
        with Image.open(io.BytesIO(source)) as opened:
            image = ImageOps.exif_transpose(opened)
            image.load()
    except Exception:
        return None

    if image.mode not in ("RGB", "L"):
        image = image.convert("RGB")
    image = _resize_longest_edge(image, max_size)

    current_quality = quality
    for _ in range(10):
        out = io.BytesIO()
        image.save(out, format="JPEG", quality=current_quality, optimize=True)
        data = out.getvalue()
        if len(data) <= max_bytes and max(image.size) <= max_size:
            return data

        width, height = image.size
        longest = max(width, height)

        if current_quality > 35:
            current_quality = max(35, current_quality - 8)

        if len(data) <= max_bytes:
            return data if longest <= max_size else None

        if longest <= 128:
            if current_quality <= 35:
                return None
            continue

        scale = min(0.82, (max_bytes / max(len(data), 1)) ** 0.5)
        new_longest = max(128, int(longest * scale))
        if new_longest >= longest:
            new_longest = max(128, longest - 1)
        if new_longest == longest:
            return None

        if width >= height:
            new_size = (new_longest, max(1, round(height * new_longest / width)))
        else:
            new_size = (max(1, round(width * new_longest / height)), new_longest)
        image = image.resize(new_size, Image.Resampling.LANCZOS)

    return None


async def _read_oversized_local_or_data_image(
    url: str,
    *,
    max_bytes: int,
) -> bytes | None:
    if url.startswith(("http://", "https://")):
        return None

    if url.startswith("data:image"):
        data = _data_url_bytes(url)
        if data is None:
            raise AdapterInputTransportError(
                "图片 data URL 无法解码，未向火山方舟发送请求。",
                media_type="image",
                stage="validate_media",
            )
        return data if len(data) > max_bytes else None

    path: Path | None
    if url.startswith("file:"):
        path = _file_url_path(url)
    else:
        candidate = Path(url)
        path = candidate if candidate.is_absolute() else None

    if path is None:
        return None

    try:
        stat = await asyncio.to_thread(path.stat)
    except OSError as exc:
        raise AdapterInputTransportError(
            "无法读取本地图片附件，未向火山方舟发送请求。",
            media_type="image",
            stage="resolve_media",
        ) from exc

    if stat.st_size <= max_bytes:
        return None
    return await asyncio.to_thread(path.read_bytes)


async def enforce_image_limits(payloads: dict) -> None:
    """Compress every oversized local/data image or fail closed."""
    limits = get_limits()
    if not limits.image_compress_enabled:
        return

    for image_url in _image_urls_from_payload(payloads):
        url = image_url["url"].strip()
        source = await _read_oversized_local_or_data_image(
            url,
            max_bytes=limits.image_max_bytes,
        )
        if source is None:
            continue

        compressed = await asyncio.to_thread(
            _compress_image_sync,
            source,
            limits.image_max_bytes,
            limits.image_compress_max_size,
            limits.image_compress_quality,
        )
        if compressed is None or len(compressed) > limits.image_max_bytes:
            raise AdapterInputTransportError(
                "图片超过输入上限且无法压缩到安全范围，未向火山方舟发送请求。",
                media_type="image",
                stage="compress_media",
            )

        image_url["url"] = (
            "data:image/jpeg;base64,"
            + base64.b64encode(compressed).decode("ascii")
        )
