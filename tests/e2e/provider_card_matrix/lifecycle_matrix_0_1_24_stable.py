"""Stable entrypoint for the 0.1.24 lifecycle contract.

The product assertions remain in ``lifecycle_matrix_0_1_24``.  AstrBot 4.27.3's
Vuetify model dialog can leave an overlay scrim mounted after a freshly restarted
process even after the already-validated dialog itself stops being the topmost
visible dialog.  That host-only cleanup state can intercept the next pointer
click for tens of seconds.

Rather than weakening any product assertion or force-clicking through the host
scrim, this wrapper starts a fresh providers-page navigation between the owned
and foreign model-card assertions.  Each card is still reopened from AstrBot's
persisted provider state in the same new browser session; the navigation only
removes transient overlay state that is not part of the product contract.
"""

from __future__ import annotations

import argparse
import asyncio
from typing import Any

from playwright.async_api import Page

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

    # Do not click through a stale Vuetify scrim after the owned assertion.
    # A full route navigation gives the following foreign assertion a clean
    # host surface while preserving the same process, data directory and
    # browser session under test.
    await base.open_providers(page)
    await base.select_source(page, str(state["openai_source_id"]))
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
