import pathlib

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


FEED = ('<dsn><dish name="DSS26"><target name="MRO" id="74" rtlt="1330.0"/></dish>'
        '<dish name="DSS43"><target name="VGR2" id="32" rtlt="140000"/><target name="MVN" id="202" rtlt="1330.4"/>'
        '</dish><timestamp>1</timestamp></dsn>')


def test_only_mars_spacecraft_are_read_from_the_feed():
    assert dsn.parse(FEED) == [{"dish": "DSS26", "craft": "MRO", "round_trip_s": 1330.0},
                               {"dish": "DSS43", "craft": "MVN", "round_trip_s": 1330.4}]


def test_the_saved_copy_of_the_real_feed_can_be_read():
    sample = pathlib.Path("data/reference/dsn_sample.xml")
    for seen in dsn.parse(sample.read_text(encoding="utf-8")) if sample.exists() else []:
        assert 360 < seen["round_trip_s"] < 2700            # Mars is 3 to 22 minutes away, each way


def test_earth_sees_two_nasa_figures_side_by_side(client, monkeypatch):
    monkeypatch.setattr(dsn, "fetch", lambda: FEED)
    dsn._cache.clear()
    seen = client.get("/api/earth/network").get_json()
    assert seen["dsn_one_way_s"] == 665.1 and len(seen["passes"]) == 2
    assert seen["differ_s"] == round(abs(665.1 - seen["horizons_one_way_s"]), 1)


def test_no_dsn_is_not_an_error(client):
    seen = client.get("/api/earth/network").get_json()
    assert seen["passes"] == [] and seen["dsn_one_way_s"] is None and seen["differ_s"] is None


def test_a_bad_resolve_body_is_a_400_not_a_crash_and_names_fit_the_column(client):
    alert = sos(client)
    url = f"/api/base/alerts/{alert['id']}/clear"
    assert client.post(url, json={"note": 123}).status_code == 400
    assert client.post(url, json=[1, 2]).status_code == 200            # not an object: treated as empty
    done = client.post("/api/base/alerts/{}/ack".format(alert["id"]), json={"by": "x" * 80}).get_json()
    assert len(done["acknowledged_by"]) == 40


def test_the_earliest_reply_after_a_blackout_counts_one_leg_back(client):
    client.post("/api/base/dial", json={"stop": "sun"})
    for crew in (1, 2, 3):
        client.post("/api/base/sos", json={"crew_id": crew})
    client.post("/api/base/dial", json={"stop": "mars"})
    from datetime import datetime
    for a in client.get("/api/base/alerts").get_json():
        line, leg = a["timeline"], lighttime.mars_seconds() / 60
        sent = client.get("/api/base/outbox").get_json()
        report = next(m for m in sent if m["kind"] == "report" and m["payload"]["alert_id"] == a["id"])
        gap = (datetime.fromisoformat(line["earliest_reply_at"].replace("Z", "+00:00"))
               - datetime.fromisoformat(report["deliver_at"].replace("Z", "+00:00"))).total_seconds()
        assert abs(gap - leg) < 0.01


def test_an_infinite_round_trip_in_the_feed_is_ignored():
    assert dsn.parse('<dsn><dish name="D"><target name="MRO" rtlt="inf"/></dish></dsn>') == []
