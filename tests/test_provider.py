import random

from lezi.content.provider import ContentProvider
from lezi.models import ContentItem, ContentType
from lezi.state import StateStore


class FakeStore:
    def __init__(self, items):
        self._items = items

    def all(self):
        return list(self._items)

    def by_type(self, t):
        return [i for i in self._items if i.type is t]


class FakeFetcher:
    def __init__(self, items):
        self._items = items

    def fetch(self, limit=20):
        return list(self._items)


def _local(id_, t=ContentType.JOKE):
    return ContentItem(id=id_, type=t, title=id_, body="b")


def _online(id_):
    return ContentItem(id=id_, type=ContentType.NEWS, title=id_, body="b", source="rss")


def test_prefers_fresh_online(tmp_path):
    store = FakeStore([_local("L1")])
    fetcher = FakeFetcher([_online("N1")])
    state = StateStore(tmp_path / "s.json")
    p = ContentProvider(store, fetcher, state, rng=random.Random(1))
    assert p.next_item().id == "N1"


def test_falls_back_to_local_when_online_empty(tmp_path):
    store = FakeStore([_local("L1")])
    fetcher = FakeFetcher([])
    state = StateStore(tmp_path / "s.json")
    p = ContentProvider(store, fetcher, state, rng=random.Random(1))
    assert p.next_item().id == "L1"


def test_all_seen_falls_back_to_any_local(tmp_path):
    store = FakeStore([_local("L1")])
    fetcher = FakeFetcher([])
    state = StateStore(tmp_path / "s.json")
    state.mark_seen("L1")
    p = ContentProvider(store, fetcher, state, rng=random.Random(1))
    assert p.next_item().id == "L1"


def test_empty_everything_returns_none(tmp_path):
    store = FakeStore([])
    fetcher = FakeFetcher([])
    state = StateStore(tmp_path / "s.json")
    p = ContentProvider(store, fetcher, state)
    assert p.next_item() is None


def test_skips_seen_online_in_favor_of_fresh_online(tmp_path):
    store = FakeStore([])
    fetcher = FakeFetcher([_online("N1"), _online("N2")])
    state = StateStore(tmp_path / "s.json")
    state.mark_seen("N1")
    p = ContentProvider(store, fetcher, state, rng=random.Random(1))
    assert p.next_item().id == "N2"


def test_falls_back_to_local_when_fetcher_is_none(tmp_path):
    store = FakeStore([_local("L1")])
    state = StateStore(tmp_path / "s.json")
    p = ContentProvider(store, None, state, rng=random.Random(1))
    assert p.next_item().id == "L1"


def test_falls_back_to_local_when_fetch_raises(tmp_path):
    class BoomFetcher:
        def fetch(self, limit=20):
            raise RuntimeError("network down")

    store = FakeStore([_local("L1")])
    state = StateStore(tmp_path / "s.json")
    p = ContentProvider(store, BoomFetcher(), state, rng=random.Random(1))
    assert p.next_item().id == "L1"


def test_next_item_does_not_mark_seen(tmp_path):
    store = FakeStore([_local("L1")])
    fetcher = FakeFetcher([_online("N1")])
    state = StateStore(tmp_path / "s.json")
    p = ContentProvider(store, fetcher, state, rng=random.Random(1))
    item = p.next_item()
    assert item is not None
    assert state.is_seen(item.id) is False