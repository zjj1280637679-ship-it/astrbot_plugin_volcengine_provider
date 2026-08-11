"""Observable real AstrBot Dashboard browser probe.

This probe intentionally exercises the actual AstrBot login and Provider page.
It is a diagnostic foundation for the provider-card UI matrix, not a substitute
for that matrix.  Every stage writes reviewable evidence so a failure can be
classified as browser/login/route/layout rather than being misattributed to the
provider plugin.

Security note: this probe never writes credential values or browser auth tokens
into artifacts.  DOM snapshots contain labels/text/classes only, not input
values or storage contents.
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
ARTIFACT_DIR = Path(os.environ.get("ASTRBOT_E2E_ARTIFACT_DIR", "e2e-artifacts"))


def _write_json(name: str, payload: Any) -> None:
    (ARTIFACT_DIR / name).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


async def _semantic_snapshot(page: Page, name: str) -> None:
    """Write a secret-free DOM/layout snapshot useful for humans and AI review."""
    payload = await page.evaluate(
        """
        () => {
          const visible = (el) => {
            const style = window.getComputedStyle(el);
            const rect = el.getBoundingClientRect();
            return style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0;
          };
          const clean = (value) => String(value || '').replace(/\\s+/g, ' ').trim().slice(0, 300);
          const nodes = Array.from(document.querySelectorAll(
            'h1,h2,h3,.v-tab,.provider-section-title,.provider-config-title,.provider-config-subtitle,label,button'
          ));
          return {
            href: location.href,
            hash: location.hash,
            title: document.title,
            visible_semantic_nodes: nodes.filter(visible).slice(0, 250).map((el) => ({
              tag: el.tagName.toLowerCase(),
              class: clean(el.className),
              text: clean(el.textContent),
            })),
            layout_counts: {
              provider_page: document.querySelectorAll('.provider-page').length,
              provider_workbench: document.querySelectorAll('.provider-workbench').length,
              provider_sidebar: document.querySelectorAll('.provider-workbench__sidebar').length,
              provider_main: document.querySelectorAll('.provider-workbench__main').length,
              provider_config_shell: document.querySelectorAll('.provider-config-shell').length,
              tabs: document.querySelectorAll('.v-tab').length,
            },
          };
        }
        """
    )
    _write_json(name, payload)


async def main() -> None:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    console_events: list[dict[str, str]] = []
    page_errors: list[str] = []
    api_responses: list[dict[str, Any]] = []
    result: dict[str, Any] = {
        "probe_version": 2,
        "stage": "starting",
        "astrbot_url": BASE_URL,
        "login_page_visible": False,
        "login_succeeded": False,
        "provider_page_visible": False,
        "provider_workbench_visible": False,
        "plugin_runtime_claim": "not_inferred_from_browser_probe",
    }

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(viewport={"width": 1440, "height": 1100})
        page = await context.new_page()

        page.on(
            "console",
            lambda msg: console_events.append(
                {"type": msg.type, "text": msg.text[:2000]}
            ),
        )
        page.on("pageerror", lambda exc: page_errors.append(str(exc)[:4000]))
        page.on(
            "response",
            lambda response: api_responses.append(
                {"url": response.url, "status": response.status}
            )
            if "/api/" in response.url
            else None,
        )

        try:
            result["stage"] = "open_login"
            await page.goto(f"{BASE_URL}/#/auth/login", wait_until="networkidle")
            await page.locator('input[autocomplete="username"]').wait_for(
                state="visible", timeout=30_000
            )
            await page.locator('input[autocomplete="current-password"]').wait_for(
                state="visible", timeout=30_000
            )
            result["login_page_visible"] = True
            result["login_url"] = page.url
            await page.screenshot(
                path=str(ARTIFACT_DIR / "00-login-page.png"), full_page=True
            )
            await _semantic_snapshot(page, "00-login-page.dom.json")

            result["stage"] = "submit_login"
            await page.locator('input[autocomplete="username"]').fill(USERNAME)
            await page.locator('input[autocomplete="current-password"]').fill(PASSWORD)
            await page.locator(".login-btn").click()

            # Playwright's wait_for_url predicate receives a string in current
            # releases.  Observe the browser hash directly to avoid depending on
            # predicate argument representation across Playwright versions.
            await page.wait_for_function(
                "() => !window.location.hash.includes('/auth/login')",
                timeout=30_000,
            )
            result["login_succeeded"] = True
            result["post_login_url"] = page.url

            # Record only storage key names/counts.  Never persist token values.
            storage_state = await context.storage_state()
            result["auth_storage_summary"] = {
                "cookie_names": sorted(
                    {str(cookie.get("name", "")) for cookie in storage_state["cookies"]}
                ),
                "cookie_count": len(storage_state["cookies"]),
                "origin_local_storage_keys": {
                    str(origin.get("origin", "")): sorted(
                        str(item.get("name", ""))
                        for item in origin.get("localStorage", [])
                    )
                    for origin in storage_state["origins"]
                },
            }
            await page.screenshot(
                path=str(ARTIFACT_DIR / "01-post-login.png"), full_page=True
            )
            await _semantic_snapshot(page, "01-post-login.dom.json")

            result["stage"] = "open_providers"
            await page.goto(f"{BASE_URL}/#/providers", wait_until="networkidle")
            await page.locator(".provider-page").wait_for(
                state="visible", timeout=30_000
            )
            result["provider_page_visible"] = True
            await page.screenshot(
                path=str(ARTIFACT_DIR / "02-providers-page.png"), full_page=True
            )
            await _semantic_snapshot(page, "02-providers-page.dom.json")

            result["stage"] = "assert_chat_workbench"
            await page.locator(".provider-workbench").wait_for(
                state="visible", timeout=30_000
            )
            result["provider_workbench_visible"] = True

            body_text = await page.locator("body").inner_text()
            provider_shells = await page.locator(".provider-config-shell").count()
            sidebar_count = await page.locator(".provider-workbench__sidebar").count()
            main_count = await page.locator(".provider-workbench__main").count()
            tab_texts = [
                text.strip()
                for text in await page.locator(".v-tab").all_inner_texts()
                if text.strip()
            ]

            result.update(
                {
                    "url": page.url,
                    "sidebar_count": sidebar_count,
                    "main_count": main_count,
                    "provider_config_shell_count": provider_shells,
                    "provider_tab_texts": tab_texts,
                    "mentions_volcengine": "volcengine" in body_text.lower()
                    or "火山" in body_text,
                }
            )

            if sidebar_count != 1 or main_count != 1:
                raise AssertionError(
                    "chat-completion Provider workbench layout is not the expected two-pane shell"
                )

            result["stage"] = "complete"
            result["success"] = True
        except Exception as exc:
            result["success"] = False
            result["error_type"] = type(exc).__name__
            result["error"] = str(exc)[:4000]
            result["traceback"] = traceback.format_exc()[-12000:]
            result["failure_url"] = page.url
            try:
                await page.screenshot(
                    path=str(ARTIFACT_DIR / "99-failure.png"), full_page=True
                )
                await _semantic_snapshot(page, "99-failure.dom.json")
            except Exception as capture_exc:  # diagnostics must not hide root error
                result["failure_capture_error"] = str(capture_exc)[:2000]
            raise
        finally:
            _write_json("browser-console.json", console_events)
            _write_json("browser-page-errors.json", page_errors)
            _write_json("browser-api-responses.json", api_responses[-500:])
            _write_json("probe-result.json", result)
            print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
