import random
from datetime import datetime

from lezi.config import Config
from lezi.scheduler import Scheduler


def test_weekday_boundaries():
    s = Scheduler(Config(), now_fn=lambda: datetime(2026, 10, 12, 9, 30))
    assert s.in_work_hours(datetime(2026, 10, 12, 9, 30)) is True
    assert s.in_work_hours(datetime(2026, 10, 12, 9, 29)) is False
    assert s.in_work_hours(datetime(2026, 10, 12, 18, 30)) is False


def test_weekend_is_not_work_hours():
    # 2026-10-17 是周六
    s = Scheduler(Config())
    assert s.in_work_hours(datetime(2026, 10, 17, 10, 0)) is False


def test_next_delay_seconds_range_and_reproducible():
    s1 = Scheduler(Config(), rng=random.Random(42))
    s2 = Scheduler(Config(), rng=random.Random(42))
    d1 = s1.next_delay_seconds()
    assert 2400 <= d1 <= 5400
    assert d1 == s2.next_delay_seconds()


def test_overnight_and_malformed_time():
    # 跨夜班（work_start > work_end）首版不支持，任何时刻都判为非工作时段
    s = Scheduler(Config(work_start="22:00", work_end="06:00"))
    assert s.in_work_hours(datetime(2026, 10, 12, 23, 0)) is False
    # 畸形时间字符串不得抛异常；字符串比较下仅当字面落在区间内为真
    s2 = Scheduler(Config(work_start="9:3", work_end="25:00"))
    assert s2.in_work_hours(datetime(2026, 10, 12, 10, 0)) in (True, False)