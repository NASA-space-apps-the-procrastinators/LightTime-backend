"""The scripted day and collapse. No randomness: every run plays the same."""
import math
import threading
from datetime import timedelta

from base_station import replay, usual
from common.models import Alert, Reading, db, utcnow

# crew_id: resting heart rate, blood oxygen, skin temperature. SIMULATED values.
NORMAL = {1: (72, 98.0, 33.5), 2: (64, 99.0, 33.2), 3: (80, 97.5, 33.8)}
PATIENT = 1
LOW_SPO2, RAISED_RATE = 86.0, 88
TREATMENT_STEP = 1  # the second step of the spo2 checklist in procedures.json

SCENARIOS = {
    "stage": {"calm_s": 4, "drift_s": 0, "collapse_s": 60, "recover_s": 8, "tail_s": 180},
    # the guided tour: the same story with no calm and a quicker drift, so it fits in 30 seconds
    "tour": {"calm_s": 0, "drift_s": 16, "collapse_s": 60, "recover_s": 8, "tail_s": 180},
    "full": {"calm_s": 20, "drift_s": 20, "collapse_s": 60, "recover_s": 8, "tail_s": 180},
    "real": {"calm_s": 0, "drift_s": 0, "collapse_s": 0, "recover_s": 8, "tail_s": 180, "event": True},
}

_thread = None
_stop = threading.Event()
_lock = threading.Lock()
_since = None       # when the running story started
_name = None        # which story was started last; None once it is stopped


def treated():
    """True once the crew has ticked the treatment step on the patient's oxygen alert from
    this run, or resolved it. Acting on the early warning counts: that is the point of it."""
    query = Alert.query.filter_by(crew_id=PATIENT, vital="spo2")
    if _since is not None:
        query = query.filter(Alert.at >= _since)
    alert = query.order_by(Alert.id.desc()).first()
    return alert is not None and (TREATMENT_STEP in alert.steps_done or alert.cleared_at is not None)


def since(source):
    """When the running story began, for the scripted story's own readings, so a trend never reaches
    back into an earlier story. None for any other sender (the "real" story's replayed wrist history
    is meant to be in the window), or once the clock has been put back."""
    if source != "scenario" or _since is None or _since > utcnow():
        return None
    return _since


def close_last_run():
    """Resolve the patient's blood-oxygen alert that an earlier story left open, and tell Earth.
    An open alert cannot be raised again, so without this a second story raises nothing.
    Returns how many were closed."""
    from base_station import routes

    left = Alert.query.filter_by(crew_id=PATIENT, vital="spo2", cleared_at=None, auto=True).all()
    for alert in left:
        alert.cleared_at, alert.cleared_by = utcnow(), "auto: a new story started"
    db.session.commit()
    for alert in left:
        routes.tell_earth(alert, {"event": "resolved", "by": alert.cleared_by, "note": None})
    return len(left)


def _patient_script(calm_s, drift_s, collapse_s, recover_s, tail_s, treated, event=False):
    """Yield (blood oxygen, heart rate) for the patient each second. None means normal.
    With event=True the fall is a real recording, played until the crew treats it."""
    rate, oxygen, _ = NORMAL[PATIENT]
    low, fast = LOW_SPO2, RAISED_RATE
    for _ in range(calm_s):
        yield None, None
    for i in range(drift_s):
        yield oxygen - 4.5 * i / drift_s, rate + 14 * i / drift_s
    for _ in range(collapse_s):
        if treated():
            break
        yield LOW_SPO2, RAISED_RATE
    for low, fast in (replay.event() if event else ()):
        if treated():
            break
        yield low, fast
    for i in range(1, recover_s + 1):
        share = i / recover_s
        yield low + (oxygen - low) * share, fast + (rate - fast) * share
    for _ in range(tail_s):
        yield None, None


def _reading(crew_id, t, spo2=None, rate=None, real=None):
    """One reading. `real` is a cleaned row from a volunteer's wrist: when given, heart rate,
    skin temperature, context and signal quality come from it. The story's own numbers for
    the patient go on top."""
    base_rate, base_oxygen, temp = NORMAL[crew_id]
    wobble = math.sin(t / 3.0 + crew_id)
    reading = {"crew_id": crew_id, "source": "scenario", "signal_ok": True, "context": None,
               "heart_rate": round(base_rate + 2 * wobble), "spo2": round(base_oxygen + 0.4 * wobble, 1),
               "skin_temp": round(temp + 0.1 * wobble, 1)}
    if real:
        reading.update(real, source="replay")
    if spo2 is not None:
        reading["spo2"] = round(spo2, 1)
    if rate is not None:
        reading["heart_rate"] = round(rate)
    return reading


def frames(calm_s, drift_s, collapse_s, recover_s, tail_s, treated=lambda: False, real=None, event=False):
    """Yield one list of readings per second: calm, a slow drift, the collapse (until
    the crew treats it or collapse_s runs out), recovery, then calm again."""
    script = _patient_script(calm_s, drift_s, collapse_s, recover_s, tail_s, treated, event)
    for t, (spo2, rate) in enumerate(script):
        yield [_reading(c, t, spo2 if c == PATIENT else None, rate if c == PATIENT else None,
                        real(c, t) if real else None) for c in NORMAL]


def backfill(seconds=replay.HISTORY_S, now=None):
    """Load each volunteer's earlier readings into the recorder as the crew's recent past."""
    now = now or utcnow()
    rows = [{**_reading(crew_id, -age, real=row), "at": now - timedelta(seconds=age)}
            for crew_id in NORMAL for age, row in replay.history(crew_id, seconds)]
    db.session.bulk_insert_mappings(Reading, rows)
    db.session.commit()
    usual.clear()
    return len(rows)


def _run(app, name, real, halt):
    from base_station import routes

    with app.app_context():
        for second in frames(**SCENARIOS[name], treated=treated, real=replay.live if real else None):
            if halt.is_set():
                return
            for reading in second:
                try:
                    routes.ingest(reading)
                except Exception:           # one bad reading must not end the story
                    db.session.rollback()
                    app.logger.exception("story reading failed")
            halt.wait(1)


def _halt():
    _stop.set()
    if _thread and _thread.is_alive():
        _thread.join(timeout=3)


def stop():
    global _name
    with _lock:
        _halt()
        _name = None


def playing():
    """The name of the story started last, or None once it has been stopped or the demo reset."""
    return _name


def start(app, name="full", real=False):
    """Start a story. With real=True the crew's heart rate and skin temperature are replayed
    from the volunteers' wrist data, and the recorder is given their earlier readings first.
    The "real" story always runs that way."""
    global _thread, _stop, _since, _name
    with _lock:                             # two start calls at once still give one story
        _halt()
        _stop = threading.Event()           # a new flag for each run, so an old run stays stopped
        real = real or name == "real"
        with app.app_context():
            close_last_run()
            if real and Reading.query.filter_by(source="replay").count() == 0:
                backfill()
        _since, _name = utcnow(), name
        _thread = threading.Thread(target=_run, args=(app, name, real, _stop), daemon=True, name="story")
        _thread.start()
