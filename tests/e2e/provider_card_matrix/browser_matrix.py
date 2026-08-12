"""Real AstrBot Dashboard provider-card UI matrix.

This test uses AstrBot's actual v4 Dashboard and normal user interactions.
It intentionally does not call the Volcengine API; the next E2E layer does.
The acceptance target here is reachability and UI/config lifecycle:

Dashboard -> Source create/save -> model create -> model edit/save -> reload.

Every case is recorded before the test fails so one broken path cannot hide
other legal paths. Screenshots and semantic JSON are evidence only, never model
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
ARTIFACT_DIR = (
    Path(os.environ.get("ASTRBOT_E2E_ARTIFACT_DIR", "e2e-artifacts"))
    / "provider-card-matrix"
)

# Deliberately not a real credential. The UI-only matrix only needs Provider
# construction to succeed; it never presses connection-test/fetch-models.
DUMMY_API_KEY = "e2e-dummy-key"

LEGACY_MODEL_VIDEO_LABEL = "视频请求通道（当前模型卡）"
SOURCE_VIDEO_MASTER_LABEL = "显示逐模型视频选项"
SOURCE_VIDEO_SELECTOR_LABEL = "启用视频请求通道的模型"
TEMP_UI_PREFIX = "_volcengine_video_transport_ui_"
SOURCE_SELECTOR_PREFIX = "_volcengine_video_models_ui_"
CANONICAL_VIDEO_KEY = "volcengine_video_input_enabled"
SOURCE_HINT_MARKER = "视频请求通道是当前火山 Source 内的逐模型请求转发设置"


@dataclass(frozen=True)
class Case:
    name: str
    template_key: str
    menu_label: str
    expected_source_id: str | None
    model_id: str
    owned: bool


CASES = (
    Case(
        name="volcengine_ark",
        template_key="volcengine_ark_chat_completion",
        menu_label="volcengine_ark_chat_completion",
        expected_source_id="volcengine-ark",
        model_id="e2e-ark-model",
        owned=True,
    ),
    Case(
        name="volcengine_agent_plan",
        template_key="volcengine_agent_plan_chat_completion",
        menu_label="volcengine_agent_plan_chat_completion",
        expected_source_id="volcengine-agent-plan",
        model_id="agentplan/e2e-agent-plan-model",
        owned=True,
    ),
    Case(
        name="foreign_openai",
        template_key="openai_chat_completion",
        menu_label="OpenAI Compatible",
        expected_source_id=None,
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
            visible_dialog_titles: Array.from(document.querySelectorAll('.v-dialog .v-card-title')).filter(visible).map((el) => clean(el.textContent)),
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


def canonical_raw_field_visible(rows: list[dict[str, Any]]) -> bool:
    """Detect fallback rendering of the hidden canonical config key."""

    return any(
        row.get("key") == CANONICAL_VIDEO_KEY
        or row.get("name") == CANONICAL_VIDEO_KEY
        or row.get("name", "").startswith(f"{CANONICAL_VIDEO_KEY} ")
        for row in rows
    )


async def source_transport_hint_visible(page: Page, *, wait: bool) -> bool:
    locator = page.locator(
        ".provider-config-shell .v-alert", has_text=SOURCE_HINT_MARKER
    ).first
    if wait:
        try:
            await expect(locator).to_be_visible(timeout=5_000)
        except Exception:
            return False
    return await locator.is_visible()


async def login(page: Page) -> None:
    await page.goto(f"{BASE_URL}/#/auth/login", wait_until="networkidle")
    await page.locator('input[autocomplete="username"]').fill(USERNAME)
    await page.locator('input[autocomplete="current-password"]').fill(PASSWORD)
    await page.locator(".login-btn").click()
    await page.wait_for_function(
        "() => !window.location.hash.includes('/auth/login')", timeout=30_000
    )


async def dismiss_first_run_dialog(page: Page, *, wait_ms: int = 0) -> bool:
    if wait_ms:
        await page.wait_for_timeout(wait_ms)
    dialog = page.locator(".v-dialog:visible", has_text="首次提示").first
    if await dialog.count() == 0:
        return False
    try:
        await expect(dialog).to_be_visible(timeout=2_000)
    except AssertionError:
        return False
    close = dialog.get_by_role("button", name="关闭").last
    if await close.count() == 0:
        close = dialog.locator("button").first
    await close.click()
    await expect(dialog).to_be_hidden(timeout=10_000)
    return True


async def open_providers(page: Page) -> None:
    await page.goto(f"{BASE_URL}/#/providers", wait_until="domcontentloaded")
    await page.locator(".provider-page").wait_for(state="visible", timeout=30_000)
    await page.locator(".provider-workbench").wait_for(state="visible", timeout=30_000)
    await dismiss_first_run_dialog(page, wait_ms=300)


async def add_source(page: Page, case: Case) -> str:
    add_button = page.locator(".provider-sources-controls button:has(.mdi-plus)").first
    await expect(add_button).to_be_visible(timeout=10_000)
    await add_button.click()

    # On a fresh AstrBot profile the first-run notice may mount *after* the
    # Source menu opens. Give that native dialog a bounded chance to appear;
    # if it does, dismiss it and reopen the Source menu. This keeps a host
    # onboarding overlay from being misclassified as a provider-card failure.
    await page.wait_for_timeout(1_200)
    await dismiss_first_run_dialog(page)

    menu_item = page.locator(
        ".v-overlay:visible .v-list-item", has_text=case.menu_label
    ).first
    # Closing the delayed first-run dialog does not necessarily close the
    # already-open Source menu. Reopen only when the target item is actually
    # absent; otherwise a second click on the plus button fights the menu
    # overlay and creates a false UI failure.
    if not await menu_item.is_visible():
        await add_button.click()
    await expect(menu_item).to_be_visible(timeout=15_000)
    await menu_item.click()

    title = page.locator(".provider-config-title")
    await expect(title).to_be_visible(timeout=15_000)
    actual_source_id = (await title.inner_text()).strip()
    if (
        case.expected_source_id is not None
        and actual_source_id != case.expected_source_id
    ):
        raise AssertionError(
            f"{case.name}: expected Source id {case.expected_source_id!r}, got {actual_source_id!r}"
        )
    return actual_source_id


async def fill_dummy_source_key(page: Page) -> None:
    rows = page.locator(".provider-config-shell .config-row")
    key_row: Locator | None = None
    for index in range(await rows.count()):
        row = rows.nth(index)
        key_marker = row.locator(".property-key")
        key_text = ""
        if await key_marker.count():
            key_text = (
                (await key_marker.first.inner_text())
                .replace("(", "")
                .replace(")", "")
                .strip()
            )
        if key_text == "key":
            key_row = row
            break

    if key_row is None:
        candidate = page.locator(
            ".provider-config-shell .config-row", has_text="API Key"
        ).first
        if await candidate.count() == 0:
            raise AssertionError("Source UI has no API Key row")
        key_row = candidate

    key_input = key_row.locator("input").first
    await expect(key_input).to_be_visible(timeout=10_000)
    await key_input.fill(DUMMY_API_KEY)


async def save_source(page: Page) -> None:
    # The first-run notice is mounted asynchronously on a fresh AstrBot profile
    # and can appear after Source creation, so dismiss it immediately before the
    # first destructive click rather than assuming it existed on page entry.
    await dismiss_first_run_dialog(page, wait_ms=900)
    save = page.locator(".provider-config-actions button").first
    await expect(save).to_be_enabled(timeout=10_000)
    await save.click()
    await expect(save).to_be_disabled(timeout=20_000)
    await page.wait_for_timeout(700)


async def open_manual_model_add(page: Page, model_id: str) -> Locator:
    manual = page.locator(
        ".provider-models-toolbar__actions button:has(.mdi-pencil-plus)"
    ).first
    await expect(manual).to_be_visible(timeout=10_000)
    await manual.click()

    manual_dialog = page.locator(".v-dialog:visible").last
    await expect(manual_dialog).to_be_visible(timeout=10_000)
    await manual_dialog.locator("input").first.fill(model_id)
    await manual_dialog.locator(".v-card-actions button").last.click()

    config_dialog = page.locator(".v-dialog:visible").last
    await expect(config_dialog.locator(".config-row").first).to_be_visible(
        timeout=10_000
    )
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


def video_row(dialog: Locator) -> Locator:
    return dialog.locator(".config-row", has_text=LEGACY_MODEL_VIDEO_LABEL)


async def set_video_switch(dialog: Locator, enabled: bool) -> bool:
    row = video_row(dialog)
    if await row.count() != 1:
        return False
    checkbox = row.locator('input[type="checkbox"]').first
    await checkbox.set_checked(enabled, force=True)
    if enabled:
        await expect(checkbox).to_be_checked(timeout=5_000)
    else:
        await expect(checkbox).not_to_be_checked(timeout=5_000)
    return True


def source_video_master_row(page: Page) -> Locator:
    return page.locator(
        ".provider-config-shell .config-row", has_text=SOURCE_VIDEO_MASTER_LABEL
    )


def source_video_selector_row(page: Page) -> Locator:
    return page.locator(
        ".provider-config-shell .config-row", has_text=SOURCE_VIDEO_SELECTOR_LABEL
    )


async def set_source_video_master(page: Page, enabled: bool) -> None:
    row = source_video_master_row(page)
    await expect(row).to_be_visible(timeout=10_000)
    checkbox = row.locator('input[type="checkbox"]').first
    await checkbox.set_checked(enabled, force=True)
    if enabled:
        await expect(checkbox).to_be_checked(timeout=5_000)
    else:
        await expect(checkbox).not_to_be_checked(timeout=5_000)


async def select_source(page: Page, source_id: str) -> None:
    item = page.locator(".provider-source-item", has_text=source_id).first
    await expect(item).to_be_visible(timeout=15_000)
    await item.click()
    await expect(page.locator(".provider-config-title")).to_have_text(
        source_id, timeout=10_000
    )


async def cancel_visible_dialogs(page: Page) -> None:
    for _ in range(4):
        dialog = page.locator(".v-dialog:visible").last
        if await dialog.count() == 0:
            return
        cancel = dialog.locator(".v-card-actions button").first
        try:
            if await cancel.count() and await cancel.is_visible():
                await cancel.click()
                await page.wait_for_timeout(150)
                continue
        except Exception:
            pass
        try:
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(150)
        except Exception:
            return


async def run_case(page: Page, case: Case) -> dict[str, Any]:
    case_dir = ARTIFACT_DIR / case.name
    case_dir.mkdir(parents=True, exist_ok=True)
    result: dict[str, Any] = {
        "case": case.name,
        "template_key": case.template_key,
        "menu_label": case.menu_label,
        "owned": case.owned,
        "stages": {},
        "errors": [],
    }

    try:
        await open_providers(page)
        actual_source_id = await add_source(page, case)
        result["actual_source_id"] = actual_source_id
        result["stages"]["source_create"] = True

        await fill_dummy_source_key(page)
        result["stages"]["dummy_key_entered"] = True
        result["source_master_count_on_create"] = await source_video_master_row(
            page
        ).count()
        result["source_selector_count_before_models"] = await source_video_selector_row(
            page
        ).count()
        expected_master_count = 1 if case.owned else 0
        if result["source_master_count_on_create"] != expected_master_count:
            result["errors"].append(
                "Source video visibility master ownership/count is incorrect"
            )
        if result["source_selector_count_before_models"] != 0:
            result["errors"].append(
                "Source video model selector appeared before any model card exists"
            )
        await page.screenshot(
            path=str(case_dir / "01-source-created.png"), full_page=True
        )
        await semantic_page_snapshot(page, case_dir / "01-source-created.dom.json")

        await save_source(page)
        result["stages"]["source_save"] = True
        result["source_transport_hint_visible"] = await source_transport_hint_visible(
            page, wait=case.owned
        )
        if not case.owned and result["source_transport_hint_visible"]:
            result["errors"].append(
                "foreign Source leaked Volcengine transport guidance"
            )
        await page.screenshot(
            path=str(case_dir / "02-source-saved.png"), full_page=True
        )

        create_dialog = await open_manual_model_add(page, case.model_id)
        create_rows = await visible_config_rows(create_dialog)
        result["model_create_rows"] = create_rows
        result["model_create_video_control_count"] = len(
            [row for row in create_rows if LEGACY_MODEL_VIDEO_LABEL in row["name"]]
        )
        result["model_create_temp_keys"] = [
            row["key"]
            for row in create_rows
            if row["key"].startswith((TEMP_UI_PREFIX, SOURCE_SELECTOR_PREFIX))
        ]
        result["model_create_canonical_raw_field_visible"] = (
            canonical_raw_field_visible(create_rows)
        )
        if (
            result["model_create_video_control_count"]
            or result["model_create_temp_keys"]
            or result["model_create_canonical_raw_field_visible"]
        ):
            result["errors"].append(
                "generic model-create dialog exposes retired/raw Volcengine video UI"
            )
        await page.screenshot(
            path=str(case_dir / "03-model-create-dialog.png"), full_page=True
        )
        await save_model_dialog(create_dialog)
        result["stages"]["model_create"] = True

        # Model creation reloads Provider schema. Select the current Source again
        # so its concrete per-Source checkbox list is the live form object.
        await page.locator(".provider-workbench").wait_for(
            state="visible", timeout=20_000
        )
        await select_source(page, actual_source_id)

        if case.owned:
            if await source_video_master_row(page).count() != 1:
                result["errors"].append(
                    "owned Source lost its video visibility master after model create"
                )
            await set_source_video_master(page, True)
            selector = source_video_selector_row(page)
            await expect(selector).to_be_visible(timeout=10_000)
            model_checks = selector.locator('input[type="checkbox"]')
            result["source_selector_checkbox_count"] = await model_checks.count()
            if result["source_selector_checkbox_count"] != 1:
                result["errors"].append(
                    "owned Source selector does not contain exactly its one model card"
                )
            else:
                await model_checks.first.set_checked(True, force=True)
                await expect(model_checks.first).to_be_checked(timeout=5_000)
            result["stages"]["source_video_selected"] = True
            await save_source(page)

            # Closing is presentation-only: the checkbox row disappears, then a
            # save/reload/reopen must recover the previous checked value.
            await select_source(page, actual_source_id)
            await set_source_video_master(page, False)
            await expect(source_video_selector_row(page)).to_have_count(
                0, timeout=5_000
            )
            result["stages"]["source_video_selector_hidden"] = True
            await save_source(page)
        else:
            if await source_video_master_row(page).count() != 0:
                result["errors"].append(
                    "foreign Source exposes Volcengine video visibility master"
                )
            if await source_video_selector_row(page).count() != 0:
                result["errors"].append(
                    "foreign Source exposes Volcengine video model selector"
                )

        edit_dialog = await open_configured_model(page, case.model_id)
        edit_rows = await visible_config_rows(edit_dialog)
        result["model_edit_rows_before"] = edit_rows
        edit_video = [
            row for row in edit_rows if LEGACY_MODEL_VIDEO_LABEL in row["name"]
        ]
        result["model_edit_video_control_count"] = len(edit_video)
        result["model_edit_temp_keys"] = [
            row["key"]
            for row in edit_rows
            if row["key"].startswith((TEMP_UI_PREFIX, SOURCE_SELECTOR_PREFIX))
        ]
        result["model_edit_canonical_raw_field_visible"] = canonical_raw_field_visible(
            edit_rows
        )
        await page.screenshot(
            path=str(case_dir / "04-model-edit-dialog.png"), full_page=True
        )
        if (
            edit_video
            or result["model_edit_temp_keys"]
            or result["model_edit_canonical_raw_field_visible"]
        ):
            result["errors"].append(
                "generic model-edit dialog exposes retired/raw Volcengine video UI"
            )
        await edit_dialog.locator(".v-card-actions button").first.click()
        await expect(edit_dialog).to_be_hidden(timeout=10_000)

        # Network-idle is not a valid reload completion criterion for the real
        # Dashboard because background requests may stay active.  The actual UI
        # shell is the completion signal we care about.
        await page.reload(wait_until="domcontentloaded", timeout=30_000)
        await page.locator(".provider-workbench").wait_for(
            state="visible", timeout=30_000
        )
        await dismiss_first_run_dialog(page, wait_ms=300)
        await select_source(page, actual_source_id)
        if case.owned:
            master = source_video_master_row(page)
            await expect(master).to_be_visible(timeout=10_000)
            result["master_after_reload"] = await master.locator(
                'input[type="checkbox"]'
            ).first.is_checked()
            if result["master_after_reload"] is not False:
                result["errors"].append(
                    "closed Source visibility master did not persist"
                )
            if await source_video_selector_row(page).count() != 0:
                result["errors"].append("closed Source selector is still visible")

            await set_source_video_master(page, True)
            reopened_selector = source_video_selector_row(page)
            await expect(reopened_selector).to_be_visible(timeout=10_000)
            reopened_checks = reopened_selector.locator('input[type="checkbox"]')
            if await reopened_checks.count() != 1:
                result["errors"].append(
                    "reopened Source selector lost its model-card identity"
                )
            else:
                result[
                    "video_value_after_hide_reopen"
                ] = await reopened_checks.first.is_checked()
                if result["video_value_after_hide_reopen"] is not True:
                    result["errors"].append(
                        "per-model video selection was lost while selector was hidden"
                    )
            await save_source(page)
        else:
            if (
                await source_video_master_row(page).count()
                or await source_video_selector_row(page).count()
            ):
                result["errors"].append(
                    "foreign Source gained Volcengine video controls after reload"
                )
        await page.screenshot(
            path=str(case_dir / "05-after-page-reload.png"), full_page=True
        )
        result["stages"]["page_reload_reopen"] = True

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
    finally:
        await cancel_visible_dialogs(page)

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
            lambda msg: console_events.append(
                {"type": msg.type, "text": msg.text[:2000]}
            ),
        )
        page.on("pageerror", lambda exc: page_errors.append(str(exc)[:4000]))

        await login(page)
        await open_providers(page)
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
