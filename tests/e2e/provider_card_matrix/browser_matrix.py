"""Real AstrBot Dashboard provider-card UI matrix.

This test uses the actual AstrBot v4 Dashboard and its normal UI interactions.
It intentionally does not call the Volcengine API; that is the next matrix
layer.  Here the acceptance target is reachability and layout/lifecycle:

Dashboard -> Source create/save -> model create -> model edit/save -> reload.

The test records every case before failing so one broken path cannot hide other
legal paths.  Screenshots and semantic JSON are evidence only, never model
capability truth.
"""

from __future__ import annotations

import asyncio
import json
import os
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from playwright.async_api import Locator, Page, async_playwright, expect

BASE_URL = os.environ.get("ASTRBOT_E2E_URL", "http://127.0.0.1:6185")
USERNAME = os.environ.get("ASTRBOT_E2E_USERNAME", "e2e-admin")
PASSWORD = os.environ.get("ASTRBOT_E2E_PASSWORD", "E2e-password-123")
ARTIFACT_DIR = Path(os.environ.get("ASTRBOT_E2E_ARTIFACT_DIR", "e2e-artifacts")) / "provider-card-matrix"

VIDEO_LABEL = "视频请求通道（当前模型卡）"
TEMP_UI_PREFIX = "_volcengine_video_transport_ui_"
CANONICAL_VIDEO_KEY = "volcengine_video_input_enabled"


@dataclass(frozen=True)
class Case:
    name: str
    template_key: str
    expected_source_id: str
    model_id: str
    owned: bool


CASES = (
    Case(
        name="volcengine_ark",
        template_key="volcengine_ark_chat_completion",
        expected_source_id="volcengine-ark",
        model_id="e2e-ark-model",
        owned=True,
    ),
    Case(
        name="volcengine_agent_plan",
        template_key="volcengine_agent_plan_chat_completion",
        expected_source_id="volcengine-agent-plan",
        model_id="agentplan/e2e-agent-plan-model",
        owned=True,
    ),
    Case(
        name="foreign_openai",
        template_key="openai_chat_completion",
        expected_source_id="openai",
        model_id="e2e-openai-model",
        owned=False,
    ),
)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


async def semantic_page_snapshot(page: Page, path: Path) -> None:
    payload = await page.evaluate(
        """
        () => {
          const visible = (el) => {
            const s = getComputedStyle(el);
            const r = el.getBoundingClientRect();
            return s.display !== 'none' && s.visibility !== 'hidden' && r.width > 0 && r.height > 0;
          };
          const clean = (x) => String(x || '').replace(/\\s+/g, ' ').trim().slice(0, 500);
          const sourceItems = Array.from(document.querySelectorAll('.provider-source-item')).filter(visible);
          const modelRows = Array.from(document.querySelectorAll('.provider-model-row')).filter(visible);
          return {
            href: location.href,
            source_items: sourceItems.map((el) => clean(el.textContent)),
            model_rows: modelRows.map((el) => clean(el.textContent)),
            visible_tabs: Array.from(document.querySelectorAll('.v-tab')).filter(visible).map((el) => clean(el.textContent)),
            provider_sections: Array.from(document.querySelectorAll('.provider-section-title')).filter(visible).map((el) => clean(el.textContent)),
            layout: {
              workbench: document.querySelectorAll('.provider-workbench').length,
              sidebar: document.querySelectorAll('.provider-workbench__sidebar').length,
              main: document.querySelectorAll('.provider-workbench__main').length,
              config_shell: document.querySelectorAll('.provider-config-shell').length,
            },
          };
        }
        """
    )
    write_json(path, payload)


async def visible_config_rows(dialog: Locator) -> list[dict[str, Any]]:
    return await dialog.locator(".config-row").evaluate_all(
        """
        (rows) => rows.map((row) => {
          const style = getComputedStyle(row);
          const rect = row.getBoundingClientRect();
          if (style.display === 'none' || style.visibility === 'hidden' || rect.width <= 0 || rect.height <= 0) return null;
          const key = row.querySelector('.property-key')?.textContent || '';
          const name = row.querySelector('.property-name')?.textContent || '';
          const hint = row.querySelector('.config-hint')?.textContent || '';
          const checkbox = row.querySelector('input[type="checkbox"]');
          return {
            key: String(key).replace(/[()]/g, '').trim(),
            name: String(name).replace(/\\s+/g, ' ').trim(),
            hint: String(hint).replace(/\\s+/g, ' ').trim(),
            bool_value: checkbox ? checkbox.checked : null,
          };
        }).filter(Boolean)
        """
    )


async def login(page: Page) -> None:
    await page.goto(f"{BASE_URL}/#/auth/login", wait_until="networkidle")
    await page.locator('input[autocomplete="username"]').fill(USERNAME)
    await page.locator('input[autocomplete="current-password"]').fill(PASSWORD)
    await page.locator(".login-btn").click()
    await page.wait_for_function(
        "() => !window.location.hash.includes('/auth/login')", timeout=30_000
    )


