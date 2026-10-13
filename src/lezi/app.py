from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QObject, Qt, QTimer
from PySide6.QtWidgets import QApplication, QWidget

from .config import Config, load_config
from .content.fetcher import FeedFetcher
from .content.provider import ContentProvider
from .content.store import ContentStore
from .platform.win import idle_seconds, is_fullscreen
from .scheduler import Scheduler
from .state import StateStore
from .ui.card import CardWindow
from .ui.favorites import FavoritesWindow
from .ui.settings import SettingsWindow
from .ui.tray import TrayController

FEEDS = [
    # 中文来源清单，保证推送内容为中文（可按需增删）
    "https://www.solidot.org/index.rss",  # 奇客资讯
    "https://sspai.com/feed",  # 少数派
    "https://www.ruanyifeng.com/blog/atom.xml",  # 科技爱好者周刊
]

IDLE_THRESHOLD_SECONDS = 120.0


def _base_dir() -> Path:
    """配置与状态文件的存放目录。

    以 PyInstaller 打包运行时，取 exe 所在目录（用户可见、可写）；
    源码运行时取项目根目录。
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def _resource_path() -> Path:
    """本地内容库文件路径。

    打包后资源被解包到 `sys._MEIPASS`，需从这里读取；源码运行时回退到项目根目录。
    """
    meipass = getattr(sys, "_MEIPASS", None)
    root = Path(meipass) if meipass is not None else _base_dir()
    return root / "resources" / "content_local.json"


def should_pop(
    scheduler: Scheduler,
    cfg: Config,
    state: StateStore,
    now: datetime,
    is_fullscreen: Callable[[], bool],
    idle_seconds: Callable[[], float],
    idle_threshold: float = IDLE_THRESHOLD_SECONDS,
) -> bool:
    if not scheduler.in_work_hours(now):
        return False
    snooze = state.snooze_until()
    if snooze is not None and now < snooze:
        return False
    if is_fullscreen():
        return False
    if idle_seconds() >= idle_threshold:
        return False
    return True


class Application(QObject):
    def __init__(self, argv: list[str] | None = None) -> None:
        super().__init__()
        self.qapp = QApplication(argv if argv is not None else sys.argv)

        base = _base_dir()
        self.config_path = base / "config.json"
        self.state_path = base / "state.json"
        self.content_path = _resource_path()

        self.cfg: Config = load_config(self.config_path)
        self.store = ContentStore(self.content_path)
        self.store.load()
        self.fetcher = FeedFetcher(FEEDS)
        self.state = StateStore(self.state_path)
        self.state.load()
        self.provider = ContentProvider(self.store, self.fetcher, self.state)
        self.scheduler = Scheduler(self.cfg)

        self.card = CardWindow(self.cfg)
        self.card.next_requested.connect(self._on_next)
        self.card.favorite_requested.connect(self._on_favorite)
        self.card.snooze_requested.connect(self._on_snooze)

        self.tray = TrayController(self)
        self.tray.setup()
        self.tray.snooze_requested.connect(self._on_snooze)
        self.tray.settings_requested.connect(self._on_settings)
        self.tray.favorites_requested.connect(self._on_favorites)
        self.tray.quit_requested.connect(self.quit)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._tick)

        self._child_windows: list[QWidget] = []

    def _show_child(self, window) -> None:
        window.setAttribute(Qt.WA_DeleteOnClose)
        self._child_windows.append(window)
        window.destroyed.connect(
            lambda *_, w=window: self._child_windows.remove(w) if w in self._child_windows else None
        )
        window.show()

    def _show_next(self) -> None:
        item = self.provider.next_item()
        if item is None:
            return
        self.state.mark_seen(item.id)
        self.state.save()
        self.card.show_item(item)

    def _schedule_next(self) -> None:
        self._timer.start(int(self.scheduler.next_delay_seconds() * 1000))

    def _tick(self) -> None:
        now = datetime.now()
        if should_pop(
            self.scheduler, self.cfg, self.state, now, is_fullscreen, idle_seconds
        ):
            self._show_next()
        self._schedule_next()

    def _on_next(self) -> None:
        self.card.close()
        self._show_next()

    def _on_favorite(self) -> None:
        if self.card._item is not None:
            self.state.add_favorite(self.card._item)
            self.state.save()

    def _on_snooze(self) -> None:
        until = datetime.now() + timedelta(minutes=self.cfg.snooze_minutes)
        self.state.set_snooze(until)
        self.state.save()
        self.card.close()

    def _on_settings(self) -> None:
        self._show_child(SettingsWindow(self.cfg))

    def _on_favorites(self) -> None:
        self._show_child(FavoritesWindow(self.state.favorites()))

    def quit(self) -> None:
        self.state.save()
        self.qapp.quit()

    def start(self) -> None:
        self._schedule_next()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="lezi", description="找点乐子")
    parser.add_argument("--version", action="store_true", help="显示版本并退出")
    args, rest = parser.parse_known_args(argv)

    if args.version:
        from . import __version__

        print(f"lezi {__version__}")
        return 0

    app = Application([sys.argv[0], *rest])
    app.start()
    return app.qapp.exec()