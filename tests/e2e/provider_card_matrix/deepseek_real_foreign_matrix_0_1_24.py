"""Real DeepSeek foreign-provider differential for the 0.1.24 Video contract.

This is deliberately stronger than a dummy-key UI isolation test and deliberately
has no predeclared DeepSeek model identifier:

1. Create AstrBot 4.27.3's native ``DeepSeek`` Source (provider=deepseek,
   type=openai_chat_completion).
2. Store ``$DEEPSEEKAPI`` in the Source key field so the real secret stays in
   the process environment and never enters screenshots/artifacts.
3. Discover the live model identifiers with the workflow's direct preflight
   call (same secret, same ``/models`` endpoint) and select the first one. The
   AstrBot source-page "fetch model list" preview is deliberately not used
   here: on v4.27.3 that endpoint builds a temporary Provider from the
   persisted source config without resolving ``$VAR`` key references, so the
   literal ``$DEEPSEEKAPI`` would be sent upstream (401). The selected model
   card is instead added through AstrBot's own custom-model dialog, and the
   real remote request through AstrBot is still asserted with the provider
   test button, whose loaded instance does resolve the environment reference.
4. Prove that neither the unsaved nor saved/reopened foreign card receives
   ``video`` or any ``volcengine_*`` model field.
5. Use AstrBot's own provider test endpoint for that same live model and
   require a real DeepSeek request to pass.
6. Check persisted config semantics using the live model ID, without ever
   serializing the secret value.

A successful remote request cannot substitute for UI isolation, and UI
isolation cannot substitute for the successful remote request; both are hard
assertions in this test.
"""

from __future__ import annotations

import asyncio
import json
import os
import traceback
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from playwright.async_api import Locator, Page, async_playwright, expect

from browser_matrix import (
    BASE_URL,
    PASSWORD,
    USERNAME,
    add_source,
    dismiss_first_run_dialog,
    login,
    open_configured_model,
    open_manual_model_add,
    open_providers,
    save_model_dialog,
    save_source,
    select_source,
    semantic_page_snapshot,
    visible_config_rows,
)

# This object describes only the Source template.  It intentionally has no
# model_id attribute: a model identifier does not exist for this test until
# AstrBot has fetched one from the live DeepSeek Source.
DEEPSEEK_SOURCE = SimpleNamespace(
    name="foreign_deepseek_real",
    template_key="DeepSeek",
    menu_label="DeepSeek",
    expected_source_id="deepseek",
    owned=False,
)

