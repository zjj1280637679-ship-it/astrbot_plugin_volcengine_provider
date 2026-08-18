"""Ark Chat image materialization and oversized-image guard.

The guard runs while AstrBot is resolving each image content part, before a local
or remote image is expanded into Base64. Oversized inputs are decoded once,
resized/flattened to JPEG, and only the compressed result is Base64-encoded.

A failure in this adapter is a transport failure, not a model-capability fact.
"""

from __future__ import annotations

import asyncio
import base64
import io

from PIL import Image, ImageOps

from astrbot.core.utils.media_utils import MediaResolver

from .errors import AdapterInputTransportError
from .limits import get_limits


def _data_url_bytes(data_url: str) -> bytes:
    header, sep, payload = data_url.partition(",")
    if not sep or not header.lower().startswith("data:image/"):
        raise AdapterInputTransportError(
            "图片 data URL 格式无效，未向火山方舟发送请求。",
            media_type="image",
            stage="validate_media",
        )
    if ";base64" not in header.lower():
        raise AdapterInputTransportError(
            "图片 data URL 不是 Base64 编码，未向火山方舟发送请求。",
            media_type="image",
            stage="validate_media",
        )
    try:
        return base64.b64decode(payload, validate=True)
    except Exception as exc:
        raise AdapterInputTransportError(
            "图片 data URL 无法解码，未向火山方舟发送请求。",
            media_type="image",
            stage="validate_media",
        ) from exc


def _flatten_for_jpeg(image: Image.Image) -> Image.Image:
    """Return a JPEG-safe image, compositing transparency onto white."""
    has_alpha = image.mode in {"RGBA", "LA"} or "transparency" in image.info
    if has_alpha:
        rgba = image.convert("RGBA")
        background = Image.new("RGB", rgba.size, "white")
        background.paste(rgba, mask=rgba.getchannel("A"))
        return background
    if image.mode == "L":
        return image
    if image.mode != "RGB":
        return image.convert("RGB")
    return image


def _resize_longest_edge(image: Image.Image, max_size: int) -> Image.Image:
    width, height = image.size
    longest = max(width, height)
    if longest <= max_size:
        return image
    scale = max_size / longest
    size = (max(1, round(width * scale)), max(1, round(height * scale)))
    return image.resize(size, Image.Resampling.LANCZOS)


def _compress_loaded_image(
    image: Image.Image,
    *,
    max_bytes: int,
    max_size: int,
    quality: int,
) -> bytes | None:
    image = ImageOps.exif_transpose(image)
    image.load()
    image = _flatten_for_jpeg(image)
    image = _resize_longest_edge(image, max_size)

    current_quality = quality
    for _ in range(12):
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


def _compress_image_sync(
    source: bytes,
    max_bytes: int,
    max_size: int,
    quality: int,
) -> bytes | None:
    """Compatibility helper for byte-backed/data-URL tests."""
    try:
        with Image.open(io.BytesIO(source)) as opened:
            return _compress_loaded_image(
                opened,
                max_bytes=max_bytes,
                max_size=max_size,
                quality=quality,
            )
    except Exception:
        return None


def _compress_image_path_sync(
    source_path,
    max_bytes: int,
    max_size: int,
    quality: int,
) -> bytes | None:
    """Compress directly from a materialized path without raw-byte/Base64 copies."""
    try:
        with Image.open(source_path) as opened:
            return _compress_loaded_image(
                opened,
                max_bytes=max_bytes,
                max_size=max_size,
                quality=quality,
            )
    except Exception:
        return None


def _jpeg_data_url(data: bytes) -> str:
    return "data:image/jpeg;base64," + base64.b64encode(data).decode("ascii")


async def materialize_ark_image_url(image_ref: str) -> str:
    """Resolve one image, compressing oversized bytes before Base64 expansion."""
    normalized = str(image_ref or "").strip()
    if not normalized:
        raise AdapterInputTransportError(
            "图片引用为空，未向火山方舟发送请求。",
            media_type="image",
            stage="resolve_media",
        )

    limits = get_limits()

    if normalized.lower().startswith("data:image/"):
        source = _data_url_bytes(normalized)
        if not limits.image_compress_enabled or len(source) <= limits.image_max_bytes:
            return normalized
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
        return _jpeg_data_url(compressed)

    try:
        async with MediaResolver(
            normalized,
            media_type="image",
            default_suffix=".img",
        ).as_path() as resolved:
            source_path = resolved.path
            mime_type = str(getattr(resolved, "mime_type", "") or "").strip()
            stat = await asyncio.to_thread(source_path.stat)
            if stat.st_size <= 0:
                raise AdapterInputTransportError(
                    "图片附件为空文件，未向火山方舟发送请求。",
                    media_type="image",
                    stage="validate_media",
                )

            oversized = stat.st_size > limits.image_max_bytes
            if oversized and limits.image_compress_enabled:
                compressed = await asyncio.to_thread(
                    _compress_image_path_sync,
                    source_path,
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
                return _jpeg_data_url(compressed)

            if mime_type and not mime_type.startswith("image/"):
                raise AdapterInputTransportError(
                    "图片附件没有可识别的图片 MIME 类型，未向火山方舟发送请求。",
                    media_type="image",
                    stage="validate_media",
                )
            data = await asyncio.to_thread(source_path.read_bytes)
            if not data:
                raise AdapterInputTransportError(
                    "图片附件为空文件，未向火山方舟发送请求。",
                    media_type="image",
                    stage="validate_media",
                )
            if not mime_type:
                raise AdapterInputTransportError(
                    "无法确定图片附件的 MIME 类型，未向火山方舟发送请求。",
                    media_type="image",
                    stage="validate_media",
                )
            return (
                f"data:{mime_type};base64,"
                + base64.b64encode(data).decode("ascii")
            )
    except AdapterInputTransportError:
        raise
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        raise AdapterInputTransportError(
            "无法读取本次图片附件，未向火山方舟发送请求。",
            media_type="image",
            stage="resolve_media",
        ) from exc


async def build_ark_image_part(
    image_ref: str,
    *,
    image_detail: str | None = None,
) -> dict:
    """Return an OpenAI/Ark ``image_url`` content block."""
    url = await materialize_ark_image_url(image_ref)
    payload: dict[str, str] = {"url": url}
    if image_detail:
        payload["detail"] = image_detail
    return {"type": "image_url", "image_url": payload}


async def enforce_image_limits(payloads: dict) -> None:
    """Compatibility post-assembly guard for callers outside this Provider.

    The main Provider path no longer uses this function because enforcing only
    after AstrBot's native materialization is too late to prevent Base64 memory
    expansion. It remains fail-closed for direct callers.
    """
    messages = payloads.get("messages")
    if not isinstance(messages, list):
        return
    for message in messages:
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict) or block.get("type") != "image_url":
                continue
            image_url = block.get("image_url")
            if not isinstance(image_url, dict):
                continue
            url = image_url.get("url")
            if not isinstance(url, str) or not url:
                continue
            detail = image_url.get("detail")
            replacement = await build_ark_image_part(
                url,
                image_detail=detail if isinstance(detail, str) else None,
            )
            block.clear()
            block.update(replacement)
