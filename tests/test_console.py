LOW = {"crew_id": 1, "spo2": 86}


def sos(client):
    for _ in range(5):
        raised = client.post("/api/base/readings", json=LOW).get_json()["alerts"]
    return raised[0]


def test_a_live_alert_speaks_the_consoles_language(client):
    alert = sos(client)
    assert alert["id"].startswith("A") and alert["crew_id"] == "C1" and alert["crew"] == "Okafor"
    assert (alert["state"], alert["level"], alert["metric"]) == ("SOS", "emergency", "spo2")
    assert alert["stage"] == "sent" and alert["symptoms"] == [] and alert["rule"]     # an SOS sends itself


def test_a_sensor_check_is_a_recheck_and_never_an_alert(client):
    raised = client.post("/api/base/readings",
                         json={"crew_id": 1, "spo2": 98, "signal_ok": False}).get_json()["alerts"]
    assert (raised[0]["state"], raised[0]["metric"], raised[0]["stage"]) == ("RECHECK", "signal", "raised")


def test_one_alert_can_be_fetched_by_its_code_or_its_number(client):
    alert = sos(client)
    assert client.get(f"/api/base/alerts/{alert['id']}").get_json()["id"] == alert["id"]
    assert client.get(f"/api/base/alerts/{alert['id'][1:]}").get_json()["id"] == alert["id"]
    missing = client.get("/api/base/alerts/A999")
    assert missing.status_code == 404 and missing.get_json() == {"error": "not found"}


def test_symptoms_given_at_acknowledge_stay_on_the_alert(client):
    alert = sos(client)
    acked = client.post(f"/api/base/alerts/{alert['id']}/ack",
                        json={"by": "Okafor", "symptoms": ["headache"]}).get_json()
    assert acked["symptoms"] == ["headache"] and acked["timeline"]["acknowledged_at"] is not None


def test_the_crew_overview_gets_the_cards_it_already_draws(morning):
    crew = morning.get("/api/base/crew").get_json()
    assert [member["id"] for member in crew] == ["C1", "C2", "C3", "C4"]
    c1 = crew[0]
    assert (c1["name"], c1["role"], c1["suit_id"], c1["state"]) == ("Okafor", "Commander", "LT-01", "ALERT")
    assert c1["baseline"]["hr_rest"] == [52, 64] and c1["baseline"]["bp"] == [[108, 122], [66, 78]]
    assert c1["baseline"]["pvt_ms"] == 265
    today = c1["today"]
    assert (today["hr_rest"], today["spo2"], today["temp_c"], today["resp"], today["sleep_h"]) == (84, 97, 37.2, 17, 5.1)
    assert (today["dose_mSv_day"], today["dose_mSv_mission"]) == (0.51, 81.0)
    # Okafor has not checked in yet today, so what they typed yesterday still stands
    assert today["symptoms"] == ["headache", "short sleep"] and c1["checkin_from"] == "2026-11-13"
    assert c1["metric_states"]["hr_rest"] == "ALERT" and c1["metric_states"]["spo2"] == "OK"
    assert all(member["state"] in ("OK", "WATCH", "ALERT") for member in crew)
    assert morning.get("/api/base/crew/C1").get_json()["today"] == today
    assert morning.get("/api/base/crew/C9").status_code == 404


def test_the_trend_chart_gets_seven_days_and_the_band(morning):
    history = morning.get("/api/base/crew/C1/history?metric=hr_rest").get_json()
    assert len(history["days"]) == 7 and [day["value"] for day in history["days"]][-3:] == [80, 82, 84]
    assert history["days"][-1]["date"] == "2026-11-14" and history["band"] == [52, 64]
    assert (history["unit"], history["days_out_of_band"], history["simulated"]) == ("bpm", 3, True)
    month = morning.get("/api/base/crew/C1/history?metric=mood&days=99").get_json()
    assert len(month["days"]) == 30 and month["band"] is None


def test_a_bad_history_request_says_which_field(morning):
    bad = morning.get("/api/base/crew/C1/history?metric=glucose")
    assert bad.status_code == 400 and bad.get_json()["field"] == "metric"
    assert morning.get("/api/base/crew/C9/history?metric=mood").status_code == 404


def test_every_rule_prints_its_words_and_its_source(morning):
    printed = morning.get("/api/base/thresholds").get_json()
    assert set(printed) == {"hr_rest", "bp_sys", "bp_dia", "spo2", "temp_c", "resp", "sleep_h", "mood", "pvt_ms",
                            "dose_mSv_day", "co2_mmHg"}
    assert all(set(rule) == {"unit", "watch", "alert", "source"} and rule["source"] for rule in printed.values())
    assert printed["hr_rest"]["source"].startswith("OCHMO Exercise Overview brief")


def test_a_normal_start_has_no_morning(client):
    assert client.get("/api/base/alerts").get_json() == []
    assert client.get("/api/base/state").get_json()["stop"] == "station"
    assert [member["id"] for member in client.get("/api/base/crew").get_json()] == ["C1", "C2", "C3", "C4"]


def test_the_station_strip_says_which_numbers_are_nasas(morning):
    station = morning.get("/api/base/station").get_json()
    co2 = station["co2_mmHg"]
    assert 1.0 < co2["value"] < 6.0 and co2["simulated"] is False
    assert co2["state"] == ("ALERT" if co2["value"] >= 4.5 else "WATCH" if co2["value"] >= 2.8 else "OK")
    assert station["temp_c"]["simulated"] is False and station["rh_pct"]["simulated"] is False
    assert station["ppo2_mmHg"]["simulated"] is True and station["pressure_kPa"]["simulated"] is True
    assert station["ppo2_mmHg"]["state"] is None                     # the ship has no sourced limit for it
    assert station["dose_mSv_today"] == {"value": 0.51, "state": "OK", "note": "ALERT over 2", "simulated": True}
    assert station["updated_at"].startswith("2026-11-14T06:2") and "Environmental Data App" in station["source"]


def test_the_solar_event_is_shown_and_marked_simulated(morning):
    weather = morning.get("/api/base/space-weather").get_json()
    assert (weather["state"], weather["event_at"], weather["simulated"]) == ("WATCH", "2026-11-14T05:58:00Z", True)
    assert weather["headline"] == "SEP event in progress" and "DONKI" in weather["source"]
