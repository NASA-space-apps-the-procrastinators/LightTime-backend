"""The scripted day and collapse. No randomness: every run plays the same."""
import math
import threading
import time

from common.models import Alert

# crew_id: resting heart rate, blood oxygen, skin temperature. SIMULATED values.
NORMAL = {1: (72, 98.0, 33.5), 2: (64, 99.0, 33.2), 3: (80, 97.5, 33.8)}
PATIENT = 1
LOW_SPO2, RAISED_RATE = 86.0, 88
TREATMENT_STEP = 1  # the second step of the spo2 checklist in procedures.json

SCENARIOS = {
    "stage": {"calm_s": 4, "drift_s": 0, "collapse_s": 60, "recover_s": 8, "tail_s": 180},
    "full": {"calm_s": 20, "drift_s": 20, "collapse_s": 60, "recover_s": 8, "tail_s": 180},
}

_thread = None
_stop = threading.Event()


def treated():
    """True once the crew has ticked the treatment step on the patient's open oxygen alert."""
    alert = Alert.query.filter_by(crew_id=PATIENT, vital="spo2", cleared_at=None).first()
    return alert is not None and TREATMENT_STEP in alert.steps_done


def _patient_script(calm_s, drift_s, collapse_s, recover_s, tail_s, treated):
    """Yield (blood oxygen, heart rate) for the patient each second. None means normal."""
    rate, oxygen, _ = NORMAL[PATIENT]
    for _ in range(calm_s):
        yield None, None
    for i in range(drift_s):
        yield oxygen - 4.5 * i / drift_s, rate + 14 * i / drift_s
    for _ in range(collapse_s):
        if treated():
            break
        yield LOW_SPO2, RAISED_RATE
    for i in range(1, recover_s + 1):
        share = i / recover_s
        yield LOW_SPO2 + (oxygen - LOW_SPO2) * share, RAISED_RATE + (rate - RAISED_RATE) * share
    for _ in range(tail_s):
        yield None, None


def _reading(crew_id, t, spo2=None, rate=None):
    base_rate, base_oxygen, temp = NORMAL[crew_id]
    wobble = math.sin(t / 3.0 + crew_id)
    return {"crew_id": crew_id, "source": "scenario", "signal_ok": True,
            "heart_rate": round(base_rate + 2 * wobble if rate is None else rate),
            "spo2": round(base_oxygen + 0.4 * wobble if spo2 is None else spo2, 1),
            "skin_temp": round(temp + 0.1 * wobble, 1)}


def frames(calm_s, drift_s, collapse_s, recover_s, tail_s, treated=lambda: False):
    """Yield one list of readings per second: calm, a slow drift, the collapse (until
    the crew treats it or collapse_s runs out), recovery, then calm again."""
    script = _patient_script(calm_s, drift_s, collapse_s, recover_s, tail_s, treated)
    for t, (spo2, rate) in enumerate(script):
        yield [_reading(c, t, spo2, rate) if c == PATIENT else _reading(c, t) for c in NORMAL]


def _run(app, name):
    from base_station.routes import ingest

    with app.app_context():
        for second in frames(**SCENARIOS[name], treated=treated):
            if _stop.is_set():
                return
            for reading in second:
                ingest(reading)
            time.sleep(1)


def stop():
    _stop.set()
    if _thread and _thread.is_alive():
        _thread.join(timeout=3)


def start(app, name="stage"):
    global _thread
    stop()
    _stop.clear()
    _thread = threading.Thread(target=_run, args=(app, name), daemon=True)
    _thread.start()
