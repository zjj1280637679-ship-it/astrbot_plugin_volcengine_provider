"""Runner that enforces AstrBot's Source-switch model-list lifecycle.

AstrBot's available-model rows are transient UI state. Selecting another Source
clears that list, so each Source must fetch its own models again before an
available model row can be opened. This wrapper preserves the cross-provider
matrix assertions while making that host lifecycle explicit.
"""

from __future__ import annotations

import asyncio

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


matrix.open_available_model = _open_available_model_after_refresh


if __name__ == "__main__":
    asyncio.run(matrix.run())
