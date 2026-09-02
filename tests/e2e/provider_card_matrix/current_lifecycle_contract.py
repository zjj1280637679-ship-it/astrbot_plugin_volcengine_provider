"""Current release lifecycle acceptance for real AstrBot processes and Dashboard.

This version-neutral entrypoint reuses the mature lifecycle implementation while
making the current release assertions explicit: checked Video, complete owned
request rows including custom_extra_body, foreign isolation, restart persistence,
same-version replacement, and uninstall cleanup.
"""

from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path
from typing import Any

from playwright.async_api import Page, expect

import lifecycle_matrix_0_1_24 as base

ARTIFACT_DIR = Path(os.environ.get("ASTRBOT_E2E_ARTIFACT_DIR", "e2e-artifacts")) / "current-lifecycle"
base.ARTIFACT_DIR = ARTIFACT_DIR
base.STATE_PATH = ARTIFACT_DIR / "state.json"

_original_assert_owned_dialog = base.assert_owned_dialog


async def assert_owned_dialog(
    dialog,
    *,
    expected_video_checked: bool,
    stage: str,
) -> dict[str, Any]:
    result = await _original_assert_owned_dialog(
        dialog,
        expected_video_checked=expected_video_checked,
        stage=stage,
    )
    rows = await base.visible_config_rows(dialog)
    keys = {str(row.get("key") or "") for row in rows}
    if "custom_extra_body" not in keys:
        raise AssertionError(f"{stage}: owned model card lost AstrBot custom_extra_body")
    result["custom_extra_body_visible"] = True
    return result


base.assert_owned_dialog = assert_owned_dialog


async def verify_installed_stage(page: Page, *, stage: str) -> dict[str, Any]:
    state = base.read_state()
    await base.open_providers(page)

    await base.select_source(page, str(state["ark_source_id"]))
    ark_dialog = await base.open_configured_model(page, base.ARK_CASE.model_id)
    ark_ui = await base.assert_owned_dialog(
        ark_dialog,
        expected_video_checked=True,
        stage=f"{stage}/owned-reopen",
    )

    # Destroy the old document between owned and foreign assertions. This avoids
    # treating a host Vuetify overlay-cleanup artifact as a plugin failure while
    # preserving all product assertions and the same browser login context.
    await page.goto("about:blank", wait_until="load")
    await base.open_providers(page)
    await base.select_source(page, str(state["openai_source_id"]))
    await expect(page.locator(".v-overlay__scrim:visible")).to_have_count(
        0,
        timeout=10_000,
    )
    foreign_dialog = await base.open_configured_model(page, base.OPENAI_CASE.model_id)
    foreign_ui = await base.assert_foreign_dialog(
        foreign_dialog,
        stage=f"{stage}/foreign-reopen",
    )

    persisted = base.assert_persisted_state(state, stage=stage)
    return {"owned": ark_ui, "foreign": foreign_ui, "persisted": persisted}


async def run(stage: str) -> None:
    base.verify_installed_stage = verify_installed_stage
    await base.run(stage)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--stage",
        required=True,
        choices=("setup", "after-restart", "after-same-version-update", "uninstalled"),
    )
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(run(parse_args().stage))
