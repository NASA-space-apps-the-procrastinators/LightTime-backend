from datetime import datetime, timedelta

from common import models

LOW = {"crew_id": 1, "spo2": 86}


def sos(client):
    for _ in range(5):
        raised = client.post("/api/base/readings", json=LOW).get_json()["alerts"]
    return raised[0]


def test_a_live_alert_speaks_the_consoles_language(client):
    alert = sos(client)
    assert alert["id"].startswith("A") and alert["crew_id"] == "C1" and alert["crew"] == "TJ"
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
                        json={"by": "TJ", "symptoms": ["headache"]}).get_json()
    assert acked["symptoms"] == ["headache"] and acked["timeline"]["acknowledged_at"] is not None


def test_the_crew_overview_gets_the_cards_it_already_draws(morning):
    crew = morning.get("/api/base/crew").get_json()
    assert [member["id"] for member in crew] == ["C1", "C2", "C3", "C4"]
    c1 = crew[0]
    assert (c1["name"], c1["role"], c1["suit_id"], c1["state"]) == ("TJ", "Commander", "LT-01", "ALERT")
    assert c1["baseline"]["hr_rest"] == [52, 64] and c1["baseline"]["bp"] == [[108, 122], [66, 78]]
    assert c1["baseline"]["pvt_ms"] == 265
    today = c1["today"]
    assert (today["hr_rest"], today["spo2"], today["temp_c"], today["resp"], today["sleep_h"]) == (84, 97, 37.2, 17, 5.1)
    assert (today["dose_mSv_day"], today["dose_mSv_mission"]) == (0.51, 81.0)
    # TJ has not checked in yet today, so what they typed yesterday still stands
    assert today["symptoms"] == ["headache", "short sleep"] and c1["checkin_from"] == "2026-11-13"
    assert c1["metric_states"]["hr_rest"] == "ALERT" and c1["metric_states"]["spo2"] == "OK"
    assert [(m["id"], m["state"]) for m in crew] == [("C1", "ALERT"), ("C2", "WATCH"), ("C3", "OK"), ("C4", "ALERT")]
    assert crew[2]["note"] == "All in band" and crew[0]["note"].startswith("Out of band: resting heart rate")
    assert c1["last_packet_at"] == "2026-11-14T06:29:00Z"                  # the dataset's last minute
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
    assert co2 == {"value": 2.99, "state": "WATCH", "note": "WATCH from 2.8, ALERT from 4.5", "simulated": False}
    assert station["temp_c"]["simulated"] is False and station["rh_pct"]["simulated"] is False
    assert station["ppo2_mmHg"]["simulated"] is True and station["pressure_kPa"]["simulated"] is True
    assert station["ppo2_mmHg"]["state"] is None                     # the ship has no sourced limit for it
    assert station["dose_mSv_today"] == {"value": 0.51, "state": "OK", "note": "ALERT over 2", "simulated": True}
    assert station["updated_at"].startswith("2026-11-14T06:2") and "Environmental Data App" in station["source"]


def test_the_solar_event_is_shown_and_marked_simulated(morning):
    weather = morning.get("/api/base/space-weather").get_json()
    assert (weather["state"], weather["event_at"], weather["simulated"]) == ("WATCH", "2026-11-14T05:58:00Z", True)
    assert weather["headline"] == "SEP event in progress" and "DONKI" in weather["source"]


GOOD = {"mood": 2, "sleep_h": 5.1, "symptoms": ["headache"], "note": "", "pvt_ms": 312}


def test_the_morning_board_knows_who_has_checked_in(morning):
    assert morning.get("/api/base/checkins/today").get_json() == {
        "date": "2026-11-14", "done": ["C2", "C3", "C4"], "due": ["C1"], "streak": 12, "next_badge_at": 14}


