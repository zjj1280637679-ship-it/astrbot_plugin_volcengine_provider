"""Real Volcengine runtime evidence with raw-vs-plugin attribution.

The matrix does not convert one run into permanent model-capability truth.  For
each supplier card it compares a minimal raw upstream request with the request
through the plugin provider.  This distinguishes an upstream/account/model
condition from a plugin-path regression before any production change is made.

Secrets are never printed or written to artifacts.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import traceback
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT.parent))

from astrbot_plugin_volcengine_provider.providers import (  # noqa: E402
    AGENT_PLAN_API_BASE,
    AGENT_PLAN_DEFAULT_MODEL,
    AGENT_PLAN_PROVIDER_TYPE,
    ARK_API_BASE,
    ARK_DEFAULT_MODEL,
    ARK_PROVIDER_TYPE,
    ProviderVolcengineAgentPlan,
    ProviderVolcengineArk,
)

API_KEY = os.environ.get("ARK_API_KEY", "").strip()
ARTIFACT_DIR = Path(os.environ.get("E2E_ARTIFACT_DIR", "e2e-artifacts"))


def safe_error(exc: BaseException) -> dict[str, Any]:
    return {
        "type": type(exc).__name__,
        "message": str(exc)[:2000],
    }


def raw_request(url: str, *, method: str = "GET", payload: dict[str, Any] | None = None) -> dict[str, Any]:
    headers = {"Authorization": f"Bearer {API_KEY}"}
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            raw = response.read().decode("utf-8", "replace")
            parsed = json.loads(raw) if raw else {}
            return {
                "success": True,
                "status": response.status,
                "body_shape": sorted(parsed.keys()) if isinstance(parsed, dict) else type(parsed).__name__,
                "data_count": len(parsed.get("data", [])) if isinstance(parsed, dict) and isinstance(parsed.get("data"), list) else None,
            }
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")[:4000]
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError:
            parsed = None
        error_obj = parsed.get("error") if isinstance(parsed, dict) else None
        return {
            "success": False,
            "status": exc.code,
            "error": {
                "code": error_obj.get("code") if isinstance(error_obj, dict) else None,
                "type": error_obj.get("type") if isinstance(error_obj, dict) else None,
                "message": str(error_obj.get("message", ""))[:2000] if isinstance(error_obj, dict) else body[:2000],
            },
        }
    except Exception as exc:
        return {"success": False, "status": None, "error": safe_error(exc)}


def classify(raw_success: bool, plugin_success: bool) -> str:
    if raw_success and plugin_success:
        return "raw_and_plugin_success"
    if raw_success and not plugin_success:
        return "plugin_path_suspect"
    if not raw_success and plugin_success:
        return "plugin_adaptation_succeeds_where_minimal_raw_fails"
    return "upstream_account_or_model_condition"


async def plugin_models(provider: Any) -> dict[str, Any]:
    try:
        models = await provider.get_models()
        return {
            "success": True,
            "count": len(models),
            "sample": models[:20],
        }
    except Exception as exc:
        return {"success": False, "error": safe_error(exc)}


async def plugin_text(provider: Any, *, marker: str) -> dict[str, Any]:
    try:
        response = await provider.text_chat(
            prompt=f"Reply with exactly {marker}",
            request_max_retries=1,
        )
        text = str(getattr(response, "completion_text", "") or "")
        return {
            "success": True,
            "response_id_present": bool(getattr(response, "id", None)),
            "completion_nonempty": bool(text.strip()),
            "marker_observed": marker in text,
            "completion_preview": text[:300],
        }
    except Exception as exc:
        return {
            "success": False,
            "error": safe_error(exc),
            "traceback_tail": traceback.format_exc()[-4000:],
        }


async def main() -> None:
    if not API_KEY:
        raise SystemExit("ARK_API_KEY is unavailable; no runtime capability conclusion may be drawn")

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    settings = {"request_max_retries": 1}

    ark_config = {
        "id": "real-e2e-volcengine-ark",
        "type": ARK_PROVIDER_TYPE,
        "provider_type": "chat_completion",
        "provider": "volcengine",
        "key": [API_KEY],
        "api_base": ARK_API_BASE,
        "model": ARK_DEFAULT_MODEL,
        "timeout": 90,
        "enable": True,
        "custom_headers": {},
        "custom_extra_body": {},
    }
    plan_config = {
        "id": "real-e2e-volcengine-agent-plan",
        "type": AGENT_PLAN_PROVIDER_TYPE,
        "provider_type": "chat_completion",
        "provider": "volcengine",
        "key": [API_KEY],
        "api_base": AGENT_PLAN_API_BASE,
        "model": AGENT_PLAN_DEFAULT_MODEL,
        "timeout": 90,
        "enable": True,
        "custom_headers": {},
        "custom_extra_body": {},
    }

    ark = ProviderVolcengineArk(ark_config, settings)
    plan = ProviderVolcengineAgentPlan(plan_config, settings)

    result: dict[str, Any] = {
        "schema_version": 1,
        "evidence_level": "L5_current_real_upstream_run",
        "timestamp_note": "workflow runtime; do not persist as permanent capability truth",
        "cards": {},
    }

    # Ordinary Ark: compare raw /models with the plugin's normalized current receipt.
    raw_models = await asyncio.to_thread(raw_request, f"{ARK_API_BASE}/models")
    ark_models = await plugin_models(ark)

    raw_ark_text = await asyncio.to_thread(
        raw_request,
        f"{ARK_API_BASE}/chat/completions",
        method="POST",
        payload={
            "model": ARK_DEFAULT_MODEL,
            "messages": [{"role": "user", "content": "Reply with exactly RAW_ARK_OK"}],
            "stream": False,
        },
    )
    plugin_ark_text = await plugin_text(ark, marker="PLUGIN_ARK_OK")

    result["cards"]["volcengine_ark"] = {
        "provider_type": "chat_completion",
        "configured_model": ARK_DEFAULT_MODEL,
        "raw_models": raw_models,
        "plugin_models": ark_models,
        "models_attribution": classify(bool(raw_models.get("success")), bool(ark_models.get("success"))),
        "raw_text": raw_ark_text,
        "plugin_text": plugin_ark_text,
        "text_attribution": classify(bool(raw_ark_text.get("success")), bool(plugin_ark_text.get("success"))),
    }

    # Agent Plan deliberately has no probed /models route in production code.
    plan_models = await plugin_models(plan)
    raw_plan_text = await asyncio.to_thread(
        raw_request,
        f"{AGENT_PLAN_API_BASE}/chat/completions",
        method="POST",
        payload={
            "model": AGENT_PLAN_DEFAULT_MODEL,
            "messages": [{"role": "user", "content": "Reply with exactly RAW_PLAN_OK"}],
            "stream": False,
        },
    )
    plugin_plan_text = await plugin_text(plan, marker="PLUGIN_PLAN_OK")

    result["cards"]["volcengine_agent_plan"] = {
        "provider_type": "chat_completion",
        "configured_public_model": plan.get_model(),
        "configured_upstream_model": AGENT_PLAN_DEFAULT_MODEL,
        "plugin_local_models": plan_models,
        "raw_text": raw_plan_text,
        "plugin_text": plugin_plan_text,
        "text_attribution": classify(bool(raw_plan_text.get("success")), bool(plugin_plan_text.get("success"))),
    }

    result["summary"] = {
        "ark_models": result["cards"]["volcengine_ark"]["models_attribution"],
        "ark_text": result["cards"]["volcengine_ark"]["text_attribution"],
        "agent_plan_text": result["cards"]["volcengine_agent_plan"]["text_attribution"],
        "production_change_allowed_without_further_attribution": False,
    }

    target = ARTIFACT_DIR / "real-volcengine-runtime-matrix.json"
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    asyncio.run(main())
