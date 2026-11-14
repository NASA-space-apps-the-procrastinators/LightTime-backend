"""Step 3: derived tables for one build: daily_summary.csv and packets.csv.

python data/scripts/summarise.py --build anomalous
"""
import argparse
import statistics
from collections import defaultdict
from datetime import timedelta

import config as C
import model as M
from schema import columns
from util import fnum, read_csv, write_csv

MORNING_MIN = 20  # morning rest window: the first 20 min after waking


def by_crew(rows):
    out = defaultdict(list)
    for r in rows:
        out[r["crew_id"]].append(r)
    return out


def morning_window(crew_rows, md):
    """The first MORNING_MIN minute rows labelled post_sleep on mission day md."""
    picked = [r for r in crew_rows if int(r["mission_day"]) == md and r["activity_label"] == "post_sleep"]
    return picked[:MORNING_MIN]


def median(rows, key):
    vals = [fnum(r[key]) for r in rows if r[key] != ""]
    return statistics.median(vals) if vals else None


def mean(rows, key):
    vals = [fnum(r[key]) for r in rows if r[key] != ""]
    return sum(vals) / len(vals) if vals else None


def morning_values(crew_rows, md):
    w = morning_window(crew_rows, md)
    return {"hr_bpm": median(w, "hr_bpm"), "spo2_pct": median(w, "spo2_pct"), "resp_rpm": median(w, "resp_rpm"),
            "core_temp_c": mean(w, "core_temp_c"), "skin_temp_c": mean(w, "skin_temp_c")}, w


def daily_summary(folder, seed):
    vit = by_crew(read_csv(folder / "vitals_1min.csv"))
    checkins = {(k["crew_id"], k["date"]): k for k in read_csv(folder / "checkins.csv")
                if C.parse_ts(k["completed_at"]) <= C.DEMO_NOW}
    dose = {r["date"]: fnum(r["dose_msv_day"]) for r in read_csv(folder / "radiation_daily.csv")}
    first = C.mission_day(C.START)
    out = []
    for cid in C.CREW_IDS:
        out += M.pre_window_daily(seed, cid, first - 1)
        rows = vit[cid]
        per_md = defaultdict(list)
        for r in rows:
            per_md[int(r["mission_day"])].append(r)
        for md in range(first, C.mission_day(C.DEMO_NOW) + 1):
            day = C.md_date(md).isoformat()
            mv, window = morning_values(rows, md)
            k = checkins.get((cid, day))
            sleep_suit = round(sum(1 for r in per_md.get(md - 1, []) + per_md.get(md, [])
                                   if r["activity_label"] == "sleep"
                                   and C.at(md - 1, 18) <= C.parse_ts(r["sensor_ts"]) < C.at(md, 12)) / 60.0, 1)
            injected = sorted({p for r in window for p in r["provenance"].split("|") if p.startswith("injected")})
            out.append({
                "crew_id": cid, "date": day, "mission_day": md,
                "hr_rest_bpm": float(round(mv["hr_bpm"])) if mv["hr_bpm"] is not None else None,
                "bp_sys_mmhg": fnum(k["cuff_bp_sys_mmhg"]) if k else None,
                "bp_dia_mmhg": fnum(k["cuff_bp_dia_mmhg"]) if k else None,
                "spo2_pct": float(round(mv["spo2_pct"])) if mv["spo2_pct"] is not None else None,
                "core_temp_c": round(mv["core_temp_c"], 2) if mv["core_temp_c"] is not None else None,
                "skin_temp_c": round(mv["skin_temp_c"], 2) if mv["skin_temp_c"] is not None else None,
                "resp_rpm": float(round(mv["resp_rpm"])) if mv["resp_rpm"] is not None else None,
                "sleep_h": fnum(k["sleep_h"]) if k else sleep_suit, "sleep_h_suit": sleep_suit,
                "mood": int(k["mood"]) if k else None, "pvt_ms": int(k["pvt_ms"]) if k else None,
                "dose_msv_day": dose.get(day), "symptoms": k["symptoms"].split("|") if k and k["symptoms"] else [],
                "resolution": "from_minute_data", "simulated": True,
                "provenance": "|".join(["sim", *injected]),
            })
    write_csv(folder / "daily_summary.csv", columns("daily_summary"), out)
    return out


PACKET_METRICS = [  # (vitals column, packet source, packet metric name, unit)
    ("hr_bpm", "ecg", "hr", "bpm"), ("resp_rpm", "chest_band", "resp", "/min"),
    ("spo2_pct", "pulse_ox", "spo2", "%"), ("skin_temp_c", "skin_temp", "skin_temp_c", "C"),
    ("core_temp_c", "core_temp", "temp_c", "C"), ("activity_g", "accel", "activity_g", "g"),
    ("bp_sys_est_mmhg", "bp_est", "bp_sys", "mmHg"),
]


def packets(folder):
    """The frontend's Packet, one per metric per 60 s window, for mission days 157-158.
    sent_to_ground is true for the 30 min before an alert whose report was sent."""
    sent_spans = defaultdict(list)
    for a in read_csv(folder / "alerts_seed.csv"):
        if a["sent_at"]:
            raised = C.parse_ts(a["raised_at"])
            sent_spans[a["crew_id"]].append((raised - timedelta(minutes=30), raised + timedelta(minutes=1)))
    out = []
    for r in read_csv(folder / "vitals_1min.csv"):
        ts = C.parse_ts(r["sensor_ts"])
        if ts < C.PACKETS_FROM:
            continue
        sent = any(a <= ts < b for a, b in sent_spans[r["crew_id"]])
        for col, source, metric, unit in PACKET_METRICS:
            out.append({
                "packet_id": f"{r['sample_id']}-{metric}", "crew_id": r["crew_id"],
                "suit_id": C.CREW_BY_ID[r["crew_id"]]["suit_id"], "ts": r["sensor_ts"],
                "mission_day": int(r["mission_day"]), "location": C.PLATFORM, "habitat_id": r["habitat_id"],
                "source": source, "metric": metric, "value": fnum(r[col]), "unit": unit,
                "signal_quality": fnum(r["signal_quality"]), "window_s": 60, "sent_to_ground": sent, "ack": "",
                "sample_id": r["sample_id"], "simulated": True, "provenance": r["provenance"],
            })
    write_csv(folder / "packets.csv", columns("packets"), out)
    return out


def run(folder, seed):
    daily_summary(folder, seed)
    packets(folder)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--build", choices=["clean", "anomalous"], required=True)
    p.add_argument("--seed", type=int, default=C.DEFAULT_SEED)
    a = p.parse_args()
    run(C.OUT_CLEAN if a.build == "clean" else C.OUT_ANOM, a.seed)
