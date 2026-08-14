"""Sequential real-Dashboard lifecycle contract for the object-scoped Video feature.

This test intentionally separates four states that a shorter phrase such as
"persistence works" would incorrectly collapse into one:

1. ``setup`` creates one concrete Ark model card and one concrete foreign OpenAI
   model card through the real AstrBot Dashboard.  The Ark card receives exactly
   one user-controlled ``video`` option, that option is enabled and saved, and a
   full Dashboard page reload must recover the same checked state from AstrBot's
   persisted provider config rather than from the original dialog object.
2. ``after-restart`` runs in a new browser session after the AstrBot process has
   been terminated and started again with the same plugin checkout and the same
   data directory.  The same persisted Ark card must still expose checked Video;
   the persisted foreign card must remain free of plugin UI/state.
3. ``after-same-version-update`` runs after the plugin directory has been removed
   and overlaid again from the exact same candidate checkout, followed by another
   real AstrBot process restart.  The replacement of plugin code must not replace
   or reset the model-card-owned persisted Video selection.
4. ``uninstalled`` runs after the plugin directory has actually been removed and
   AstrBot restarted without the plugin.  It does not demand deletion of the
   user's stored Ark Source/model configuration; that persisted user data is a
   different object from public host UI injection.  It does demand that the
   public Source-add menu no longer offers the plugin Source types, a normal
   foreign OpenAI model card has no plugin Video/lower rows, and the Dashboard JS
   actually delivered to the browser contains no Volcengine transformation marker.

None of these stages is allowed to substitute for another stage in the five-part
product acceptance contract.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
from typing import Any

from playwright.async_api import Locator, Page, async_playwright, expect

from browser_matrix import (
    BASE_URL,
    PASSWORD,
    USERNAME,
    Case,
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
    visible_config_rows,
)

ARK_CASE = Case(
    name="lifecycle_ark",
    template_key="volcengine_ark_chat_completion",
    menu_label="volcengine_ark_chat_completion",
    expected_source_id="volcengine-ark",
    model_id="e2e-lifecycle-ark-model",
    owned=True,
)
OPENAI_CASE = Case(
    name="lifecycle_foreign_openai",
    template_key="openai_chat_completion",
    menu_label="OpenAI Compatible",
    expected_source_id=None,
    model_id="e2e-lifecycle-openai-model",
    owned=False,
)

PLUGIN_KEYS = {
    "volcengine_video_input_profile",
    "volcengine_reasoning_mode",
    "volcengine_reasoning_effort",
    "volcengine_temperature",
    "volcengine_top_p",
    "volcengine_max_output_tokens",
    "volcengine_stop_sequences",
    "volcengine_frequency_penalty",
    "volcengine_presence_penalty",
}
PLUGIN_SOURCE_MENU_MARKERS = {
    "volcengine_ark_chat_completion",
    "volcengine_agent_plan_chat_completion",
}
ARTIFACT_DIR = (
    Path(os.environ.get("ASTRBOT_E2E_ARTIFACT_DIR", "e2e-artifacts"))
    / "lifecycle-0.1.24"
)
STATE_PATH = ARTIFACT_DIR / "state.json"
CONFIG_PATH = Path(
    os.environ.get("ASTRBOT_E2E_CONFIG_PATH", "AstrBot/data/cmd_config.json")
)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def read_state() -> dict[str, Any]:
    data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise AssertionError("lifecycle state artifact is not an object")
    return data


async def row_for_key(scope: Locator, key: str) -> Locator:
    rows = scope.locator(".config-row")
    for index in range(await rows.count()):
        row = rows.nth(index)
        marker = row.locator(".property-key")
        if not await marker.count():
            continue
        raw = await marker.first.text_content()
        actual = str(raw or "").replace("(", "").replace(")", "").strip()
        if actual == key:
            return row
    raise AssertionError(f"no config row for key={key!r}")


async def modality_values(dialog: Locator) -> list[dict[str, Any]]:
    row = await row_for_key(dialog, "modalities")
    return await row.evaluate(
        """
        (row) => Array.from(row.querySelectorAll('input[type="checkbox"]')).map((input) => {
          const labels = Array.from(row.querySelectorAll('label'));
          const direct = input.id ? labels.find((label) => label.htmlFor === input.id) : null;
          const control = input.closest('.v-selection-control');
          return {
            value: String(input.value || ''),
            label: String(direct?.textContent || control?.textContent || '').replace(/\s+/g, ' ').trim(),
            checked: Boolean(input.checked),
          };
        })
        """
    )


async def assert_owned_dialog(
    dialog: Locator,
    *,
    expected_video_checked: bool,
    stage: str,
) -> dict[str, Any]:
    options = await modality_values(dialog)
    videos = [item for item in options if item.get("value") == "video"]
    if len(videos) != 1:
        raise AssertionError(f"{stage}: expected one Video option, got {options!r}")
    video = videos[0]
    if video.get("label") != "视频":
        raise AssertionError(f"{stage}: expected zh-CN Video label '视频', got {video!r}")
    if bool(video.get("checked")) is not expected_video_checked:
        raise AssertionError(
            f"{stage}: Video checked state expected {expected_video_checked}, got {video!r}"
        )

    rows = await visible_config_rows(dialog)
    visible_plugin_keys = {
        str(row.get("key") or "") for row in rows
    }.intersection(PLUGIN_KEYS)
    if visible_plugin_keys != PLUGIN_KEYS:
        raise AssertionError(
            f"{stage}: owned lower request rows incomplete: "
            f"missing={sorted(PLUGIN_KEYS - visible_plugin_keys)}"
        )
    return {"modalities": options, "plugin_keys": sorted(visible_plugin_keys)}


async def assert_foreign_dialog(dialog: Locator, *, stage: str) -> dict[str, Any]:
    options = await modality_values(dialog)
    if any(item.get("value") == "video" for item in options):
        raise AssertionError(f"{stage}: foreign model card leaked Video: {options!r}")
    rows = await visible_config_rows(dialog)
    plugin_rows = [
        row for row in rows if str(row.get("key") or "") in PLUGIN_KEYS
    ]
    if plugin_rows:
        raise AssertionError(f"{stage}: foreign model card leaked plugin rows: {plugin_rows!r}")
    return {"modalities": options}


async def enable_owned_video(dialog: Locator) -> None:
    row = await row_for_key(dialog, "modalities")
    checkbox = row.locator('input[type="checkbox"][value="video"]')
    if await checkbox.count() != 1:
        raise AssertionError("owned model card does not have exactly one Video checkbox")
    control_id = await checkbox.get_attribute("id")
    if not control_id:
        raise AssertionError("Video checkbox has no host-visible label target")
    label = row.locator(f'label[for="{control_id}"]')
    await expect(label).to_be_visible(timeout=5_000)
    await label.click()
    await expect(checkbox).to_be_checked(timeout=5_000)


def persisted_cards(state: dict[str, Any]) -> dict[str, Any]:
    data = json.loads(CONFIG_PATH.read_text(encoding="utf-8-sig"))
    providers = {
        str(item.get("id") or ""): item
        for item in data.get("provider", [])
        if isinstance(item, dict)
    }
    ark_id = f"{state['ark_source_id']}/{ARK_CASE.model_id}"
    openai_id = f"{state['openai_source_id']}/{OPENAI_CASE.model_id}"
    ark = providers.get(ark_id)
    foreign = providers.get(openai_id)
    if not isinstance(ark, dict) or not isinstance(foreign, dict):
        raise AssertionError(
            f"persisted lifecycle cards missing: ark={bool(ark)} foreign={bool(foreign)}"
        )
    foreign_plugin_keys = sorted(
        key for key in foreign if str(key).startswith("volcengine_")
    )
    return {
        "ark_id": ark_id,
        "ark_modalities": ark.get("modalities"),
        "ark_video_enabled": ark.get("volcengine_video_input_enabled"),
        "foreign_id": openai_id,
        "foreign_modalities": foreign.get("modalities"),
        "foreign_plugin_keys": foreign_plugin_keys,
    }


def assert_persisted_state(state: dict[str, Any], *, stage: str) -> dict[str, Any]:
    persisted = persisted_cards(state)
    if "video" not in (persisted["ark_modalities"] or []):
        raise AssertionError(f"{stage}: persisted Ark modalities lost video: {persisted!r}")
    if persisted["ark_video_enabled"] is not True:
        raise AssertionError(f"{stage}: persisted Ark runtime mirror is not true: {persisted!r}")
    if "video" in (persisted["foreign_modalities"] or []):
        raise AssertionError(f"{stage}: foreign persisted modalities gained video: {persisted!r}")
    if persisted["foreign_plugin_keys"]:
        raise AssertionError(f"{stage}: foreign persisted plugin keys leaked: {persisted!r}")
    return persisted


async def setup_stage(page: Page) -> dict[str, Any]:
    await open_providers(page)
    ark_source_id = await add_source(page, ARK_CASE)
    await fill_dummy_source_key(page)
    await save_source(page)
    ark_dialog = await open_manual_model_add(page, ARK_CASE.model_id)
    create_state = await assert_owned_dialog(
        ark_dialog,
        expected_video_checked=False,
        stage="setup/owned-unsaved-create",
    )
    await enable_owned_video(ark_dialog)
    await save_model_dialog(ark_dialog)

    await open_providers(page)
    openai_source_id = await add_source(page, OPENAI_CASE)
    await fill_dummy_source_key(page)
    await save_source(page)
    foreign_dialog = await open_manual_model_add(page, OPENAI_CASE.model_id)
    foreign_create = await assert_foreign_dialog(
        foreign_dialog, stage="setup/foreign-unsaved-create"
    )
    await save_model_dialog(foreign_dialog)

    state = {
        "ark_source_id": ark_source_id,
        "openai_source_id": openai_source_id,
        "ark_model_id": ARK_CASE.model_id,
        "openai_model_id": OPENAI_CASE.model_id,
    }
    write_json(STATE_PATH, state)
    persisted_before_refresh = assert_persisted_state(state, stage="setup/before-refresh")

    # Page reload is a different lifecycle state from closing/reopening a dialog.
    # Wait for the provider workbench rather than network-idle because AstrBot
    # keeps background requests alive.
    await page.reload(wait_until="domcontentloaded", timeout=30_000)
    await page.locator(".provider-workbench").wait_for(state="visible", timeout=30_000)
    await dismiss_first_run_dialog(page, wait_ms=300)
    await select_source(page, ark_source_id)
    reopened = await open_configured_model(page, ARK_CASE.model_id)
    after_refresh = await assert_owned_dialog(
        reopened,
        expected_video_checked=True,
        stage="setup/after-dashboard-refresh",
    )
    await reopened.locator(".v-card-actions button").first.click()
    await expect(reopened).to_be_hidden(timeout=10_000)

    persisted_after_refresh = assert_persisted_state(state, stage="setup/after-refresh")
    return {
        "create_owned": create_state,
        "create_foreign": foreign_create,
        "persisted_before_refresh": persisted_before_refresh,
        "after_dashboard_refresh": after_refresh,
        "persisted_after_refresh": persisted_after_refresh,
    }


async def verify_installed_stage(page: Page, *, stage: str) -> dict[str, Any]:
    state = read_state()
    await open_providers(page)
    await select_source(page, str(state["ark_source_id"]))
    ark_dialog = await open_configured_model(page, ARK_CASE.model_id)
    ark_ui = await assert_owned_dialog(
        ark_dialog,
        expected_video_checked=True,
        stage=f"{stage}/owned-reopen",
    )
    await ark_dialog.locator(".v-card-actions button").first.click()
    await expect(ark_dialog).to_be_hidden(timeout=10_000)

    await select_source(page, str(state["openai_source_id"]))
    foreign_dialog = await open_configured_model(page, OPENAI_CASE.model_id)
    foreign_ui = await assert_foreign_dialog(
        foreign_dialog, stage=f"{stage}/foreign-reopen"
    )
    await foreign_dialog.locator(".v-card-actions button").first.click()
    await expect(foreign_dialog).to_be_hidden(timeout=10_000)

    persisted = assert_persisted_state(state, stage=stage)
    return {"owned": ark_ui, "foreign": foreign_ui, "persisted": persisted}


async def uninstalled_stage(page: Page) -> dict[str, Any]:
    state = read_state()
    await open_providers(page)

    add_button = page.locator(".provider-sources-controls button:has(.mdi-plus)").first
    await expect(add_button).to_be_visible(timeout=10_000)
    await add_button.click()
    await page.wait_for_timeout(500)
    menu_texts = [
        str(text or "").strip()
        for text in await page.locator(
            ".v-overlay:visible .v-list-item"
        ).all_text_contents()
    ]
    leaked_source_markers = sorted(
        marker
        for marker in PLUGIN_SOURCE_MENU_MARKERS
        if any(marker in text for text in menu_texts)
    )
    if leaked_source_markers:
        raise AssertionError(
            f"uninstalled/public-source-menu: plugin Source types remain visible: "
            f"{leaked_source_markers}"
        )
    await page.keyboard.press("Escape")

    await select_source(page, str(state["openai_source_id"]))
    foreign_dialog = await open_configured_model(page, OPENAI_CASE.model_id)
    foreign_ui = await assert_foreign_dialog(
        foreign_dialog, stage="uninstalled/foreign-reopen"
    )
    await foreign_dialog.locator(".v-card-actions button").first.click()
    await expect(foreign_dialog).to_be_hidden(timeout=10_000)

    # The concrete public JS responses loaded by this browser are checked rather
    # than merely inspecting plugin Python globals after termination.
    js_delivery = await page.evaluate(
        """
        async () => {
          const urls = performance.getEntriesByType('resource')
            .map((entry) => String(entry.name || ''))
            .filter((url) => url.includes('/assets/') && url.endsWith('.js'));
          const unique = [...new Set(urls)];
          const hits = [];
          for (const url of unique) {
            try {
              const text = await (await fetch(url, {cache: 'reload'})).text();
              if (text.includes('astrbot-volcengine-model-dialog-v')) hits.push(url);
            } catch (_) {}
          }
          return {checked_js_urls: unique.length, marker_hits: hits};
        }
        """
    )
    if js_delivery.get("marker_hits"):
        raise AssertionError(
            f"uninstalled/public-assets: browser still receives transformed JS: "
            f"{js_delivery!r}"
        )

    return {
        "source_menu_entries": menu_texts,
        "foreign": foreign_ui,
        "public_js_delivery": js_delivery,
    }


async def run(stage: str) -> None:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    result: dict[str, Any] = {"stage": stage, "success": False}
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(viewport={"width": 1440, "height": 1200})
        page = await context.new_page()
        try:
            await login(page)
            if stage == "setup":
                result["evidence"] = await setup_stage(page)
            elif stage in {"after-restart", "after-same-version-update"}:
                result["evidence"] = await verify_installed_stage(page, stage=stage)
            elif stage == "uninstalled":
                result["evidence"] = await uninstalled_stage(page)
            else:
                raise AssertionError(f"unsupported lifecycle stage: {stage}")
            result["success"] = True
        finally:
            await cancel_visible_dialogs(page)
            await browser.close()

    write_json(ARTIFACT_DIR / f"{stage}.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


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
