from common import lighttime

SAMPLE = """
 Date__(UT)__HR:MN, , ,  1-way_down_LT,
$$SOE
 2026-Nov-15 00:00, , ,  10.94362708,
 2026-Nov-16 00:00, , ,  10.87269269,
$$EOE
"""


def test_parse_reads_minutes_and_returns_seconds():
    assert abs(lighttime.parse(SAMPLE) - 656.62) < 0.01


def test_offline_falls_back_to_the_dated_table(app):
    assert lighttime.mars_seconds("2026-11-15") == 656.62
    assert "2026-11-13" in lighttime.source("2026-11-15")
