from __future__ import annotations

import re
from typing import Optional
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from app.tool.base import BaseTool


class FetchUrl(BaseTool):
    """抓取公开网页正文，弥补搜索结果只有标题/摘要的不足。"""

    name: str = "fetch_url"
    description: str = (
        "打开并读取指定 URL 的网页正文（去标签后的纯文本摘要）。"
        "适合在 web_search 之后，对关键链接做二次精读。"
        "注意：部分站点可能拦截抓取；失败时请换链接或仅使用搜索摘要。"
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "要抓取的完整 URL（http/https）。",
            },
            "max_chars": {
                "type": "integer",
                "description": "返回正文的最大字符数，默认 4000。",
            },
        },
        "required": ["url"],
    }

    async def execute(self, url: str, max_chars: int = 4000) -> str:
        url = (url or "").strip()
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return "Error: url 必须是合法的 http/https 链接。"

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
        try:
            async with httpx.AsyncClient(
                follow_redirects=True, timeout=20.0, headers=headers
            ) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                ctype = (resp.headers.get("content-type") or "").lower()
                if "text/html" not in ctype and "text/plain" not in ctype:
                    return f"Error: 不支持的内容类型 {ctype or 'unknown'}"
                html = resp.text
        except Exception as e:
            return f"Error: 抓取失败（{e}）。可换一条公开链接重试。"

        text = self._html_to_text(html)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        if not text:
            return "Error: 页面未解析出有效正文。"
        if len(text) > max_chars:
            text = text[:max_chars] + "\n…(已截断)"
        title = self._guess_title(html)
        head = f"Title: {title}\nURL: {url}\n\n" if title else f"URL: {url}\n\n"
        return head + text

    @staticmethod
    def _guess_title(html: str) -> str:
        try:
            soup = BeautifulSoup(html, "html.parser")
            if soup.title and soup.title.string:
                return " ".join(soup.title.string.split())
        except Exception:
            pass
        return ""

    @staticmethod
    def _html_to_text(html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript", "svg", "iframe"]):
            tag.decompose()
        # 优先主内容区域
        main = (
            soup.find("article")
            or soup.find("main")
            or soup.find(attrs={"id": re.compile("content|article", re.I)})
            or soup.body
            or soup
        )
        return main.get_text("\n", strip=True)
