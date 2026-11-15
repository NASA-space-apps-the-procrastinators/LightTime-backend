"""The flight recorder keeps 24 hours of readings. Older ones leave as a daily summary."""
import statistics
from datetime import timedelta

from common.models import Alert, Reading, db, utcnow

KEEP = timedelta(hours=24)
SUMMARY_VITALS = ["heart_rate", "spo2", "skin_temp"]


def prune(now=None):
    """Delete readings older than 24 hours. Returns how many went."""
    gone = Reading.query.filter(Reading.at < (now or utcnow()) - KEEP).delete()
    db.session.commit()
    return gone


def daily_summary(crew, now=None):
    """One person's last 24 hours: low, middle and high for each vital, and the alerts raised."""
    since = (now or utcnow()) - KEEP
    readings = Reading.query.filter(Reading.crew_id == crew.id, Reading.at >= since,
                                    Reading.source != "typed", Reading.signal_ok).all()
    vitals = {}
    for vital in SUMMARY_VITALS:
        values = [getattr(r, vital) for r in readings if getattr(r, vital) is not None]
        if values:
            vitals[vital] = {"low": min(values), "median": statistics.median(values), "high": max(values)}
    alerts = Alert.query.filter(Alert.crew_id == crew.id, Alert.at >= since).all()
    return {
        "crew_id": crew.id, "crew": crew.name, "readings": len(readings),
        "exercise_minutes": round(sum(r.context == "exercise" for r in readings) / 60),
        "vitals": vitals, "alerts": [{"level": a.level, "reason": a.reason} for a in alerts],
        "sources": sorted({r.source for r in readings}),
    }
