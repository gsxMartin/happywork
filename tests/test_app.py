import sys
from datetime import datetime
from pathlib import Path

from lezi.app import _base_dir, _resource_path, should_pop
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


def test_base_dir_is_project_root_when_not_frozen(monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)
    assert _base_dir() == Path(__file__).resolve().parents[1]


def test_base_dir_is_exe_dir_when_frozen(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "lezi.exe"))
    assert _base_dir() == tmp_path


def test_resource_path_prefers_meipass(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    assert _resource_path() == tmp_path / "resources" / "content_local.json"


def test_resource_path_falls_back_to_base_dir_when_frozen(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "lezi.exe"))
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)
    assert _resource_path() == tmp_path / "resources" / "content_local.json"