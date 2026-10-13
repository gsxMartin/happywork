from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Callable

import requests

from ..models import ContentItem, ContentType

logger = logging.getLogger(__name__)

# 部分站点会拦截默认的 python-requests UA，这里使用常见浏览器 UA。
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)


def _http_get(url: str, timeout: float) -> bytes:
    resp = requests.get(url, timeout=timeout, headers={"User-Agent": _USER_AGENT})
    resp.raise_for_status()
    return resp.content


def parse_hitokoto(raw: bytes) -> str | None:
    """解析「一言」接口的 JSON，取 hitokoto 字段。"""
    data = json.loads(raw.decode("utf-8"))
    text = (data.get("hitokoto") or "").strip()
    return text or None


def parse_shadiao(raw: bytes) -> str | None:
    """解析 shadiao 系列接口的 JSON，取 data.text 字段。"""
    data = json.loads(raw.decode("utf-8"))
    text = ((data.get("data") or {}).get("text") or "").strip()
    return text or None


def parse_plain(raw: bytes) -> str | None:
    """解析纯文本接口，直接返回去除首尾空白后的文本。"""
    text = raw.decode("utf-8", errors="replace").strip()
    return text or None


@dataclass(frozen=True)
class QuipSource:
    """一个联网趣味来源：如何取、如何解析。"""

    name: str
    url: str
    parse: Callable[[bytes], str | None]


# 中文趣味来源清单：只提供「乐子」，不含任何资讯 / 新闻。
SOURCES: tuple[QuipSource, ...] = (
    QuipSource("一言", "https://v1.hitokoto.cn/?c=l", parse_hitokoto),
    QuipSource("毒鸡汤", "https://api.shadiao.app/du", parse_shadiao),
    QuipSource("趣味一言", "https://api.btstu.cn/yan/api.php", parse_plain),
)


class QuipFetcher:
    """从若干中文趣味接口抓取短句，逐个来源独立失败降级。"""

    def __init__(
        self,
        sources: list[QuipSource] | None = None,
        timeout: float = 5.0,
        fetch_fn: Callable[[str, float], bytes] | None = None,
    ) -> None:
        self.sources = list(sources) if sources is not None else list(SOURCES)
        self.timeout = timeout
        self.fetch_fn = fetch_fn if fetch_fn is not None else _http_get

    def fetch(self, limit: int = 20) -> list[ContentItem]:
        items: list[ContentItem] = []
        for src in self.sources:
            try:
                text = src.parse(self.fetch_fn(src.url, self.timeout))
            except Exception:
                logger.warning("quip fetch failed: %s", src.url, exc_info=True)
                continue
            if not text:
                continue
            items.append(
                ContentItem(
                    id=ContentItem.make_id(text),
                    type=ContentType.QUIP,
                    title=src.name,
                    body=text,
                    source=src.name,
                    url=src.url,
                    fetched_at=datetime.now().isoformat(),
                )
            )
            if len(items) >= limit:
                break
        return items