from __future__ import annotations

from PySide6.QtWidgets import QListWidget, QVBoxLayout, QWidget

from ..models import ContentItem


def favorites_to_rows(items: list[ContentItem]) -> list[str]:
    return [f"[{item.type.label}] {item.title}" for item in items]


class FavoritesWindow(QWidget):
    def __init__(self, items: list[ContentItem], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("找点乐子 · 收藏夹")
        layout = QVBoxLayout(self)
        self._list = QListWidget()
        self._list.addItems(favorites_to_rows(items))
        layout.addWidget(self._list)