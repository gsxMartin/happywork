from pathlib import Path

from lezi.content.store import ContentStore
from lezi.models import ContentType

SAMPLE = {
    "items": [
        {"type": "joke", "title": "加班", "body": "b1"},
        {"type": "joke", "title": "Ctrl+C", "body": "b2"},
        {"type": "riddle", "title": "什么车寸步难行？", "body": "q", "answer": "风车。"},
    ]
}


def _write(tmp_path: Path) -> Path:
    import json

    p = tmp_path / "content.json"
    p.write_text(json.dumps(SAMPLE, ensure_ascii=False), encoding="utf-8")
    return p


def test_load_count(tmp_path: Path):
    store = ContentStore(_write(tmp_path))
    store.load()
    assert len(store.all()) == 3


def test_by_type_filters(tmp_path: Path):
    store = ContentStore(_write(tmp_path))
    store.load()
    assert len(store.by_type(ContentType.JOKE)) == 2
    assert len(store.by_type(ContentType.RIDDLE)) == 1
    assert store.by_type(ContentType.TRIVIA) == []


def test_missing_file_returns_empty(tmp_path: Path):
    store = ContentStore(tmp_path / "missing.json")
    store.load()
    assert store.all() == []