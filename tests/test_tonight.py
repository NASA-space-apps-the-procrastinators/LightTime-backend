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


def test_the_alert_says_when_the_earliest_reply_could_land(client):
    client.post("/api/base/dial", json={"stop": "mars"})
    sos(client)
    line = client.get("/api/base/alerts").get_json()[0]["timeline"]
    assert line["earliest_reply_at"] > line["sent_at"]


def test_a_queued_report_has_no_reply_time_yet(client):
    client.post("/api/base/dial", json={"stop": "sun"})
    sos(client)
    assert client.get("/api/base/alerts").get_json()[0]["timeline"]["earliest_reply_at"] is None


def test_earth_can_watch_its_reply_in_flight(client):
    client.post("/api/base/dial", json={"stop": "mars"})
    sent = client.post("/api/earth/reply", json={"text": "Give oxygen."}).get_json()
    out = client.get("/api/earth/outbox").get_json()
    assert [m["id"] for m in out] == [sent["id"]] and out[0]["status"] == "in_flight"
    assert 0 < out[0]["eta_s"] <= out[0]["delay_s"]
    assert client.get("/api/base/inbox").get_json() == []       # the ship has not heard yet


def test_every_alert_says_how_it_was_reached(client):
    sos(client)
    why = client.get("/api/base/alerts").get_json()[0]["why"]
    assert why[1] == "Last readings: 86, 86, 86, 86, 86%."
    assert any("NEWS2" in line for line in why) and why[-1].endswith("decides.")


def test_a_manual_sos_says_no_rule_was_involved(client):
    alert = client.post("/api/base/sos", json={"crew_id": 2}).get_json()
    assert alert["why"] == ["A crew member pressed SOS. No rule was involved."]


def test_resolving_keeps_the_crews_own_words_and_tells_earth(client):
    alert = sos(client)
    note = "Mask on. Back to 97 in two minutes."
    done = client.post(f"/api/base/alerts/{alert['id']}/clear", json={"by": "Damola", "note": note}).get_json()
    assert done["cleared_note"] == note
    resolved = [m for m in client.get("/api/base/outbox").get_json() if m["payload"].get("event") == "resolved"]
    assert resolved[0]["payload"]["note"] == note


def test_the_sources_route_lists_the_nasa_data_we_use(client):
    listed = client.get("/api/base/sources").get_json()
    assert sum(s["agency"].startswith("NASA") for s in listed) >= 4
    assert all(set(s) == {"id", "agency", "name", "kind", "url", "used_for", "as_of"} for s in listed)
    assert listed[0]["id"] == "horizons" and "JPL Horizons" in listed[0]["as_of"]
