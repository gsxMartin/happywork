from lezi.models import ContentItem, ContentType
from lezi.ui.card import build_card_view


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