def test_a_check_in_is_saved_scored_and_copied_to_the_open_alert(morning):
    saved = morning.post("/api/base/crew/C1/checkins", json={**GOOD, "bp_sys": 128, "bp_dia": 82})
    body = saved.get_json()
    assert saved.status_code == 201
    assert (body["crew_id"], body["first_today"], body["streak"], body["open_alert_id"]) == ("C1", True, 13, "A1")
    assert body["metric_states"] == {"sleep_h": "ALERT", "mood": "ALERT", "pvt_ms": "ALERT"}
    c1 = morning.get("/api/base/crew/C1").get_json()
    assert c1["today"]["bp"] == [128, 82] and c1["today"]["mood"] == 2 and c1["today"]["pvt_ms"] == 312
    assert c1["checkin_from"] == "2026-11-14"
    assert c1["metric_states"] == {      # the contract's own example for TJ, value for value
        "hr_rest": "ALERT", "bp_sys": "ALERT", "bp_dia": "ALERT", "spo2": "OK", "temp_c": "ALERT", "resp": "OK",
        "sleep_h": "ALERT", "mood": "ALERT", "pvt_ms": "ALERT", "dose_mSv_day": "OK"}
    assert morning.get("/api/base/alerts/A1").get_json()["symptoms"] == ["headache"]
    assert morning.get("/api/base/checkins/today").get_json()["due"] == []
    morning.post("/api/base/crew/C1/checkins", json={**GOOD, "symptoms": ["nausea", "short sleep"]})
    assert morning.get("/api/base/alerts/A1").get_json()["symptoms"] == ["nausea", "short sleep"]
    mood = morning.get("/api/base/crew/C1/history?metric=mood").get_json()["days"]
    assert mood[-1] == {"date": "2026-11-14", "value": 2}                   # today's point is the check-in


def test_a_second_check_in_the_same_day_replaces_the_first(morning):
    morning.post("/api/base/crew/C1/checkins", json=GOOD)
    again = morning.post("/api/base/crew/C1/checkins", json={**GOOD, "mood": 4}).get_json()
    assert (again["first_today"], again["streak"]) == (False, 13)
    today = morning.get("/api/base/crew/C1").get_json()["today"]
    assert today["mood"] == 4 and today["bp"] == [110, 71]      # no cuff reading was sent: yesterday's stands


def test_a_bad_check_in_names_the_field(morning):
    for field, value in (("mood", 6), ("mood", 2.5), ("sleep_h", 25), ("note", "x" * 501), ("pvt_ms", 50),
                         ("symptoms", ["dizzy"]), ("bp_sys", "high"), ("bp_dia", "high"), ("mood", True),
                         ("sleep_h", True), ("pvt_ms", 3001)):
        bad = morning.post("/api/base/crew/C1/checkins", json={**GOOD, field: value})
        assert bad.status_code == 400 and bad.get_json()["field"] == field, field
    assert morning.post("/api/base/crew/C9/checkins", json=GOOD).status_code == 404
    assert morning.get("/api/base/checkins/today").get_json()["due"] == ["C1"]


def later(seconds):
    """Let mission time pass: long enough for a message to cross at 60 times speed."""
    models.set_clock(models.utcnow() + timedelta(seconds=seconds))


def reply_and_accept(morning):
    morning.post("/api/base/alerts/A1/ack", json={"by": "TJ"})
    morning.post("/api/base/alerts/A1/send")
    later(30)
    report = morning.get("/api/earth/inbox").get_json()["messages"][0]
    morning.post("/api/earth/reply",
                 json={"message_id": report["id"], "text": "Temperature every 4 hours.", "from": "Dr. Youssef"})
    later(30)
    return morning.post("/api/base/alerts/A1/accept-plan", json={"by": "TJ"}).get_json()


def test_sending_an_alert_puts_the_week_in_the_report_and_one_message_in_the_thread(morning):
    morning.post("/api/base/alerts/A1/ack", json={"by": "TJ", "symptoms": ["headache"]})
    assert morning.post("/api/base/alerts/A1/send").get_json()["stage"] == "sent"
    report = morning.get("/api/base/outbox").get_json()[0]
    assert report["kind"] == "report" and report["payload"]["text"].startswith("Alert bundle")
    week = report["payload"]["bundle"]["days"]
    assert set(week) == {"hr_rest", "bp_sys", "bp_dia", "temp_c", "sleep_h"}
    assert [day["value"] for day in week["hr_rest"]][-3:] == [80, 82, 84]
    today = report["payload"]["bundle"]["today"]
    assert (today["symptoms"], today["checkin_from"]) == (["headache", "short sleep"], "2026-11-13")
    thread = morning.get("/api/base/alerts/A1/thread").get_json()
    assert thread["alert_id"] == "A1"
    assert [(m["from"], m["author"], m["status"]) for m in thread["messages"]] == [("crew", "TJ", "in_flight")]


