from lezi.config import Config
from lezi.ui.settings import config_to_form, form_to_config


def test_config_to_form_fields():
    form = config_to_form(Config())
    assert form == {
        "work_start": "09:30",
        "work_end": "18:30",
        "interval_min_minutes": 40,
        "interval_max_minutes": 90,
        "card_seconds": 15,
        "snooze_minutes": 60,
    }


def test_form_to_config_roundtrip():
    cfg = Config(work_start="08:00", interval_min_minutes=20, snooze_minutes=30)
    assert form_to_config(config_to_form(cfg)) == cfg


def test_form_to_config_casts_strings():
    form = {
        "work_start": "07:00",
        "work_end": "19:00",
        "interval_min_minutes": "10",
        "interval_max_minutes": "20",
        "card_seconds": "5",
        "snooze_minutes": "45",
    }
    cfg = form_to_config(form)
    assert cfg.interval_min_minutes == 10
    assert cfg.card_seconds == 5