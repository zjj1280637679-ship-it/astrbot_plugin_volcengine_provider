"""Real AstrBot 4.27.2 Dashboard evidence for 0.1.19 model-card fields.

This browser matrix deliberately keeps the released 0.1.18 Source UI contract
intact while proving that configured Volcengine model edit dialogs gain the new
bilingual horizontal rows and foreign model dialogs do not.

No Volcengine request is sent. The API key is a dummy value and the test never
presses model-test/fetch-models buttons.
"""

from __future__ import annotations

import asyncio
import json
import os
import traceback
from pathlib import Path
from typing import Any

from playwright.async_api import Locator, Page, async_playwright, expect

from browser_matrix import (
    ARTIFACT_DIR as BASE_ARTIFACT_DIR,
    CASES,
    add_source,
    cancel_visible_dialogs,
    dismiss_first_run_dialog,
    fill_dummy_source_key,
    login,
    open_configured_model,
    open_manual_model_add,
    open_providers,
    save_model_dialog,
    save_source,
    select_source,
    semantic_page_snapshot,
    set_source_video_master,
    source_video_master_row,
    source_video_selector_row,
    visible_config_rows,
)

ARTIFACT_DIR = Path(
    os.environ.get("ASTRBOT_E2E_ARTIFACT_DIR", "e2e-artifacts")
) / "model-fields-0.1.19"

VIDEO_MODE_KEY = "_volcengine_video_input_mode_ui"
VIDEO_PROFILE_KEY = "volcengine_video_input_profile"
REASONING_MODE_KEY = "volcengine_reasoning_mode"
REASONING_EFFORT_KEY = "volcengine_reasoning_effort"
TEMPERATURE_KEY = "volcengine_temperature"
TOP_P_KEY = "volcengine_top_p"
MAX_OUTPUT_TOKENS_KEY = "volcengine_max_output_tokens"
STOP_SEQUENCES_KEY = "volcengine_stop_sequences"
FREQUENCY_PENALTY_KEY = "volcengine_frequency_penalty"
PRESENCE_PENALTY_KEY = "volcengine_presence_penalty"

VISIBLE_FIELD_KEYS = (
    VIDEO_MODE_KEY,
    REASONING_MODE_KEY,
    REASONING_EFFORT_KEY,
    TEMPERATURE_KEY,
    TOP_P_KEY,
    MAX_OUTPUT_TOKENS_KEY,
    STOP_SEQUENCES_KEY,
    FREQUENCY_PENALTY_KEY,
    PRESENCE_PENALTY_KEY,
)
ALL_PLUGIN_MODEL_KEYS = (*VISIBLE_FIELD_KEYS, VIDEO_PROFILE_KEY)

EXPECTED_BILINGUAL_NAMES = {
    VIDEO_MODE_KEY: "视频输入模式 / Video Input Mode",
    REASONING_MODE_KEY: "思考模式 / Thinking Mode",
    REASONING_EFFORT_KEY: "思考强度 / Reasoning Effort",
    TEMPERATURE_KEY: "温度 / Temperature",
    TOP_P_KEY: "核采样 / Top P",
    MAX_OUTPUT_TOKENS_KEY: "最大输出 Token / Max Output Tokens",
    STOP_SEQUENCES_KEY: "停止序列 / Stop Sequences",
    FREQUENCY_PENALTY_KEY: "频率惩罚 / Frequency Penalty",
    PRESENCE_PENALTY_KEY: "存在惩罚 / Presence Penalty",
}


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


async def row_for_key(dialog: Locator, key: str) -> Locator:
    rows = dialog.locator(".config-row")
    for index in range(await rows.count()):
        row = rows.nth(index)
        marker = row.locator(".property-key")
        if not await marker.count():
            continue
        raw = await marker.first.text_content()
        actual = str(raw or "").replace("(", "").replace(")", "").strip()
        if actual == key:
            return row
    raise AssertionError(f"model dialog has no row for key={key!r}")


async def select_row_option(dialog: Locator, key: str, label: str) -> None:
    row = await row_for_key(dialog, key)
    select = row.locator(".v-select").first
    await expect(select).to_be_visible(timeout=5_000)
    await select.click()
    option = dialog.page.locator(
        ".v-overlay:visible .v-list-item", has_text=label
    ).first
    await expect(option).to_be_visible(timeout=5_000)
    await option.click()


async def fill_row_input(dialog: Locator, key: str, value: str) -> None:
    row = await row_for_key(dialog, key)
    control = row.locator("input").first
    await expect(control).to_be_visible(timeout=5_000)
    await control.fill(value)


async def row_input_value(dialog: Locator, key: str) -> str:
    row = await row_for_key(dialog, key)
    control = row.locator("input").first
    await expect(control).to_be_visible(timeout=5_000)
    return await control.input_value()


async def row_visible_text(dialog: Locator, key: str) -> str:
    row = await row_for_key(dialog, key)
    return " ".join((await row.inner_text()).split())


