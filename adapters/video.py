"""Ark Chat video last-mile adapter and trust boundary.

AstrBot currently exposes video attachments to Chat providers as trusted TextPart
envelopes rather than a native video_urls field. This module recognizes only
those current-request envelopes, resolves their media references through
AstrBot MediaResolver, and emits Ark ``video_url`` blocks.
"""

from __future__ import annotations

import re
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


async def resolve_video_reference(media_ref: str) -> str:
    """Resolve one trusted AstrBot video reference for Ark Chat Completions.

    Failures here are transport evidence only: no valid Ark request has reached
    the model, so model capability remains unknown.
    """

    normalized = media_ref.strip()
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
        video_url = await resolve_video_reference(media_ref)
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
