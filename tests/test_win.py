import win32api
import win32gui

from lezi.platform.win import _rect_covers, is_fullscreen

SCREEN = (0, 0, 1920, 1080)


def test_rect_covers_equal_is_true():
    assert _rect_covers((0, 0, 1920, 1080), SCREEN) is True


def test_rect_covers_slightly_smaller_is_false():
    assert _rect_covers((0, 0, 1919, 1080), SCREEN) is False


def test_rect_covers_larger_is_true():
    assert _rect_covers((-10, -10, 1930, 1090), SCREEN) is True


def test_rect_covers_negative_and_slightly_smaller():
    # 任务栏占位：窗口略矮（底部留出任务栏）应判为非全屏
    assert _rect_covers((0, 0, 1920, 1040), (0, 0, 1920, 1080)) is False
    # 负坐标显示器：窗口刚好覆盖负坐标显示器应判为全屏
    assert _rect_covers((-1920, 0, 0, 1080), (-1920, 0, 0, 1080)) is True


def _fake_foreground(monkeypatch, rect, monitor):
    monkeypatch.setattr(win32gui, "GetForegroundWindow", lambda: 100)
    monkeypatch.setattr(win32gui, "GetWindowRect", lambda hwnd: rect)
    monkeypatch.setattr(win32api, "MonitorFromWindow", lambda hwnd, flag: 1)
    monkeypatch.setattr(win32api, "GetMonitorInfo", lambda mon: {"Monitor": monitor})


def test_is_fullscreen_true_when_window_covers_monitor(monkeypatch):
    _fake_foreground(monkeypatch, (0, 0, 1920, 1080), (0, 0, 1920, 1080))
    assert is_fullscreen() is True


def test_is_fullscreen_false_when_window_smaller_than_monitor(monkeypatch):
    _fake_foreground(monkeypatch, (0, 0, 1280, 900), (0, 0, 1920, 1080))
    assert is_fullscreen() is False