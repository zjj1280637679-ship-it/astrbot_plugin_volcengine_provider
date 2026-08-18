"""Stable lifecycle entrypoint with repeated post-transition confirmation.

The base 0.1.24 lifecycle contract already separates Dashboard refresh, process
restart, same-version replacement and uninstall.  This wrapper additionally
tests the normal AstrBot plugin-config hot-reload path: save plugin settings
through the real Dashboard API, wait for the plugin to reinitialize/rebind live
owned Provider instances, then re-confirm UI/persistence in the same process.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
from typing import Any

from playwright.async_api import Page

import lifecycle_matrix_0_1_24 as base


PLUGIN_NAME = "astrbot_plugin_volcengine_provider"
SERVER_LOG_PATH = Path(
    os.environ.get("ASTRBOT_E2E_SERVER_LOG", "/tmp/astrbot-lifecycle.log")
)


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

    await base.open_providers(page)
    await base.select_source(page, str(state["openai_source_id"]))
    foreign_dialog = await base.open_configured_model(
        page, base.OPENAI_CASE.model_id
    )
    foreign_ui = await base.assert_foreign_dialog(
        foreign_dialog,
        stage=f"{stage}/foreign-reopen",
    )

    persisted = base.assert_persisted_state(state, stage=stage)
    return {"owned": ark_ui, "foreign": foreign_ui, "persisted": persisted}


async def _wait_for_log_marker(marker: str, *, timeout_seconds: float = 20.0) -> None:
    deadline = asyncio.get_running_loop().time() + timeout_seconds
    while asyncio.get_running_loop().time() < deadline:
        try:
            text = SERVER_LOG_PATH.read_text("utf-8", errors="replace")
        except OSError:
            text = ""
        if marker in text:
            return
        await asyncio.sleep(0.25)
    raise AssertionError(f"timed out waiting for lifecycle log marker: {marker!r}")


async def hot_config_reload_stage(page: Page) -> dict[str, Any]:
    """Change runtime policy through AstrBot's real plugin-config API."""
    endpoint = f"{base.BASE_URL}/api/v1/plugins/config"
    response = await page.request.get(
        endpoint,
        params={"plugin_id": PLUGIN_NAME},
    )
    if not response.ok:
        raise AssertionError(
            f"plugin config GET failed: status={response.status} body={await response.text()}"
        )
    payload = await response.json()
    if payload.get("status") not in {"ok", "success"}:
        raise AssertionError(f"plugin config GET returned failure: {payload!r}")

    data = payload.get("data")
    current = data.get("config") if isinstance(data, dict) else None
    if not isinstance(current, dict):
        raise AssertionError(f"plugin config response has no config object: {payload!r}")

    updated = dict(current)
    updated.update(
        {
            "video_max_mb": 1,
            "image_max_mb": 2,
            "cache_log_enabled": True,
            "cache_log_every": 3,
        }
    )

    if SERVER_LOG_PATH.exists():
        with SERVER_LOG_PATH.open("a", encoding="utf-8") as stream:
            stream.write("\n[LIFECYCLE] about-to-save-hot-policy\n")

    saved = await page.request.put(
        endpoint,
        data={"plugin_id": PLUGIN_NAME, "config": updated},
    )
    if not saved.ok:
        raise AssertionError(
            f"plugin config PUT failed: status={saved.status} body={await saved.text()}"
        )
    saved_payload = await saved.json()
    if saved_payload.get("status") not in {"ok", "success"}:
        raise AssertionError(f"plugin config PUT returned failure: {saved_payload!r}")

    marker = (
        "[VolcenginePolicy] lifecycle-confirm phase=plugin-initialize "
        "provider_reloads=1"
    )
    await _wait_for_log_marker(marker)
    await _wait_for_log_marker(
        "audio=25MiB video=1MiB image=2MiB cache=True/every=3"
    )

    verify = await verify_installed_stage(
        page,
        stage="after-hot-config-reload",
    )

    reread = await page.request.get(
        endpoint,
        params={"plugin_id": PLUGIN_NAME},
    )
    reread_payload = await reread.json()
    reread_data = reread_payload.get("data")
    persisted_plugin_config = (
        reread_data.get("config") if isinstance(reread_data, dict) else None
    )
    if not isinstance(persisted_plugin_config, dict):
        raise AssertionError(
            f"plugin config reread has no config object: {reread_payload!r}"
        )
    expected = {
        "video_max_mb": 1,
        "image_max_mb": 2,
        "cache_log_enabled": True,
        "cache_log_every": 3,
    }
    actual = {key: persisted_plugin_config.get(key) for key in expected}
    if actual != expected:
        raise AssertionError(
            f"hot-reload plugin config did not persist: expected={expected!r} actual={actual!r}"
        )

    return {
        "saved_policy": expected,
        "post_reload": verify,
        "provider_rebind_marker": marker,
    }


async def run_hot_stage() -> None:
    base.ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    result: dict[str, Any] = {
        "stage": "after-hot-config-reload",
        "success": False,
    }
    async with base.async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(viewport={"width": 1440, "height": 1200})
        page = await context.new_page()
        try:
            await base.login(page)
            result["evidence"] = await hot_config_reload_stage(page)
            result["success"] = True
        finally:
            await base.cancel_visible_dialogs(page)
            await browser.close()

    base.write_json(
        base.ARTIFACT_DIR / "after-hot-config-reload.json",
        result,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


async def run(stage: str) -> None:
    base.verify_installed_stage = verify_installed_stage
    if stage == "after-hot-config-reload":
        await run_hot_stage()
        return
    await base.run(stage)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--stage",
        required=True,
        choices=(
            "setup",
            "after-hot-config-reload",
            "after-restart",
            "after-same-version-update",
            "uninstalled",
        ),
    )
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(run(parse_args().stage))
