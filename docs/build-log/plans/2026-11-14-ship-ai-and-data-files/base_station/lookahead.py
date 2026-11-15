"""Ship AI: how long until a falling reading reaches its red line?

It fits a Theil-Sen line (the median of the slopes between every pair of readings),
which a few bad readings cannot pull off course. Readings are one a second.

The numbers below were chosen on real recordings, not on the scripted story:
scripts/check_spo2_rules.py prints the results and data/spo2_uw/README.md keeps them.
"""
import statistics

from common.models import Reading

WINDOW = 60          # readings looked at
MIN_READINGS = 15    # fewer than this is not a trend
MIN_DROP = 2.0       # the fitted line must fall at least this far across the window
MIN_AGREEMENT = 0.5  # share of reading pairs that fall, minus the share that rise
HORIZON_S = 600      # stay quiet if the red line is more than ten minutes away
FALLING = "and falling"


def falling(values, red_line):
    """None, or how fast the readings are falling and the seconds left until the red line."""
    if len(values) < MIN_READINGS:
        return None
    slopes = sorted((values[j] - values[i]) / (j - i)
                    for i in range(len(values)) for j in range(i + 1, len(values)))
    slope = slopes[len(slopes) // 2]
    agreement = (sum(s < 0 for s in slopes) - sum(s > 0 for s in slopes)) / len(slopes)
    now = statistics.median(values[-5:])
    if agreement < MIN_AGREEMENT or -slope * (len(values) - 1) < MIN_DROP or now <= red_line:
        return None
    eta_s = (now - red_line) / -slope
    if eta_s > HORIZON_S:
        return None
    return {"now": round(now, 1), "per_min": round(slope * 60, 1), "eta_s": round(eta_s), "red_line": red_line}


def check(crew_id, vital, red_line, source=None):
    """The same, for one person's last WINDOW clean sensor readings in the recorder.
    Give the source to look at one sender only."""
    column = getattr(Reading, vital)
    sender = Reading.source == source if source else Reading.source != "typed"
    recent = (Reading.query.filter(Reading.crew_id == crew_id, column.isnot(None), Reading.signal_ok, sender)
              .order_by(Reading.at.desc(), Reading.id.desc()).limit(WINDOW).all())
    return falling([getattr(r, vital) for r in reversed(recent)], red_line)
