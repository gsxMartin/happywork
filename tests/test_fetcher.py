from lezi.content.fetcher import FeedFetcher
from lezi.models import ContentType

RSS = b"""<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0"><channel><title>T</title>
<item><title>Hello</title><link>http://x/1</link><description>d1</description></item>
<item><title>World</title><link>http://x/2</link><description>d2</description></item>
</channel></rss>"""


def test_fetch_parses_entries():
    f = FeedFetcher(["http://feed"], fetch_fn=lambda url, timeout: RSS)
    items = f.fetch()
    assert [i.title for i in items] == ["Hello", "World"]
    assert all(i.type is ContentType.NEWS for i in items)
    assert all(i.source == "rss" for i in items)
    assert items[0].url == "http://x/1"


def test_fetch_respects_limit():
    f = FeedFetcher(["http://feed"], fetch_fn=lambda url, timeout: RSS)
    assert len(f.fetch(limit=1)) == 1


def test_fetch_skips_garbage_source():
    def bad(url, timeout):
        raise ValueError("boom")

    f = FeedFetcher(["http://feed"], fetch_fn=bad)
    assert f.fetch() == []


def test_fetch_skips_garbage_bytes_returns_empty():
    f = FeedFetcher(["http://feed"], fetch_fn=lambda url, timeout: b"<html>not xml")
    assert f.fetch() == []