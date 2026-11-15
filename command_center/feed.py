"""The suits' vitals feed to Earth: every few minutes, one reading per crew member.

Each tick does what the suits and the ship would: the readings go to the ship first, through
its public API (POST /api/base/readings), where they sit in its 24-hour recorder and its rules
run on them; then the tick goes over the link to Earth as one message (kind "vitals"), with the
same light delay as everything else, queued while the link is down and sent after any SOS or
report when it returns. Earth is the long-term record and keeps every tick it receives
(GET /api/earth/vitals); the ship is the short-term cache. This module never imports the
ship's code or tables.

The values are replayed, not random: the suits' minute rows for the 24 hours before the demo
morning (data/processed/anomalous/vitals_1min.csv), picked by the mission clock's time of day.
Crew names come from data/processed/reference/crew.csv. Every value is SIMULATED and says so.
"""
import threading

from flask import current_app

from common import dataset, link, modes
from common.models import MissionState, db, iso

DEFAULT_INTERVAL_S = 120          # every 2 minutes: kept low on purpose, changeable per start
MIN_INTERVAL_S, MAX_INTERVAL_S = 5, 3600
PRIORITY = 9                      # behind every report, update and SOS when a queue flushes
SOURCE = "feed"                   # how the ship labels these readings

_lock = threading.Lock()
_halt = threading.Event()
_thread = None
_status = {"running": False, "interval_s": DEFAULT_INTERVAL_S, "started_at": None,
           "last_tick_at": None, "ticks": 0, "stored_on_ship": 0}


def _number(text):
    return None if text in ("", None) else float(text)


def _crew():
    """[("C1", "Okafor"), ...] from the mission's reference crew list."""
    return [(row["crew_id"], row["name"]) for row in dataset.table("reference/crew")]


def _day():
    """{("C1", "06:30"): row} for every minute of the generated day, one row per crew member."""
    return {(row["crew_id"], row["sensor_ts"][11:16]): row for row in dataset.last_minutes(24)}


def to_ship(readings):
    """Hand each reading to the ship the way a suit does: through its public API, POST
    /api/base/readings, never its tables. The ship keeps them in its 24-hour recorder and runs
    its rules on them. Returns how many it stored."""
    client, stored = current_app.test_client(), 0
    for r in readings:
        answer = client.post("/api/base/readings", json={
            "crew_id": r["crew_id"], "heart_rate": r["heart_rate"], "spo2": r["spo2"],
            "skin_temp": r["skin_temp"], "signal_ok": r["signal_ok"], "source": SOURCE})
        if answer.status_code == 201:
            stored += 1
        else:
            current_app.logger.warning("the ship refused a feed reading for %s: %s",
                                       r["crew_id"], answer.get_data(as_text=True))
    with _lock:
        _status["stored_on_ship"] += stored
    return stored


def tick(now=None):
    """Send one round of readings to Earth. Returns the link message, or None if there was no data."""
    now = now or link.utcnow()
    minute, day, readings = now.strftime("%H:%M"), _day(), []
    for code, name in _crew():
        row = day.get((code, minute))
        if row is None:
            continue
        readings.append({
            "crew_id": code, "crew": name, "at": iso(now),
            "heart_rate": _number(row["hr_bpm"]), "spo2": _number(row["spo2_pct"]),
            "skin_temp": _number(row["skin_temp_c"]), "resp_rpm": _number(row["resp_rpm"]),
            "core_temp_c": _number(row["core_temp_c"]), "signal_quality": _number(row["signal_quality"]),
            "signal_ok": row["signal_ok"] == "true", "data_minute": row["sensor_ts"][:16] + "Z",
        })
    if not readings:
        return None
    to_ship(readings)
    state = modes.describe(db.session.get(MissionState, 1).stop)
    message = link.send("to_earth", "vitals", {"alert_id": None, "simulated": True, "readings": readings},
                        state["delay_s"], state["link_up"], priority=PRIORITY, now=now)
    with _lock:
        _status["ticks"] += 1
        _status["last_tick_at"] = iso(now)
    return message


def _run(app, interval_s, halt):
    with app.app_context():
        while not halt.is_set():
            try:
                tick()
            except Exception:                     # one bad tick must not end the feed
                app.logger.exception("vitals feed tick failed")
            finally:
                db.session.remove()
            halt.wait(interval_s)


def start(app, interval_s=DEFAULT_INTERVAL_S):
    """Start the feed, or restart it with a new interval. The first tick goes at once."""
    global _thread
    stop()
    with _lock:
        _halt.clear()
        _status.update(running=True, interval_s=interval_s, started_at=iso(link.utcnow()),
                       ticks=0, last_tick_at=None, stored_on_ship=0)
        _thread = threading.Thread(target=_run, args=(app, interval_s, _halt), daemon=True, name="vitals-feed")
        _thread.start()


def stop():
    global _thread
    _halt.set()
    if _thread is not None and _thread is not threading.current_thread():
        _thread.join(timeout=5)
    _thread = None
    with _lock:
        _status["running"] = False


def status():
    with _lock:
        return dict(_status, simulated=True)
