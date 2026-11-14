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


def earth_messages(client):
    return client.get("/api/earth/inbox").get_json()["messages"]


def test_earth_sees_nothing_until_the_light_arrives(client, monkeypatch):
    emergency_at(client, "mars")
    assert earth_messages(client) == []
    later(monkeypatch, 12)
    messages = earth_messages(client)
    assert len(messages) == 1
    assert messages[0]["payload"]["sbar"]["situation"].startswith("David")
    assert messages[0]["status"] == "delivered"


def test_near_earth_the_report_lands_at_once(client, monkeypatch):
    emergency_at(client, "station")
    later(monkeypatch, 1)
    assert len(earth_messages(client)) == 1


def test_a_reply_takes_the_same_time_to_come_back(client, monkeypatch):
    emergency_at(client, "mars")
    later(monkeypatch, 12)
    report = earth_messages(client)[0]
    sent = client.post("/api/earth/reply",
                       json={"message_id": report["id"], "text": "Keep the mask on."})
    assert sent.status_code == 201
    assert client.get("/api/base/inbox").get_json() == []
    later(monkeypatch, 12)
    reply = client.get("/api/base/inbox").get_json()[0]
    assert reply["payload"]["text"] == "Keep the mask on." and reply["in_reply_to"] == report["id"]


def test_a_blackout_queues_the_report_and_flushes_when_the_link_returns(client, monkeypatch):
    emergency_at(client, "sun")
    assert client.get("/api/base/outbox").get_json()[0]["status"] == "queued"
    assert client.get("/api/earth/inbox").get_json()["link_up"] is False
    later(monkeypatch, 3600)
    assert earth_messages(client) == []
    assert client.post("/api/base/dial", json={"stop": "mars"}).get_json()["flushed"] == 1
    later(monkeypatch, 12)
    assert len(earth_messages(client)) == 1


def test_the_round_trip_shows_on_the_alert_timeline(client, monkeypatch):
    def timeline():
        return client.get("/api/base/alerts?open=1").get_json()[0]["timeline"]

    emergency_at(client, "mars")
    assert timeline()["earth_at"] is None and timeline()["earth_eta_s"] > 0
    later(monkeypatch, 12)
    report = earth_messages(client)[0]
    client.post("/api/earth/reply", json={"message_id": report["id"], "text": "Keep the mask on."})
    assert timeline()["earth_at"] is not None and timeline()["reply_at"] is None
    later(monkeypatch, 12)
    assert timeline()["reply_at"] is not None
