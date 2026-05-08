# ai-

抖音网页版自动化工具集（Playwright 浏览器自动化）。

## 功能

- `auth/` 扫码登录抖音，保存登录态到 `storage_state.json`
- `upload/` 自动上传视频到抖音创作者中心
- `scrape/` 通过监听 XHR 抓取用户/视频/评论数据
- `reply/` 轮询创作者中心私信，对未读消息自动回复

## 安装

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

## 使用

### 1. 登录（首次必跑）

```bash
python -m auth.login
```

会弹出 Chromium，用抖音 App 扫码。成功后 `auth/storage_state.json` 保存登录态，
之后其他模块都会自动复用，过期了会再次弹出扫码。

### 2. 发布视频

```bash
python -m upload.douyin_uploader path/to/video.mp4 \
    --title "今日份的猫片" \
    --tags 猫咪 萌宠 \
    --desc "这是描述"
```

### 3. 抓取数据

```bash
# 用户主页视频列表
python -m scrape.douyin_scraper user --sec-uid MS4wLjABAAAA...

# 单个视频详情
python -m scrape.douyin_scraper video --aweme-id 7123456789

# 视频评论
python -m scrape.douyin_scraper comments --aweme-id 7123456789
```

### 4. 自动回复私信

```bash
# 固定回复
python -m reply.auto_reply --reply "你好，已收到~" --interval 60

# 自定义回复逻辑（接 LLM 也行）
python -m reply.auto_reply --reply-fn mymod.replies:answer
```

`mymod/replies.py`:
```python
def answer(msg: str) -> str:
    return f"收到你说的: {msg[:20]}…"
```

## 注意

- 抖音网页风控严格。批量自动化操作账号有封号风险，自用脚本可以，规模化谨慎。
- DOM 选择器（特别是私信页）抖音会改，跑不动时用 `await page.pause()` 调试。
- `auth/storage_state.json` 含登录凭证，**绝对不要提交**（已在 `.gitignore`）。

## 致谢

发布逻辑参考自 [dreammis/social-auto-upload](https://github.com/dreammis/social-auto-upload)。
