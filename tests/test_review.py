"""Found by the review of the console contract on 14 November."""
from datetime import datetime, timedelta

from common import models

GOOD = {"mood": 2, "sleep_h": 5.1, "symptoms": ["headache"], "note": "", "pvt_ms": 312}
SEEDED = {"A1", "A2", "A3", "A6", "A7"}


def falls(client, crew):
    """Five low blood oxygen readings in a row: the ship raises an SOS."""
    raised = []
    for _ in range(5):
        raised += client.post("/api/base/readings", json={"crew_id": crew, "spo2": 86}).get_json()["alerts"]
    return raised[-1]


def later(seconds):
    models.set_clock(models.utcnow() + timedelta(seconds=seconds))


def at(text):
    return datetime.fromisoformat(text[:-1])


def test_a_live_alert_in_the_morning_has_its_own_id(morning):
    for _ in range(2):                                   # the second time after a reset
        pressed = morning.post("/api/base/sos", json={"crew_id": "C3"}).get_json()
        fell = falls(morning, "C1")
        assert pressed["id"] not in SEEDED and fell["id"] not in SEEDED and pressed["id"] != fell["id"]
        ids = [a["id"] for a in morning.get("/api/base/alerts").get_json()]
        assert len(ids) == len(set(ids))
        assert morning.get(f"/api/base/alerts/{pressed['id']}").get_json()["crew_id"] == "C3"
        got = morning.get(f"/api/base/alerts/{fell['id']}").get_json()
        assert (got["crew_id"], got["metric"], got["state"]) == ("C1", "spo2", "SOS")
        morning.post("/api/base/reset")
    assert morning.get("/api/base/alerts/1").get_json()["id"] == "A1"


def test_a_loaded_message_names_its_alert_by_the_same_number(morning):
    old = morning.get("/api/earth/inbox").get_json()["messages"]
    about = {m["payload"]["alert_id"] for m in old if m["payload"].get("alert_id") is not None}
    assert about <= {int(code[1:]) for code in SEEDED}


def test_a_body_that_is_not_an_object_names_the_crew_id(client):
    for payload in ([1], 5, "C1", True):
        for route in ("/api/base/sos", "/api/base/readings"):
            answer = client.post(route, json=payload)
            assert answer.status_code == 400 and answer.get_json()["field"] == "crew_id", (route, payload)


def test_an_odd_id_is_not_found_rather_than_a_crash(client):
    for path in ("/api/base/alerts/A%C2%B2", "/api/base/crew/%C2%B2", "/api/base/crew/%C2%B2/readings",
                 "/api/base/crew/" + "9" * 25, "/api/base/alerts/A" + "9" * 25, "/api/base/reminders?crew=%C2%B2"):
        assert client.get(path).status_code == 404, path
    for ref in ("R%C2%B2", "R" + "9" * 25):
        assert client.post(f"/api/base/reminders/{ref}/done").status_code == 404, ref
    assert client.post("/api/base/sos", json={"crew_id": "²"}).status_code == 400
    assert client.post("/api/base/readings", json={"crew_id": "9" * 25, "spo2": 98}).status_code == 400


def test_every_400_names_its_field(client):
    alert = client.post("/api/base/sos", json={"crew_id": "C1"}).get_json()
    for route, sent, field in (
            ("/api/base/dial", {"stop": "pluto"}, "stop"),
            (f"/api/base/alerts/{alert['id']}/steps", {"index": 99}, "index"),
            (f"/api/base/alerts/{alert['id']}/clear", {"note": 5}, "note"),
            ("/api/base/messages", {}, "text"),
            ("/api/base/messages", {"text": "Still dizzy.", "alert_id": "A999"}, "alert_id"),
            ("/api/base/scenario/start", {"name": "nope"}, "name"),
            ("/api/base/readings", {"crew_id": "C1", "spo2": "high"}, "spo2"),
            ("/api/base/readings", {"crew_id": "C1", "heart_rate": 70, "context": "x" * 13}, "context"),
            ("/api/base/readings", {"crew_id": "C1", "heart_rate": 70, "source": "s" * 13}, "source")):
        answer = client.post(route, json=sent)
        assert answer.status_code == 400 and set(answer.get_json()) == {"error", "field"}, route
        assert answer.get_json()["field"] == field, route
    assert client.post("/api/base/dial", data="mars", content_type="text/plain").get_json()["field"] == "stop"
    missing = client.get("/api/base/no-such-route")
    assert missing.status_code == 404 and missing.get_json() == {"error": "not found"}
    assert client.delete("/api/base/reset").status_code == 405 and client.delete("/api/base/reset").is_json


