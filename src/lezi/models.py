from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from enum import Enum


class ContentType(str, Enum):
    JOKE = "joke"
    RIDDLE = "riddle"
    TRIVIA = "trivia"
    NEWS = "news"


@dataclass(frozen=True)
class ContentItem:
    id: str
    type: ContentType
    title: str
    body: str
    answer: str | None = None
    source: str = "local"
    url: str | None = None
    fetched_at: str | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "title": self.title,
            "body": self.body,
            "answer": self.answer,
            "source": self.source,
            "url": self.url,
            "fetched_at": self.fetched_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ContentItem":
        return cls(
            id=d["id"],
            type=ContentType(d["type"]),
            title=d["title"],
            body=d["body"],
            answer=d.get("answer"),
            source=d.get("source", "local"),
            url=d.get("url"),
            fetched_at=d.get("fetched_at"),
        )

    @staticmethod
    def make_id(text: str) -> str:
        normalized = re.sub(r"\s+", " ", text.strip())
        return hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:16]