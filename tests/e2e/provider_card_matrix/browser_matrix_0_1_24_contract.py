"""Current object-scoped UI contract layered over the 0.1.19 rich-field matrix.

The historical 0.1.19 matrix still contains valuable edit/save/reopen coverage for
Video Quality, Thinking Mode, Reasoning Effort, Temperature, Top P, output-token,
stop-sequence and penalty fields.  One historical create-dialog assertion is no
longer the product contract: it expected those plugin rows to be absent before a
new model card had been saved because older implementations projected them only
from the server after persistence.

The current contract is stricter and refers to different concrete objects:

* an unsaved new Ark / Agent Plan model-card data object must already contain the
  nine lower Volcengine request-field keys so AstrBotConfig can actually render
  their bilingual rows, while its upper native modalities row independently gains
  one initially-unchecked Video option;
* an unsaved foreign model-card data object must contain none of those plugin
  keys, show none of those bilingual row labels, and retain the host modalities
  row without Video;
* the historical matrix continues unchanged after creation, so owned edit/save/
  reopen persistence and foreign edit isolation remain independently exercised.
"""

from __future__ import annotations

import asyncio

import browser_matrix_0_1_19 as baseline


async def assert_create_dialog_scope(
    dialog, *, case_name: str, owned: bool
):
    rows = await baseline.visible_config_rows(dialog)
    by_key = {row["key"]: row for row in rows}
    plugin_keys = set(baseline.ALL_PLUGIN_MODEL_KEYS)
    visible_keys = set(baseline.VISIBLE_FIELD_KEYS)
    actual_plugin_keys = plugin_keys.intersection(by_key)

    if owned:
        missing = sorted(visible_keys - actual_plugin_keys)
        if missing:
            raise AssertionError(
                f"{case_name}: owned unsaved model-card data object is missing "
                f"renderable Volcengine request rows: {missing}"
            )
        retired_raw_key = baseline.VIDEO_MODE_KEY
        if retired_raw_key in actual_plugin_keys:
            raise AssertionError(
                f"{case_name}: retired raw video transport field leaked into the "
                f"owned model-card UI: {retired_raw_key}"
            )
        for key, expected_name in baseline.EXPECTED_BILINGUAL_NAMES.items():
            actual_name = str(by_key[key].get("name") or "")
            if expected_name not in actual_name:
                raise AssertionError(
                    f"{case_name}/{key}: owned create row must keep bilingual "
                    f"plugin label {expected_name!r}, got {actual_name!r}"
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
                f"{case_name}: foreign unsaved model-card data object received "
                f"Volcengine-only keys: {leaked}"
            )
        dialog_text = await dialog.inner_text()
        leaked_labels = [
            label
            for label in baseline.EXPECTED_BILINGUAL_NAMES.values()
            if label in dialog_text
        ]
        if leaked_labels:
            raise AssertionError(
                f"{case_name}: foreign unsaved model card rendered Volcengine "
                f"bilingual rows: {leaked_labels}"
            )
        options = await baseline.assert_video_modality_scope(
            dialog,
            expected=False,
            case_name=f"{case_name} foreign create",
        )

    return rows, options


# Replace only the one historical assertion whose objective referent changed.
# The baseline module's run_case resolves this global at execution time, so all
# of its remaining real-browser edit/save/reopen logic is reused unchanged.
baseline.assert_create_dialog_scope = assert_create_dialog_scope


if __name__ == "__main__":
    asyncio.run(baseline.main())
