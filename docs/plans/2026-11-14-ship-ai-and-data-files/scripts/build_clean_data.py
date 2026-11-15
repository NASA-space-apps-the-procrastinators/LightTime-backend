"""Turn the raw downloads in data/ into the tables the backend reads, in data/clean/.

Run from the repo root:  python scripts/build_clean_data.py
Nothing is deleted or changed in the raw files. Rows that look wrong are kept and flagged.
"""
import csv
import json
import pathlib
import statistics

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW_WRIST, RAW_EDA, CLEAN = ROOT / "data" / "ppg_dalia", ROOT / "data" / "eda", ROOT / "data" / "clean"
RAW_SPO2 = ROOT / "data" / "spo2_uw"

EXERCISE = {"STAIRS", "SOCCER", "CYCLING", "WALKING"}
COOL_DOWN_S = 300        # heart rate stays high for a while after exercise
MAX_HR_JUMP = 10.0       # bpm in one second; the default threshold in the CSA's heart-rate filter
MAX_TEMP_JUMP = 0.5      # degrees C in one second; skin cannot change faster, a loose sensor can
EVENT_ROWS = slice(110, 879)   # volunteer 100001: a minute of normal readings, the fall to 67%, the recovery


def read_e4(text):
    """An Empatica file: start time, rate, then one value a line."""
    lines = text.split()
    return float(lines[0]), int(float(lines[1])), [float(x) for x in lines[2:]]


def read_activity(text):
    """[(name, start second)] from the dataset's activity file."""
    starts = []
    for line in text.splitlines():
        name, _, second = line.lstrip("# ").partition(",")
        if name.strip() != "SUBJECT_ID" and second.strip():
            starts.append((name.strip(), int(float(second))))
    return starts


def align_wrist(hr_text, temp_text, activity_text):
    """One row a second: t_s, heart_rate, skin_temp, activity, context, signal_ok."""
    hr_start, _, heart = read_e4(hr_text)
    temp_start, temp_rate, temp = read_e4(temp_text)
    offset = int(round(hr_start - temp_start))          # heart rate starts later than temperature
    starts = read_activity(activity_text)
    rows, last_exercise, previous = [], None, None
    for i, rate in enumerate(heart):
        t = i + offset
        samples = temp[t * temp_rate:(t + 1) * temp_rate]
        if not samples:
            break
        skin = round(statistics.median(samples), 2)
        activity = [name for name, start in starts if start <= t][-1] if starts and starts[0][1] <= t else "NO_ACTIVITY"
        if activity in EXERCISE:
            last_exercise = t
        resting = last_exercise is None or t - last_exercise > COOL_DOWN_S
        ok = previous is None or (abs(rate - previous[0]) <= MAX_HR_JUMP and abs(skin - previous[1]) <= MAX_TEMP_JUMP)
        rows.append([t, rate, skin, activity, "rest" if resting else "exercise", int(ok)])
        previous = (rate, skin)
    return rows


def read_uw(text, oximeter="5"):
    """[[blood oxygen, pulse]] a second from one UW recording. Oximeter 5 is the Masimo Radical-7.
    The file ends with a line that is not data, and that line has no reading."""
    rows = csv.DictReader(text.lstrip("\ufeff").splitlines())
    return [[float(r[f"SpO2 {oximeter}"]), float(r[f"Pulse {oximeter}"])] for r in rows if r[f"SpO2 {oximeter}"]]


def clean_cabin(telemetry):
    """ISS cabin rows only, with the units NASA's app prints. Rows with a gap are dropped."""
    rows = [[r["time"], r["temperature_iss"], r["humidity_iss"], r["co2_iss"]] for r in telemetry]
    return [r for r in rows if None not in r]


def write(path, header, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        csv.writer(f).writerows([header] + rows)


if __name__ == "__main__":
    print("wrist (PPG-DaLiA): volunteer, seconds, exercise seconds, flagged seconds")
    for hr_file in sorted(RAW_WRIST.glob("S*_HR.csv"), key=lambda p: int(p.name[1:].split("_")[0])):
        subject = hr_file.name.split("_")[0]
        rows = align_wrist(hr_file.read_text(), (RAW_WRIST / f"{subject}_TEMP.csv").read_text(),
                           (RAW_WRIST / f"{subject}_activity.csv").read_text())
        write(CLEAN / "wrist" / f"{subject}.csv", ["t_s", "heart_rate", "skin_temp", "activity", "context", "signal_ok"], rows)
        print(f"  {subject:4} {len(rows):6d} {sum(r[4] == 'exercise' for r in rows):6d} {sum(not r[5] for r in rows):4d}")
    telemetry = json.loads((RAW_EDA / "rr1_telemetry.json").read_text())
    cabin = clean_cabin(telemetry)
    write(CLEAN / "cabin_rr1.csv", ["time", "temp_c", "humidity_pct", "co2_ppm"], cabin)
    print(f"cabin (NASA EDA, RR-1): {len(telemetry)} rows in, {len(cabin)} kept, {len(telemetry) - len(cabin)} dropped for gaps")
    radiation = json.loads((RAW_EDA / "rr1_radiation.json").read_text())
    write(CLEAN / "radiation_rr1.csv", ["date", "gcr_mgy_day", "saa_mgy_day", "total_mgy_day"],
          [[r["time"][:10], r["gcr"], r["saa"], r["total"]] for r in radiation])
    print(f"radiation (NASA EDA, RR-1): {len(radiation)} days")
    event = read_uw((RAW_SPO2 / "100001.csv").read_text(encoding="utf-8"))[EVENT_ROWS]
    write(CLEAN / "spo2_event.csv", ["t_s", "spo2", "pulse"], [[i, *row] for i, row in enumerate(event)])
    print(f"blood oxygen event (UW, volunteer 100001): {len(event)} seconds, "
          f"{event[0][0]:g}% down to {min(r[0] for r in event):g}% and back to {event[-1][0]:g}%")
