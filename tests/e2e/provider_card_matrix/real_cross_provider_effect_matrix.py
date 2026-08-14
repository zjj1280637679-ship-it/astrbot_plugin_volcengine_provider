"""Real cross-provider effect matrix for the 0.1.24 model-card contract.

This runs one AstrBot 4.27.3 process with the plugin loaded and compares three
real Source objects:

1. OpenAI Compatible pointed at Volcengine Ark, using the real Ark key.
2. The plugin-owned Volcengine Ark Source, using the same Ark key/endpoint/model.
3. AstrBot's native DeepSeek Source, using the real DeepSeek key.

The acceptance target is object ownership:
- the two foreign cards must not gain Video or any visible ``volcengine_*`` rows;
- the plugin-owned Ark card must gain exactly one native Video modality and all
  lower plugin model fields;
- only the owned Ark card may persist plugin-owned request settings.

Secrets are used only at runtime.  They are never serialized into artifacts.
"""

from __future__ import annotations

import asyncio
import json
import os
import traceback
from pathlib import Path
from typing import Any

from playwright.async_api import Locator, Page, async_playwright, expect

from browser_matrix import (
    Case,
    add_source,
    login,
    open_configured_model,
    open_providers,
    save_model_dialog,
    save_source,
    select_source,
    semantic_page_snapshot,
    visible_config_rows,
)
from capabilities.model_fields import MODEL_SETTING_KEYS

ARK_API_BASE = "https://ark.cn-beijing.volces.com/api/v3"
ARK_API_KEY = os.environ.get("ARK_API_KEY", "").strip()
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEKAPI", "").strip()
ARTIFACT_DIR = (
    Path(os.environ.get("ASTRBOT_E2E_ARTIFACT_DIR", "e2e-artifacts"))
    / "real-cross-provider-effect"
)
CONFIG_PATH = Path(
    os.environ.get("ASTRBOT_E2E_CONFIG_PATH", "AstrBot/data/cmd_config.json")
)

