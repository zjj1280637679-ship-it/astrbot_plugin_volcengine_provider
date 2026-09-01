"""Stable entrypoint for the 0.1.24 lifecycle contract.

The product assertions remain in ``lifecycle_matrix_0_1_24``.  AstrBot 4.27.3's
Vuetify model dialog can leave an overlay scrim mounted after a freshly restarted
process even after the already-validated dialog itself stops being the topmost
visible dialog.  That host-only cleanup state can intercept the next pointer
click for tens of seconds.

Rather than weakening any product assertion or force-clicking through the host
scrim, this wrapper performs a cross-document reset between the owned and
foreign model-card assertions, then waits for the fresh Providers surface to be
free of visible scrims.  Each card is still reopened from AstrBot's persisted
provider state in the same browser context; the reset only removes transient
overlay state that is not part of the product contract.
"""

from __future__ import annotations

import argparse
import asyncio
from typing import Any

from playwright.async_api import Page, expect

import lifecycle_matrix_0_1_24 as base


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

    # A same-route navigation is not sufficient here: AstrBot 4.27.3 can retain
    # the existing Vuetify overlay subtree when the URL stays on /#/providers.
    # Crossing to about:blank guarantees that the old document is destroyed;
    # returning in the same context preserves login state while rebuilding the
    # Providers surface from the same process and persisted data directory.
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
    # base.run resolves this name from its module globals at execution time.
    # Only cleanup-sensitive navigation is replaced; all product assertions,
    # setup semantics, uninstall assertions and artifact formats stay intact.
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
