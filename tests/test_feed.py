"""The vitals feed lives on the Earth side: each tick goes over the link and Earth keeps it.
The ship's tables are not touched."""
import time
from datetime import datetime, timedelta

from command_center import feed
from common import link
from common.models import Reading

DEMO = datetime(2026, 11, 14, 6, 30)


def later(monkeypatch, seconds):
    clock = link.utcnow
    monkeypatch.setattr(link, "utcnow", lambda: clock() + timedelta(seconds=seconds))


def tick_at(app, when):
    with app.app_context():
        return feed.tick(now=when)


def test_a_tick_is_one_link_message_with_four_readings(app, client):
    assert tick_at(app, DEMO) is not None
    sent = [m for m in client.get("/api/base/outbox").get_json() if m["kind"] == "vitals"]
    assert len(sent) == 1 and sent[0]["direction"] == "to_earth" and sent[0]["priority"] == feed.PRIORITY
    payload = sent[0]["payload"]
    assert payload["simulated"] is True and payload["alert_id"] is None
    assert [(r["crew_id"], r["crew"]) for r in payload["readings"]] == [
        ("C1", "Okafor"), ("C2", "Linda Rodenburg"), ("C3", "Sato"), ("C4", "Rebecca Qi")]


def test_the_ship_stores_each_reading_through_its_own_api(app, client):
    tick_at(app, DEMO)
    with app.app_context():
        assert Reading.query.filter_by(source=feed.SOURCE).count() == 4
    latest = client.get("/api/base/crew/C2/readings?limit=1").get_json()[0]
    assert latest["source"] == "feed" and latest["heart_rate"] is not None
    assert client.get("/api/base/alerts").get_json() == []


def test_the_ship_drops_them_after_24_hours_earth_keeps_them(app, client, monkeypatch):
    tick_at(app, DEMO)
    later(monkeypatch, 5)
    with app.app_context():
        from common import models
        models.set_clock(link.utcnow() + timedelta(hours=25))
    try:
        assert client.post("/api/base/summary/send").get_json()["pruned"] == 4
    finally:
        models.set_clock(None)
    assert client.get("/api/base/crew/C1/readings").get_json() == []
    assert len(client.get("/api/earth/vitals?crew=C1").get_json()["readings"]) == 1


def test_a_day_of_ticks_raises_no_vital_alarm_on_the_ship(app):
    with app.app_context():
        from common.models import Alert
        for minute in range(0, 24 * 60, 2):
            feed.tick(now=DEMO + timedelta(minutes=minute))
        assert {a.vital for a in Alert.query.all()} <= {"signal"}   # only "check your sensor"
        assert Alert.query.filter_by(level="emergency").count() == 0


def test_the_values_are_the_generated_minute_for_the_clock(app, client):
    tick_at(app, DEMO.replace(hour=3, minute=15))
    [c1] = [r for r in client.get("/api/base/outbox").get_json()[0]["payload"]["readings"] if r["crew_id"] == "C1"]
    assert c1["data_minute"][11:16] == "03:15"
    assert 30 < c1["heart_rate"] < 140 and 80 < c1["spo2"] <= 100 and 0 <= c1["signal_quality"] <= 1


def test_earth_sees_the_vitals_only_after_the_light_delay(app, client, monkeypatch):
    client.post("/api/base/dial", json={"stop": "mars"})
    tick_at(app, link.utcnow())
    assert client.get("/api/earth/vitals").get_json()["readings"] == []
    later(monkeypatch, 12)
    body = client.get("/api/earth/vitals").get_json()
    assert len(body["readings"]) == 4 and body["simulated"] is True
    assert set(body["latest"]) == {"C1", "C2", "C3", "C4"}
    one = body["latest"]["C2"]
    assert one["message_id"].startswith("M") and one["arrived_at"] and one["age_s"] > 600


def test_a_blackout_queues_the_ticks_until_the_link_returns(app, client, monkeypatch):
    client.post("/api/base/dial", json={"stop": "sun"})
    tick_at(app, link.utcnow())
    later(monkeypatch, 60)
    assert client.get("/api/earth/vitals").get_json()["readings"] == []
    client.post("/api/base/dial", json={"stop": "station"})
    later(monkeypatch, 61)
    assert len(client.get("/api/earth/vitals").get_json()["readings"]) == 4


def test_earth_keeps_every_tick_and_filters_by_crew(app, client, monkeypatch):
    for minute in (0, 2, 4):
        tick_at(app, link.utcnow() - timedelta(minutes=10 - minute))
    later(monkeypatch, 5)
    c3 = client.get("/api/earth/vitals?crew=C3").get_json()["readings"]
    assert len(c3) == 3 and {r["crew_id"] for r in c3} == {"C3"}
    assert c3[0]["at"] > c3[-1]["at"]                       # newest first
    assert len(client.get("/api/earth/vitals?crew=3&limit=2").get_json()["readings"]) == 2


def test_vitals_do_not_become_cases(app, client, monkeypatch):
    tick_at(app, link.utcnow())
    later(monkeypatch, 5)
    assert client.get("/api/earth/cases").get_json()["cases"] == []


def test_earth_vitals_checks_its_input(client):
    assert client.get("/api/earth/vitals?crew=bob").get_json()["field"] == "crew"
    assert client.get("/api/earth/vitals?limit=0").status_code == 400
    assert client.get("/api/earth/vitals?limit=x").get_json()["field"] == "limit"


def test_start_and_stop(client):
    assert client.post("/api/earth/feed/start", json={"interval_s": 1}).get_json()["field"] == "interval_s"
    assert client.post("/api/earth/feed/start", json={"interval_s": "fast"}).status_code == 400
    try:
        status = client.post("/api/earth/feed/start", json={"interval_s": 60}).get_json()
        assert status["running"] is True and status["interval_s"] == 60 and status["simulated"] is True
        for _ in range(50):                    # the first tick goes at once
            if client.get("/api/earth/feed").get_json()["ticks"] >= 1:
                break
            time.sleep(0.1)
        status = client.get("/api/earth/feed").get_json()
        assert status["ticks"] == 1 and status["stored_on_ship"] == 4
    finally:
        assert client.post("/api/earth/feed/stop").get_json()["running"] is False
    assert client.post("/api/earth/feed/start").get_json()["interval_s"] == feed.DEFAULT_INTERVAL_S == 120
    client.post("/api/earth/feed/stop")