async def open_providers(page: Page) -> None:
    await page.goto(f"{BASE_URL}/#/providers", wait_until="networkidle")
    await page.locator(".provider-page").wait_for(state="visible", timeout=30_000)
    await page.locator(".provider-workbench").wait_for(state="visible", timeout=30_000)


async def add_source(page: Page, case: Case) -> Locator:
    # The Source menu is the plus button in the Source-panel header.  Its entries
    # are the actual registered provider template keys.
    add_button = page.locator(".provider-sources-controls button:has(.mdi-plus)").first
    await add_button.click()
    menu_item = page.locator(".v-overlay:visible .v-list-item", has_text=case.template_key).first
    await expect(menu_item).to_be_visible(timeout=15_000)
    await menu_item.click()

    title = page.locator(".provider-config-title")
    await expect(title).to_have_text(case.expected_source_id, timeout=15_000)
    return page.locator(".provider-config-shell")


async def save_source(page: Page) -> None:
    save = page.locator(".provider-config-actions button").first
    await expect(save).to_be_enabled(timeout=10_000)
    await save.click()
    await expect(save).to_be_disabled(timeout=20_000)
    await page.wait_for_timeout(500)


async def open_manual_model_add(page: Page, model_id: str) -> Locator:
    manual = page.locator(
        ".provider-models-toolbar__actions button:has(.mdi-pencil-plus)"
    ).first
    await expect(manual).to_be_visible(timeout=10_000)
    await manual.click()

    manual_dialog = page.locator(".v-dialog:visible").last
    await expect(manual_dialog).to_be_visible(timeout=10_000)
    first_input = manual_dialog.locator("input").first
    await first_input.fill(model_id)
    await manual_dialog.locator(".v-card-actions button").last.click()

    config_dialog = page.locator(".v-dialog:visible").last
    await expect(config_dialog.locator(".config-row").first).to_be_visible(timeout=10_000)
    return config_dialog


async def save_model_dialog(dialog: Locator) -> None:
    save = dialog.locator(".v-card-actions button").last
    await save.click()
    await expect(dialog).to_be_hidden(timeout=20_000)


async def open_configured_model(page: Page, model_id: str) -> Locator:
    row = page.locator(".provider-model-row", has_text=model_id).first
    await expect(row).to_be_visible(timeout=15_000)
    await row.locator(".provider-model-row__main").click()
    dialog = page.locator(".v-dialog:visible").last
    await expect(dialog.locator(".config-row").first).to_be_visible(timeout=10_000)
    return dialog


async def video_row(dialog: Locator) -> Locator:
    return dialog.locator(".config-row", has_text=VIDEO_LABEL)


async def set_video_switch(dialog: Locator, enabled: bool) -> bool:
    row = await video_row(dialog)
    if await row.count() != 1:
        return False
    checkbox = row.locator('input[type="checkbox"]').first
    current = await checkbox.is_checked()
    if current != enabled:
        await checkbox.click(force=True)
        await expect(checkbox).to_be_checked(timeout=5_000) if enabled else await expect(checkbox).not_to_be_checked(timeout=5_000)
    return True


async def select_source(page: Page, source_id: str) -> None:
    item = page.locator(".provider-source-item", has_text=source_id).first
    await expect(item).to_be_visible(timeout=15_000)
    await item.click()
    await expect(page.locator(".provider-config-title")).to_have_text(source_id, timeout=10_000)


