from common import dsn, lighttime, modes

LOW = {"crew_id": 1, "spo2": 86}


def sos(client):
    for _ in range(5):
        raised = client.post("/api/base/readings", json=LOW).get_json()["alerts"]
    return raised[0]


def stop(state, name):
    return next(s for s in state["stops"] if s["stop"] == name)


def test_one_astronomical_unit_is_499_seconds_of_light():
    assert abs(lighttime.AU_KM / lighttime.C_KM_S - 499.0048) < 0.0001


def test_the_moon_figure_matches_the_moons_distance():
    assert abs(384_400 / lighttime.C_KM_S - modes.FIXED_DELAY_S["moon"]) < 0.05


def test_mars_light_time_is_inside_what_the_orbits_allow(app):
    assert 0.372 * 499 <= lighttime.mars_seconds() <= 2.68 * 499


def test_the_state_shows_its_working(client):
    state = client.get("/api/base/state").get_json()
    mars, moon = stop(state, "mars"), stop(state, "moon")
    assert mars["round_trip_s"] == 2 * mars["delay_s"]
    assert mars["plays_as_s"] == mars["delay_s"] / state["speedup"]
    assert abs(mars["path_km"] - mars["delay_s"] * 299_792.458) < 1
    assert moon["plays_as_s"] == moon["delay_s"]          # under a minute plays in real time
