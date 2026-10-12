from __future__ import annotations

from PySide6.QtWidgets import (
    QFormLayout, QLineEdit, QSpinBox, QVBoxLayout, QWidget,
)

from ..config import Config


def config_to_form(cfg: Config) -> dict:
    return {
        "work_start": cfg.work_start,
        "work_end": cfg.work_end,
        "interval_min_minutes": cfg.interval_min_minutes,
        "interval_max_minutes": cfg.interval_max_minutes,
        "card_seconds": cfg.card_seconds,
        "snooze_minutes": cfg.snooze_minutes,
    }


def form_to_config(form: dict) -> Config:
    return Config(
        work_start=str(form["work_start"]),
        work_end=str(form["work_end"]),
        interval_min_minutes=int(form["interval_min_minutes"]),
        interval_max_minutes=int(form["interval_max_minutes"]),
        card_seconds=int(form["card_seconds"]),
        snooze_minutes=int(form["snooze_minutes"]),
    )


class SettingsWindow(QWidget):
    def __init__(self, cfg: Config, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("找点乐子 · 设置")
        form = config_to_form(cfg)

        self._work_start = QLineEdit(form["work_start"])
        self._work_end = QLineEdit(form["work_end"])
        self._interval_min = QSpinBox()
        self._interval_min.setRange(1, 600)
        self._interval_min.setValue(form["interval_min_minutes"])
        self._interval_max = QSpinBox()
        self._interval_max.setRange(1, 600)
        self._interval_max.setValue(form["interval_max_minutes"])
        self._card_seconds = QSpinBox()
        self._card_seconds.setRange(3, 300)
        self._card_seconds.setValue(form["card_seconds"])
        self._snooze_minutes = QSpinBox()
        self._snooze_minutes.setRange(5, 480)
        self._snooze_minutes.setValue(form["snooze_minutes"])

        layout = QVBoxLayout(self)
        rows = QFormLayout()
        rows.addRow("上班时间", self._work_start)
        rows.addRow("下班时间", self._work_end)
        rows.addRow("最小间隔(分)", self._interval_min)
        rows.addRow("最大间隔(分)", self._interval_max)
        rows.addRow("卡片停留(秒)", self._card_seconds)
        rows.addRow("安静一会(分)", self._snooze_minutes)
        layout.addLayout(rows)

    def current_config(self) -> Config:
        return form_to_config(
            {
                "work_start": self._work_start.text(),
                "work_end": self._work_end.text(),
                "interval_min_minutes": self._interval_min.value(),
                "interval_max_minutes": self._interval_max.value(),
                "card_seconds": self._card_seconds.value(),
                "snooze_minutes": self._snooze_minutes.value(),
            }
        )