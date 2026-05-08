"""扫码登录抖音并保存 storage_state，供 upload/scrape/reply 复用。

用法:
    python -m auth.login
首次运行会弹出 Chromium，需要在 30s 内用抖音 App 扫码。登录成功后
storage_state 会保存到 auth/storage_state.json。
"""
import asyncio
from pathlib import Path

from playwright.async_api import async_playwright

STORAGE_STATE = Path(__file__).parent / "storage_state.json"
CREATOR_HOME = "https://creator.douyin.com/creator-micro/home"
CREATOR_LOGIN = "https://creator.douyin.com/"


async def is_logged_in(state_path: Path) -> bool:
    if not state_path.exists():
        return False
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(storage_state=str(state_path))
        page = await ctx.new_page()
        await page.goto(CREATOR_HOME, wait_until="domcontentloaded")
        try:
            await page.wait_for_url("**/creator-micro/home**", timeout=5000)
            ok = not await page.get_by_text("扫码登录", exact=True).count()
        except Exception:
            ok = False
        await browser.close()
        return ok


async def login(state_path: Path = STORAGE_STATE) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        ctx = await browser.new_context()
        page = await ctx.new_page()
        await page.goto(CREATOR_LOGIN)
        print("[login] 请用抖音 App 扫码登录…")
        # 登录成功后会跳转到 creator-micro/home
        await page.wait_for_url("**/creator-micro/home**", timeout=120_000)
        await ctx.storage_state(path=str(state_path))
        print(f"[login] 登录态已保存: {state_path}")
        await browser.close()


async def ensure_login(state_path: Path = STORAGE_STATE) -> Path:
    if await is_logged_in(state_path):
        print(f"[login] 已登录，复用 {state_path}")
        return state_path
    await login(state_path)
    return state_path


if __name__ == "__main__":
    asyncio.run(ensure_login())
