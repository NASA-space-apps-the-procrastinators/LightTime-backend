"""Ship AI: each person's own usual range, learned from the last 24 hours in the recorder.

On real wrist data a personal range was too wide to raise alarms on its own (see
data/ppg_dalia/README.md), so it is shown as context and sent to Earth, not used as an alarm.
"""
from datetime import timedelta

from sqlalchemy import or_

from common.models import Reading, utcnow

MIN_READINGS = 600     # ten minutes at one reading a second
REFRESH_S = 300
_cache = {}


def usual_range(crew_id, vital="heart_rate", now=None):
    """{"low", "high", "n"}: the 1st and 99th percentile of this person's resting readings, or None."""
    now = now or utcnow()
    cached = _cache.get((crew_id, vital))
    if cached and (now - cached[0]).total_seconds() < REFRESH_S:
        return cached[1]
    column = getattr(Reading, vital)
    values = sorted(v for (v,) in Reading.query.with_entities(column).filter(
        Reading.crew_id == crew_id, column.isnot(None), Reading.signal_ok, Reading.source != "typed",
        or_(Reading.context.is_(None), Reading.context != "exercise"), Reading.at >= now - timedelta(hours=24)))
    result = None
    if len(values) >= MIN_READINGS:
        result = {"low": round(values[len(values) // 100]), "high": round(values[-1 - len(values) // 100]),
                  "n": len(values)}
    _cache[(crew_id, vital)] = (now, result)
    return result


def clear():
    _cache.clear()
