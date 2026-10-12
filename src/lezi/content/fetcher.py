from __future__ import annotations

import logging
from datetime import datetime
from typing import Callable

import feedparser
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


class FeedFetcher:
    def __init__(
        self,
        feeds: list[str],
        timeout: float = 5.0,
        fetch_fn: Callable[[str, float], bytes] | None = None,
    ) -> None:
        self.feeds = list(feeds)
        self.timeout = timeout
        self.fetch_fn = fetch_fn if fetch_fn is not None else _http_get

    def fetch(self, limit: int = 20) -> list[ContentItem]:
        items: list[ContentItem] = []
        for url in self.feeds:
            try:
                raw = self.fetch_fn(url, self.timeout)
                parsed = feedparser.parse(raw)
                for entry in parsed.entries:
                    title = (entry.get("title") or "").strip()
                    if not title:
                        continue
                    items.append(
                        ContentItem(
                            id=ContentItem.make_id(title),
                            type=ContentType.NEWS,
                            title=title,
                            body=entry.get("summary", ""),
                            source="rss",
                            url=entry.get("link"),
                            fetched_at=datetime.now().isoformat(),
                        )
                    )
                    if len(items) >= limit:
                        return items
            except Exception:
                logger.warning("feed fetch failed: %s", url, exc_info=True)
                continue
        return items