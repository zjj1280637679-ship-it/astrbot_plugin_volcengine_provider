"""Real AstrBot Dashboard foreign-model-card isolation matrix for 0.1.24.

This matrix is deliberately separate from the same-endpoint OpenAI@Ark differential.
That differential proves that an Ark URL/key/model does not make a foreign Source
owned.  This matrix proves two additional concrete foreign Source instances named
in the product contract: AstrBot's xAI template and Google Gemini template.

No xAI or Gemini remote API is called.  Each Source receives only a dummy key and
a manually entered model ID.  The objects under test are the unsaved new model-card
form object, the saved/reopened model-card form object, and the persisted provider
config.  In every state the foreign card must retain its host capability surface
without a plugin ``video`` option and must contain no lower Volcengine-only rows.
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any

from playwright.async_api import Locator, Page, async_playwright, expect

from browser_matrix import (
    BASE_URL,
    PASSWORD,
    USERNAME,
    Case,
    add_source,
    cancel_visible_dialogs,
    fill_dummy_source_key,
    login,
    open_configured_model,
    open_manual_model_add,
    open_providers,
    save_model_dialog,
    save_source,
    visible_config_rows,
)

PLUGIN_PREFIX = "volcengine_"
ARTIFACT_DIR = (
    Path(os.environ.get("ASTRBOT_E2E_ARTIFACT_DIR", "e2e-artifacts"))
    / "foreign-scope-0.1.24"
)
CONFIG_PATH = Path(
    os.environ.get("ASTRBOT_E2E_CONFIG_PATH", "AstrBot/data/cmd_config.json")
)

CASES = (
    Case(
        name="foreign_xai",
        template_key="openai_responses",
        menu_label="xAI",
        expected_source_id=None,
        model_id="e2e-xai-foreign-model",
        owned=False,
    ),
    Case(
        name="foreign_gemini",
        template_key="googlegenai_chat_completion",
        menu_label="Google Gemini",
        expected_source_id=None,
        model_id="e2e-gemini-foreign-model",
        owned=False,
    ),
)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


async def row_for_key(scope: Locator, key: str) -> Locator:
    rows = scope.locator(".config-row")
    for index in range(await rows.count()):
        row = rows.nth(index)
        marker = row.locator(".property-key")
        if not await marker.count():
            continue
        raw = await marker.first.text_content()
        actual = str(raw or "").replace("(", "").replace(")", "").strip()
        if actual == key:
            return row
    raise AssertionError(f"no config row for key={key!r}")


async def modality_values(dialog: Locator) -> list[dict[str, Any]]:
    row = await row_for_key(dialog, "modalities")
    return await row.evaluate(
        """
        (row) => Array.from(row.querySelectorAll('input[type="checkbox"]')).map((input) => {
          const labels = Array.from(row.querySelectorAll('label'));
          const direct = input.id ? labels.find((label) => label.htmlFor === input.id) : null;
          const control = input.closest('.v-selection-control');
          return {
            value: String(input.value || ''),
            label: String(direct?.textContent || control?.textContent || '').replace(/\s+/g, ' ').trim(),
            checked: Boolean(input.checked),
          };
        })
        """
    )


async def assert_foreign_dialog(dialog: Locator, *, stage: str) -> dict[str, Any]:
    rows = await visible_config_rows(dialog)
    options = await modality_values(dialog)
    plugin_rows = [
        row for row in rows if str(row.get("key") or "").startswith(PLUGIN_PREFIX)
    ]
    video_options = [item for item in options if item.get("value") == "video"]
    if video_options:
        raise AssertionError(
            f"{stage}: foreign model-card native modalities leaked plugin Video: "
            f"{video_options!r}; all={options!r}"
        )
    if plugin_rows:
        raise AssertionError(
            f"{stage}: foreign model-card lower UI leaked Volcengine rows: "
            f"{plugin_rows!r}"
        )
    return {"modalities": options, "rows": rows}


def persisted_provider(source_id: str, model_id: str) -> dict[str, Any]:
    data = json.loads(CONFIG_PATH.read_text(encoding="utf-8-sig"))
    provider_id = f"{source_id}/{model_id}"
    provider = next(
        (
            item
            for item in data.get("provider", [])
            if isinstance(item, dict) and str(item.get("id") or "") == provider_id
        ),
        None,
    )
    if not isinstance(provider, dict):
        raise AssertionError(f"persisted foreign provider missing: {provider_id}")
    source = next(
        (
            item
            for item in data.get("provider_sources", [])
            if isinstance(item, dict) and str(item.get("id") or "") == source_id
        ),
        {},
    )
    return {"source_type": source.get("type"), "provider": provider}


async def run_case(page: Page, case: Case) -> dict[str, Any]:
    result: dict[str, Any] = {"case": case.name, "success": False}
    try:
        await open_providers(page)
        source_id = await add_source(page, case)
        result["source_id"] = source_id
        await fill_dummy_source_key(page)
        await save_source(page)

        create_dialog = await open_manual_model_add(page, case.model_id)
        result["create"] = await assert_foreign_dialog(
            create_dialog, stage=f"{case.name}/unsaved-create"
        )
        await save_model_dialog(create_dialog)

        edit_dialog = await open_configured_model(page, case.model_id)
        result["edit"] = await assert_foreign_dialog(
            edit_dialog, stage=f"{case.name}/saved-reopen"
        )
        await edit_dialog.locator(".v-card-actions button").first.click()
        await expect(edit_dialog).to_be_hidden(timeout=10_000)

        persisted = persisted_provider(source_id, case.model_id)
        result["source_type"] = persisted["source_type"]
        provider = persisted["provider"]
        persisted_plugin_keys = sorted(
            key for key in provider if str(key).startswith(PLUGIN_PREFIX)
        )
        if "video" in (provider.get("modalities") or []):
            raise AssertionError(
                f"{case.name}: foreign persisted modalities contain video: "
                f"{provider.get('modalities')!r}"
            )
        if persisted_plugin_keys:
            raise AssertionError(
                f"{case.name}: foreign persisted provider contains plugin keys: "
                f"{persisted_plugin_keys}"
            )
        result["persisted_modalities"] = provider.get("modalities")
        result["persisted_plugin_keys"] = persisted_plugin_keys
        result["success"] = True
    finally:
        await cancel_visible_dialogs(page)
    return result


async def main() -> None:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(viewport={"width": 1440, "height": 1200})
        page = await context.new_page()
        await login(page)
        await open_providers(page)
        for case in CASES:
            try:
                results.append(await run_case(page, case))
            except Exception as exc:
                results.append(
                    {
                        "case": case.name,
                        "success": False,
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )

        await browser.close()

    summary = {
        "schema_version": 1,
        "purpose": "xai_gemini_foreign_model_card_ui_and_persistence_isolation",
        "cases": results,
        "all_passed": all(item.get("success") for item in results),
    }
    write_json(ARTIFACT_DIR / "matrix-result.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    if not summary["all_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
