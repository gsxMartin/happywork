from datetime import datetime
from pathlib import Path

from lezi.models import ContentItem, ContentType
from lezi.state import StateStore


def _item() -> ContentItem:
    return ContentItem(id="x1", type=ContentType.JOKE, title="t", body="b")


def test_mark_seen_then_is_seen(tmp_path: Path):
    st = StateStore(tmp_path / "state.json")
    assert st.is_seen("x1") is False
    st.mark_seen("x1")
    assert st.is_seen("x1") is True


def test_favorites_roundtrip(tmp_path: Path):
    path = tmp_path / "state.json"
    st = StateStore(path)
    st.add_favorite(_item())
    st.save()
    st2 = StateStore(path)
    st2.load()
    assert st2.favorites() == [_item()]


def test_snooze_roundtrip_and_persist(tmp_path: Path):
    path = tmp_path / "state.json"
    until = datetime(2026, 10, 12, 10, 30)
    st = StateStore(path)
    st.set_snooze(until)
    st.save()
    st2 = StateStore(path)
    st2.load()
    assert st2.snooze_until() == until


def test_load_corrupt_state_resets(tmp_path: Path):
    path = tmp_path / "state.json"
    path.write_text('{"seen": "oops", "favorites": 5, "snooze_until": "not-a-date"}', encoding="utf-8")
    st = StateStore(path)
    st.load()
    assert st.favorites() == []
    assert st.snooze_until() is None