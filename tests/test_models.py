from lezi.models import ContentItem, ContentType


def test_make_id_is_stable_and_normalizes_whitespace():
    a = ContentItem.make_id("  你好   世界  ")
    b = ContentItem.make_id("你好 世界")
    assert a == b
    assert len(a) == 16
    assert ContentItem.make_id("你好世界") != a


def test_to_dict_from_dict_roundtrip():
    item = ContentItem(
        id="abc123",
        type=ContentType.RIDDLE,
        title="什么车寸步难行？",
        body="什么车寸步难行？",
        answer="风车。",
        source="local",
        url="http://x/1",
        fetched_at="2026-10-12T09:30:00",
    )
    assert ContentItem.from_dict(item.to_dict()) == item


def test_from_dict_restores_enum_from_string():
    d = {"id": "i1", "type": "joke", "title": "t", "body": "b"}
    item = ContentItem.from_dict(d)
    assert item.type is ContentType.JOKE
    assert item.answer is None
    assert item.source == "local"
    assert item.url is None
    assert item.fetched_at is None