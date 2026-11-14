from common import modes


def test_doctor_decides_below_five_minutes():
    assert modes.mode_for(0.25, True) == "doctor_live"
    assert modes.mode_for(299, True) == "doctor_live"


def test_crew_decides_from_five_minutes():
    assert modes.mode_for(300, True) == "crew_first"


def test_no_link_means_the_ship_is_alone():
    assert modes.mode_for(656, False) == "ship_alone"


def test_mars_stop_uses_real_light_time(app):
    mars = modes.describe("mars")
    assert mars["mode"] == "crew_first"
    assert 180 <= mars["delay_s"] <= 1350
    assert mars["who_decides"] == "Crew medical officer"


def test_station_and_moon_are_short_and_live(app):
    assert modes.describe("station")["mode"] == "doctor_live"
    assert modes.describe("moon")["delay_s"] == 1.3
