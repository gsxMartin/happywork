from __future__ import annotations

import json
from pathlib import Path

from ..models import ContentItem, ContentType


class ContentStore:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._items: list[ContentItem] = []

    def load(self) -> None:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            entries = raw.get("items", [])
        except Exception:
            self._items = []
            return
        items: list[ContentItem] = []
        for d in entries:
            title = d["title"]
            body = d["body"]
            items.append(
                ContentItem(
                    id=ContentItem.make_id(f"{title}\n{body}"),
                    type=ContentType(d["type"]),
                    title=title,
                    body=body,
                    answer=d.get("answer"),
                    source="local",
                )
            )
        self._items = items

    def all(self) -> list[ContentItem]:
        return list(self._items)

    def by_type(self, t: ContentType) -> list[ContentItem]:
        return [i for i in self._items if i.type is t]