"""Run the NEWS2-style heart-rate bands over every volunteer's wrist heart rate
and count who would trip an alert. Run from this folder: python rule_check.py"""
import pathlib

BANDS = [(40, 3), (50, 1), (90, 0), (110, 1), (130, 2), (None, 3)]  # same as base_station/limits.json
HERE = pathlib.Path(__file__).parent
HR_STARTS_AFTER_S = 10  # HR.csv starts 10 s after the session start that activity.csv counts from


def band(value):
    for upper, score in BANDS:
        if upper is None or value <= upper:
            return score


def worst_sustained(values, hold):
    """Highest band held for `hold` readings in a row (readings are one a second)."""
    worst, run = 0, {1: 0, 2: 0, 3: 0}
    for value in values:
        for score in run:
            run[score] = run[score] + 1 if band(value) >= score else 0
            if run[score] >= hold:
                worst = max(worst, score)
    return worst


def load(subject):
    heart_rate = [float(x) for x in (HERE / f"{subject}_HR.csv").read_text().split()[2:]]
    starts = []
    for line in (HERE / f"{subject}_activity.csv").read_text().splitlines():
        name, _, second = line.lstrip("# ").partition(",")
        if name != "SUBJECT_ID" and second.strip():
            starts.append((name.strip(), int(float(second))))
    segments = {}
    for (name, start), (_, end) in zip(starts, starts[1:] + [("END", len(heart_rate) + HR_STARTS_AFTER_S)]):
        segments.setdefault(name, heart_rate[max(0, start - HR_STARTS_AFTER_S):end - HR_STARTS_AFTER_S])
    return heart_rate, segments


if __name__ == "__main__":
    people = {f"S{k}": load(f"S{k}") for k in range(1, 16)}
    print("Volunteers out of 15 who trip the heart-rate bands")
    print("hold   | sitting: caution warning sos | desk work: caution warning sos | whole session: warning sos")
    for hold in (5, 30, 120):
        def count(pick, level):
            return sum(1 for hr, seg in people.values() if worst_sustained(pick(hr, seg), hold) >= level)
        sitting = [count(lambda hr, seg: seg["BASELINE"], level) for level in (1, 2, 3)]
        desk = [count(lambda hr, seg: seg["WORKING"], level) for level in (1, 2, 3)]
        whole = [count(lambda hr, seg: hr, level) for level in (2, 3)]
        print(f"{hold:4d} s | {sitting[0]:16d} {sitting[1]:7d} {sitting[2]:3d} | {desk[0]:18d} {desk[1]:7d} {desk[2]:3d} "
              f"| {whole[0]:22d} {whole[1]:3d}")
    clean = [name for name, (hr, seg) in people.items() if worst_sustained(seg["BASELINE"], 5) == 0]
    print("Sitting segments that trip nothing at a 5 s hold (safe to replay):", ", ".join(clean))
    clean = [name for name, (hr, seg) in people.items() if worst_sustained(seg["WORKING"], 5) == 0]
    print("Desk-work segments that trip nothing at a 5 s hold:", ", ".join(clean))