async def assert_source_surface_unchanged(page: Page, *, owned: bool) -> dict[str, Any]:
    master_count = await source_video_master_row(page).count()
    selector_count = await source_video_selector_row(page).count()
    source_text = await page.locator(".provider-config-shell").inner_text()
    leaked_model_labels = [
        label
        for label in EXPECTED_BILINGUAL_NAMES.values()
        if label in source_text
    ]
    if leaked_model_labels:
        raise AssertionError(
            f"model-card fields leaked into Source panel: {leaked_model_labels}"
        )
    if owned:
        if master_count != 1:
            raise AssertionError(
                f"owned Source must keep exactly one 0.1.18 video master, got {master_count}"
            )
    elif master_count or selector_count:
        raise AssertionError("foreign Source exposes 0.1.18 Volcengine video controls")
    return {
        "master_count": master_count,
        "selector_count": selector_count,
        "model_field_labels_on_source": leaked_model_labels,
    }


async def assert_create_dialog_is_host_native(
    dialog: Locator, *, case_name: str
) -> list[dict[str, Any]]:
    rows = await visible_config_rows(dialog)
    keys = {row["key"] for row in rows}
    leaked = sorted(set(ALL_PLUGIN_MODEL_KEYS) & keys)
    if leaked:
        raise AssertionError(
            f"{case_name}: unsaved model-create dialog unexpectedly contains "
            f"server-projected fields: {leaked}"
        )
    return rows


async def assert_owned_edit_rows(dialog: Locator) -> list[dict[str, Any]]:
    rows = await visible_config_rows(dialog)
    by_key = {row["key"]: row for row in rows}
    missing = [key for key in VISIBLE_FIELD_KEYS if key not in by_key]
    if missing:
        raise AssertionError(f"owned configured model is missing rows: {missing}")
    if VIDEO_PROFILE_KEY in by_key:
        raise AssertionError("hidden video profile rendered as a visible row")
    for key, expected_name in EXPECTED_BILINGUAL_NAMES.items():
        actual_name = str(by_key[key].get("name") or "")
        if expected_name not in actual_name:
            raise AssertionError(
                f"{key}: expected bilingual name {expected_name!r}, got {actual_name!r}"
            )
    return rows


async def assert_foreign_edit_rows(dialog: Locator) -> list[dict[str, Any]]:
    rows = await visible_config_rows(dialog)
    keys = {row["key"] for row in rows}
    leaked = sorted(set(ALL_PLUGIN_MODEL_KEYS) & keys)
    if leaked:
        raise AssertionError(f"foreign configured model leaked Volcengine rows: {leaked}")
    text = await dialog.inner_text()
    leaked_labels = [
        label for label in EXPECTED_BILINGUAL_NAMES.values() if label in text
    ]
    if leaked_labels:
        raise AssertionError(
            f"foreign configured model leaked bilingual labels: {leaked_labels}"
        )
    return rows


async def exercise_owned_fields(dialog: Locator) -> dict[str, Any]:
    # Source checkbox enabled the new model before this dialog was opened, so the
    # first projected three-state mode must be Original (0.1.18 compatibility).
    initial_video = await row_visible_text(dialog, VIDEO_MODE_KEY)
    if "原画 / Original Quality" not in initial_video:
        raise AssertionError(
            f"0.1.18 enabled video did not project as Original: {initial_video!r}"
        )

    await select_row_option(dialog, VIDEO_MODE_KEY, "压缩 / Compressed")
    await select_row_option(dialog, REASONING_MODE_KEY, "自动 / Auto")
    await select_row_option(dialog, REASONING_EFFORT_KEY, "高 / High")
    await fill_row_input(dialog, TEMPERATURE_KEY, "0.6")
    await fill_row_input(dialog, TOP_P_KEY, "0.9")
    await fill_row_input(dialog, MAX_OUTPUT_TOKENS_KEY, "8192")
    await fill_row_input(dialog, FREQUENCY_PENALTY_KEY, "-0.25")
    await fill_row_input(dialog, PRESENCE_PENALTY_KEY, "0.5")

    return {
        "initial_video_text": initial_video,
        "set_video": "compressed",
        "set_reasoning_mode": "auto",
        "set_reasoning_effort": "high",
        "set_temperature": "0.6",
        "set_top_p": "0.9",
        "set_max_output_tokens": "8192",
        "set_frequency_penalty": "-0.25",
        "set_presence_penalty": "0.5",
    }


