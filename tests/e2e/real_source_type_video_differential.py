"""Real same-endpoint source-type differential for the model-card Video control.

This test deliberately uses one Volcengine Ark account, one /api/v3 endpoint and
one model ID through two AstrBot Source types:

A. AstrBot native ``openai_chat_completion`` pointed at Ark;
B. this plugin's ``volcengine_ark_chat_completion`` Source.

The API key is supplied only through ``ARK_API_KEY`` and is never written to the
evidence artifact.  The test performs model discovery only; it does not send a
paid chat-completion request.

The acceptance variable is Source ownership, not vendor/model capability.  In the
same Chinese AstrBot Dashboard and for the same real Ark endpoint/key/model, the
native OpenAI card is the host-owned control object: its four modality values and
visible labels must remain untouched.  The plugin Ark card must preserve those
same four host-owned value/label pairs and add exactly one fifth plugin-owned
``video`` option labelled ``视频``.  Saving/reopening must retain the Video state,
while the foreign OpenAI card must persist no plugin Video state.
"""

from __future__ import annotations

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
    dismiss_first_run_dialog,
    login,
    open_configured_model,
    open_providers,
    save_model_dialog,
    save_source,
    select_source,
)

API_BASE = "https://ark.cn-beijing.volces.com/api/v3"
API_KEY = os.environ.get("ARK_API_KEY", "").strip()
ARTIFACT_DIR = Path(os.environ.get("ASTRBOT_E2E_ARTIFACT_DIR", "e2e-artifacts")) / "real-source-type-video"
CONFIG_PATH = Path(os.environ.get("ASTRBOT_E2E_CONFIG_PATH", "AstrBot/data/cmd_config.json"))

OPENAI_CASE = Case(
    name="openai_on_volcengine",
    template_key="openai_chat_completion",
    menu_label="OpenAI Compatible",
    expected_source_id=None,
    model_id="unused",
    owned=False,
)
ARK_CASE = Case(
    name="plugin_volcengine_ark",
    template_key="volcengine_ark_chat_completion",
    menu_label="volcengine_ark_chat_completion",
    expected_source_id="volcengine-ark",
    model_id="unused",
    owned=True,
)

HOST_NATIVE_MODALITY_VALUES = ["text", "image", "audio", "tool_use"]
HOST_NATIVE_ZH_LABELS = ["文本", "图像", "音频", "工具使用"]


