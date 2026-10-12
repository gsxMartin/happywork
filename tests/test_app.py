from datetime import datetime
from pathlib import Path

from lezi.app import should_pop
from lezi.config import Config
from lezi.scheduler import Scheduler
from lezi.state import StateStore


def _mk(tmp_path: Path) -> tuple[Scheduler, StateStore]:
    return Scheduler(Config()), StateStore(tmp_path / "s.json")


def test_should_pop_true_in_work_hours(tmp_path):
    s, st = _mk(tmp_path)
    now = datetime(2026, 10, 12, 10, 0)
    assert should_pop(s, Config(), st, now, lambda: False, lambda: 0.0) is True


def test_should_pop_false_outside_hours(tmp_path):
    s, st = _mk(tmp_path)
    now = datetime(2026, 10, 12, 8, 0)
    assert should_pop(s, Config(), st, now, lambda: False, lambda: 0.0) is False


def test_should_pop_false_when_fullscreen(tmp_path):
    s, st = _mk(tmp_path)
    now = datetime(2026, 10, 12, 10, 0)
    assert should_pop(s, Config(), st, now, lambda: True, lambda: 0.0) is False


def test_should_pop_false_when_idle(tmp_path):
    s, st = _mk(tmp_path)
    now = datetime(2026, 10, 12, 10, 0)
    assert should_pop(s, Config(), st, now, lambda: False, lambda: 300.0) is False


def test_should_pop_snooze_boundary(tmp_path):
    s, st = _mk(tmp_path)
    now = datetime(2026, 10, 12, 10, 0)
    st.set_snooze(datetime(2026, 10, 12, 10, 30))
    assert should_pop(s, Config(), st, now, lambda: False, lambda: 0.0) is False
    # 恰好到期当刻应恢复推送
    assert should_pop(s, Config(), st, datetime(2026, 10, 12, 10, 30), lambda: False, lambda: 0.0) is True