"""Causal reachability probe for DeepSeek's current API model ID.

This test intentionally bypasses AstrBot's "fetch model list" path. It manually
enters the current official DeepSeek model ID into AstrBot's native DeepSeek
Source, then requires AstrBot's own provider-test request to succeed.

The remote request is deliberately evaluated before orthogonal persistence
observations so a config-representation detail cannot mask model-ID reachability.

Interpretation:
- PASS => model-ID -> AstrBot provider card -> real DeepSeek request is causally
  reachable; any separate live-model-list failure belongs to discovery/rendering.
- FAIL => do not blame discovery yet; inspect the manual model/request path first.
"""

from __future__ import annotations

import asyncio
import json
import os
import traceback
from pathlib import Path
from typing import Any

from playwright.async_api import async_playwright

from browser_matrix import (
    add_source,
    login,
    open_configured_model,
    open_manual_model_add,
    open_providers,
    save_model_dialog,
    save_source,
    select_source,
    semantic_page_snapshot,
)
from deepseek_real_foreign_matrix_0_1_24 import (
    CONFIG_PATH,
    DEEPSEEK_SOURCE,
    ENV_REFERENCE,
    assert_foreign_model_dialog,
    close_validated_dialog,
    fill_key_with_environment_reference,
    test_model_through_astrbot,
)

MODEL_ID = "deepseek-v4-flash"
ARTIFACT_DIR = (
    Path(os.environ.get("ASTRBOT_E2E_ARTIFACT_DIR", "e2e-artifacts"))
    / "deepseek-manual-latest-id-reachability"
)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def persisted_manual_evidence(source_id: str) -> dict[str, Any]:
    """Record safe, orthogonal persistence evidence without exposing a key."""

    data = json.loads(CONFIG_PATH.read_text(encoding="utf-8-sig"))
    sources = {
        str(item.get("id") or ""): item
        for item in data.get("provider_sources", [])
        if isinstance(item, dict)
    }
    providers = {
        str(item.get("id") or ""): item
        for item in data.get("provider", [])
        if isinstance(item, dict)
    }

    source = sources.get(source_id)
    provider_id = f"{source_id}/{MODEL_ID}"
    model = providers.get(provider_id)

    if not isinstance(source, dict):
        raise AssertionError(f"persisted DeepSeek Source missing: {source_id!r}")
    if not isinstance(model, dict):
        raise AssertionError(f"persisted manual DeepSeek model missing: {provider_id!r}")
    if source.get("type") != "openai_chat_completion":
        raise AssertionError(f"DeepSeek Source type changed unexpectedly: {source.get('type')!r}")
    if source.get("provider") != "deepseek":
        raise AssertionError(f"DeepSeek Source provider changed unexpectedly: {source.get('provider')!r}")

    # AstrBot may resolve or normalize environment references while persisting
    # provider config. That representation is not part of the causal question
    # under test. Never serialize the actual key; only safe booleans.
    source_key = source.get("key")

    modalities = model.get("modalities") or []
    volcengine_keys = sorted(key for key in model if str(key).startswith("volcengine_"))
    if "video" in modalities:
        raise AssertionError(f"manual DeepSeek model gained video: {modalities!r}")
    if volcengine_keys:
        raise AssertionError(f"manual DeepSeek model gained plugin keys: {volcengine_keys!r}")

    return {
        "source_id": source_id,
        "source_provider": source.get("provider"),
        "source_type": source.get("type"),
        "source_api_base": source.get("api_base"),
        "source_key_present": bool(source_key),
        "source_key_is_environment_reference": source_key == ENV_REFERENCE,
        "manual_model_id": MODEL_ID,
        "persisted_provider_id": provider_id,
        "model_modalities": modalities,
        "model_volcengine_keys": volcengine_keys,
    }


async def run() -> None:
    if not os.environ.get("DEEPSEEKAPI"):
        raise AssertionError("DEEPSEEKAPI environment secret is unavailable")

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    result: dict[str, Any] = {
        "success": False,
        "provider": "DeepSeek",
        "manual_model_id": MODEL_ID,
        "model_id_origin": "hard-coded current official DeepSeek API ID",
        "fetch_models_bypassed": True,
    }
    failure: BaseException | None = None

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(viewport={"width": 1440, "height": 1200})
        page = await context.new_page()
        try:
            await login(page)
            await open_providers(page)

            source_id = await add_source(page, DEEPSEEK_SOURCE)
            result["source_id"] = source_id
            await fill_key_with_environment_reference(page)
            await save_source(page)

            create_dialog = await open_manual_model_add(page, MODEL_ID)
            result["unsaved_manual_model_card"] = await assert_foreign_model_dialog(
                create_dialog,
                stage="deepseek/manual-current-id-unsaved",
            )
            await save_model_dialog(create_dialog)

            await select_source(page, source_id)
            edit_dialog = await open_configured_model(page, MODEL_ID)
            result["saved_reopened_manual_model_card"] = await assert_foreign_model_dialog(
                edit_dialog,
                stage="deepseek/manual-current-id-reopened",
            )
            await close_validated_dialog(
                page,
                edit_dialog,
                stage="deepseek/manual-current-id-close",
            )

            # This is the causal gate. It must run before persistence observations.
            result["astrbot_provider_test_message"] = await test_model_through_astrbot(
                page,
                source_id=source_id,
                model_id=MODEL_ID,
            )
            result["real_remote_request_via_astrbot"] = True
            result["causal_reachability"] = (
                "manual current DeepSeek model ID -> AstrBot -> DeepSeek API succeeded"
            )

            # Secondary evidence only; it cannot prevent the remote request above.
            result["persisted"] = persisted_manual_evidence(source_id)
            result["success"] = True
        except BaseException as exc:
            failure = exc
            result["error_type"] = type(exc).__name__
            result["error"] = str(exc)
            result["traceback"] = traceback.format_exc()
            try:
                await semantic_page_snapshot(page, ARTIFACT_DIR / "failure-page.dom.json")
            except Exception as snapshot_exc:
                result["snapshot_error"] = str(snapshot_exc)
        finally:
            try:
                await page.keyboard.press("Escape")
            except Exception:
                pass
            await browser.close()

    write_json(ARTIFACT_DIR / "result.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    if failure is not None:
        raise failure


if __name__ == "__main__":
    asyncio.run(run())
