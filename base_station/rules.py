"""Fixed rules that turn readings into alerts. Bands follow the NEWS2 chart."""
import json
import os

from common.models import Alert, Reading, db, utcnow

with open(os.path.join(os.path.dirname(__file__), "limits.json")) as f:
    LIMITS = json.load(f)

LEVELS = {1: "caution", 2: "warning", 3: "emergency"}
RANK = {"nominal": -1, "advisory": 0, "caution": 1, "warning": 2, "emergency": 3}


def band(vital, value):
    for upper, score in LIMITS["vitals"][vital]["bands"]:
        if upper is None or value <= upper:
            return score


def sustained(crew_id, vital, score, n):
    """True when the last n readings of this vital are all at this band or worse,
    each with a clean signal."""
    column = getattr(Reading, vital)
    recent = (Reading.query.filter(Reading.crew_id == crew_id, column.isnot(None))
              .order_by(Reading.at.desc(), Reading.id.desc()).limit(n).all())
    return len(recent) == n and all(
        r.signal_ok and band(vital, getattr(r, vital)) >= score for r in recent)


def _open_alert(crew_id, vital):
    return Alert.query.filter_by(crew_id=crew_id, vital=vital, cleared_at=None).first()


def _quiet(crew_id, vital, level):
    """True when a person cleared this alert in the last quiet_s seconds and it is
    no worse now. This is the alarm pause on a bedside monitor."""
    last = (Alert.query.filter(Alert.crew_id == crew_id, Alert.vital == vital,
                               Alert.cleared_at.isnot(None))
            .order_by(Alert.cleared_at.desc()).first())
    return (last is not None and not last.cleared_by.startswith("auto")
            and (utcnow() - last.cleared_at).total_seconds() < LIMITS["quiet_s"]
            and RANK[level] <= RANK[last.level])


def _raise(crew_id, vital, level, value, reason, nasa_risk=""):
    """Open an alert, or escalate the open one. Returns None when nothing changed."""
    alert = _open_alert(crew_id, vital)
    if alert is None:
        if _quiet(crew_id, vital, level):
            return None
        alert = Alert(crew_id=crew_id, vital=vital, level=level, value=value, reason=reason,
                      nasa_risk=nasa_risk, steps_done=[])
        db.session.add(alert)
    elif RANK[level] > RANK[alert.level]:
        alert.level, alert.value, alert.reason = level, value, reason
    else:
        return None
    db.session.commit()
    return alert


def evaluate(reading):
    """Return the alerts this reading raised or escalated."""
    typed = reading.source == "typed"
    if not typed:
        if not reading.signal_ok:
            alert = _raise(reading.crew_id, "signal", "advisory", None,
                           "Check your sensor: no clean signal")
            return [alert] if alert else []
        stale = _open_alert(reading.crew_id, "signal")
        if stale:
            stale.cleared_at, stale.cleared_by = utcnow(), "auto: signal is back"
            db.session.commit()

    n = 1 if typed else LIMITS["sustain_n"]
    raised = []
    for vital, cfg in LIMITS["vitals"].items():
        value = getattr(reading, vital)
        if value is None:
            continue
        # A typed number can be a typo, so it stops at a warning. SOS needs a sensor.
        score = min(band(vital, value), 2) if typed else band(vital, value)
        while score and not sustained(reading.crew_id, vital, score, n):
            score -= 1
        if not score:
            continue
        held = f", out of range for {n} s" if n > 1 else ", out of range"
        alert = _raise(reading.crew_id, vital, LEVELS[score], value,
                       f"{cfg['label']} {value:g}{cfg['unit']}{held}", cfg["nasa_risk"])
        if alert:
            raised.append(alert)
    return raised