def test_a_reply_takes_the_light_time_and_only_then_can_the_plan_be_accepted(morning):
    morning.post("/api/base/alerts/A1/ack", json={"by": "TJ"})
    morning.post("/api/base/alerts/A1/send")
    early = morning.post("/api/base/alerts/A1/accept-plan", json={"by": "TJ"}).get_json()
    assert early["alert"]["stage"] == "sent" and early["reminders"] == []           # nothing to accept yet
    later(30)
    report = morning.get("/api/earth/inbox").get_json()["messages"][0]
    morning.post("/api/earth/reply",
                 json={"message_id": report["id"], "text": "Temperature every 4 hours.", "from": "Dr. Youssef"})
    assert morning.get("/api/base/alerts/A1").get_json()["stage"] == "sent"           # the reply is still on its way
    early_thread = morning.get("/api/base/alerts/A1/thread").get_json()["messages"]
    assert [(m["from"], m["author"]) for m in early_thread] == [("crew", "TJ")]
    later(30)
    assert morning.get("/api/base/alerts/A1").get_json()["stage"] == "replied"
    thread = morning.get("/api/base/alerts/A1/thread").get_json()["messages"]
    assert [(m["from"], m["author"]) for m in thread] == [("crew", "TJ"), ("ground", "Dr. Youssef")]


def test_accepting_the_plan_resolves_the_alert_and_sets_four_reminders(morning):
    done = reply_and_accept(morning)
    assert done["alert"]["stage"] == "resolved"
    assert [r["text"] for r in done["reminders"]] == ["Take temperature"] * 4
    waiting = morning.get("/api/base/reminders?crew=C1&open=1").get_json()
    assert len(waiting) == 4 and waiting[0]["due_at"] < waiting[1]["due_at"] and waiting[0]["crew_id"] == "C1"
    ticked = morning.post(f"/api/base/reminders/{waiting[0]['id']}/done").get_json()
    assert ticked["done_at"] is not None
    assert len(morning.get("/api/base/reminders?open=1").get_json()) == 3
    assert morning.post("/api/base/reminders/R999/done").status_code == 404
    assert morning.get("/api/base/alerts?open=1").get_json() == []
    again = morning.post("/api/base/alerts/A1/accept-plan", json={"by": "TJ"}).get_json()
    assert again["reminders"] == [] and len(morning.get("/api/base/reminders?open=1").get_json()) == 3
    assert any(m["payload"].get("event") == "resolved" for m in morning.get("/api/base/outbox").get_json())
    dues = [datetime.fromisoformat(r["due_at"][:-1]) for r in done["reminders"]]
    assert {(b - a).total_seconds() for a, b in zip(dues, dues[1:])} == {14400}
    assert {r["crew_id"] for r in morning.get("/api/base/reminders?crew=C1").get_json()} == {"C1"}
    assert {r["crew_id"] for r in morning.get("/api/base/reminders").get_json()} == {"C1", "C2"}


def test_a_typed_message_joins_its_alerts_thread(morning):
    morning.post("/api/base/messages", json={"text": "Headache is worse.", "from": "TJ", "alert_id": "A1"})
    thread = morning.get("/api/base/alerts/A1/thread").get_json()["messages"]
    assert [(m["from"], m["text"], m["kind"]) for m in thread] == [("crew", "Headache is worse.", "message")]
    old = morning.get("/api/base/alerts/A7/thread").get_json()["messages"]
    assert [(m["from"], m["author"], m["kind"]) for m in old] == [            # the blackout alert's history
        ("crew", "Ship (auto SOS)", "report"), ("crew", "Rebecca", "message"), ("crew", "Rebecca", "update"),
        ("ground", "Dr. Youssef", "reply")]
