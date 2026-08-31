"""Runtime media limits for the Ark Chat adapters.

Module constants in ``audio.py`` / ``video.py`` remain the safe defaults; the
plugin entrypoint may override them from AstrBot plugin configuration. All
adapters read limits through :func:`get_limits` so a config change takes effect
on the next plugin reload without restarting AstrBot.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MediaLimits:
    audio_max_bytes: int = 25 * 1024 * 1024
    audio_transcode_timeout_seconds: int = 120
    video_max_bytes: int = 200 * 1024 * 1024
    video_transcode_timeout_seconds: int = 300
    image_compress_enabled: bool = True
    image_max_bytes: int = 5 * 1024 * 1024
    image_compress_max_size: int = 1280
    image_compress_quality: int = 85


_current_limits = MediaLimits()


def get_limits() -> MediaLimits:
    return _current_limits


def set_limits(limits: MediaLimits) -> None:
    global _current_limits
    _current_limits = limits
