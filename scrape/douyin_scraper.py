"""通过浏览器自动化抓取抖音数据。

思路: 用登录态打开目标页面，监听 XHR/Fetch 响应。抖音前端拿到的数据
都来自 /aweme/v1/web/* 接口，比手动解析 DOM 稳，也避开了 a_bogus 签名。

用法:
    python -m scrape.douyin_scraper user --sec-uid MS4wLjABAAAA...
    python -m scrape.douyin_scraper video --aweme-id 7123456789

输出 JSON 到 stdout。
"""
import argparse
import asyncio
import json
from pathlib import Path

from playwright.async_api import async_playwright

from auth.login import BROWSER_CHANNEL, STORAGE_STATE, ensure_login


async def _capture(url: str, match_path: str, state_path: Path, headless: bool = True) -> list[dict]:
    """打开 url，收集所有路径包含 match_path 的接口响应 JSON。"""
    await ensure_login(state_path)
    captured: list[dict] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless, channel=BROWSER_CHANNEL)
        ctx = await browser.new_context(storage_state=str(state_path))
        page = await ctx.new_page()

        async def on_response(resp):
            if match_path in resp.url:
                try:
                    captured.append(await resp.json())
                except Exception:
                    pass

        page.on("response", on_response)
        await page.goto(url, wait_until="networkidle")
        # 触发滚动以加载更多
        for _ in range(3):
            await page.mouse.wheel(0, 2000)
            await asyncio.sleep(1.5)
        await browser.close()
    return captured


async def fetch_user(sec_uid: str, state_path: Path = STORAGE_STATE) -> list[dict]:
    url = f"https://www.douyin.com/user/{sec_uid}"
    return await _capture(url, "/aweme/v1/web/aweme/post/", state_path)


async def fetch_video(aweme_id: str, state_path: Path = STORAGE_STATE) -> list[dict]:
    url = f"https://www.douyin.com/video/{aweme_id}"
    return await _capture(url, "/aweme/v1/web/aweme/detail/", state_path)


async def fetch_comments(aweme_id: str, state_path: Path = STORAGE_STATE) -> list[dict]:
    url = f"https://www.douyin.com/video/{aweme_id}"
    return await _capture(url, "/aweme/v1/web/comment/list/", state_path)


def _parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    u = sub.add_parser("user", help="抓取用户主页视频列表")
    u.add_argument("--sec-uid", required=True)

    v = sub.add_parser("video", help="抓取视频详情")
    v.add_argument("--aweme-id", required=True)

    c = sub.add_parser("comments", help="抓取视频评论")
    c.add_argument("--aweme-id", required=True)

    return ap.parse_args()


async def _main(args: argparse.Namespace) -> None:
    if args.cmd == "user":
        data = await fetch_user(args.sec_uid)
    elif args.cmd == "video":
        data = await fetch_video(args.aweme_id)
    elif args.cmd == "comments":
        data = await fetch_comments(args.aweme_id)
    else:
        raise SystemExit(f"unknown cmd: {args.cmd}")
    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(_main(_parse_args()))
