from __future__ import annotations

import base64
from playwright.async_api import async_playwright, Browser, Page, BrowserContext

VIEWPORT = {"width": 1280, "height": 900}

_playwright = None
_browser: Browser | None = None


async def _get_browser() -> Browser:
    global _playwright, _browser
    if _browser is None or not _browser.is_connected():
        _playwright = await async_playwright().start()
        _browser = await _playwright.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"],
        )
    return _browser


async def create_page(url: str) -> tuple[Page, BrowserContext, str]:
    """Create a new browser page, navigate to URL, return (page, context, screenshot_base64)."""
    b = await _get_browser()
    context = await b.new_context(
        viewport=VIEWPORT,
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
    )
    page = await context.new_page()
    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
    await page.wait_for_timeout(2000)

    screenshot_bytes = await page.screenshot(type="png")
    screenshot = base64.b64encode(screenshot_bytes).decode()

    return page, context, screenshot


async def take_screenshot(page: Page) -> str:
    buf = await page.screenshot(type="png")
    return base64.b64encode(buf).decode()


async def perform_click(page: Page, x: int, y: int) -> str:
    await page.mouse.click(x, y)
    await page.wait_for_timeout(1500)
    return await take_screenshot(page)


async def perform_hover(page: Page, x: int, y: int) -> str:
    await page.mouse.move(x, y)
    await page.wait_for_timeout(800)
    return await take_screenshot(page)


async def perform_type(page: Page, text: str) -> str:
    await page.keyboard.type(text, delay=50)
    await page.wait_for_timeout(500)
    return await take_screenshot(page)


async def perform_press(page: Page, key: str) -> str:
    await page.keyboard.press(key)
    await page.wait_for_timeout(800)
    return await take_screenshot(page)


async def perform_scroll(page: Page, direction: str) -> str:
    delta = 500 if direction == "down" else -500
    await page.mouse.wheel(0, delta)
    await page.wait_for_timeout(800)
    return await take_screenshot(page)


async def perform_goto(page: Page, url: str) -> str:
    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
    await page.wait_for_timeout(2000)
    return await take_screenshot(page)


async def perform_go_back(page: Page) -> str:
    try:
        await page.go_back(wait_until="domcontentloaded", timeout=10000)
    except Exception:
        pass
    await page.wait_for_timeout(1500)
    return await take_screenshot(page)


async def perform_go_forward(page: Page) -> str:
    try:
        await page.go_forward(wait_until="domcontentloaded", timeout=10000)
    except Exception:
        pass
    await page.wait_for_timeout(1500)
    return await take_screenshot(page)


async def shutdown() -> None:
    global _browser, _playwright
    if _browser:
        await _browser.close()
        _browser = None
    if _playwright:
        await _playwright.stop()
        _playwright = None
