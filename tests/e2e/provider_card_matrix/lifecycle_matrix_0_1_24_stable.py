"""Stable entrypoint for the 0.1.24 lifecycle contract.

The product assertions remain in ``lifecycle_matrix_0_1_24``.  This wrapper only
changes how an already-validated Vuetify model dialog is dismissed.  On AstrBot
4.27.3 a transient overlay scrim can legitimately sit above the dialog's Cancel
button after a fresh process restart, causing Playwright's pointer click to time
out even though every owned-card assertion has already passed.  Keyboard Escape
closes the topmost host overlay without weakening any product assertion.
"""

from __future__ import annotations

import argparse
import asyncio
from typing import Any

from playwright.async_api import Locator, Page, expect

import lifecycle_matrix_0_1_24 as base


async def close_validated_dialog(page: Page, dialog: Locator, *, stage: str) -> None:
    """Dismiss a dialog after its semantic assertions have already succeeded."""

    for _ in range(5):
        if not await dialog.is_visible():
            return
        await page.keyboard.press("Escape")
        try:
            await expect(dialog).to_be_hidden(timeout=2_000)
            return
        except AssertionError:
            await page.wait_for_timeout(100)
    raise AssertionError(f"{stage}: validated model dialog could not be dismissed")


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
    await close_validated_dialog(page, ark_dialog, stage=f"{stage}/owned-close")

    await base.select_source(page, str(state["openai_source_id"]))
    foreign_dialog = await base.open_configured_model(page, base.OPENAI_CASE.model_id)
    foreign_ui = await base.assert_foreign_dialog(
        foreign_dialog,
        stage=f"{stage}/foreign-reopen",
    )
    await close_validated_dialog(page, foreign_dialog, stage=f"{stage}/foreign-close")

    persisted = base.assert_persisted_state(state, stage=stage)
    return {"owned": ark_ui, "foreign": foreign_ui, "persisted": persisted}


async def run(stage: str) -> None:
    # base.run resolves these names from its module globals at execution time.
    # Replacing only this cleanup-sensitive stage leaves every existing product
    # assertion, setup step, uninstall assertion and artifact format unchanged.
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
