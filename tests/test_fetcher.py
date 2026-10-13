import json

from lezi.content.fetcher import (
    SOURCES,
    QuipFetcher,
    QuipSource,
    parse_hitokoto,
    parse_plain,
    parse_shadiao,
)
from lezi.models import ContentType


def _src(parse, name="测试源", url="http://x") -> QuipSource:
    return QuipSource(name=name, url=url, parse=parse)


def test_parse_hitokoto_reads_hitokoto_field():
    assert parse_hitokoto(json.dumps({"hitokoto": " 十年OI一场空 "}).encode()) == "十年OI一场空"


def test_parse_hitokoto_returns_none_when_missing():
    assert parse_hitokoto(json.dumps({"foo": "bar"}).encode()) is None


def test_parse_shadiao_reads_nested_text():
    raw = json.dumps({"data": {"text": " 想要打起精神 "}}).encode()
    assert parse_shadiao(raw) == "想要打起精神"


def test_parse_plain_strips_whitespace():
    assert parse_plain(" 你的脖子真可爱 ".encode()) == "你的脖子真可爱"


def test_fetch_builds_quip_item_from_source():
    f = QuipFetcher(
        [_src(parse_hitokoto, name="一言")],
        fetch_fn=lambda url, timeout: json.dumps({"hitokoto": "哈"}).encode(),
    )
    items = f.fetch()
    assert len(items) == 1
    assert items[0].type is ContentType.QUIP
    assert items[0].title == "一言"
    assert items[0].body == "哈"
    assert items[0].source == "一言"


def test_fetch_collects_from_multiple_sources():
    payloads = {
        "http://a": json.dumps({"hitokoto": "甲"}).encode(),
        "http://b": json.dumps({"data": {"text": "乙"}}).encode(),
    }
    sources = [
        _src(parse_hitokoto, name="一言", url="http://a"),
        _src(parse_shadiao, name="毒鸡汤", url="http://b"),
    ]
    f = QuipFetcher(sources, fetch_fn=lambda url, timeout: payloads[url])
    assert {i.body for i in f.fetch()} == {"甲", "乙"}


def test_fetch_skips_failing_source_but_keeps_others():
    def bad(url, timeout):
        if url == "http://a":
            raise ValueError("boom")
        return json.dumps({"data": {"text": "乙"}}).encode()

    sources = [
        _src(parse_hitokoto, name="一言", url="http://a"),
        _src(parse_shadiao, name="毒鸡汤", url="http://b"),
    ]
    f = QuipFetcher(sources, fetch_fn=bad)
    assert [i.body for i in f.fetch()] == ["乙"]


def test_fetch_skips_empty_result():
    f = QuipFetcher(
        [_src(parse_plain)],
        fetch_fn=lambda url, timeout: b"   ",
    )
    assert f.fetch() == []


def test_fetch_respects_limit():
    sources = [_src(parse_plain, name=f"s{i}", url=f"http://{i}") for i in range(5)]
    f = QuipFetcher(sources, fetch_fn=lambda url, timeout: b"hello")
    assert len(f.fetch(limit=2)) == 2


def test_default_sources_are_fun_not_news():
    urls = [s.url for s in SOURCES]
    assert urls, "应至少配置一个联网趣味来源"
    assert all(
        ("hitokoto" in u) or ("shadiao" in u) or ("btstu" in u) for u in urls
    )
    # 不得再保留任何资讯 / 新闻类来源
    banned = ("solidot", "sspai", "ruanyifeng", "jandan", "bbc")
    assert not any(b in u for u in urls for b in banned)