from __future__ import annotations

import win32api
import win32con
import win32gui

Rect = tuple[int, int, int, int]


def _rect_covers(window_rect: Rect, screen_rect: Rect) -> bool:
    wl, wt, wr, wb = window_rect
    sl, st, sr, sb = screen_rect
    return wl <= sl and wt <= st and wr >= sr and wb >= sb


def is_fullscreen() -> bool:
    hwnd = win32gui.GetForegroundWindow()
    if not hwnd:
        return False
    try:
        rect = win32gui.GetWindowRect(hwnd)
        monitor = win32api.MonitorFromWindow(hwnd, win32con.MONITOR_DEFAULTTONEAREST)
        screen_rect = win32api.GetMonitorInfo(monitor)["Monitor"]
    except Exception:
        return False
    return _rect_covers(tuple(rect), tuple(screen_rect))


def idle_seconds() -> float:
    info = win32api.GetLastInputInfo()
    now = win32api.GetTickCount()
    return max(0.0, (now - info) / 1000.0)