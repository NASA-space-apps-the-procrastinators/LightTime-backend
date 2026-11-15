from datetime import timedelta

from base_station import recorder
from common import link
from common.models import Crew, Reading, db, utcnow


def test_readings_older_than_a_day_leave_the_recorder(app):
    with app.app_context():
        now = utcnow()
        db.session.add_all([Reading(crew_id=1, heart_rate=70, at=now - timedelta(hours=25)),
                            Reading(crew_id=1, heart_rate=72, at=now - timedelta(hours=1))])
        db.session.commit()
        assert recorder.prune(now) == 1
        assert [r.heart_rate for r in Reading.query.all()] == [72]


def test_the_daily_summary_gives_low_middle_and_high(app):
    with app.app_context():
        for rate in (60, 70, 95):
            db.session.add(Reading(crew_id=1, heart_rate=rate, spo2=98, context="rest"))
        db.session.add(Reading(crew_id=1, heart_rate=150, context="exercise"))
        db.session.commit()
        summary = recorder.daily_summary(db.session.get(Crew, 1))
        assert summary["vitals"]["heart_rate"] == {"low": 60, "median": 82.5, "high": 150}
        assert summary["readings"] == 4 and summary["alerts"] == [] and summary["sources"] == ["suit"]


def test_summaries_travel_to_earth_like_everything_else(client, monkeypatch):
    client.post("/api/base/readings", json={"crew_id": 1, "heart_rate": 70, "spo2": 98})
    assert client.post("/api/base/summary/send").get_json() == {"sent": 3, "pruned": 0}
    clock = link.utcnow
    monkeypatch.setattr(link, "utcnow", lambda: clock() + timedelta(seconds=2))
    arrived = client.get("/api/earth/inbox").get_json()["messages"]
    assert sorted(m["payload"]["crew"] for m in arrived if m["kind"] == "summary") == ["Lindqvist", "Okafor", "Sato"]
