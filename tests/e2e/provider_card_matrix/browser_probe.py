"""Minimal real AstrBot Dashboard browser probe.

This intentionally tests the actual login page and Provider page served by a
running AstrBot instance. It is the foundation for provider-card layout
snapshots; it does not yet assert every card layout.
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from playwright.async_api import async_playwright

BASE_URL = os.environ.get("ASTRBOT_E2E_URL", "http://127.0.0.1:6185")
USERNAME = os.environ.get("ASTRBOT_E2E_USERNAME", "e2e-admin")
PASSWORD = os.environ.get("ASTRBOT_E2E_PASSWORD", "e2e-password")
ARTIFACT_DIR = Path(os.environ.get("ASTRBOT_E2E_ARTIFACT_DIR", "e2e-artifacts"))


async def main() -> None:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1440, "height": 1100})

        await page.goto(f"{BASE_URL}/#/auth/login", wait_until="networkidle")
        await page.locator('input[autocomplete="username"]').fill(USERNAME)
        await page.locator('input[autocomplete="current-password"]').fill(PASSWORD)
        await page.locator(".login-btn").click()
        await page.wait_for_url(lambda url: "/auth/login" not in url.fragment, timeout=30_000)

        await page.goto(f"{BASE_URL}/#/providers", wait_until="networkidle")
        await page.locator(".provider-page").wait_for(state="visible", timeout=30_000)
        await page.locator(".provider-workbench").wait_for(state="visible", timeout=30_000)

        # Keep a human/AI-reviewable visual artifact and a small semantic probe.
        await page.screenshot(path=str(ARTIFACT_DIR / "providers-root.png"), full_page=True)
        body_text = await page.locator("body").inner_text()
        provider_shells = await page.locator(".provider-config-shell").count()
        sidebar_count = await page.locator(".provider-workbench__sidebar").count()
        main_count = await page.locator(".provider-workbench__main").count()

        result = {
            "url": page.url,
            "provider_page_visible": True,
            "provider_workbench_visible": True,
            "sidebar_count": sidebar_count,
            "main_count": main_count,
            "provider_config_shell_count": provider_shells,
            "mentions_volcengine": "volcengine" in body_text.lower() or "火山" in body_text,
        }
        (ARTIFACT_DIR / "browser-probe.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))

        if sidebar_count != 1 or main_count != 1:
            raise AssertionError("chat-completion Provider workbench layout is not the expected two-pane shell")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