OPENAI_ARK_CASE = Case(
    name="foreign_openai_on_ark",
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
DEEPSEEK_CASE = Case(
    name="foreign_deepseek",
    template_key="DeepSeek",
    menu_label="DeepSeek",
    expected_source_id="deepseek",
    model_id="unused",
    owned=False,
)


def redact(text: str) -> str:
    result = str(text)
    for secret in (ARK_API_KEY, DEEPSEEK_API_KEY):
        if secret:
            result = result.replace(secret, "<redacted>")
    return result


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
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
    row = await row_for_key(page.locator(".provider-config-shell"), key)
    control = row.locator("input").first
    await expect(control).to_be_visible(timeout=10_000)
    await control.fill(value)
    if await control.input_value() != value:
        raise AssertionError(f"Source field did not retain key={key!r}")


async def configure_source(
    page: Page,
    case: Case,
    *,
    api_key: str,
    api_base: str | None,
) -> str:
    source_id = await add_source(page, case)
    await fill_source_field(page, "key", api_key)
    if api_base is not None:
        await fill_source_field(page, "api_base", api_base)
    await save_source(page)
    return source_id


async def fetch_models(page: Page) -> list[str]:
    button = page.locator(
        ".provider-models-toolbar__actions button:has(.mdi-download)"
    ).first
    await expect(button).to_be_visible(timeout=10_000)
    await button.click()

    rows = page.locator(
        ".provider-models-section--available .provider-model-row__title"
    )
    await expect(rows.first).to_be_visible(timeout=60_000)
    values = [str(value or "").strip() for value in await rows.all_text_contents()]
    return list(dict.fromkeys(value for value in values if value))


async def open_available_model(page: Page, model_id: str) -> Locator:
    row = page.locator(
        ".provider-models-section--available .provider-model-row",
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


async def visible_plugin_keys(dialog: Locator) -> list[str]:
    rows = await visible_config_rows(dialog)
    return sorted(
        {
            str(row.get("key") or "")
            for row in rows
            if str(row.get("key") or "").startswith("volcengine_")
        }
    )


async def inspect_foreign(dialog: Locator, *, stage: str) -> dict[str, Any]:
    modalities = await modality_values(dialog)
    plugin_keys = await visible_plugin_keys(dialog)
    if any(item.get("value") == "video" for item in modalities):
        raise AssertionError(f"{stage}: foreign card leaked Video: {modalities!r}")
    if plugin_keys:
        raise AssertionError(f"{stage}: foreign card leaked plugin rows: {plugin_keys!r}")
    return {
        "modalities": modalities,
        "video_present": False,
        "visible_volcengine_keys": plugin_keys,
    }


async def inspect_owned_ark(dialog: Locator, *, stage: str) -> dict[str, Any]:
    modalities = await modality_values(dialog)
    video = [item for item in modalities if item.get("value") == "video"]
    if len(video) != 1:
        raise AssertionError(f"{stage}: expected exactly one Video item: {modalities!r}")
    if video[0].get("label") != "视频":
        raise AssertionError(f"{stage}: unexpected Video label: {video[0]!r}")

    plugin_keys = await visible_plugin_keys(dialog)
    expected = sorted(MODEL_SETTING_KEYS)
    if plugin_keys != expected:
        raise AssertionError(
            f"{stage}: visible owned plugin rows differ; expected={expected!r} actual={plugin_keys!r}"
        )
    return {
        "modalities": modalities,
        "video_present": True,
        "video_checked": bool(video[0].get("checked")),
        "visible_volcengine_keys": plugin_keys,
    }


async def enable_video(dialog: Locator) -> None:
    row = await row_for_key(dialog, "modalities")
    checkbox = row.locator('input[type="checkbox"][value="video"]').first
    await expect(checkbox).to_be_visible(timeout=5_000)
    await checkbox.set_checked(True, force=True)
    await expect(checkbox).to_be_checked(timeout=5_000)


async def set_owned_temperature(dialog: Locator, value: str) -> None:
    row = await row_for_key(dialog, "volcengine_temperature")
    control = row.locator("input").first
    await expect(control).to_be_visible(timeout=5_000)
    await control.fill(value)
    if await control.input_value() != value:
        raise AssertionError("owned Ark temperature field did not retain test value")


def persisted_matrix(
    *,
    openai_source_id: str,
    ark_source_id: str,
    deepseek_source_id: str,
    ark_model_id: str,
    deepseek_model_id: str,
) -> dict[str, Any]:
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

    openai_source = sources.get(openai_source_id, {})
    ark_source = sources.get(ark_source_id, {})
    deepseek_source = sources.get(deepseek_source_id, {})

    openai_provider_id = f"{openai_source_id}/{ark_model_id}"
    ark_provider_id = f"{ark_source_id}/{ark_model_id}"
    deepseek_provider_id = f"{deepseek_source_id}/{deepseek_model_id}"
    openai = providers.get(openai_provider_id)
    ark = providers.get(ark_provider_id)
    deepseek = providers.get(deepseek_provider_id)
    if not all(isinstance(item, dict) for item in (openai, ark, deepseek)):
        raise AssertionError(
            "persisted cross-provider cards missing: "
            f"openai={bool(openai)} ark={bool(ark)} deepseek={bool(deepseek)}"
        )

    def plugin_keys(card: dict[str, Any]) -> list[str]:
        return sorted(key for key in card if str(key).startswith("volcengine_"))

    openai_plugin_keys = plugin_keys(openai)
    ark_plugin_keys = plugin_keys(ark)
    deepseek_plugin_keys = plugin_keys(deepseek)

    if "video" in (openai.get("modalities") or []):
        raise AssertionError("persisted OpenAI@Ark foreign card gained Video")
    if "video" in (deepseek.get("modalities") or []):
        raise AssertionError("persisted DeepSeek foreign card gained Video")
    if openai_plugin_keys:
        raise AssertionError(f"persisted OpenAI@Ark leaked plugin keys: {openai_plugin_keys!r}")
    if deepseek_plugin_keys:
        raise AssertionError(f"persisted DeepSeek leaked plugin keys: {deepseek_plugin_keys!r}")
    if "video" not in (ark.get("modalities") or []):
        raise AssertionError("persisted owned Ark card lost Video")
    if ark.get("volcengine_video_input_enabled") is not True:
        raise AssertionError("persisted owned Ark card did not retain Video transport=true")
    if ark.get("volcengine_temperature") != 0.7:
        raise AssertionError(
            f"persisted owned Ark temperature mismatch: {ark.get('volcengine_temperature')!r}"
        )

    openai_key = openai_source.get("key")
    ark_key = ark_source.get("key")
    deepseek_key = deepseek_source.get("key")

    return {
        "sources": {
            "openai_on_ark": {
                "id": openai_source_id,
                "type": openai_source.get("type"),
                "provider": openai_source.get("provider"),
                "api_base": openai_source.get("api_base"),
                "key_present": bool(openai_key),
            },
            "plugin_ark": {
                "id": ark_source_id,
                "type": ark_source.get("type"),
                "provider": ark_source.get("provider"),
                "api_base": ark_source.get("api_base"),
                "key_present": bool(ark_key),
            },
            "deepseek": {
                "id": deepseek_source_id,
                "type": deepseek_source.get("type"),
                "provider": deepseek_source.get("provider"),
                "api_base": deepseek_source.get("api_base"),
                "key_present": bool(deepseek_key),
            },
            "same_ark_key": bool(openai_key) and openai_key == ark_key,
            "same_ark_api_base": str(openai_source.get("api_base") or "").rstrip("/")
            == str(ark_source.get("api_base") or "").rstrip("/"),
        },
        "cards": {
            "openai_on_ark": {
                "provider_id": openai_provider_id,
                "model": openai.get("model"),
                "modalities": openai.get("modalities"),
                "plugin_keys": openai_plugin_keys,
            },
            "plugin_ark": {
                "provider_id": ark_provider_id,
                "model": ark.get("model"),
                "modalities": ark.get("modalities"),
                "video_enabled": ark.get("volcengine_video_input_enabled"),
                "temperature": ark.get("volcengine_temperature"),
                "plugin_keys": ark_plugin_keys,
            },
            "deepseek": {
                "provider_id": deepseek_provider_id,
                "model": deepseek.get("model"),
                "modalities": deepseek.get("modalities"),
                "plugin_keys": deepseek_plugin_keys,
            },
        },
        "credentials_serialized": False,
    }


async def run() -> None:
    if not ARK_API_KEY:
        raise AssertionError("ARK_API_KEY secret is unavailable")
    if not DEEPSEEK_API_KEY:
        raise AssertionError("DEEPSEEKAPI secret is unavailable")

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    result: dict[str, Any] = {
        "success": False,
        "purpose": "real_cross_provider_plugin_effect_matrix",
        "ark_api_base": ARK_API_BASE,
        "credentials_serialized": False,
    }
    failure: BaseException | None = None

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(viewport={"width": 1440, "height": 1200})
        page = await context.new_page()
        try:
            await login(page)
            await open_providers(page)

            openai_source_id = await configure_source(
                page,
                OPENAI_ARK_CASE,
                api_key=ARK_API_KEY,
                api_base=ARK_API_BASE,
            )
            openai_models = await fetch_models(page)

            ark_source_id = await configure_source(
                page,
                ARK_CASE,
                api_key=ARK_API_KEY,
                api_base=None,
            )
            ark_models = await fetch_models(page)

            deepseek_source_id = await configure_source(
                page,
                DEEPSEEK_CASE,
                api_key=DEEPSEEK_API_KEY,
                api_base=None,
            )
            deepseek_models = await fetch_models(page)

            openai_set = set(openai_models)
            ark_set = set(ark_models)
            if openai_set != ark_set:
                raise AssertionError(
                    "same Ark key/endpoint produced different model sets: "
                    f"openai_only={sorted(openai_set - ark_set)[:20]!r} "
                    f"ark_only={sorted(ark_set - openai_set)[:20]!r}"
                )
            if not ark_models:
                raise AssertionError("Ark model discovery returned no models")
            if not deepseek_models:
                raise AssertionError("DeepSeek model discovery returned no models")

            ark_model_id = sorted(ark_set)[0]
            deepseek_model_id = deepseek_models[0]
            result["model_discovery"] = {
                "openai_on_ark_count": len(openai_models),
                "plugin_ark_count": len(ark_models),
                "same_ark_model_set": True,
                "selected_shared_ark_model": ark_model_id,
                "deepseek_count": len(deepseek_models),
                "deepseek_models": deepseek_models,
                "selected_deepseek_model": deepseek_model_id,
            }

            await select_source(page, openai_source_id)
            openai_dialog = await open_available_model(page, ark_model_id)
            result["openai_on_ark_unsaved"] = await inspect_foreign(
                openai_dialog,
                stage="openai-on-ark/unsaved",
            )
            await save_model_dialog(openai_dialog)
            openai_reopened = await open_configured_model(page, ark_model_id)
            result["openai_on_ark_reopened"] = await inspect_foreign(
                openai_reopened,
                stage="openai-on-ark/reopened",
            )
            await openai_reopened.locator(".v-card-actions button").first.click()
            await expect(openai_reopened).to_be_hidden(timeout=10_000)

            await select_source(page, ark_source_id)
            ark_dialog = await open_available_model(page, ark_model_id)
            result["plugin_ark_unsaved"] = await inspect_owned_ark(
                ark_dialog,
                stage="plugin-ark/unsaved",
            )
            await enable_video(ark_dialog)
            await set_owned_temperature(ark_dialog, "0.7")
            await save_model_dialog(ark_dialog)
            ark_reopened = await open_configured_model(page, ark_model_id)
            ark_reopened_state = await inspect_owned_ark(
                ark_reopened,
                stage="plugin-ark/reopened",
            )
            if ark_reopened_state.get("video_checked") is not True:
                raise AssertionError("plugin Ark Video state did not persist after reopen")
            temperature_row = await row_for_key(ark_reopened, "volcengine_temperature")
            temperature_value = await temperature_row.locator("input").first.input_value()
            if temperature_value not in {"0.7", "0.70"}:
                raise AssertionError(
                    f"plugin Ark temperature UI did not persist: {temperature_value!r}"
                )
            ark_reopened_state["temperature_value"] = temperature_value
            result["plugin_ark_reopened"] = ark_reopened_state
            await ark_reopened.locator(".v-card-actions button").first.click()
            await expect(ark_reopened).to_be_hidden(timeout=10_000)

            await select_source(page, deepseek_source_id)
            deepseek_dialog = await open_available_model(page, deepseek_model_id)
            result["deepseek_unsaved"] = await inspect_foreign(
                deepseek_dialog,
                stage="deepseek/unsaved",
            )
            await save_model_dialog(deepseek_dialog)
            deepseek_reopened = await open_configured_model(page, deepseek_model_id)
            result["deepseek_reopened"] = await inspect_foreign(
                deepseek_reopened,
                stage="deepseek/reopened",
            )
            await deepseek_reopened.locator(".v-card-actions button").first.click()
            await expect(deepseek_reopened).to_be_hidden(timeout=10_000)

            result["persisted"] = persisted_matrix(
                openai_source_id=openai_source_id,
                ark_source_id=ark_source_id,
                deepseek_source_id=deepseek_source_id,
                ark_model_id=ark_model_id,
                deepseek_model_id=deepseek_model_id,
            )
            if result["persisted"]["sources"]["same_ark_key"] is not True:
                raise AssertionError("same Ark secret was not persisted identically")
            if result["persisted"]["sources"]["same_ark_api_base"] is not True:
                raise AssertionError("OpenAI@Ark and plugin Ark did not use same api_base")

            result["effect_summary"] = {
                "foreign_openai_on_ark_video": False,
                "plugin_ark_video": True,
                "foreign_deepseek_video": False,
                "foreign_openai_on_ark_plugin_rows": 0,
                "plugin_ark_plugin_rows": len(MODEL_SETTING_KEYS),
                "foreign_deepseek_plugin_rows": 0,
                "ownership_boundary_proven": True,
            }
            result["success"] = True
        except BaseException as exc:
            failure = exc
            result["error_type"] = type(exc).__name__
            result["error"] = redact(str(exc))
            result["traceback"] = redact(traceback.format_exc())
            try:
                await semantic_page_snapshot(
                    page,
                    ARTIFACT_DIR / "failure-page.dom.json",
                )
            except Exception as snapshot_exc:
                result["snapshot_error"] = redact(str(snapshot_exc))
        finally:
            await browser.close()

    write_json(ARTIFACT_DIR / "result.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    if failure is not None:
        raise failure


if __name__ == "__main__":
    asyncio.run(run())
