"""The console's state rules: OK, WATCH or ALERT for a daily value against the person's own band.

This follows src/lib/scoring.ts in the console repo step for step, so the ship and the screen
give the same answer. The words and the source for each rule are in
data/reference/console_thresholds.json, a copy of the console's thresholds.json."""
import functools
import json
import os

from common import dataset

METRICS = ["hr_rest", "bp_sys", "bp_dia", "spo2", "temp_c", "resp", "sleep_h", "mood", "pvt_ms", "dose_mSv_day"]
BANDED = {"hr_rest", "bp_sys", "bp_dia", "spo2", "temp_c", "resp", "sleep_h"}
RANK = {"OK": 0, "WATCH": 1, "ALERT": 2}
INDICATOR = {"hr_rest": "heart_rate_rest", "bp_sys": "blood_pressure", "bp_dia": "blood_pressure", "spo2": "spo2",
             "temp_c": "core_temperature", "resp": "respiratory_rate", "sleep_h": "sleep_hours", "mood": "mood",
             "pvt_ms": "reaction_time_pvt", "dose_mSv_day": "radiation_daily_dose", "co2_mmHg": "cabin_co2"}


def worst(states):
    return max(states, key=RANK.get, default="OK")


def hard_alert(metric, value):
    """The three limits that alert on their own."""
    return ((metric == "spo2" and value < 94) or (metric == "temp_c" and value > 38.0)
            or (metric == "dose_mSv_day" and value > 2))


def out_of_range(metric, value, band, pvt_baseline=None):
    below = band is not None and value < band[0]
    above = band is not None and value > band[1]
    if metric == "spo2":
        return below
    if metric == "temp_c":
        return above
    if metric == "resp":
        return value > 20
    if metric == "sleep_h":
        return below or value < 6.5
    if metric == "mood":
        return value <= 2
    if metric == "pvt_ms":
        return pvt_baseline is not None and value > pvt_baseline * 1.15
    if metric == "dose_mSv_day":
        return False
    return below or above            # resting heart rate and blood pressure


def days_out_of_band(series, band):
    """Days in a row outside the band, counted back from today. A day with no value ends the run."""
    days = 0
    for value in reversed(series):
        if value is None or band[0] <= value <= band[1]:
            break
        days += 1
    return days


def score(metric, value, band, days_out, has_symptom, pvt_baseline=None):
    if value is None:
        return None
    if hard_alert(metric, value):
        return "ALERT"
    if not out_of_range(metric, value, band, pvt_baseline):
        return "OK"
    return "ALERT" if days_out >= 3 or has_symptom else "WATCH"


@functools.lru_cache(maxsize=None)
def rule_text():
    """{metric: {unit, watch, alert, source}}: the words the console prints for each rule."""
    with open(os.path.join(dataset.ROOT, "reference", "console_thresholds.json"), encoding="utf-8") as f:
        indicators = json.load(f)["indicators"]
    return {metric: {"unit": indicators[key]["unit"], "watch": indicators[key]["watch"],
                     "alert": indicators[key]["alert"],
                     # the console prints this wording for the standard's section 3004, so the ship does too
                     "source": indicators[key]["source"].replace("V1 3004 vital-sign trending",
                                                                 "V1 3004 In-Mission Medical Care")}
            for metric, key in INDICATOR.items()}
