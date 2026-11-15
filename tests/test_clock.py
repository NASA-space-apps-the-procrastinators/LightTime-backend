from datetime import datetime, timezone

from common import models

MORNING = datetime(2026, 11, 14, 6, 30)


def test_the_mission_clock_starts_where_it_is_told_and_keeps_running():
    models.set_clock(MORNING)
    try:
        first = models.utcnow()
        assert MORNING <= first < datetime(2026, 11, 14, 6, 30, 5)
        assert models.utcnow() >= first
    finally:
        models.set_clock(None)


def test_without_a_mission_clock_the_ship_keeps_real_time():
    models.set_clock(None)
    real = datetime.now(timezone.utc).replace(tzinfo=None)
    assert abs((models.utcnow() - real).total_seconds()) < 5