def test_a_check_in_symptom_that_is_not_text_is_a_400(morning):
    for symptoms in ([["headache"]], [{}], [{"name": "headache"}]):
        bad = morning.post("/api/base/crew/C1/checkins", json={**GOOD, "symptoms": symptoms})
        assert bad.status_code == 400 and bad.get_json()["field"] == "symptoms", symptoms


def test_the_report_for_a_console_alert_carries_what_the_crew_sees_and_no_strip(morning):
    for _ in range(6):
        morning.post("/api/base/readings", json={"crew_id": "C1", "heart_rate": 80, "spo2": 97})
    morning.post("/api/base/alerts/A1/ack", json={"by": "TJ"})
    morning.post("/api/base/alerts/A1/send")
    payload = morning.get("/api/base/outbox").get_json()[0]["payload"]
    assert payload["why"] == morning.get("/api/base/alerts/A1").get_json()["why"]
    assert "NEWS2" not in str(payload["why"])
    assert payload["recent"] == [] and payload["usual"] is None
    assert "Latest:" not in payload["sbar"]["background"]
    assert payload["bundle"]["simulated"] is True


def test_reset_clears_check_ins_and_reminders_without_the_morning(client):
    client.post("/api/base/crew/C1/checkins", json=GOOD)
    client.post("/api/base/sos", json={"crew_id": "C1"})
    later(2)
    report = client.get("/api/earth/inbox").get_json()["messages"][0]
    client.post("/api/earth/reply", json={"message_id": report["id"], "text": "Rest.", "from": "Dr. Youssef"})
    later(2)
    assert len(client.post("/api/base/alerts/A1/accept-plan", json={"by": "TJ"}).get_json()["reminders"]) == 4
    client.post("/api/base/reset")
    assert client.get("/api/base/reminders").get_json() == []
    assert client.get("/api/base/checkins/today").get_json()["done"] == []


def test_a_check_in_without_a_reaction_time_keeps_the_last_one(morning):
    morning.post("/api/base/crew/C1/checkins", json={"mood": 2, "sleep_h": 5.1, "symptoms": []})
    assert morning.get("/api/base/crew/C1").get_json()["today"]["pvt_ms"] == 301       # typed on 13 November
    morning.post("/api/base/crew/C1/checkins", json=GOOD)
    morning.post("/api/base/crew/C1/checkins", json={"mood": 2, "sleep_h": 5.1, "symptoms": []})
    assert morning.get("/api/base/crew/C1").get_json()["today"]["pvt_ms"] == 312


def test_a_typed_blood_pressure_alert_lists_only_typed_readings(client):
    for _ in range(5):
        client.post("/api/base/readings", json={"crew_id": "C1", "bp_sys": 95})
    raised = client.post("/api/base/readings",
                         json={"crew_id": "C1", "source": "typed", "bp_sys": 88}).get_json()["alerts"]
    assert raised[0]["why"][1] == "Last readings: 88 mmHg."


def test_a_loaded_alerts_earliest_reply_is_one_full_leg_after_earth_heard(morning):
    line = morning.get("/api/base/alerts/A2").get_json()["timeline"]
    back, out = at(line["earliest_reply_at"]) - at(line["earth_at"]), at(line["earth_at"]) - at(line["sent_at"])
    assert abs(back - out) < timedelta(seconds=1)              # the dataset rounds its times to the second


def test_a_resolved_sos_from_the_morning_says_nothing_more(morning):
    assert morning.get("/api/base/alerts/A6").get_json()["speak"] is None


def test_a_resolved_sos_says_nothing_more(client):
    alert = client.post("/api/base/sos", json={"crew_id": "C1"}).get_json()
    assert alert["speak"]
    assert client.post(f"/api/base/alerts/{alert['id']}/clear").get_json()["speak"] is None


