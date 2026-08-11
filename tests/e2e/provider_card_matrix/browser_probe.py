"""Collect reviewable evidence from the real AstrBot Dashboard.

This script intentionally keeps its hard assertions coarse: login must work and
the Provider page must be reachable.  Layout details are evidence, not a
protocol contract.  They are captured for human/AI review instead of turning
Vuetify classes, labels, welcome overlays, or button order into product truth.

Security: credential values, browser auth-token values, input values, and local
storage values are never written to artifacts.
"""

from __future__ import annotations

import asyncio
import json
import os
import traceback
from pathlib import Path
from typing import Any

from playwright.async_api import Page, async_playwright

BASE_URL = os.environ.get("ASTRBOT_E2E_URL", "http://127.0.0.1:6185")
USERNAME = os.environ.get("ASTRBOT_E2E_USERNAME", "e2e-admin")
PASSWORD = os.environ.get("ASTRBOT_E2E_PASSWORD", "E2e-password-123")
ARTIFACT_DIR = Path(os.environ.get("ASTRBOT_E2E_ARTIFACT_DIR", "e2e-artifacts")) / "ui-evidence"


def write_json(name: str, payload: Any) -> None:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    (ARTIFACT_DIR / name).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


async def semantic_snapshot(page: Page, name: str) -> dict[str, Any]:
    """Capture visible semantics and coarse geometry without input values."""
    payload = await page.evaluate(
        r"""
        () => {
          const visible = (el) => {
            const s = getComputedStyle(el);
            const r = el.getBoundingClientRect();
            return s.display !== 'none' && s.visibility !== 'hidden' && r.width > 0 && r.height > 0;
          };
          const clean = (x) => String(x || '').replace(/\s+/g, ' ').trim().slice(0, 500);
          const selectors = 'h1,h2,h3,.v-tab,label,button,[role="button"],.provider-source-item,.provider-model-row,.provider-config-title';
          const nodes = Array.from(document.querySelectorAll(selectors)).filter(visible).slice(0, 400);
          return {
            href: location.href,
            hash: location.hash,
            title: document.title,
            visible_text: clean(document.body?.innerText || '').slice(0, 20000),
            semantic_nodes: nodes.map((el) => ({
              tag: el.tagName.toLowerCase(),
              role: el.getAttribute('role') || '',
              class: clean(el.className),
              text: clean(el.textContent),
              rect: (() => {
                const r = el.getBoundingClientRect();
                return {x: Math.round(r.x), y: Math.round(r.y), width: Math.round(r.width), height: Math.round(r.height)};
              })(),
            })),
            layout_counts: {
              provider_page: document.querySelectorAll('.provider-page').length,
              provider_workbench: document.querySelectorAll('.provider-workbench').length,
              provider_sidebar: document.querySelectorAll('.provider-workbench__sidebar').length,
              provider_main: document.querySelectorAll('.provider-workbench__main').length,
              provider_config_shell: document.querySelectorAll('.provider-config-shell').length,
              provider_source_items: document.querySelectorAll('.provider-source-item').length,
              provider_model_rows: document.querySelectorAll('.provider-model-row').length,
              dialogs: document.querySelectorAll('.v-dialog').length,
              tabs: document.querySelectorAll('.v-tab').length,
            },
          };
        }
        """
    )
    write_json(name, payload)
    return payload


async def main() -> None:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    console_events: list[dict[str, str]] = []
    page_errors: list[str] = []
    api_responses: list[dict[str, Any]] = []
    result: dict[str, Any] = {
        "probe_version": 3,
        "purpose": "ui_evidence_collection",
        "evidence_level": "L4_when_page_observed",
        "layout_assertions_block_release": False,
        "stage": "starting",
        "login_page_visible": False,
        "login_succeeded": False,
        "provider_page_reachable": False,
        "provider_layout_interpretation": "not_decided_by_probe",
    }

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(viewport={"width": 1440, "height": 1100})
        page = await context.new_page()

        page.on("console", lambda msg: console_events.append({"type": msg.type, "text": msg.text[:2000]}))
        page.on("pageerror", lambda exc: page_errors.append(str(exc)[:4000]))
        page.on(
            "response",
            lambda response: api_responses.append({"url": response.url, "status": response.status})
            if "/api/" in response.url else None,
        )

        try:
            result["stage"] = "open_login"
            await page.goto(f"{BASE_URL}/#/auth/login", wait_until="networkidle")
            username = page.locator('input[autocomplete="username"]')
            password = page.locator('input[autocomplete="current-password"]')
            await username.wait_for(state="visible", timeout=30_000)
            await password.wait_for(state="visible", timeout=30_000)
            result["login_page_visible"] = True
            await page.screenshot(path=str(ARTIFACT_DIR / "00-login.png"), full_page=True)
            await semantic_snapshot(page, "00-login.semantic.json")

            result["stage"] = "login"
            await username.fill(USERNAME)
            await password.fill(PASSWORD)
            await page.locator(".login-btn").click()
            await page.wait_for_function("() => !location.hash.includes('/auth/login')", timeout=30_000)
            result["login_succeeded"] = True

            storage_state = await context.storage_state()
            result["auth_storage_summary"] = {
                "cookie_names": sorted({str(item.get("name", "")) for item in storage_state["cookies"]}),
                "cookie_count": len(storage_state["cookies"]),
                "local_storage_keys": {
                    str(origin.get("origin", "")): sorted(str(item.get("name", "")) for item in origin.get("localStorage", []))
                    for origin in storage_state["origins"]
                },
            }

            result["stage"] = "open_providers"
            await page.goto(f"{BASE_URL}/#/providers", wait_until="networkidle")
            # Reachability is the hard browser contract.  Detailed layout is
            # captured below and deliberately not asserted.
            await page.wait_for_function(
                "() => location.hash.includes('/providers') && document.body && document.body.innerText.length > 0",
                timeout=30_000,
            )
            result["provider_page_reachable"] = True
            snapshot = await semantic_snapshot(page, "01-providers.semantic.json")
            await page.screenshot(path=str(ARTIFACT_DIR / "01-providers.png"), full_page=True)

            text_lower = str(snapshot.get("visible_text", "")).lower()
            result["observations"] = {
                "mentions_volcengine": "volcengine" in text_lower or "火山" in str(snapshot.get("visible_text", "")),
                "layout_counts": snapshot.get("layout_counts", {}),
                "visible_text_chars": len(str(snapshot.get("visible_text", ""))),
            }
            result["stage"] = "complete"
            result["success"] = True
        except Exception as exc:
            result["success"] = False
            result["error_type"] = type(exc).__name__
            result["error"] = str(exc)[:4000]
            result["traceback"] = traceback.format_exc()[-12000:]
            try:
                await page.screenshot(path=str(ARTIFACT_DIR / "99-failure.png"), full_page=True)
                await semantic_snapshot(page, "99-failure.semantic.json")
            except Exception as capture_exc:
                result["failure_capture_error"] = str(capture_exc)[:2000]
            raise
        finally:
            write_json("browser-console.json", console_events)
            write_json("browser-page-errors.json", page_errors)
            write_json("browser-api-responses.json", api_responses[-500:])
            write_json("probe-result.json", result)
            print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
