"""Real recordings standing in for the crew's suits.

Each crew member replays one PPG-DaLiA volunteer's wrist. The first two hours of the session
go into the recorder as history. The rest plays live, one row a second, and loops.
The "real" story also plays one recorded fall in blood oxygen (see data/spo2_uw/README.md).
"""
import csv
import functools
import os

CLEAN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "clean")
CREW_TO_VOLUNTEER = {1: "S15", 2: "S12", 3: "S2"}   # calm, clean live windows (see the data spec)
HISTORY_S = 7200


@functools.lru_cache(maxsize=None)
def rows(crew_id):
    with open(os.path.join(CLEAN, "wrist", f"{CREW_TO_VOLUNTEER[crew_id]}.csv"), newline="") as f:
        return [{"heart_rate": float(r["heart_rate"]), "skin_temp": float(r["skin_temp"]),
                 "context": r["context"], "signal_ok": r["signal_ok"] == "1"} for r in csv.DictReader(f)]


def history(crew_id, seconds=HISTORY_S):
    """(age in seconds, row) for the last `seconds` rows before the live part starts."""
    past = rows(crew_id)[HISTORY_S - seconds:HISTORY_S]
    return [(seconds - i, row) for i, row in enumerate(past)]


def live(crew_id, t):
    """The row to play t seconds into the live part. Loops when the session runs out."""
    after = rows(crew_id)[HISTORY_S:]
    return after[t % len(after)]


@functools.lru_cache(maxsize=None)
def event():
    """[(blood oxygen, pulse)] a second: a healthy volunteer breathing low-oxygen gas in a lab."""
    with open(os.path.join(CLEAN, "spo2_event.csv"), newline="") as f:
        return [(float(r["spo2"]), float(r["pulse"])) for r in csv.DictReader(f)]
