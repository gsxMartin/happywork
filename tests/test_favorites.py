from lezi.models import ContentItem, ContentType
from lezi.ui.favorites import favorites_to_rows


def test_favorites_to_rows_labels_type_and_title():
    items = [
        ContentItem(id="a", type=ContentType.JOKE, title="冷笑话A", body="x"),
        ContentItem(id="b", type=ContentType.RIDDLE, title="脑筋急转弯B", body="y", answer="z"),
    ]
    assert favorites_to_rows(items) == ["[joke] 冷笑话A", "[riddle] 脑筋急转弯B"]


def test_favorites_to_rows_empty():
    assert favorites_to_rows([]) == []