def write_result(payload: dict[str, Any]) -> None:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    (ARTIFACT_DIR / "differential-result.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


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


async def fill_source_field(page: Page, key: str, value: str) -> None:
    shell = page.locator(".provider-config-shell")
    row = await row_for_key(shell, key)
    control = row.locator("input").first
    await expect(control).to_be_visible(timeout=10_000)
    await control.fill(value)


async def configure_source(page: Page, case: Case, *, api_base: str | None) -> str:
    source_id = await add_source(page, case)
    await fill_source_field(page, "key", API_KEY)
    if api_base is not None:
        await fill_source_field(page, "api_base", api_base)
    await save_source(page)
    return source_id


async def fetch_real_models(page: Page) -> list[str]:
    await dismiss_first_run_dialog(page, wait_ms=300)
    button = page.locator(".provider-models-toolbar__actions button:has(.mdi-download)").first
    await expect(button).to_be_visible(timeout=10_000)
    await button.click()
    await expect(button).not_to_have_attribute("disabled", "", timeout=60_000)
    rows = page.locator(".provider-models-list--available .provider-model-row__title")
    await expect(rows.first).to_be_visible(timeout=60_000)
    values = [str(v).strip() for v in await rows.all_text_contents()]
    return sorted({v for v in values if v})


async def open_available_model(page: Page, model_id: str) -> Locator:
    row = page.locator(
        ".provider-models-list--available .provider-model-row",
        has_text=model_id,
    ).first
    await expect(row).to_be_visible(timeout=20_000)
    await row.locator(".provider-model-row__main").click()
    dialog = page.locator(".v-dialog:visible").last
    await expect(dialog.locator(".config-row").first).to_be_visible(timeout=10_000)
    return dialog


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
            label: String(direct?.textContent || control?.textContent || '').replace(/\\s+/g, ' ').trim(),
            checked: Boolean(input.checked),
          };
        })
        """
    )


def assert_host_native_prefix(
    candidate: list[dict[str, Any]],
    control: list[dict[str, Any]],
    *,
    object_name: str,
) -> None:
    """Require the plugin-owned card to preserve the host-owned first four items.

    Equality is checked on the actually rendered value/label pairs from the same
    AstrBot process, not against a plugin copy of AstrBot's translations.  The
    fixed Chinese constants below additionally prove that this workflow really is
    exercising AstrBot's default zh-CN locale rather than two identically wrong
    English copies.
    """

    control_prefix = [
        {"value": item.get("value"), "label": item.get("label")}
        for item in control[:4]
    ]
    candidate_prefix = [
        {"value": item.get("value"), "label": item.get("label")}
        for item in candidate[:4]
    ]
    expected_control = [
        {"value": value, "label": label}
        for value, label in zip(HOST_NATIVE_MODALITY_VALUES, HOST_NATIVE_ZH_LABELS)
    ]
    if control_prefix != expected_control:
        raise AssertionError(
            f"native OpenAI@Ark control did not render the expected zh-CN host "
            f"modalities: {control_prefix!r}"
        )
    if candidate_prefix != control_prefix:
        raise AssertionError(
            f"{object_name}: plugin rewrote host-owned native modality value/label "
            f"pairs; control={control_prefix!r} candidate={candidate_prefix!r}"
        )


async def enable_video(dialog: Locator) -> None:
    row = await row_for_key(dialog, "modalities")
    checkbox = row.locator('input[type="checkbox"][value="video"]')
    if await checkbox.count() != 1:
        raise AssertionError(f"expected one Video checkbox, found {await checkbox.count()}")
    control_id = await checkbox.get_attribute("id")
    if not control_id:
        raise AssertionError("Video checkbox has no visible label target")
    label = row.locator(f'label[for="{control_id}"]')
    await expect(label).to_be_visible(timeout=5_000)
    await label.click()
    await expect(checkbox).to_be_checked(timeout=5_000)


def _extract_persisted(source_ids: tuple[str, str], model_id: str) -> dict[str, Any]:
    data = json.loads(CONFIG_PATH.read_text(encoding="utf-8-sig"))
    sources = {
        str(item.get("id") or ""): item
        for item in data.get("provider_sources", [])
        if isinstance(item, dict)
    }
    providers = {
        str(item.get("id") or ""): item
        for item in data.get("provider", [])
        if isinstance(item, dict)
    }
    openai_id = f"{source_ids[0]}/{model_id}"
    ark_id = f"{source_ids[1]}/{model_id}"
    openai = providers.get(openai_id)
    ark = providers.get(ark_id)
    if not isinstance(openai, dict) or not isinstance(ark, dict):
        raise AssertionError(
            f"persisted model cards missing: openai={bool(openai)} ark={bool(ark)}"
        )

    openai_source = sources.get(source_ids[0], {})
    ark_source = sources.get(source_ids[1], {})
    openai_key = openai_source.get("key")
    ark_key = ark_source.get("key")
    same_nonempty_key = bool(openai_key) and openai_key == ark_key

    return {
        "same_nonempty_key": same_nonempty_key,
        "openai_source_type": openai_source.get("type"),
        "ark_source_type": ark_source.get("type"),
        "same_api_base": str(openai_source.get("api_base") or "").rstrip("/")
        == str(ark_source.get("api_base") or "").rstrip("/"),
        "openai_card": {
            "provider_source_id": openai.get("provider_source_id"),
            "model": openai.get("model"),
            "modalities": openai.get("modalities"),
            "has_plugin_video_key": "volcengine_video_input_enabled" in openai,
        },
        "ark_card": {
            "provider_source_id": ark.get("provider_source_id"),
            "model": ark.get("model"),
            "modalities": ark.get("modalities"),
            "video_enabled": ark.get("volcengine_video_input_enabled"),
        },
    }


async def main() -> None:
    if not API_KEY:
        raise SystemExit("ARK_API_KEY secret is unavailable")

    result: dict[str, Any] = {
        "schema_version": 2,
        "purpose": "same_endpoint_same_key_same_model_source_type_and_host_label_ownership_differential",
        "endpoint": API_BASE,
        "browser_base_url": BASE_URL,
    }

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(viewport={"width": 1440, "height": 1200})
        page = await context.new_page()
        await login(page)
        await open_providers(page)

        openai_source_id = await configure_source(page, OPENAI_CASE, api_base=API_BASE)
        openai_models = await fetch_real_models(page)
        ark_source_id = await configure_source(page, ARK_CASE, api_base=None)
        ark_models = await fetch_real_models(page)

        common = sorted(set(openai_models).intersection(ark_models))
        if not common:
            raise AssertionError(
                f"same Ark account produced no common model IDs: "
                f"openai_count={len(openai_models)} ark_count={len(ark_models)}"
            )
        model_id = common[0]
        result.update(
            {
                "openai_source_id": openai_source_id,
                "ark_source_id": ark_source_id,
                "openai_model_count": len(openai_models),
                "ark_model_count": len(ark_models),
                "common_model_count": len(common),
                "selected_common_model": model_id,
            }
        )

        await select_source(page, openai_source_id)
        openai_again = await fetch_real_models(page)
        if model_id not in openai_again:
            raise AssertionError("selected common model disappeared from OpenAI@Ark refresh")
        openai_dialog = await open_available_model(page, model_id)
        openai_modalities = await modality_values(openai_dialog)
        result["openai_dialog_modalities"] = openai_modalities
        assert_host_native_prefix(
            openai_modalities,
            openai_modalities,
            object_name="native OpenAI@Ark control",
        )
        if any(item["value"] == "video" for item in openai_modalities):
            raise AssertionError(
                f"OpenAI@Ark dialog leaked Video despite foreign Source type: {openai_modalities!r}"
            )
        await save_model_dialog(openai_dialog)

        await select_source(page, ark_source_id)
        ark_again = await fetch_real_models(page)
        if model_id not in ark_again:
            raise AssertionError("selected common model disappeared from plugin Ark refresh")
        ark_dialog = await open_available_model(page, model_id)
        ark_modalities = await modality_values(ark_dialog)
        result["ark_dialog_modalities_before"] = ark_modalities
        assert_host_native_prefix(
            ark_modalities,
            openai_modalities,
            object_name="plugin Ark@Ark model card",
        )
        video_items = [item for item in ark_modalities if item["value"] == "video"]
        if len(video_items) != 1:
            raise AssertionError(
                f"plugin Ark dialog expected one Video option, got {ark_modalities!r}"
            )
        if video_items[0].get("label") != "视频":
            raise AssertionError(
                f"plugin Ark Video must use the current zh-CN localized fifth label "
                f"without rewriting the first four; got {video_items[0]!r}"
            )
        if bool(video_items[0].get("checked")) is not False:
            raise AssertionError(
                f"new plugin Ark Video must start user-controllable and unchecked; "
                f"got {video_items[0]!r}"
            )
        await enable_video(ark_dialog)
        await save_model_dialog(ark_dialog)

        reopened = await open_configured_model(page, model_id)
        reopened_modalities = await modality_values(reopened)
        result["ark_dialog_modalities_reopened"] = reopened_modalities
        assert_host_native_prefix(
            reopened_modalities,
            openai_modalities,
            object_name="reopened plugin Ark@Ark model card",
        )
        reopened_video = [item for item in reopened_modalities if item["value"] == "video"]
        if (
            len(reopened_video) != 1
            or reopened_video[0]["checked"] is not True
            or reopened_video[0].get("label") != "视频"
        ):
            raise AssertionError(
                f"plugin Ark Video label/state did not persist after reopen: "
                f"{reopened_modalities!r}"
            )
        await reopened.locator(".v-card-actions button").first.click()
        await expect(reopened).to_be_hidden(timeout=10_000)
        await browser.close()

    persisted = _extract_persisted((openai_source_id, ark_source_id), model_id)
    result["persisted"] = persisted
    if persisted["same_nonempty_key"] is not True:
        raise AssertionError("the two Sources were not configured with the same non-empty key")
    if persisted["same_api_base"] is not True:
        raise AssertionError("the two Sources were not configured against the same Ark api_base")
    if persisted["openai_source_type"] != "openai_chat_completion":
        raise AssertionError(f"unexpected OpenAI Source type: {persisted['openai_source_type']!r}")
    if persisted["ark_source_type"] != "volcengine_ark_chat_completion":
        raise AssertionError(f"unexpected plugin Ark Source type: {persisted['ark_source_type']!r}")
    if "video" in (persisted["openai_card"].get("modalities") or []):
        raise AssertionError("foreign OpenAI@Ark card persisted video")
    if persisted["openai_card"]["has_plugin_video_key"]:
        raise AssertionError("foreign OpenAI@Ark card persisted plugin video state")
    if "video" not in (persisted["ark_card"].get("modalities") or []):
        raise AssertionError("plugin Ark card did not persist video modality")
    if persisted["ark_card"]["video_enabled"] is not True:
        raise AssertionError("plugin Ark runtime mirror did not persist enabled=True")

    result["success"] = True
    write_result(result)
    print(
        json.dumps(
            {
                "success": True,
                "selected_common_model": model_id,
                "openai_modalities": result["openai_dialog_modalities"],
                "ark_modalities": result["ark_dialog_modalities_before"],
                "ark_reopened_video_checked": True,
                "same_nonempty_key": True,
                "same_api_base": True,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
