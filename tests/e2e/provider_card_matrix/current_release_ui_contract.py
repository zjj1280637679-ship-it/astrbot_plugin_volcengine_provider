"""Current release UI acceptance: real AstrBot Dashboard, real visible model-card state.

This is the only active browser entrypoint used by release CI. Historical test
modules are imported only as regression implementation; their old version names
are not release authority.
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

import browser_matrix_0_1_19 as baseline

ARTIFACT_DIR = Path(os.environ.get("ASTRBOT_E2E_ARTIFACT_DIR", "e2e-artifacts")) / "current-release-ui"
baseline.ARTIFACT_DIR = ARTIFACT_DIR

_original_owned_edit_rows = baseline.assert_owned_edit_rows


async def assert_create_dialog_scope(dialog, *, case_name: str, owned: bool):
    rows = await baseline.visible_config_rows(dialog)
    by_key = {row["key"]: row for row in rows}
    plugin_keys = set(baseline.ALL_PLUGIN_MODEL_KEYS)
    visible_plugin_keys = set(baseline.VISIBLE_FIELD_KEYS)
    actual_plugin_keys = plugin_keys.intersection(by_key)

    if owned:
        missing = sorted(visible_plugin_keys - actual_plugin_keys)
        if missing:
            raise AssertionError(
                f"{case_name}: owned unsaved model card is missing visible Volcengine request rows: {missing}"
            )
        if "custom_extra_body" not in by_key:
            raise AssertionError(
                f"{case_name}: owned model card lost AstrBot custom_extra_body"
            )
        if baseline.VIDEO_MODE_KEY in actual_plugin_keys:
            raise AssertionError(
                f"{case_name}: retired raw video transport field leaked into the current UI"
            )
        for key, expected_name in baseline.EXPECTED_BILINGUAL_NAMES.items():
            actual_name = str(by_key[key].get("name") or "")
            if expected_name not in actual_name:
                raise AssertionError(
                    f"{case_name}/{key}: expected visible label {expected_name!r}, got {actual_name!r}"
                )
        options = await baseline.assert_video_modality_scope(
            dialog,
            expected=True,
            expected_checked=False,
            case_name=f"{case_name} owned create",
        )
    else:
        leaked = sorted(actual_plugin_keys)
        if leaked:
            raise AssertionError(
                f"{case_name}: foreign unsaved model card received Volcengine-only keys: {leaked}"
            )
        dialog_text = await dialog.inner_text()
        leaked_labels = [
            label
            for label in baseline.EXPECTED_BILINGUAL_NAMES.values()
            if label in dialog_text
        ]
        if leaked_labels:
            raise AssertionError(
                f"{case_name}: foreign unsaved model card rendered Volcengine rows: {leaked_labels}"
            )
        options = await baseline.assert_video_modality_scope(
            dialog,
            expected=False,
            case_name=f"{case_name} foreign create",
        )

    return rows, options


async def assert_owned_edit_rows(dialog):
    rows = await _original_owned_edit_rows(dialog)
    by_key = {row["key"]: row for row in rows}
    if "custom_extra_body" not in by_key:
        raise AssertionError("owned configured model card lost AstrBot custom_extra_body")
    return rows


# The historical run_case resolves these functions from its module globals at
# execution time. Replace only the active product assertions; its real user
# click, save, reopen and typed-field persistence sequence remains unchanged.
baseline.assert_create_dialog_scope = assert_create_dialog_scope
baseline.assert_owned_edit_rows = assert_owned_edit_rows


async def main() -> None:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    console_events: list[dict[str, str]] = []
    page_errors: list[str] = []
    results: list[dict] = []

    async with baseline.async_playwright() as p:
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

        await baseline.login(page)
        await baseline.open_providers(page)
        for case in baseline.CASES:
            results.append(await baseline.run_case(page, case))
        await browser.close()

    summary = {
        "schema_version": 1,
        "purpose": "current_release_real_model_card_video_and_request_fields",
        "cases": results,
        "page_errors": page_errors,
        "all_passed": all(case.get("success") for case in results) and not page_errors,
        "failed_cases": [case["case"] for case in results if not case.get("success")],
    }
    baseline.write_json(ARTIFACT_DIR / "matrix-result.json", summary)
    baseline.write_json(ARTIFACT_DIR / "browser-console.json", console_events)
    baseline.write_json(ARTIFACT_DIR / "browser-page-errors.json", page_errors)
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    if not summary["all_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
