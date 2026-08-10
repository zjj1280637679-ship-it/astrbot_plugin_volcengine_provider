"""Ark Chat audio last-mile adapter.

AstrBot owns media resolution and generic format handling. This module owns only
the final Ark Chat invariant (16 kHz, mono, PCM16 WAV, <=25 MiB) and serialization
to ``input_audio``. It has no Provider, retry, key-pool or model lifecycle logic.
"""

from __future__ import annotations

import asyncio
import base64
import io
import subprocess
import uuid
import wave
from pathlib import Path

from astrbot import logger
from astrbot.core.utils.astrbot_path import get_astrbot_temp_path
from astrbot.core.utils.media_utils import MediaResolver, describe_media_ref

ARK_CHAT_AUDIO_MAX_BYTES = 25 * 1024 * 1024
ARK_CHAT_AUDIO_SAMPLE_RATE = 16_000
ARK_CHAT_AUDIO_CHANNELS = 1
ARK_CHAT_AUDIO_SAMPLE_WIDTH = 2
ARK_CHAT_AUDIO_TRANSCODE_TIMEOUT_SECONDS = 120


def _validate_ark_chat_wav(wav_data: bytes) -> None:
    """Enforce the exact audio invariant sent to Ark Chat Completions."""

    if len(wav_data) > ARK_CHAT_AUDIO_MAX_BYTES:
        raise ValueError(
            "音频归一化后超过火山方舟 Base64 音频输入的 25 MB 上限，未发送请求。"
        )
    if not wav_data.startswith(b"RIFF") or wav_data[8:12] != b"WAVE":
        raise ValueError("音频归一化结果不是有效的 RIFF/WAVE 文件，未发送请求。")

    try:
        with wave.open(io.BytesIO(wav_data), "rb") as wav_file:
            if wav_file.getnchannels() != ARK_CHAT_AUDIO_CHANNELS:
                raise ValueError("音频归一化结果不是单声道 WAV，未发送请求。")
            if wav_file.getsampwidth() != ARK_CHAT_AUDIO_SAMPLE_WIDTH:
                raise ValueError("音频归一化结果不是 16-bit PCM WAV，未发送请求。")
            if wav_file.getframerate() != ARK_CHAT_AUDIO_SAMPLE_RATE:
                raise ValueError("音频归一化结果不是 16 kHz WAV，未发送请求。")
            if wav_file.getcomptype() != "NONE":
                raise ValueError("音频归一化结果不是未压缩 PCM WAV，未发送请求。")
            if wav_file.getnframes() <= 0:
                raise ValueError("音频归一化结果没有可用音频帧，未发送请求。")
    except (EOFError, wave.Error) as exc:
        raise ValueError("音频归一化结果的 WAV 结构无效，未发送请求。") from exc


async def _ffmpeg_to_ark_chat_wav(source_path: Path, output_path: Path) -> None:
    """Convert one materialized audio file to the provider's canonical WAV."""

    args = [
        "ffmpeg",
        "-nostdin",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(source_path),
        "-vn",
        "-ac",
        str(ARK_CHAT_AUDIO_CHANNELS),
        "-ar",
        str(ARK_CHAT_AUDIO_SAMPLE_RATE),
        "-c:a",
        "pcm_s16le",
        "-f",
        "wav",
        str(output_path),
    ]

    try:
        process = await asyncio.create_subprocess_exec(
            *args,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
    except FileNotFoundError as exc:
        raise ValueError("找不到 ffmpeg，无法把音频附件转换为火山方舟可读格式。") from exc

    try:
        _, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=ARK_CHAT_AUDIO_TRANSCODE_TIMEOUT_SECONDS,
        )
    except TimeoutError as exc:
        process.kill()
        await process.communicate()
        raise ValueError("音频附件转换超时，未向火山方舟发送请求。") from exc

    if process.returncode != 0:
        # Do not expose a signed source URL, local path or raw ffmpeg command in
        # user-visible errors. The exit code is sufficient for diagnosis.
        stderr_size = len(stderr or b"")
        raise ValueError(
            "音频附件无法解码为标准 WAV，未向火山方舟发送请求"
            f"（ffmpeg exit={process.returncode}, stderr_bytes={stderr_size}）。"
        )


async def normalize_ark_chat_audio(audio_ref: str) -> bytes:
    """Use AstrBot for audio resolution and enforce only Ark's final WAV invariant."""

    temp_dir = Path(get_astrbot_temp_path())
    temp_dir.mkdir(parents=True, exist_ok=True)
    output_path = temp_dir / f"volcengine_audio_{uuid.uuid4().hex}.wav"

    try:
        async with MediaResolver(
            audio_ref,
            media_type="audio",
            default_suffix=".wav",
        ).as_path(target_format="wav") as resolved:
            source_path = resolved.path

            wav_data: bytes | None = None
            source_stat = await asyncio.to_thread(source_path.stat)
            if source_stat.st_size <= ARK_CHAT_AUDIO_MAX_BYTES:
                candidate = await asyncio.to_thread(source_path.read_bytes)
                try:
                    _validate_ark_chat_wav(candidate)
                except ValueError:
                    pass
                else:
                    wav_data = candidate

            if wav_data is None:
                await _ffmpeg_to_ark_chat_wav(source_path, output_path)
                wav_data = await asyncio.to_thread(output_path.read_bytes)

        _validate_ark_chat_wav(wav_data)
        logger.debug(
            "Normalized Ark audio attachment: source=%s format=wav "
            "pcm_s16le=%dHz mono bytes=%d",
            describe_media_ref(audio_ref),
            ARK_CHAT_AUDIO_SAMPLE_RATE,
            len(wav_data),
        )
        return wav_data
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(
            "无法把本次音频附件归一化为火山方舟可读格式，未发送请求。"
        ) from exc
    finally:
        try:
            output_path.unlink(missing_ok=True)
        except OSError:
            logger.warning("Failed to clean provider-owned audio temp file")

async def build_ark_input_audio(audio_ref: str) -> dict:
    """Return one Ark ``input_audio`` block from an AstrBot media reference."""

    wav_data = await normalize_ark_chat_audio(audio_ref)
    audio_base64 = await asyncio.to_thread(
        lambda: base64.b64encode(wav_data).decode("ascii")
    )
    return {
        "type": "input_audio",
        "input_audio": {
            "data": audio_base64,
            "format": "wav",
        },
    }

