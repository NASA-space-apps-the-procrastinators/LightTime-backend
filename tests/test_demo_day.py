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