async def run_case(page: Page, case: Case) -> dict[str, Any]:
    case_dir = ARTIFACT_DIR / case.name
    case_dir.mkdir(parents=True, exist_ok=True)
    result: dict[str, Any] = {
        "case": case.name,
        "template_key": case.template_key,
        "owned": case.owned,
        "stages": {},
        "errors": [],
    }

    try:
        await open_providers(page)
        await add_source(page, case)
        result["stages"]["source_create"] = True
        await page.screenshot(path=str(case_dir / "01-source-created.png"), full_page=True)
        await semantic_page_snapshot(page, case_dir / "01-source-created.dom.json")

        await save_source(page)
        result["stages"]["source_save"] = True
        await page.screenshot(path=str(case_dir / "02-source-saved.png"), full_page=True)

        create_dialog = await open_manual_model_add(page, case.model_id)
        create_rows = await visible_config_rows(create_dialog)
        result["model_create_rows"] = create_rows
        create_video_rows = [row for row in create_rows if VIDEO_LABEL in row["name"]]
        result["model_create_video_control_count"] = len(create_video_rows)
        result["model_create_temp_keys"] = [
            row["key"] for row in create_rows if row["key"].startswith(TEMP_UI_PREFIX)
        ]
        result["model_create_canonical_key_visible"] = any(
            row["key"] == CANONICAL_VIDEO_KEY for row in create_rows
        )
        await page.screenshot(path=str(case_dir / "03-model-create-dialog.png"), full_page=True)
        await save_model_dialog(create_dialog)
        result["stages"]["model_create"] = True

        edit_dialog = await open_configured_model(page, case.model_id)
        edit_rows = await visible_config_rows(edit_dialog)
        result["model_edit_rows_before"] = edit_rows
        edit_video = [row for row in edit_rows if VIDEO_LABEL in row["name"]]
        result["model_edit_video_control_count"] = len(edit_video)
        result["model_edit_temp_keys"] = [
            row["key"] for row in edit_rows if row["key"].startswith(TEMP_UI_PREFIX)
        ]
        result["model_edit_canonical_key_visible"] = any(
            row["key"] == CANONICAL_VIDEO_KEY for row in edit_rows
        )
        await page.screenshot(path=str(case_dir / "04-model-edit-dialog.png"), full_page=True)

        if case.owned:
            toggled = await set_video_switch(edit_dialog, True)
            result["stages"]["video_toggle_available_on_edit"] = toggled
            if not toggled:
                result["errors"].append("owned model edit dialog has no video transport control")
        else:
            if len(edit_video) != 0:
                result["errors"].append("foreign model edit dialog leaked Volcengine video transport control")

        await save_model_dialog(edit_dialog)
        result["stages"]["model_edit_save"] = True

        reopen = await open_configured_model(page, case.model_id)
        reopen_rows = await visible_config_rows(reopen)
        result["model_edit_rows_after_save"] = reopen_rows
        if case.owned:
            row = await video_row(reopen)
            if await row.count() == 1:
                result["video_value_after_save"] = await row.locator('input[type="checkbox"]').first.is_checked()
                if result["video_value_after_save"] is not True:
                    result["errors"].append("video transport value did not survive save/reopen")
            else:
                result["errors"].append("video transport control disappeared after save")
        else:
            if await (await video_row(reopen)).count() != 0:
                result["errors"].append("foreign model gained Volcengine video control after save")
        await reopen.locator(".v-card-actions button").first.click()
        await expect(reopen).to_be_hidden(timeout=10_000)
        result["stages"]["model_reopen_after_save"] = True

        await page.reload(wait_until="networkidle")
        await page.locator(".provider-workbench").wait_for(state="visible", timeout=30_000)
        await select_source(page, case.expected_source_id)
        post_reload = await open_configured_model(page, case.model_id)
        post_reload_rows = await visible_config_rows(post_reload)
        result["model_edit_rows_after_page_reload"] = post_reload_rows
        if case.owned:
            row = await video_row(post_reload)
            if await row.count() == 1:
                result["video_value_after_page_reload"] = await row.locator('input[type="checkbox"]').first.is_checked()
                if result["video_value_after_page_reload"] is not True:
                    result["errors"].append("video transport value did not survive full page reload")
            else:
                result["errors"].append("video transport control missing after full page reload")
        else:
            if await (await video_row(post_reload)).count() != 0:
                result["errors"].append("foreign model leaked Volcengine video control after full reload")
        await page.screenshot(path=str(case_dir / "05-after-page-reload.png"), full_page=True)
        await post_reload.locator(".v-card-actions button").first.click()
        result["stages"]["page_reload_reopen"] = True

        # UI layout expectations.  New-card visibility is intentionally asserted:
        # users should not need a hidden create-then-edit detour to reach the same
        # per-model-card transport setting.
        if case.owned:
            if result["model_create_video_control_count"] != 1:
                result["errors"].append(
                    "owned model create dialog does not expose exactly one video transport control"
                )
            if result["model_edit_video_control_count"] != 1:
                result["errors"].append(
                    "owned model edit dialog does not expose exactly one video transport control"
                )
        else:
            if result["model_create_video_control_count"] != 0:
                result["errors"].append(
                    "foreign model create dialog leaked Volcengine video transport control"
                )

        result["success"] = not result["errors"]
    except Exception as exc:
        result["success"] = False
        result["errors"].append(f"{type(exc).__name__}: {exc}")
        result["traceback"] = traceback.format_exc()[-12000:]
        try:
            await page.screenshot(path=str(case_dir / "99-failure.png"), full_page=True)
            await semantic_page_snapshot(page, case_dir / "99-failure.dom.json")
        except Exception as capture_error:
            result["capture_error"] = str(capture_error)

    write_json(case_dir / "result.json", result)
    return result


async def main() -> None:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    console_events: list[dict[str, str]] = []
    page_errors: list[str] = []
    results: list[dict[str, Any]] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(viewport={"width": 1440, "height": 1200})
        page = await context.new_page()
        page.on(
            "console",
            lambda msg: console_events.append({"type": msg.type, "text": msg.text[:2000]}),
        )
        page.on("pageerror", lambda exc: page_errors.append(str(exc)[:4000]))

        await login(page)
        for case in CASES:
            results.append(await run_case(page, case))

        await browser.close()

    summary = {
        "schema_version": 1,
        "cases": results,
        "all_passed": all(case.get("success") for case in results),
        "failed_cases": [case["case"] for case in results if not case.get("success")],
    }
    write_json(ARTIFACT_DIR / "matrix-result.json", summary)
    write_json(ARTIFACT_DIR / "browser-console.json", console_events)
    write_json(ARTIFACT_DIR / "browser-page-errors.json", page_errors)
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))

    if not summary["all_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