def test_the_station_and_the_weather_count_a_row_from_its_first_moment(morning):
    models.set_clock(datetime(2026, 11, 14, 5, 58, 0, 300000))
    assert morning.get("/api/base/space-weather").get_json()["state"] == "WATCH"
    models.set_clock(datetime(2026, 11, 14, 6, 29, 0, 300000))
    assert morning.get("/api/base/station").get_json()["updated_at"] == "2026-11-14T06:29:00Z"


def test_the_mission_day_stops_with_the_dataset(client):
    models.set_clock(datetime(2026, 11, 16, 12))
    try:
        assert client.get("/api/base/state").get_json()["mission_day"] == 158
        assert client.get("/api/base/checkins/today").get_json()["date"] == "2026-11-14"
    finally:
        models.set_clock(None)


def test_ask_ahead_answers_from_the_check_in(morning):
    morning.post("/api/base/sos", json={"crew_id": "C2"})
    report = next(m for m in morning.get("/api/base/outbox").get_json() if m["kind"] == "report")
    answer = next(qa["a"] for qa in report["payload"]["asked_ahead"] if qa["q"] == "How did they sleep and feel?")
    assert answer == "Last check-in: slept 6 h, mood 4 of 5."                            # C2 on 14 November


def test_the_morning_delay_is_the_one_for_14_november(morning):
    state = morning.get("/api/base/state").get_json()
    assert (state["delay_s"], state["round_trip_s"]) == (660.86, 1321.72)


def test_the_ships_own_sos_report_is_signed_by_the_ship(client):
    for alert in (falls(client, "C1"), client.post("/api/base/sos", json={"crew_id": "C2"}).get_json()):
        thread = client.get(f"/api/base/alerts/{alert['id']}/thread").get_json()["messages"]
        assert thread[0]["author"] == "Ship (auto SOS)", alert["metric"]


def test_an_empty_box_is_no_alert_and_no_source_is_the_suit(client):
    sent = client.post("/api/base/messages", json={"text": "All fine.", "alert_id": ""})
    assert sent.status_code == 201 and sent.get_json()["payload"]["alert_id"] is None
    posted = client.post("/api/base/readings", json={"crew_id": "C1", "heart_rate": 70, "source": None})
    assert posted.status_code == 201 and posted.get_json()["reading"]["source"] == "suit"


# Found by the check of the fixes above.

def test_a_wrong_method_is_json_and_still_says_which_methods_work(client):
    answer = client.delete("/api/base/reset")
    assert answer.status_code == 405 and answer.is_json and "POST" in answer.headers["Allow"]


def test_the_dial_and_the_mission_day_use_the_same_date(client):
    models.set_clock(datetime(2026, 11, 16, 12))
    try:
        state = client.post("/api/base/dial", json={"stop": "mars"}).get_json()["state"]
        assert state["delay_s"] == 660.86                                  # 14 November, the dataset's last day
        assert client.get("/api/base/state").get_json()["mission_day"] == 158
    finally:
        models.set_clock(None)


def test_a_number_that_is_not_finite_or_too_big_is_a_400(client):
    for raw in ('{"crew_id": "C1", "heart_rate": "inf"}', '{"crew_id": "C1", "spo2": "nan"}',
                '{"crew_id": "C1", "spo2": 1e400}', '{"crew_id": "C1", "spo2": 1' + "0" * 400 + '}'):
        answer = client.post("/api/base/readings", data=raw, content_type="application/json")
        assert answer.status_code == 400 and answer.get_json()["field"] in ("heart_rate", "spo2"), raw[:40]
    assert client.get("/api/base/crew/C1/readings").get_json() == []
    alert = client.post("/api/base/sos", json={"crew_id": "C1"}).get_json()
    step = client.post(f"/api/base/alerts/{alert['id']}/steps", data='{"index": 1e400}', content_type="application/json")
    assert step.status_code == 400 and step.get_json()["field"] == "index"


def test_a_list_where_a_name_belongs_is_a_400(client):
    for route, sent, field in (("/api/base/dial", {"stop": ["mars"]}, "stop"),
                               ("/api/base/scenario/start", {"name": {"x": 1}}, "name")):
        answer = client.post(route, json=sent)
        assert answer.status_code == 400 and answer.get_json()["field"] == field, route
