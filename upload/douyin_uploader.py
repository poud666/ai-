"""上传视频到抖音创作者中心。

用法:
    python -m upload.douyin_uploader path/to/video.mp4 \
        --title "标题" --tags 旅行 美食 --desc "描述文字"

参考 dreammis/social-auto-upload 的发布流程，去掉了商品、定时、封面等
非必要项；如需扩展可在 upload_video 内追加步骤。
"""
import argparse
import asyncio
from pathlib import Path

from playwright.async_api import Page, async_playwright

from auth.login import BROWSER_CHANNEL, STORAGE_STATE, ensure_login

UPLOAD_URL = "https://creator.douyin.com/creator-micro/content/upload"


async def _fill_title_and_desc(page: Page, title: str, desc: str, tags: list[str]) -> None:
    section = (
        page.get_by_text("作品描述", exact=True)
        .locator("xpath=ancestor::div[2]")
        .locator("xpath=following-sibling::div[1]")
    )
    title_input = section.locator('input[type="text"]').first
    await title_input.wait_for(state="visible", timeout=10_000)
    await title_input.fill(title[:30])

    editor = section.locator('.zone-container[contenteditable="true"]').first
    await editor.wait_for(state="visible", timeout=10_000)
    await editor.click()
    await page.keyboard.press("Control+KeyA")
    await page.keyboard.press("Delete")
    await page.keyboard.type(desc or title)
    for tag in tags:
        await page.keyboard.type(f" #{tag}")
        await page.keyboard.press("Space")


async def _wait_video_uploaded(page: Page) -> None:
    while True:
        if await page.locator('[class^="long-card"] div:has-text("重新上传")').count():
            return
        await asyncio.sleep(2)


async def _click_publish(page: Page) -> None:
    while True:
        try:
            btn = page.get_by_role("button", name="发布", exact=True)
            if await btn.count():
                await btn.click()
            await page.wait_for_url("**/creator-micro/content/manage**", timeout=3000)
            return
        except Exception:
            await asyncio.sleep(0.5)


async def upload_video(
    file_path: str,
    title: str,
    tags: list[str],
    desc: str = "",
    state_path: Path = STORAGE_STATE,
    headless: bool = False,
) -> None:
    file_path = str(Path(file_path).expanduser().resolve())
    await ensure_login(state_path)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless, channel=BROWSER_CHANNEL)
        ctx = await browser.new_context(storage_state=str(state_path))
        page = await ctx.new_page()

        await page.goto(UPLOAD_URL)
        await page.wait_for_url(UPLOAD_URL)
        print(f"[upload] 选择文件 {file_path}")
        await page.locator("div[class^='container'] input").set_input_files(file_path)

        # 跳到发布页（两种 URL 结构都兼容）
        for _ in range(120):
            url = page.url
            if "publish?enter_from=publish_page" in url or "post/video?enter_from=publish_page" in url:
                break
            await asyncio.sleep(0.5)

        await asyncio.sleep(1)
        await _fill_title_and_desc(page, title, desc, tags)
        print("[upload] 等待视频上传完成…")
        await _wait_video_uploaded(page)
        print("[upload] 点击发布")
        await _click_publish(page)
        await ctx.storage_state(path=str(state_path))
        print("[upload] 发布成功")
        await browser.close()


def _parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("file", help="本地视频路径，建议 mp4")
    ap.add_argument("--title", required=True)
    ap.add_argument("--tags", nargs="*", default=[])
    ap.add_argument("--desc", default="")
    ap.add_argument("--headless", action="store_true")
    return ap.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    asyncio.run(
        upload_video(
            args.file,
            title=args.title,
            tags=args.tags,
            desc=args.desc,
            headless=args.headless,
        )
    )
