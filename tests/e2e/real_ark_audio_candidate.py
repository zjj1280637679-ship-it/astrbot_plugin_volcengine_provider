"""Probe one audio candidate selected only from the current Ark /models receipt.

This avoids model-ID priors.  A current `modalities.input_modalities` entry that
contains `audio` is used only as a candidate-selection hint.  The actual
raw-vs-plugin request decides what happened in this run.
"""

from __future__ import annotations

import asyncio
import base64
import json
import math
import os
import struct
import sys
import tempfile
import urllib.error
import urllib.request
import wave
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT.parent))

from astrbot_plugin_volcengine_provider.providers import (  # noqa: E402
    ARK_API_BASE,
    ARK_PROVIDER_TYPE,
    ProviderVolcengineArk,
)

API_KEY = os.environ.get("ARK_API_KEY", "").strip()
ARTIFACT_DIR = Path(os.environ.get("E2E_ARTIFACT_DIR", "e2e-artifacts"))


def request_json(url: str, *, payload: dict[str, Any] | None = None) -> tuple[int | None, Any]:
    headers = {"Authorization": f"Bearer {API_KEY}"}
    data = None
    method = "GET"
    if payload is not None:
        method = "POST"
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            return response.status, json.loads(response.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        try:
            body = json.loads(raw)
        except json.JSONDecodeError:
            body = {"raw": raw[:2000]}
        return exc.code, body


def audio_candidates(receipt: Any) -> list[str]:
    result: list[str] = []
    data = receipt.get("data") if isinstance(receipt, dict) else None
    if not isinstance(data, list):
        return result
    for item in data:
        if not isinstance(item, dict):
            continue
        model_id = str(item.get("id") or "").strip()
        modalities = item.get("modalities")
        inputs = modalities.get("input_modalities") if isinstance(modalities, dict) else None
        if model_id and isinstance(inputs, list) and any(str(value).strip().lower() == "audio" for value in inputs):
            result.append(model_id)
    return sorted(set(result))


def make_wav() -> tuple[Path, str]:
    sample_rate = 16_000
    buf = tempfile.SpooledTemporaryFile()
    with wave.open(buf, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        frames = bytearray()
        for index in range(int(sample_rate * 0.35)):
            sample = int(5000 * math.sin(2 * math.pi * 440.0 * index / sample_rate))
            frames.extend(struct.pack("<h", sample))
        wav_file.writeframes(bytes(frames))
    buf.seek(0)
    data = buf.read()
    fd, name = tempfile.mkstemp(prefix="ark-audio-candidate-", suffix=".wav")
    os.close(fd)
    path = Path(name)
    path.write_bytes(data)
    return path, base64.b64encode(data).decode("ascii")


def error_shape(body: Any) -> dict[str, Any]:
    error = body.get("error") if isinstance(body, dict) else None
    if not isinstance(error, dict):
        return {"message": str(body)[:1000]}
    return {
        "code": error.get("code"),
        "type": error.get("type"),
        "message": str(error.get("message", ""))[:1000],
        "param": error.get("param"),
    }


async def main() -> None:
    if not API_KEY:
        raise SystemExit("ARK_API_KEY unavailable")
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    models_status, receipt = await asyncio.to_thread(request_json, f"{ARK_API_BASE}/models")
    candidates = audio_candidates(receipt)
    result: dict[str, Any] = {
        "schema_version": 1,
        "evidence_level": "L5_current_receipt_candidate_plus_runtime_when_attempted",
        "models_status": models_status,
        "explicit_audio_candidate_count": len(candidates),
        "explicit_audio_candidates": candidates[:30],
        "selection_rule": "lexicographically_first_model_with_current_explicit_audio_input_feedback",
        "attempted": False,
    }

    if models_status != 200 or not candidates:
        result["outcome"] = "no_current_explicit_audio_candidate_to_test"
    else:
        model = candidates[0]
        result["attempted"] = True
        result["selected_model"] = model
        wav_path, wav_b64 = make_wav()
        try:
            raw_status, raw_body = await asyncio.to_thread(
                request_json,
                f"{ARK_API_BASE}/chat/completions",
                payload={
                    "model": model,
                    "messages": [{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Reply with exactly RAW_AUDIO_CANDIDATE_OK"},
                            {"type": "input_audio", "input_audio": {"data": wav_b64, "format": "wav"}},
                        ],
                    }],
                    "stream": False,
                },
            )
            raw_success = raw_status == 200
            result["raw"] = {
                "status": raw_status,
                "success": raw_success,
                "error": None if raw_success else error_shape(raw_body),
            }

            config = {
                "id": "real-e2e-audio-candidate",
                "type": ARK_PROVIDER_TYPE,
                "provider_type": "chat_completion",
                "provider": "volcengine",
                "key": [API_KEY],
                "api_base": ARK_API_BASE,
                "model": model,
                "timeout": 90,
                "enable": True,
                "custom_headers": {},
                "custom_extra_body": {},
            }
            provider = ProviderVolcengineArk(config, {"request_max_retries": 1})
            try:
                response = await provider.text_chat(
                    prompt="Reply with exactly PLUGIN_AUDIO_CANDIDATE_OK",
                    audio_urls=[str(wav_path)],
                    request_max_retries=1,
                )
                completion = str(getattr(response, "completion_text", "") or "")
                plugin_success = True
                result["plugin"] = {
                    "success": True,
                    "completion_nonempty": bool(completion.strip()),
                    "marker_observed": "PLUGIN_AUDIO_CANDIDATE_OK" in completion,
                }
            except Exception as exc:
                plugin_success = False
                result["plugin"] = {
                    "success": False,
                    "error_type": type(exc).__name__,
                    "message": str(exc)[:1500],
                }

            if raw_success and plugin_success:
                result["outcome"] = "raw_and_plugin_success"
            elif raw_success and not plugin_success:
                result["outcome"] = "plugin_path_suspect"
            elif not raw_success and plugin_success:
                result["outcome"] = "plugin_adaptation_succeeds_where_minimal_raw_fails"
            else:
                result["outcome"] = "current_feedback_candidate_rejected_by_upstream_and_plugin"
        finally:
            wav_path.unlink(missing_ok=True)

    (ARTIFACT_DIR / "real-ark-audio-candidate.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps({
        "explicit_audio_candidate_count": result["explicit_audio_candidate_count"],
        "attempted": result["attempted"],
        "selected_model": result.get("selected_model"),
        "outcome": result.get("outcome"),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
