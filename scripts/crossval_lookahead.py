"""Are the time-left settings luck? Choose them on five volunteers, test on the sixth, six times.

    python scripts/crossval_lookahead.py        about three minutes
"""
import itertools
import pathlib
import statistics
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from base_station import lookahead                      # noqa: E402
from scripts.build_clean_data import read_uw            # noqa: E402
from scripts.check_spo2_rules import one_hz, play       # noqa: E402

GRID = list(itertools.product((45, 60), (1.5, 2.0, 2.5), (0.4, 0.5, 0.6)))   # window, drop, agreement
MAX_FALSE = 3       # trend warnings allowed on the 7.8 hour control recording


def lead(values):
    """Seconds between the last trend warning and the SOS, or None if there was no warning first."""
    sos, warnings = play(values)
    before = [t for t, _ in warnings if t < sos[0]]
    return sos[0] - before[-1] if before else None


def score(leads):
    """More volunteers warned first, then a longer median warning."""
    got = [x for x in leads if x is not None]
    return len(got), statistics.median(got) if got else 0


if __name__ == "__main__":
    volunteers = {s: [row[0] for row in read_uw((ROOT / "data" / "spo2_uw" / f"{s}.csv").read_text(encoding="utf-8"))]
                  for s in range(100001, 100007)}
    control, table = one_hz("c01r"), {}
    for setting in GRID:
        lookahead.WINDOW, lookahead.MIN_DROP, lookahead.MIN_AGREEMENT = setting
        false = len(play(control)[1])
        table[setting] = (false, {s: lead(v) for s, v in volunteers.items()})
        print(f"window {setting[0]}, drop {setting[1]}, agreement {setting[2]}: "
              f"{false} control warnings, leads {list(table[setting][1].values())}")
    allowed = {k: v[1] for k, v in table.items() if v[0] <= MAX_FALSE}
    held = []
    for out in volunteers:
        best = max(allowed, key=lambda k: score([allowed[k][s] for s in volunteers if s != out]))
        held.append(allowed[best][out])
        print(f"held out {out}: settings chosen without it {best}, warning ahead by {held[-1]} s")
    got = [x for x in held if x is not None]
    print(f"\nHeld-out result: warned before the SOS for {len(got)} of 6, median {statistics.median(got) if got else 0:g} s ahead")
    print(f"Settings in the ship today: window 60, drop 2.0, agreement 0.5 -> {table[(60, 2.0, 0.5)]}")
