"""Runner that enforces AstrBot's real Dashboard interaction lifecycle.

AstrBot's available-model rows are transient UI state. Selecting another Source
clears that list, so each Source must fetch its own models again before an
available model row can be opened.

Vuetify selection controls are also user-driven through the visible label. The
native checkbox input may be visually wrapped and direct Playwright set_checked
can click without updating Vue state, so this runner uses the same visible-label
interaction already proven by the real Source-Type Video differential.
"""

from __future__ import annotations

import asyncio

from playwright.async_api import expect

import real_cross_provider_effect_matrix as matrix

_original_open_available_model = matrix.open_available_model


async def _open_available_model_after_refresh(page, model_id: str):
    models = await matrix.fetch_models(page)
    if model_id not in models:
        raise AssertionError(
            f"model disappeared after selecting/refetching Source: {model_id!r}; "
            f"refetched_count={len(models)}"
        )
    return await _original_open_available_model(page, model_id)


async def _enable_video_by_visible_label(dialog) -> None:
    row = await matrix.row_for_key(dialog, "modalities")
    checkbox = row.locator('input[type="checkbox"][value="video"]')
    if await checkbox.count() != 1:
        raise AssertionError(
            f"expected exactly one Video checkbox, found {await checkbox.count()}"
        )
    control_id = await checkbox.get_attribute("id")
    if not control_id:
        raise AssertionError("Video checkbox has no visible label target")
    label = row.locator(f'label[for="{control_id}"]')
    await expect(label).to_be_visible(timeout=5_000)
    await label.click()
    await expect(checkbox).to_be_checked(timeout=5_000)


matrix.open_available_model = _open_available_model_after_refresh
matrix.enable_video = _enable_video_by_visible_label


if __name__ == "__main__":
    asyncio.run(matrix.run())
