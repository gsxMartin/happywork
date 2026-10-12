from __future__ import annotations

import json
from dataclasses import asdict, dataclass, fields
from pathlib import Path


@dataclass
class Config:
    work_start: str = "09:30"
    work_end: str = "18:30"
    work_days: tuple[int, ...] = (0, 1, 2, 3, 4)
    interval_min_minutes: int = 40
    interval_max_minutes: int = 90
    card_seconds: int = 15
    snooze_minutes: int = 60


def default_config() -> Config:
    return Config()


def load_config(path: Path) -> Config:
    """读取 JSON 配置；文件缺失、损坏或字段异常时一律返回默认配置。"""
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return default_config()
        kwargs = {f.name: raw[f.name] for f in fields(Config) if f.name in raw}
        cfg = Config(**kwargs)
        cfg.work_days = tuple(int(d) for d in cfg.work_days)
        return cfg
    except Exception:
        return default_config()


def save_config(cfg: Config, path: Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps(asdict(cfg), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )