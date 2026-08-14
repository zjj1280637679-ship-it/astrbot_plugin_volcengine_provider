"""Real DeepSeek model-list equivalence probe through AstrBot 4.27.3.

The same real credential is used in two paths:

1. Direct GET https://api.deepseek.com/v1/models.
2. AstrBot native DeepSeek Source -> Dashboard "fetch model list".

The credential is never written to artifacts. Only model IDs and safe booleans
are persisted. The test passes only when both non-empty model-ID sets are equal.
"""

from __future__ import annotations

import asyncio
import json
import os
import traceback
import urllib.request
from pathlib import Path
from typing import Any

from playwright.async_api import Page, async_playwright, expect

from browser_matrix import add_source, login, open_providers, save_source
from deepseek_real_foreign_matrix_0_1_24 import (
    DEEPSEEK_SOURCE,
    fetch_models_through_astrbot,
    row_for_key,
)

API_URL = "https://api.deepseek.com/v1/models"
SECRET = os.environ.get("DEEPSEEKAPI", "").strip()
ARTIFACT_DIR = (
    Path(os.environ.get("ASTRBOT_E2E_ARTIFACT_DIR", "e2e-artifacts"))
    / "deepseek-real-model-fetch"
)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def direct_model_ids() -> list[str]:
    request = urllib.request.Request(
        API_URL,
        headers={"Authorization": f"Bearer {SECRET}"},
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        if int(response.status) != 200:
            raise AssertionError(f"direct DeepSeek /models returned HTTP {response.status}")
        payload = json.loads(response.read().decode("utf-8"))

    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, list):
        raise AssertionError("direct DeepSeek /models response has no data list")

    ids = sorted(
        {
            str(item.get("id") or "").strip()
            for item in data
            if isinstance(item, dict) and str(item.get("id") or "").strip()
        }
    )
    if not ids:
        raise AssertionError("direct DeepSeek /models returned no usable model IDs")
    return ids


async def fill_real_secret(page: Page) -> None:
    shell = page.locator(".provider-config-shell")
    row = await row_for_key(shell, "key")
    key_input = row.locator("input").first
    await expect(key_input).to_be_visible(timeout=10_000)
    await key_input.fill(SECRET)
    if await key_input.input_value() != SECRET:
        raise AssertionError("AstrBot DeepSeek Source did not retain the real runtime secret")


async def run() -> None:
    if not SECRET:
        raise AssertionError("DEEPSEEKAPI secret is unavailable")

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    result: dict[str, Any] = {
        "success": False,
        "provider": "DeepSeek",
        "direct_api": API_URL,
        "credential_present": True,
        "credential_serialized": False,
    }
    failure: BaseException | None = None

    try:
        direct_ids = direct_model_ids()
        result["direct_model_ids"] = direct_ids
        result["direct_model_count"] = len(direct_ids)

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            context = await browser.new_context(viewport={"width": 1440, "height": 1200})
            page = await context.new_page()
            try:
                await login(page)
                await open_providers(page)
                source_id = await add_source(page, DEEPSEEK_SOURCE)
                result["source_id"] = source_id

                await fill_real_secret(page)
                await save_source(page)

                astrbot_ids, selected_id = await fetch_models_through_astrbot(page)
                astrbot_ids = sorted(set(astrbot_ids))
                result["astrbot_model_ids"] = astrbot_ids
                result["astrbot_model_count"] = len(astrbot_ids)
                result["selected_first_model_id"] = selected_id
            finally:
                await browser.close()

        direct_set = set(direct_ids)
        astrbot_set = set(result["astrbot_model_ids"])
        result["missing_from_astrbot"] = sorted(direct_set - astrbot_set)
        result["extra_in_astrbot"] = sorted(astrbot_set - direct_set)
        result["model_sets_equal"] = direct_set == astrbot_set

        if direct_set != astrbot_set:
            raise AssertionError(
                "AstrBot DeepSeek model fetch differs from direct /models: "
                f"missing={result['missing_from_astrbot']!r} "
                f"extra={result['extra_in_astrbot']!r}"
            )

        result["success"] = True
    except BaseException as exc:
        failure = exc
        result["error_type"] = type(exc).__name__
        result["error"] = str(exc)
        result["traceback"] = traceback.format_exc()

    write_json(ARTIFACT_DIR / "result.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    if failure is not None:
        raise failure


if __name__ == "__main__":
    asyncio.run(run())
