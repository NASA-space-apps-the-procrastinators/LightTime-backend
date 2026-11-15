"""Learn how far heart rate normally sits above a person's resting rate in each activity.

Fifteen real wrist recordings (PPG-DaLiA). Leave one person out, learn on fourteen, test on the
one left out, fifteen times. Prints the result and writes base_station/hr_normal.json.
This is an adviser: it can say "unusual", never "dangerous". No recording holds an emergency."""
import csv
import glob
import json
import statistics
import sys

REST = "BASELINE"
SUSTAIN_S = 60


def load(path):
    with open(path, newline="") as f:
        return [(row["activity"], float(row["heart_rate"])) for row in csv.DictReader(f)
                if row["signal_ok"] == "1" and row["heart_rate"]]


def resting(rows):
    return statistics.median(rate for activity, rate in rows if activity == REST)


def learn(people):
    """{activity: beats above resting}, and the size of the largest normal gap, from these people."""
    offsets, gaps = {}, []
    for rows in people:
        rest = resting(rows)
        for activity in {a for a, _ in rows}:
            offsets.setdefault(activity, []).append(statistics.median(r for a, r in rows if a == activity) - rest)
    effect = {activity: statistics.median(values) for activity, values in offsets.items()}
    for rows in people:
        rest = resting(rows)
        gaps += [abs(rate - rest - effect[activity]) for activity, rate in rows]
    gaps.sort()
    return effect, gaps[int(len(gaps) * 0.999)]


def flagged_minutes(rows, effect, limit):
    """Whole minutes in which every second sat further from normal than the limit."""
    rest, run, minutes = resting(rows), 0, 0
    for activity, rate in rows:
        run = run + 1 if abs(rate - rest - effect.get(activity, 0.0)) > limit else 0
        if run == SUSTAIN_S:
            minutes, run = minutes + 1, 0
    return minutes


def main():
    paths = sorted(glob.glob("data/clean/wrist/S*.csv"))
    people = [load(path) for path in paths]
    worst = 0.0
    for index, held_out in enumerate(people):
        effect, limit = learn(people[:index] + people[index + 1:])
        per_hour = flagged_minutes(held_out, effect, limit) / (len(held_out) / 3600)
        worst = max(worst, per_hour)
        print(f"{paths[index]}: limit {limit:.0f} bpm, flagged {per_hour:.2f} minutes an hour")
    effect, limit = learn(people)
    print(f"worst held-out person: {worst:.2f} flagged minutes an hour")
    if worst > 1.0:
        sys.exit("Gate failed: more than one flagged minute an hour on a healthy person. Do not ship it.")
    with open("base_station/hr_normal.json", "w") as f:
        json.dump({"effect": effect, "limit_bpm": round(limit, 1), "worst_flagged_minutes_per_hour": round(worst, 2),
                   "source": "PPG-DaLiA wrist recordings, 15 people, each held out in turn"}, f, indent=2)


if __name__ == "__main__":
    main()
