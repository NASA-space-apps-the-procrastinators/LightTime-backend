from base_station import reports

POOR = {"crew_id": "C3", "spo2": 98, "signal_ok": False}


def test_the_state_carries_the_ships_clock(morning):
    assert morning.get("/api/base/state").get_json()["now"].startswith("2026-11-14T06:30")


def test_a_live_emergency_turns_the_crew_card_red(client):
    before = client.get("/api/base/crew/C3").get_json()["state"]
    for _ in range(5):
        client.post("/api/base/readings", json={"crew_id": "C3", "spo2": 86})
    card = client.get("/api/base/crew/C3").get_json()
    assert before != "ALERT" and (card["state"], card["level"]) == ("ALERT", "emergency")


def test_a_sensor_check_does_not_colour_the_card(client):
    before = client.get("/api/base/crew/C3").get_json()["state"]
    client.post("/api/base/readings", json=POOR)
    assert client.get("/api/base/crew/C3").get_json()["state"] == before


def test_generated_values_say_so(morning):
    assert morning.get("/api/base/crew/C1").get_json()["simulated"] is True
    old = morning.get("/api/base/alerts/A7/thread").get_json()["messages"]
    assert old and all(message["simulated"] for message in old)
    morning.post("/api/base/messages", json={"text": "Checking in.", "from": "Okafor", "alert_id": "A1"})
    assert morning.get("/api/base/alerts/A1/thread").get_json()["messages"][-1]["simulated"] is False


def test_every_alert_ends_by_saying_who_decides(client):
    pressed = client.post("/api/base/sos", json={"crew_id": "C2"}).get_json()
    check = client.post("/api/base/readings", json=POOR).get_json()["alerts"][0]
    assert pressed["why"][-1] == "A person raised this, and a person decides what happens next."
    assert check["why"][-1] == reports.NOT_A_DIAGNOSIS and check["rule"].startswith("a reading with a poor signal")


def test_an_alert_says_who_raised_it(morning):
    assert morning.get("/api/base/alerts/A1").get_json()["raised_by"] == "console"
    pressed = morning.post("/api/base/sos", json={"crew_id": "C2"}).get_json()
    for _ in range(5):
        raised = morning.post("/api/base/readings", json={"crew_id": "C3", "spo2": 86}).get_json()["alerts"]
    assert (pressed["raised_by"], raised[0]["raised_by"]) == ("crew", "lighttime")


def test_the_crew_object_carries_the_week(morning):
    okafor = morning.get("/api/base/crew/C1").get_json()
    week = okafor["week"]
    assert set(week) == set(okafor["metric_states"]) and all(len(days) == 7 for days in week.values())
    assert week["hr_rest"] == [60, 59, 58, 59, 80, 82, 84] and week["hr_rest"][-1] == okafor["today"]["hr_rest"]
    chart = morning.get("/api/base/crew/C1/history?metric=bp_sys&days=7").get_json()
    assert week["bp_sys"] == [day["value"] for day in chart["days"]]
    assert week["bp_sys"][-1] == 110            # no cuff reading yet today, so yesterday's stands


SUIT = {"astronaut_id": "LT-04", "heart_rate_bpm": 76, "spo2_percent": 98, "skin_temp_c": 33.9,
        "radiation_dose_msv": 84.2, "radiation_rate_usvh": 12.5}


def test_the_suit_can_use_its_own_field_names(client):
    sent = client.post("/api/base/readings", json=SUIT)
    answer = sent.get_json()
    assert sent.status_code == 201 and answer["reading"]["crew_id"] == 4
    reading = answer["reading"]
    assert (reading["heart_rate"], reading["spo2"], reading["skin_temp"]) == (76, 98, 33.9)
    assert answer["ignored"] == ["radiation_dose_msv", "radiation_rate_usvh"]      # said, not silently dropped
    assert client.get("/api/base/crew/C4").get_json()["latest"]["heart_rate"] == 76


def test_the_ships_own_names_still_work_and_win(client):
    answer = client.post("/api/base/readings",
                         json={"crew_id": "C4", "heart_rate": 70, "heart_rate_bpm": 99}).get_json()
    assert answer["reading"]["heart_rate"] == 70 and answer["ignored"] == []


def test_a_suit_nobody_wears_is_refused_by_name(client):
    refused = client.post("/api/base/readings", json={"astronaut_id": "S1", "heart_rate_bpm": 76})
    assert refused.status_code == 400 and refused.get_json()["field"] == "crew_id"


def test_five_low_readings_in_the_suits_words_still_raise_the_sos(client):
    for _ in range(5):
        raised = client.post("/api/base/readings",
                             json={"astronaut_id": "LT-04", "spo2_percent": 86}).get_json()["alerts"]
    assert [(alert["crew_id"], alert["state"]) for alert in raised] == [("C4", "SOS")]


def test_the_ship_never_uses_the_words_to_avoid(client):
    for _ in range(5):
        raised = client.post("/api/base/readings", json={"crew_id": "C3", "spo2": 86}).get_json()["alerts"]
    said = " ".join([raised[0]["source"], *raised[0]["why"]]).lower()
    assert not [word for word in ("machine learning", "trained", "validated", "predicts illness") if word in said]