PLUGIN_KEYS = {
    "volcengine_video_input_enabled",
    "volcengine_video_input_profile",
    "volcengine_reasoning_mode",
    "volcengine_reasoning_effort",
    "volcengine_temperature",
    "volcengine_top_p",
    "volcengine_max_output_tokens",
    "volcengine_stop_sequences",
    "volcengine_frequency_penalty",
    "volcengine_presence_penalty",
}
ENV_REFERENCE = "$DEEPSEEKAPI"
ARTIFACT_DIR = (
    Path(os.environ.get("ASTRBOT_E2E_ARTIFACT_DIR", "e2e-artifacts"))
    / "deepseek-real-foreign-0.1.24"
)
CONFIG_PATH = Path(
    os.environ.get("ASTRBOT_E2E_CONFIG_PATH", "AstrBot/data/cmd_config.json")
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


async def fill_key_with_environment_reference(page: Page) -> None:
    shell = page.locator(".provider-config-shell")
    row = await row_for_key(shell, "key")
    key_input = row.locator("input").first
    await expect(key_input).to_be_visible(timeout=10_000)
    await key_input.fill(ENV_REFERENCE)
    if await key_input.input_value() != ENV_REFERENCE:
        raise AssertionError("DeepSeek Source key field did not retain the env reference")


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
            label: String(direct?.textContent || control?.textContent || '').replace(/\\s+/g, ' ').trim(),
            checked: Boolean(input.checked),
          };
        })
        """
    )


async def assert_foreign_model_dialog(dialog: Locator, *, stage: str) -> dict[str, Any]:
    modalities = await modality_values(dialog)
    if any(item.get("value") == "video" for item in modalities):
        raise AssertionError(f"{stage}: DeepSeek foreign card leaked Video: {modalities!r}")

    rows = await visible_config_rows(dialog)
    leaked_rows = sorted(
        {
            str(row.get("key") or "")
            for row in rows
            if str(row.get("key") or "") in PLUGIN_KEYS
            or str(row.get("key") or "").startswith("volcengine_")
        }
    )
    if leaked_rows:
        raise AssertionError(
            f"{stage}: DeepSeek foreign card leaked Volcengine rows: {leaked_rows!r}"
        )

    return {
        "modalities": modalities,
        "visible_volcengine_keys": leaked_rows,
    }


async def close_validated_dialog(page: Page, dialog: Locator, *, stage: str) -> None:
    for _ in range(5):
        if not await dialog.is_visible():
            return
        await page.keyboard.press("Escape")
        try:
            await expect(dialog).to_be_hidden(timeout=2_000)
            return
        except AssertionError:
            await page.wait_for_timeout(100)
    raise AssertionError(f"{stage}: validated DeepSeek dialog could not be dismissed")


def load_live_model_ids() -> tuple[list[str], str]:
    """Return (all live IDs, selected live ID) from the workflow preflight.

    The workflow's direct authenticated ``/models`` call writes only the model
    identifiers to ``raw-secret-model-list.json``; the raw secret never enters
    this test process or the browser. No model identifier is hard-coded here:
    the selected ID is derived solely from the live upstream response order.
    """

    list_path = ARTIFACT_DIR / "raw-secret-model-list.json"
    if not list_path.is_file():
        raise AssertionError(
            "workflow preflight did not produce raw-secret-model-list.json; "
            "the direct DeepSeek /models discovery step must run before this test"
        )
    payload = json.loads(list_path.read_text(encoding="utf-8"))
    model_ids = payload.get("model_ids") if isinstance(payload, dict) else None
    if not isinstance(model_ids, list):
        raise AssertionError("raw-secret-model-list.json has no model_ids list")
    models = [str(value).strip() for value in model_ids if str(value).strip()]
    if not models:
        raise AssertionError("the direct DeepSeek /models response contained no model IDs")
    return models, models[0]


async def test_model_through_astrbot(
    page: Page, *, source_id: str, model_id: str
) -> str:
    provider_id = f"{source_id}/{model_id}"
    row = page.locator(".provider-model-row", has_text=provider_id).first
    if not await row.count():
        row = page.locator(".provider-model-row", has_text=model_id).first
    await expect(row).to_be_visible(timeout=15_000)

    test_button = row.locator("button:has(.mdi-connection)").first
    await expect(test_button).to_be_visible(timeout=10_000)
    await expect(test_button).to_be_enabled(timeout=10_000)
    await test_button.click()

    success = page.locator(".v-snackbar:visible", has_text="测试通过").last
    await expect(success).to_be_visible(timeout=60_000)
    text = str(await success.inner_text() or "").replace("\n", " ").strip()
    if "测试通过" not in text:
        raise AssertionError(f"DeepSeek provider test did not report success: {text!r}")
    return text


def persisted_evidence(source_id: str, model_id: str) -> dict[str, Any]:
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
    provider_id = f"{source_id}/{model_id}"
    model = providers.get(provider_id)
    if not isinstance(source, dict):
        raise AssertionError(f"persisted DeepSeek Source missing: {source_id!r}")
    if not isinstance(model, dict):
        raise AssertionError(f"persisted DeepSeek model card missing: {provider_id!r}")

    if source.get("type") != "openai_chat_completion":
        raise AssertionError(f"DeepSeek Source type changed unexpectedly: {source.get('type')!r}")
    if source.get("provider") != "deepseek":
        raise AssertionError(f"DeepSeek Source provider changed unexpectedly: {source.get('provider')!r}")
    if source.get("key") != ENV_REFERENCE:
        raise AssertionError("DeepSeek Source did not persist the safe environment reference")

    model_modalities = model.get("modalities") or []
    leaked_keys = sorted(key for key in model if str(key).startswith("volcengine_"))
    if "video" in model_modalities:
        raise AssertionError(f"persisted DeepSeek model gained video: {model_modalities!r}")
    if leaked_keys:
        raise AssertionError(f"persisted DeepSeek model gained plugin keys: {leaked_keys!r}")

    return {
        "source_id": source_id,
        "source_type": source.get("type"),
        "source_provider": source.get("provider"),
        "source_api_base": source.get("api_base"),
        "source_key_is_environment_reference": source.get("key") == ENV_REFERENCE,
        "selected_model_id_from_live_discovery": model_id,
        "persisted_provider_id": provider_id,
        "model_modalities": model_modalities,
        "model_volcengine_keys": leaked_keys,
    }


async def run() -> None:
    if not os.environ.get("DEEPSEEKAPI"):
        raise AssertionError("DEEPSEEKAPI environment secret is unavailable")

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    result: dict[str, Any] = {"success": False, "provider": "DeepSeek"}
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
            result["source_api_base_before_save"] = str(
                await page.locator(".provider-config-subtitle").inner_text() or ""
            ).strip()
            await save_source(page)

            models, selected_model_id = load_live_model_ids()
            result["deepseek_live_models"] = models
            result["selected_model_id_from_live_discovery"] = selected_model_id
            result["selected_model_origin"] = (
                "workflow direct DeepSeek /models preflight; model card added "
                "through AstrBot's custom-model dialog"
            )

            create_dialog = await open_manual_model_add(page, selected_model_id)
            result["unsaved_model_card"] = await assert_foreign_model_dialog(
                create_dialog,
                stage="deepseek/unsaved-live-model-card",
            )
            await save_model_dialog(create_dialog)

            await page.locator(".provider-workbench").wait_for(state="visible", timeout=20_000)
            await select_source(page, source_id)
            edit_dialog = await open_configured_model(page, selected_model_id)
            result["saved_reopened_model_card"] = await assert_foreign_model_dialog(
                edit_dialog,
                stage="deepseek/saved-reopened-model-card",
            )
            await close_validated_dialog(
                page,
                edit_dialog,
                stage="deepseek/saved-reopened-close",
            )

            result["persisted"] = persisted_evidence(source_id, selected_model_id)
            result["astrbot_provider_test_message"] = await test_model_through_astrbot(
                page,
                source_id=source_id,
                model_id=selected_model_id,
            )
            result["real_remote_request_via_astrbot"] = True
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
