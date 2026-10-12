from __future__ import annotations

import random
from datetime import datetime
from typing import Callable

from .config import Config


class Scheduler:
    def __init__(
        self,
        cfg: Config,
        now_fn: Callable[[], datetime] = datetime.now,
        rng: random.Random | None = None,
    ) -> None:
        self.cfg = cfg
        self.now_fn = now_fn
        self.rng = rng if rng is not None else random.Random()

    def in_work_hours(self, now: datetime | None = None) -> bool:
        now = now if now is not None else self.now_fn()
        if now.weekday() not in self.cfg.work_days:
            return False
        cur = now.strftime("%H:%M")
        return self.cfg.work_start <= cur < self.cfg.work_end

    def next_delay_seconds(self) -> float:
        return self.rng.uniform(
            self.cfg.interval_min_minutes, self.cfg.interval_max_minutes
        ) * 60.0