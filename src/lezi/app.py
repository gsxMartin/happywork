from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QObject, QTimer
from PySide6.QtWidgets import QApplication

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
    # 计划阶段确定的 RSS 来源清单（可按需增删）
    "https://feeds.bbci.co.uk/news/world/rss.xml",
]

IDLE_THRESHOLD_SECONDS = 120.0


def _base_dir() -> Path:
    return Path(__file__).resolve().parents[2]


def should_pop(
    scheduler: Scheduler,
    cfg: Config,
    state: StateStore,
    now: datetime,
    is_fullscreen: Callable[[], bool],
    idle_seconds: Callable[[], float],
    idle_threshold: float = 120.0,
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
        self.content_path = base / "resources" / "content_local.json"

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
        self.settings_window = SettingsWindow(self.cfg)
        self.settings_window.show()

    def _on_favorites(self) -> None:
        self.favorites_window = FavoritesWindow(self.state.favorites())
        self.favorites_window.show()

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