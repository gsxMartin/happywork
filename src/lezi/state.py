from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .models import ContentItem


class StateStore:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._seen: set[str] = set()
        self._favorites: list[ContentItem] = []
        self._snooze_until: datetime | None = None

    def load(self) -> None:
        self._seen = set()
        self._favorites = []
        self._snooze_until = None
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                return
            seen = raw.get("seen", [])
            if isinstance(seen, list):
                self._seen = {str(s) for s in seen}
            favs = raw.get("favorites", [])
            if isinstance(favs, list):
                for d in favs:
                    try:
                        self._favorites.append(ContentItem.from_dict(d))
                    except Exception:
                        continue
            s = raw.get("snooze_until")
            if isinstance(s, str) and s:
                try:
                    self._snooze_until = datetime.fromisoformat(s)
                except Exception:
                    self._snooze_until = None
        except Exception:
            self._seen = set()
            self._favorites = []
            self._snooze_until = None

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "seen": sorted(self._seen),
            "favorites": [f.to_dict() for f in self._favorites],
            "snooze_until": self._snooze_until.isoformat() if self._snooze_until else None,
        }
        self.path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def is_seen(self, item_id: str) -> bool:
        return item_id in self._seen

    def mark_seen(self, item_id: str) -> None:
        self._seen.add(item_id)

    def add_favorite(self, item: ContentItem) -> None:
        if all(f.id != item.id for f in self._favorites):
            self._favorites.append(item)

    def favorites(self) -> list[ContentItem]:
        return list(self._favorites)

    def snooze_until(self) -> datetime | None:
        return self._snooze_until

    def set_snooze(self, until: datetime) -> None:
        self._snooze_until = until