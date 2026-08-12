"""Ark Chat video last-mile adapter and trust boundary.

AstrBot currently exposes video attachments to Chat providers as trusted TextPart
envelopes rather than a native video_urls field. This module recognizes only
those current-request envelopes, resolves their media references through
AstrBot MediaResolver, and emits Ark ``video_url`` blocks.
"""

from __future__ import annotations

import asyncio
import base64
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any

from astrbot.core.agent.message import ContentPart, TextPart
from astrbot.core.utils.media_utils import MediaResolver

from .errors import AdapterInputTransportError

# AstrBot currently represents an incoming video as a framework-generated
# TextPart because ProviderRequest has no video_urls field. Match only the
# exact framework envelope, and only when the same TextPart is present in
# extra_user_content_parts for the current request. This prevents ordinary
# chat text that happens to look like a local path from becoming file access.
VIDEO_ATTACHMENT_PATTERN = re.compile(
    r"^\[Video Attachment(?: in quoted message)?: "
    r"name (?P<name>.*?), (?P<source_kind>path|ref) "
    r"(?P<source>.+)\]$"
)

VIDEO_MODE_ORIGINAL = "original"
VIDEO_MODE_COMPRESSED = "compressed"


def _video_attachments_from_current_request(
    extra_user_content_parts: list[ContentPart] | None,
) -> list[tuple[str, str]]:
    """Return trusted ``(marker_text, media_ref)`` pairs for this request.

    The trust boundary is the ContentPart list assembled by AstrBot and passed
    separately from the user's prompt. Context history alone is deliberately
    insufficient because a user can type arbitrary text that resembles an
    attachment marker.
    """

    attachments: list[tuple[str, str]] = []
    for part in extra_user_content_parts or []:
        if not isinstance(part, TextPart):
            continue
        match = VIDEO_ATTACHMENT_PATTERN.fullmatch(part.text)
        if not match:
            continue
        media_ref = match.group("source").strip()
        if media_ref:
            attachments.append((part.text, media_ref))
    return attachments


def _replace_last_text_block(
    messages: list[dict],
    marker_text: str,
    replacement: dict[str, Any],
) -> bool:
    """Replace the newest exact marker, preserving earlier conversation text."""

    for message in reversed(messages):
        content = message.get("content")
        if not isinstance(content, list):
            continue
        for index in range(len(content) - 1, -1, -1):
            block = content[index]
            if not isinstance(block, dict):
                continue
            if block.get("type") == "text" and block.get("text") == marker_text:
                content[index] = replacement
                return True
    return False


async def _compress_video_reference(media_ref: str) -> str:
    """Resolve and compress one trusted video to a compact H.264 MP4 data URL."""

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise AdapterInputTransportError(
            "当前环境未安装 ffmpeg，无法使用“压缩 / Compressed”视频模式。",
            media_type="video",
            stage="compress_media",
        )

    resolver = MediaResolver(
        media_ref.strip(),
        media_type="video",
        default_suffix=".mp4",
    )
    fd, output_name = tempfile.mkstemp(prefix="volcengine_video_", suffix=".mp4")
    os.close(fd)
    output_path = Path(output_name)
    try:
        async with resolver.as_path() as resolved:
            process = await asyncio.create_subprocess_exec(
                ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                str(resolved.path),
                "-map",
                "0:v:0",
                "-map",
                "0:a?",
                "-vf",
                "scale=min(1280\\,iw):-2,fps=5",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "28",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-b:a",
                "96k",
                "-movflags",
                "+faststart",
                str(output_path),
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await process.communicate()
        if process.returncode != 0:
            detail = stderr.decode("utf-8", errors="replace").strip()
            if len(detail) > 400:
                detail = detail[-400:]
            raise AdapterInputTransportError(
                "视频压缩失败，未向火山方舟发送请求。"
                + (f" ffmpeg: {detail}" if detail else ""),
                media_type="video",
                stage="compress_media",
            )
        if not output_path.exists() or output_path.stat().st_size <= 0:
            raise AdapterInputTransportError(
                "视频压缩结果为空，未向火山方舟发送请求。",
                media_type="video",
                stage="compress_media",
            )
        data = await asyncio.to_thread(output_path.read_bytes)
        encoded = base64.b64encode(data).decode("utf-8")
        return f"data:video/mp4;base64,{encoded}"
    except AdapterInputTransportError:
        raise
    except Exception as exc:
        raise AdapterInputTransportError(
            "视频压缩或读取失败，未向火山方舟发送请求。",
            media_type="video",
            stage="compress_media",
        ) from exc
    finally:
        try:
            output_path.unlink(missing_ok=True)
        except OSError:
            pass


async def resolve_video_reference(media_ref: str, *, mode: str = VIDEO_MODE_ORIGINAL) -> str:
    """Resolve one trusted AstrBot video reference for Ark Chat Completions.

    ``original`` preserves the exact 0.1.18 behavior: remote/data URLs pass
    through, while local references are materialized to a data URL. ``compressed``
    explicitly downloads/materializes then transcodes to a compact MP4 first.

    Failures here are transport evidence only: no valid Ark request has reached
    the model, so model capability remains unknown.
    """

    normalized = media_ref.strip()
    if mode == VIDEO_MODE_COMPRESSED:
        return await _compress_video_reference(normalized)
    if normalized.startswith(("http://", "https://", "data:video/")):
        return normalized

    try:
        media = await MediaResolver(
            normalized,
            media_type="video",
            default_suffix=".mp4",
        ).to_base64_data(
            strict=True,
            default_mime_type="video/mp4",
        )
    except Exception as exc:
        raise AdapterInputTransportError(
            "无法读取本次视频附件，未向火山方舟发送请求。",
            media_type="video",
            stage="resolve_media",
        ) from exc

    if media is None or not media.mime_type.startswith("video/"):
        raise AdapterInputTransportError(
            "视频附件没有可识别的视频 MIME 类型，未向火山方舟发送请求。",
            media_type="video",
            stage="validate_media",
        )
    return media.to_data_url()


async def inject_current_request_videos(
    messages: list[dict],
    extra_user_content_parts: list[ContentPart] | None,
    *,
    enabled: bool,
    mode: str = VIDEO_MODE_ORIGINAL,
) -> None:
    """Replace only trusted current-request video envelopes in assembled messages."""

    attachments = _video_attachments_from_current_request(extra_user_content_parts)
    if not attachments:
        return

    if not enabled:
        for marker_text, _ in reversed(attachments):
            if not _replace_last_text_block(
                messages,
                marker_text,
                {"type": "text", "text": "[Video]"},
            ):
                raise AdapterInputTransportError(
                    "AstrBot 已声明视频附件，但当前请求中找不到对应内容块；本次请求已停止。",
                    media_type="video",
                    stage="assemble_payload",
                )
        return

    replacements: list[tuple[str, dict[str, Any]]] = []
    for marker_text, media_ref in attachments:
        video_url = await resolve_video_reference(media_ref, mode=mode)
        replacements.append(
            (
                marker_text,
                {
                    "type": "video_url",
                    "video_url": {"url": video_url},
                },
            )
        )

    # The prompt text precedes extra parts in AstrBot's message assembly.
    # Replace from the tail so a user-typed lookalike remains ordinary text.
    for marker_text, replacement in reversed(replacements):
        if not _replace_last_text_block(messages, marker_text, replacement):
            raise AdapterInputTransportError(
                "AstrBot 已声明视频附件，但当前请求中找不到对应内容块；"
                "为避免静默丢视频，本次请求已停止。",
                media_type="video",
                stage="assemble_payload",
            )