async def verify_owned_persisted_fields(dialog: Locator) -> dict[str, Any]:
    video_text = await row_visible_text(dialog, VIDEO_MODE_KEY)
    reasoning_mode_text = await row_visible_text(dialog, REASONING_MODE_KEY)
    effort_text = await row_visible_text(dialog, REASONING_EFFORT_KEY)
    if "压缩 / Compressed" not in video_text:
        raise AssertionError(f"video mode did not persist: {video_text!r}")
    if "自动 / Auto" not in reasoning_mode_text:
        raise AssertionError(f"thinking mode did not persist: {reasoning_mode_text!r}")
    if "高 / High" not in effort_text:
        raise AssertionError(f"reasoning effort did not persist: {effort_text!r}")

    values = {
        TEMPERATURE_KEY: await row_input_value(dialog, TEMPERATURE_KEY),
        TOP_P_KEY: await row_input_value(dialog, TOP_P_KEY),
        MAX_OUTPUT_TOKENS_KEY: await row_input_value(dialog, MAX_OUTPUT_TOKENS_KEY),
        FREQUENCY_PENALTY_KEY: await row_input_value(dialog, FREQUENCY_PENALTY_KEY),
        PRESENCE_PENALTY_KEY: await row_input_value(dialog, PRESENCE_PENALTY_KEY),
    }
    expected = {
        TEMPERATURE_KEY: "0.6",
        TOP_P_KEY: "0.9",
        MAX_OUTPUT_TOKENS_KEY: "8192",
        FREQUENCY_PENALTY_KEY: "-0.25",
        PRESENCE_PENALTY_KEY: "0.5",
    }
    for key, expected_value in expected.items():
        if values[key] != expected_value:
            raise AssertionError(
                f"{key}: expected persisted UI value {expected_value!r}, got {values[key]!r}"
            )
    return {
        "video_text": video_text,
        "reasoning_mode_text": reasoning_mode_text,
        "reasoning_effort_text": effort_text,
        "numeric_values": values,
    }


async def run_case(page: Page, case) -> dict[str, Any]:
    case_dir = ARTIFACT_DIR / case.name
    case_dir.mkdir(parents=True, exist_ok=True)
    result: dict[str, Any] = {
        "case": case.name,
        "owned": case.owned,
        "stages": {},
        "errors": [],
    }

    try:
        await open_providers(page)
        source_id = await add_source(page, case)
        result["source_id"] = source_id
        await fill_dummy_source_key(page)
        result["source_before_model"] = await assert_source_surface_unchanged(
            page, owned=case.owned
        )
        await save_source(page)
        result["stages"]["source_saved"] = True

        create_dialog = await open_manual_model_add(page, case.model_id)
        result["model_create_rows"] = await assert_create_dialog_is_host_native(
            create_dialog, case_name=case.name
        )
        await page.screenshot(
            path=str(case_dir / "01-model-create-host-native.png"), full_page=True
        )
        await save_model_dialog(create_dialog)
        result["stages"]["model_created"] = True

        await page.locator(".provider-workbench").wait_for(
            state="visible", timeout=20_000
        )
        await select_source(page, source_id)
        if case.owned:
            # Preserve the released 0.1.18 Source workflow and use it as the
            # shortcut that enables video for this configured card.
            await set_source_video_master(page, True)
            selector = source_video_selector_row(page)
            await expect(selector).to_be_visible(timeout=10_000)
            checks = selector.locator('input[type="checkbox"]')
            if await checks.count() != 1:
                raise AssertionError(
                    f"{case.name}: expected one Source video checkbox, got {await checks.count()}"
                )
            await checks.first.set_checked(True, force=True)
            await expect(checks.first).to_be_checked(timeout=5_000)
            await save_source(page)
            result["stages"]["source_video_enabled"] = True
        else:
            await assert_source_surface_unchanged(page, owned=False)

        edit_dialog = await open_configured_model(page, case.model_id)
        if case.owned:
            result["model_edit_rows"] = await assert_owned_edit_rows(edit_dialog)
            result["model_edit_changes"] = await exercise_owned_fields(edit_dialog)
            await page.screenshot(
                path=str(case_dir / "02-owned-model-fields-edited.png"), full_page=True
            )
            await save_model_dialog(edit_dialog)
            result["stages"]["model_fields_saved"] = True

            reopened = await open_configured_model(page, case.model_id)
            result["persisted"] = await verify_owned_persisted_fields(reopened)
            await page.screenshot(
                path=str(case_dir / "03-owned-model-fields-persisted.png"), full_page=True
            )
            await reopened.locator(".v-card-actions button").first.click()
            await expect(reopened).to_be_hidden(timeout=10_000)
            result["stages"]["model_fields_reopened"] = True

            await select_source(page, source_id)
            source_state = await assert_source_surface_unchanged(page, owned=True)
            # We intentionally left the 0.1.18 master open, so its one-model
            # selector must still be present after model-field save/reload.
            source_state["selector_count_after_model_save"] = await source_video_selector_row(
                page
            ).count()
            if source_state["selector_count_after_model_save"] != 1:
                raise AssertionError(
                    "0.1.19 model save disturbed the 0.1.18 Source selector"
                )
            result["source_after_model_save"] = source_state
        else:
            result["model_edit_rows"] = await assert_foreign_edit_rows(edit_dialog)
            await page.screenshot(
                path=str(case_dir / "02-foreign-model-clean.png"), full_page=True
            )
            await edit_dialog.locator(".v-card-actions button").first.click()
            await expect(edit_dialog).to_be_hidden(timeout=10_000)
            result["stages"]["foreign_model_clean"] = True

        await semantic_page_snapshot(page, case_dir / "04-final.dom.json")
        result["success"] = True
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
        "purpose": "0.1.19_real_dashboard_model_field_evidence",
        "cases": results,
        "page_errors": page_errors,
        "all_passed": all(case.get("success") for case in results) and not page_errors,
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
