from PySide6.QtWidgets import QApplication

from lezi.models import ContentItem, ContentType
from lezi.ui.card import build_card_view

_APP = None


def _qapp():
    global _APP
    if _APP is None:
        _APP = QApplication.instance() or QApplication([])
    return _APP


def _riddle():
    return ContentItem(
        id="r1", type=ContentType.RIDDLE, title="什么车寸步难行？",
        body="什么车寸步难行？", answer="风车。",
    )


def _joke():
    return ContentItem(id="j1", type=ContentType.JOKE, title="加班", body="b")


def test_riddle_hides_answer_before_reveal():
    view = build_card_view(_riddle(), reveal=False)
    assert view.answer is None
    assert view.show_answer is False


def test_riddle_shows_answer_after_reveal():
    view = build_card_view(_riddle(), reveal=True)
    assert view.answer == "风车。"
    assert view.show_answer is True


def test_joke_never_shows_answer():
    view = build_card_view(_joke(), reveal=True)
    assert view.answer is None
    assert view.show_answer is False
    assert view.title == "加班"


def test_card_paints_its_own_background(monkeypatch):
    # 卡片是 QWidget 子类且开启了 WA_TranslucentBackground：若不同时开启
    # WA_StyledBackground，Qt 不会绘制样式表里的背景，卡片会整块透明，
    # 浅色正文在白色背景上便不可见。
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from lezi.config import Config
    from lezi.ui.card import CardWindow

    _qapp()
    card = CardWindow(Config())
    card.show_item(_joke())
    card.setWindowOpacity(1.0)

    image = card.grab().toImage()
    # 取左侧留白处（无子控件覆盖），此像素应为卡片自身的半透明深色背景
    pixel = image.pixelColor(4, image.height() // 2)
    assert pixel.alpha() > 0