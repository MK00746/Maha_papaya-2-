import asyncio
from playwright.async_api import async_playwright
import json

LOGIN_URL = "https://asean.v-iec.com/#/loginer?redirect=/"
USERNAME = "JP_Global"
PASSWORD = "511511"

async def fetch_latest_wcommon():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(LOGIN_URL)

        await page.fill('input[placeholder="Username"]', USERNAME)
        await page.fill('input[placeholder="Password"]', PASSWORD)
        await page.click('button:has-text("Login")')

        # Wait for `wcommon` to appear in localStorage
        await page.wait_for_timeout(3000)  # wait for 3s after login
        wcommon = await page.evaluate("window.localStorage.getItem('wcommon')")
        await browser.close()

        return json.loads(wcommon) if wcommon else None
