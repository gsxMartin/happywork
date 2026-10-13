from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import (
    QPropertyAnimation,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStyle,
    QStyleOption,
    QVBoxLayout,
    QWidget,
)

from ..config import Config
from ..models import ContentItem, ContentType


@dataclass
class CardView:
    title: str
    body: str
    answer: str | None
    show_answer: bool


def build_card_view(item: ContentItem, reveal: bool) -> CardView:
    if item.type is ContentType.RIDDLE:
        return CardView(
            title=item.title,
            body=item.body,
            answer=item.answer if reveal else None,
            show_answer=reveal,
        )
    return CardView(title=item.title, body=item.body, answer=None, show_answer=False)


_STYLE = """
CardWindow {
    background-color: rgba(28, 28, 30, 225);
    border-radius: 16px;
}
QLabel {
    color: #F5F5F5;
    font-family: "微软雅黑";
}
QLabel#title {
    font-size: 16px;
    font-weight: bold;
    color: #FFB74D;
}
QPushButton {
    color: #FFB74D;
    background: rgba(255, 183, 77, 40);
    border: 1px solid #FFB74D;
    border-radius: 8px;
    padding: 4px 10px;
    font-family: "微软雅黑";
}
QPushButton:hover {
    background: rgba(255, 183, 77, 90);
}
"""


class CardWindow(QWidget):
    next_requested = Signal()
    favorite_requested = Signal()
    snooze_requested = Signal()

    def __init__(self, cfg: Config, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.cfg = cfg
        self._item: ContentItem | None = None
        self._reveal = False
        self._anim: QPropertyAnimation | None = None

        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self._title = QLabel()
        self._title.setObjectName("title")
        self._body = QLabel()
        self._body.setWordWrap(True)
        self._answer = QLabel()
        self._answer.setWordWrap(True)

        self._reveal_btn = QPushButton("看答案")
        self._reveal_btn.clicked.connect(self._on_reveal)
        self._next_btn = QPushButton("再来一个")
        self._next_btn.clicked.connect(self.next_requested.emit)
        self._fav_btn = QPushButton("收藏")
        self._fav_btn.clicked.connect(self.favorite_requested.emit)
        self._snooze_btn = QPushButton("安静一会")
        self._snooze_btn.clicked.connect(self.snooze_requested.emit)

        buttons = QHBoxLayout()
        buttons.addWidget(self._reveal_btn)
        buttons.addStretch(1)
        buttons.addWidget(self._next_btn)
        buttons.addWidget(self._fav_btn)
        buttons.addWidget(self._snooze_btn)

        layout = QVBoxLayout(self)
        layout.addWidget(self._title)
        layout.addWidget(self._body)
        layout.addWidget(self._answer)
        layout.addLayout(buttons)

        self.setStyleSheet(_STYLE)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._close_with_fade)

    def paintEvent(self, event) -> None:
        # 自定义 QWidget 子类不会自动绘制样式表里的背景，需自绘 PE_Widget；
        # 否则卡片整块透明，浅色正文在白色背景上会看不见。
        option = QStyleOption()
        option.initFrom(self)
        painter = QPainter(self)
        self.style().drawPrimitive(QStyle.PE_Widget, option, painter, self)

    def _render(self) -> None:
        if self._item is None:
            return
        view = build_card_view(self._item, self._reveal)
        self._title.setText(view.title)
        self._body.setText(view.body)
        self._answer.setText(view.answer or "")
        self._answer.setVisible(view.show_answer)
        self._reveal_btn.setVisible(
            self._item.type is ContentType.RIDDLE and not self._reveal
        )

    def _on_reveal(self) -> None:
        self._reveal = True
        self._render()

    def _place_bottom_right(self) -> None:
        screen = self.screen().availableGeometry()
        margin = 24
        self.move(
            screen.right() - self.width() - margin,
            screen.bottom() - self.height() - margin,
        )

    def _fade(self, start: float, end: float, on_finished=None) -> None:
        self._anim = QPropertyAnimation(self, b"windowOpacity", self)
        self._anim.setDuration(200)
        self._anim.setStartValue(start)
        self._anim.setEndValue(end)
        if on_finished is not None:
            self._anim.finished.connect(on_finished)
        self._anim.start()

    def _show_with_fade(self) -> None:
        self._place_bottom_right()
        self.setWindowOpacity(0.0)
        self.show()
        self._fade(0.0, 1.0)

    def _close_with_fade(self) -> None:
        self._fade(1.0, 0.0, on_finished=self.close)

    def show_item(self, item: ContentItem) -> None:
        self._item = item
        self._reveal = False
        self._render()
        self.adjustSize()
        self._show_with_fade()
        self._timer.start(self.cfg.card_seconds * 1000)