"""轮询创作者中心的私信/评论，对未读消息自动回复。

骨架版本: 只演示打开页面 + 找到未读项 + 输入回复的流程。具体选择器
抖音网页常变，跑起来后建议用 page.pause() 在浏览器里调一下。

用法:
    python -m reply.auto_reply --reply "你好，已收到~"
    python -m reply.auto_reply --reply-fn reply.demo_logic:reply_for

`reply_for(message_text: str) -> str` 是你自己的回复逻辑，可以接 LLM。
"""
import argparse
import asyncio
import importlib
from pathlib import Path
from typing import Callable

from playwright.async_api import Page, async_playwright

from auth.login import STORAGE_STATE, ensure_login

INBOX_URL = "https://creator.douyin.com/creator-micro/data-center/im"
COMMENTS_URL = "https://creator.douyin.com/creator-micro/data/interaction/comment"


def _load_reply_fn(spec: str) -> Callable[[str], str]:
    mod_name, fn_name = spec.split(":", 1)
    mod = importlib.import_module(mod_name)
    return getattr(mod, fn_name)


async def _reply_inbox(page: Page, reply_fn: Callable[[str], str]) -> int:
    """打开私信页，对未读对话回复。返回处理条数。"""
    await page.goto(INBOX_URL, wait_until="domcontentloaded")
    await page.wait_for_timeout(2000)

    # 未读会话项: 抖音用红点标识，class 名经常变；下面是常见之一
    unread = page.locator('[class*="unread"], [class*="Unread"]')
    n = await unread.count()
    handled = 0
    for i in range(n):
        item = unread.nth(i)
        try:
            await item.click()
            await page.wait_for_timeout(800)
            # 取最近一条对方消息的纯文本
            last_msg = page.locator('[class*="message"]').last
            text = (await last_msg.inner_text()).strip() if await last_msg.count() else ""
            answer = reply_fn(text)
            box = page.locator('textarea, [contenteditable="true"]').last
            await box.click()
            await box.type(answer)
            await page.keyboard.press("Enter")
            handled += 1
            await page.wait_for_timeout(500)
        except Exception as e:
            print(f"[reply] 跳过一条: {e}")
    return handled


async def run(
    reply_fn: Callable[[str], str],
    interval_sec: int = 60,
    once: bool = False,
    state_path: Path = STORAGE_STATE,
    headless: bool = False,
) -> None:
    await ensure_login(state_path)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        ctx = await browser.new_context(storage_state=str(state_path))
        page = await ctx.new_page()
        while True:
            try:
                n = await _reply_inbox(page, reply_fn)
                print(f"[reply] 本轮处理 {n} 条")
            except Exception as e:
                print(f"[reply] 轮询出错: {e}")
            if once:
                break
            await asyncio.sleep(interval_sec)
        await ctx.storage_state(path=str(state_path))
        await browser.close()


def _parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reply", help="固定回复文本")
    ap.add_argument("--reply-fn", help="模块路径:函数名，签名 (msg) -> str")
    ap.add_argument("--interval", type=int, default=60, help="轮询秒数")
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--headless", action="store_true")
    return ap.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    if args.reply_fn:
        fn = _load_reply_fn(args.reply_fn)
    elif args.reply:
        fixed = args.reply
        fn = lambda _msg: fixed  # noqa: E731
    else:
        raise SystemExit("必须指定 --reply 或 --reply-fn")
    asyncio.run(run(fn, interval_sec=args.interval, once=args.once, headless=args.headless))
