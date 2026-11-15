"""The Earth console: cases, threads, data age, link state and Earth's outbox,
all built from what the link has delivered."""
import ast
import pathlib
from datetime import timedelta

from base_station import rules
from common import link


def emergency_at(client, stop):
    client.post("/api/base/dial", json={"stop": stop})
    for _ in range(rules.LIMITS["sustain_n"]):
        client.post("/api/base/readings", json={"crew_id": 1, "spo2": 86, "heart_rate": 72})


def later(monkeypatch, seconds):
    clock = link.utcnow
    monkeypatch.setattr(link, "utcnow", lambda: clock() + timedelta(seconds=seconds))


def cases(client):
    return client.get("/api/earth/cases").get_json()["cases"]


def ship_alert_id(client):
    return client.get("/api/base/alerts?open=1").get_json()[0]["id"]


def test_state_reports_the_link_and_the_last_contact(client, monkeypatch):
    state = client.get("/api/earth/state").get_json()
    assert state["link_up"] is True and state["last_contact_at"] is None
    emergency_at(client, "mars")
    state = client.get("/api/earth/state").get_json()
    assert state["delay_s"] > 600 and state["mode"] == "crew_first" and state["last_contact_at"] is None
    later(monkeypatch, 12)
    state = client.get("/api/earth/state").get_json()
    assert state["last_contact_at"] is not None and state["arrived"] == 1


def test_earth_has_no_case_until_the_report_arrives(client, monkeypatch):
    emergency_at(client, "mars")
    assert cases(client) == []
    later(monkeypatch, 12)
    [case] = cases(client)
    assert case["alert_id"] == ship_alert_id(client) and case["alert_id"].startswith("A")
    assert case["crew_id"] == "C1" and case["crew"] == "Okafor" and case["vital"] == "spo2"
    assert case["level"] == "emergency" and case["state"] == "SOS" and case["status"] == "reported"
    assert case["awaiting_reply"] is True


def test_data_age_is_in_mission_time(client, monkeypatch):
    emergency_at(client, "mars")
    later(monkeypatch, 12)
    age = cases(client)[0]["data_age"]
    assert 600 < age["report_age_s"] < 700           # an 11-minute trip, not 11 seconds
    assert age["newest_reading_age_s"] >= age["report_age_s"]
    assert age["newest_reading_at"] is not None


def test_case_status_follows_the_updates_that_arrive(client, monkeypatch):
    emergency_at(client, "station")
    aid = ship_alert_id(client)
    client.post(f"/api/base/alerts/{aid}/ack", json={"by": "Damola"})
    client.post(f"/api/base/alerts/{aid}/steps", json={"index": 0})
    later(monkeypatch, 1)
    case = client.get(f"/api/earth/cases/{aid}").get_json()
    assert case["status"] == "in_progress" and case["acknowledged_by"] == "Damola"
    assert case["steps_done"] == [0] and case["report"]["sbar"]["situation"].startswith("Okafor")
    client.post(f"/api/base/alerts/{aid}/clear", json={"by": "Damola"})
    later(monkeypatch, 2)
    assert client.get(f"/api/earth/cases/{aid}").get_json()["status"] == "resolved"


def test_the_thread_shows_both_sides_with_their_status(client, monkeypatch):
    emergency_at(client, "mars")
    later(monkeypatch, 12)
    aid = cases(client)[0]["alert_id"]
    assert client.post("/api/earth/reply", json={"alert_id": aid, "text": "Keep the mask on."}).status_code == 201
    thread = client.get(f"/api/earth/cases/{aid}/thread").get_json()
    report, reply = thread["messages"]
    assert report["from"] == "crew" and report["status"] == "delivered" and report["arrived_at"]
    assert reply["from"] == "ground" and reply["status"] == "in_flight" and reply["arrived_at"] is None
    assert reply["text"] == "Keep the mask on." and reply["id"].startswith("M") and reply["alert_id"] == aid
    assert thread["alert_id"] == aid
    later(monkeypatch, 24)
    assert client.get(f"/api/earth/cases/{aid}/thread").get_json()["messages"][1]["status"] == "delivered"


def test_a_reply_by_alert_id_reaches_the_ship_timeline(client, monkeypatch):
    emergency_at(client, "mars")
    later(monkeypatch, 12)
    aid = cases(client)[0]["alert_id"]
    client.post("/api/earth/reply", json={"alert_id": aid.lstrip("A"), "text": "Mask on."})   # a bare number works too
    assert cases(client)[0]["awaiting_reply"] is False and cases(client)[0]["reply_status"] == "in_flight"
    later(monkeypatch, 24)
    timeline = client.get("/api/base/alerts?open=1").get_json()[0]["timeline"]
    assert timeline["reply_at"] is not None


def test_reply_checks_its_input(client, monkeypatch):
    emergency_at(client, "mars")
    later(monkeypatch, 12)
    aid = cases(client)[0]["alert_id"]
    bad = client.post("/api/earth/reply", json={"alert_id": aid})
    assert bad.status_code == 400 and bad.get_json()["field"] == "text"
    assert client.post("/api/earth/reply", json={"message_id": 999, "text": "x"}).status_code == 404
    assert client.post("/api/earth/reply", json={"alert_id": "A999", "text": "x"}).status_code == 404
    mine = client.post("/api/earth/reply", json={"alert_id": aid, "text": "first"}).get_json()
    reply_to_self = client.post("/api/earth/reply", json={"message_id": mine["id"], "text": "x"})
    assert reply_to_self.status_code == 400 and reply_to_self.get_json()["field"] == "message_id"


def test_unknown_case_is_404(client):
    assert client.get("/api/earth/cases/A42").status_code == 404
    assert client.get("/api/earth/cases/42/thread").status_code == 404
    assert client.get("/api/earth/cases/abc").status_code == 404


def test_the_earth_outbox_lists_what_the_ground_sent(client, monkeypatch):
    emergency_at(client, "mars")
    later(monkeypatch, 12)
    aid = cases(client)[0]["alert_id"]
    client.post("/api/earth/reply", json={"alert_id": aid, "text": "Mask on."})
    [sent] = client.get("/api/earth/outbox").get_json()
    assert sent["status"] == "in_flight" and f"A{sent['payload']['alert_id']}" == aid and sent["eta_s"] > 0


def test_a_blackout_hides_the_case_until_the_queue_flushes(client, monkeypatch):
    emergency_at(client, "sun")
    later(monkeypatch, 3600)
    assert cases(client) == [] and client.get("/api/earth/state").get_json()["link_up"] is False
    client.post("/api/base/dial", json={"stop": "mars"})
    later(monkeypatch, 12)
    [case] = cases(client)
    assert case["data_age"]["queued_s"] >= 3600         # Earth can see the report waited for the link


def test_the_command_center_never_imports_the_ship_tables():
    folder = pathlib.Path(__file__).resolve().parents[1] / "command_center"
    for path in folder.glob("*.py"):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                names = {a.name for a in node.names}
                assert not names & {"Crew", "Reading", "Alert"}, path.name
                assert not (node.module or "").startswith("base_station"), path.name
