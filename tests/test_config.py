from pathlib import Path

from lezi.config import Config, default_config, load_config, save_config


def test_default_config_values():
    cfg = default_config()
    assert cfg.work_start == "09:30"
    assert cfg.work_end == "18:30"
    assert cfg.work_days == (0, 1, 2, 3, 4)
    assert cfg.interval_min_minutes == 40
    assert cfg.interval_max_minutes == 90
    assert cfg.card_seconds == 15
    assert cfg.snooze_minutes == 60


def test_load_missing_file_returns_default(tmp_path: Path):
    cfg = load_config(tmp_path / "nope.json")
    assert cfg == default_config()


def test_save_then_load_roundtrip(tmp_path: Path):
    path = tmp_path / "cfg.json"
    cfg = Config(work_start="08:00", card_seconds=20)
    save_config(cfg, path)
    assert load_config(path) == cfg


def test_load_corrupt_json_returns_default(tmp_path: Path):
    path = tmp_path / "bad.json"
    path.write_text("{not valid json", encoding="utf-8")
    assert load_config(path) == default_config()