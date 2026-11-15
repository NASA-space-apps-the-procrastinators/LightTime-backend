from datetime import datetime

from common import models
from tests.test_console import GOOD, later, reply_and_accept


def test_the_morning_starts_at_half_past_six_on_day_158_at_mars(morning):
    state = morning.get("/api/base/state").get_json()
    assert (state["mission_day"], state["platform"], state["stop"]) == (158, "ISS", "mars")


def test_the_one_open_alert_is_the_resting_heart_rate(morning):
    alerts = morning.get("/api/base/alerts?open=1").get_json()
    assert [a["id"] for a in alerts] == ["A1"]
    a1 = alerts[0]
    assert (a1["crew_id"], a1["metric"], a1["value"], a1["unit"]) == ("C1", "hr_rest", 84, "bpm")
    assert (a1["state"], a1["stage"], a1["symptoms"]) == ("ALERT", "raised", ["headache"])
    assert a1["timeline"]["raised_at"] == "2026-11-14T06:12:00Z"
    assert a1["rule"].startswith("resting HR") and a1["source"].startswith("OCHMO")
    assert a1["steps"][1] == "Have them stop work and rest"
    everything = morning.get("/api/base/alerts").get_json()
    assert [a["id"] for a in everything] == ["A1", "A7", "A6", "A3", "A2"]     # A4 and A5 have no rule behind them
    assert "pending" not in str(everything)


def test_restart_puts_the_same_morning_back(morning):
    morning.post("/api/base/alerts/A1/ack", json={"by": "TJ"})
    morning.post("/api/base/readings", json={"crew_id": "C2", "spo2": 97})
    morning.post("/api/base/dial", json={"stop": "moon"})
    assert morning.post("/api/base/reset").get_json() == {"ok": True}
    a1 = morning.get("/api/base/alerts/A1").get_json()
    assert a1["stage"] == "raised" and a1["timeline"]["acknowledged_at"] is None
    state = morning.get("/api/base/state").get_json()
    assert (state["stop"], state["mission_day"]) == ("mars", 158)
    assert morning.get("/api/base/crew/C2/readings").get_json() == []


def board(morning):
    """Today's check-ins and the reminders, without row numbers: Postgres does not hand deleted ones back."""
    reminders = [{k: v for k, v in r.items() if k != "id"} for r in morning.get("/api/base/reminders").get_json()]
    return morning.get("/api/base/checkins/today").get_json(), reminders


def test_restart_undoes_the_whole_loop(morning):
    before = board(morning)
    morning.post("/api/base/crew/C1/checkins", json=GOOD)
    reply_and_accept(morning)
    later(3600)
    morning.post("/api/base/reset")
    assert board(morning) == before
    assert abs((models.utcnow() - datetime(2026, 11, 14, 6, 30)).total_seconds()) < 5
