"""Ark Chat video last-mile adapter and trust boundary.

AstrBot currently exposes video attachments to Chat providers as trusted TextPart
envelopes rather than a native video_urls field. This module recognizes only
those current-request envelopes, resolves their media references through
AstrBot MediaResolver, and emits Ark ``video_url`` blocks.

Every local materialization path enforces Ark's documented video input ceiling
*before* base64-encoding, and the compressed path additionally bounds
transcoding wall-clock time. A timed-out or cancelled ffmpeg is always
terminated so a chat request can neither hang forever nor strand subprocesses.
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
from .limits import get_limits

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

# Ark Chat video understanding ceiling documented for doubao vision models.
# Local media is rejected before reading/base64-encoding when it exceeds this
# bound, and the compressed output is checked again before serialization.
ARK_CHAT_VIDEO_MAX_MB = 200
ARK_CHAT_VIDEO_MAX_BYTES = ARK_CHAT_VIDEO_MAX_MB * 1024 * 1024
# Audio transcoding is bounded at 120 s. Video re-encoding legitimately takes
# longer, but must still be bounded so a stuck ffmpeg cannot hang the whole
# chat request indefinitely.
ARK_CHAT_VIDEO_TRANSCODE_TIMEOUT_SECONDS = 300


def _video_max_bytes() -> int:
    return get_limits().video_max_bytes


def _video_max_mb() -> int:
    return _video_max_bytes() // (1024 * 1024)


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


def _data_url_payload_within_limit(data_url: str, *, max_bytes: int) -> bool:
    """Cheap ceiling check for a base64 data URL without decoding it.

    ``ceil(max_bytes / 3) * 4`` is the length of the longest base64 payload that
    can still decode to at most ``max_bytes`` bytes.
    """

    payload = data_url.rsplit(",", 1)[-1]
    if not payload:
        return True
    return len(payload) <= ((max_bytes + 2) // 3) * 4


async def _terminate_transcode_process(
    process: asyncio.subprocess.Process | None,
    *,
    reap: bool = False,
) -> None:
    """Kill a transcoding subprocess left running by timeout or cancellation.

    ``kill()`` runs synchronously first so even a re-cancelled task has already
    terminated the child. ``reap`` additionally waits for process exit; it is
    only used on the timeout path where the task is still healthy.
    """

    if process is None or process.returncode is not None:
        return
    try:
        process.kill()
    except (OSError, ProcessLookupError):
        pass
    if reap:
        try:
            await process.wait()
        except Exception:
            pass


async def _compress_video_reference(media_ref: str) -> str:
    """Resolve and compress one trusted video to a compact H.264 MP4 data URL.

    The transcoding subprocess is bounded by a wall-clock timeout and is killed
    on timeout or cancellation. Input and output are checked against Ark's
    documented video ceiling before any base64 expansion happens.
    """

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
    process: asyncio.subprocess.Process | None = None
    try:
        async with resolver.as_path() as resolved:
            source_path = resolved.path
            source_stat = await asyncio.to_thread(source_path.stat)
            if source_stat.st_size <= 0:
                raise AdapterInputTransportError(
                    "视频附件为空文件，未向火山方舟发送请求。",
                    media_type="video",
                    stage="validate_media",
                )
            if source_stat.st_size > _video_max_bytes():
                raise AdapterInputTransportError(
                    f"视频附件超过火山方舟 {_video_max_mb()} MB 输入上限，"
                    "未向火山方舟发送请求。",
                    media_type="video",
                    stage="validate_media",
                )

            process = await asyncio.create_subprocess_exec(
                ffmpeg,
                "-nostdin",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                str(source_path),
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
            try:
                _, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=get_limits().video_transcode_timeout_seconds,
                )
            except TimeoutError as exc:
                await _terminate_transcode_process(process, reap=True)
                raise AdapterInputTransportError(
                    f"视频压缩超时（{get_limits().video_transcode_timeout_seconds} 秒），"
                    "未向火山方舟发送请求。",
                    media_type="video",
                    stage="compress_media",
                ) from exc
            except asyncio.CancelledError:
                await _terminate_transcode_process(process, reap=False)
                raise

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
        if not output_path.exists():
            raise AdapterInputTransportError(
                "视频压缩结果缺失，未向火山方舟发送请求。",
                media_type="video",
                stage="compress_media",
            )
        output_stat = await asyncio.to_thread(output_path.stat)
        if output_stat.st_size <= 0:
            raise AdapterInputTransportError(
                "视频压缩结果为空，未向火山方舟发送请求。",
                media_type="video",
                stage="compress_media",
            )
        if output_stat.st_size > _video_max_bytes():
            raise AdapterInputTransportError(
                f"视频压缩结果仍超过火山方舟 {_video_max_mb()} MB 输入上限，"
                "未向火山方舟发送请求。",
                media_type="video",
                stage="validate_media",
            )
        data = await asyncio.to_thread(output_path.read_bytes)
        encoded = base64.b64encode(data).decode("utf-8")
        return f"data:video/mp4;base64,{encoded}"
    except AdapterInputTransportError:
        raise
    except asyncio.CancelledError:
        # Defensive: a cancellation landing outside the communicate window must
        # not strand an already-started ffmpeg.
        await _terminate_transcode_process(process, reap=False)
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
    Both local materialization paths now enforce Ark's documented video input
    ceiling before base64-encoding, so oversized media fails closed instead of
    spiking memory or being rejected upstream.

    Failures here are transport evidence only: no valid Ark request has reached
    the model, so model capability remains unknown.
    """

    normalized = media_ref.strip()
    if mode == VIDEO_MODE_COMPRESSED:
        return await _compress_video_reference(normalized)
    if normalized.startswith(("http://", "https://")):
        # Ark fetches remote URLs server-side; their size is unknown locally and
        # the 0.1.18 pass-through shape is preserved.
        return normalized
    if normalized.startswith("data:video/"):
        if not _data_url_payload_within_limit(
            normalized,
            max_bytes=_video_max_bytes(),
        ):
            raise AdapterInputTransportError(
                f"视频附件超过火山方舟 {_video_max_mb()} MB 输入上限，"
                "未向火山方舟发送请求。",
                media_type="video",
                stage="validate_media",
            )
        return normalized

    try:
        async with MediaResolver(
            normalized,
            media_type="video",
            default_suffix=".mp4",
        ).as_path() as resolved:
            source_stat = await asyncio.to_thread(resolved.path.stat)
            if source_stat.st_size <= 0:
                raise AdapterInputTransportError(
                    "视频附件为空文件，未向火山方舟发送请求。",
                    media_type="video",
                    stage="validate_media",
                )
            if source_stat.st_size > _video_max_bytes():
                raise AdapterInputTransportError(
                    f"视频附件超过火山方舟 {_video_max_mb()} MB 输入上限，"
                    "未向火山方舟发送请求。",
                    media_type="video",
                    stage="validate_media",
                )
            mime_type = str(getattr(resolved, "mime_type", "") or "video/mp4").strip()
            if not mime_type.startswith("video/"):
                raise AdapterInputTransportError(
                    "视频附件没有可识别的视频 MIME 类型，未向火山方舟发送请求。",
                    media_type="video",
                    stage="validate_media",
                )
            data = await asyncio.to_thread(resolved.read_bytes)
    except AdapterInputTransportError:
        raise
    except Exception as exc:
        raise AdapterInputTransportError(
            "无法读取本次视频附件，未向火山方舟发送请求。",
            media_type="video",
            stage="resolve_media",
        ) from exc

    encoded = base64.b64encode(data).decode("utf-8")
    return f"data:{mime_type};base64,{encoded}"


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
        # Preserve the exact 0.1.18 resolver call shape for Original mode. Some
        # regression fixtures (and potential third-party monkeypatches) provide
        # a one-argument resolver. Only the new compressed path needs ``mode``.
        if mode == VIDEO_MODE_ORIGINAL:
            video_url = await resolve_video_reference(media_ref)
        else:
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
