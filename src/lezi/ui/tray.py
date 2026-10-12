from __future__ import annotations

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QApplication, QMenu, QStyle, QSystemTrayIcon


class TrayController(QObject):
    snooze_requested = Signal()
    favorites_requested = Signal()
    settings_requested = Signal()
    quit_requested = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)

    def setup(self) -> None:
        app = QApplication.instance()
        if app is not None:
            icon = app.style().standardIcon(QStyle.SP_MessageBoxInformation)
        else:
            icon = QIcon()
        self.icon = QSystemTrayIcon(icon)
        self.icon.setToolTip("找点乐子")
        menu = QMenu()

        snooze = QAction("暂停 1 小时", menu)
        snooze.triggered.connect(self.snooze_requested.emit)
        favorites = QAction("收藏夹", menu)
        favorites.triggered.connect(self.favorites_requested.emit)
        settings = QAction("设置", menu)
        settings.triggered.connect(self.settings_requested.emit)
        quit_ = QAction("退出", menu)
        quit_.triggered.connect(self.quit_requested.emit)

        menu.addAction(snooze)
        menu.addAction(favorites)
        menu.addSeparator()
        menu.addAction(settings)
        menu.addAction(quit_)

        self.icon.setContextMenu(menu)
        self.icon.show()