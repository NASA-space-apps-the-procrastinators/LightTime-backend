"""Step 2: copy the clean build, inject the anomalies in config.ANOMALIES on top of the
clean signal, and write the anomalous build plus ground_truth/anomalies.csv.

python data/scripts/inject_anomalies.py --seed 2026
"""
import argparse
import json
import math
from collections import defaultdict
from datetime import datetime, timedelta

import config as C
import generate_clean as G
import model as M
import summarise as S
from config import at, iso
from schema import columns
from util import Link, fnum, read_csv, rng, smoothstep, write_csv

NUM = ["hr_bpm", "resp_rpm", "spo2_pct", "skin_temp_c", "core_temp_c", "activity_g", "bp_sys_est_mmhg",
       "signal_quality"]
AN = {a["id"]: a for a in C.ANOMALIES}
PROCEDURES = json.loads((C.REPO / "base_station" / "procedures.json").read_text())


def true_time(row):
    stamp = row["sample_id"].split("-", 2)[2]
    fmt = "%Y%m%dT%H%MZ" if row["sample_id"][3] == "M" else "%Y%m%dT%H%M%SZ"
    return datetime.strptime(stamp, fmt).replace(tzinfo=C.UTC)


def num(row, k):
    v = row[k]
    return None if v in ("", None) else float(v)


def tag(row, label):
    if label not in row["provenance"].split("|"):
        row["provenance"] += "|" + label


def add(row, k, dv):
    v = num(row, k)
    if v is not None:
        row[k] = v + dv


def piecewise(anchors, t):
    if t <= anchors[0][0]:
        return 0.0
    for (t0, v0), (t1, v1) in zip(anchors, anchors[1:]):
        if t0 <= t < t1:
            return v0 + (v1 - v0) * (t - t0) / (t1 - t0)
    return anchors[-1][1]


def wake_effect(row):
    """A minute that was asleep is now awake in bed."""
    row["activity_label"] = "awake_in_bed"
    add(row, "hr_bpm", 4)
    add(row, "resp_rpm", 1)
    add(row, "spo2_pct", 0.5)
    add(row, "bp_sys_est_mmhg", 4)
    add(row, "skin_temp_c", -0.2)
    row["activity_g"] = num(row, "activity_g") * 2.5


# ---------------------------------------------------------------- vitals
def an01_plan(clean_min):
    """Deltas that put C1's morning-rest values on the contract's numbers."""
    rows = [r for r in clean_min if r["crew_id"] == "C1"]
    plan = {}
    for md, targets in C.AN01_TARGETS.items():
        mv, _ = S.morning_values(rows, md)
        plan[md] = {k: v - mv[k] for k, v in targets.items()}
    hr = [(at(155, 21, 30), 0.0)] + [(at(md, 6), plan[md]["hr_bpm"]) for md in (156, 157, 158)]
    resp = [(at(155, 21, 30), 0.0)] + [(at(md, 6), plan[md]["resp_rpm"]) for md in (156, 157, 158)]
    core = [(at(157, 18), 0.0), (at(158, 6), plan[158]["core_temp_c"])]
    spo2 = [(at(158, 5), 0.0), (at(158, 6), plan[158]["spo2_pct"])]
    # sleep minutes to take away (from sleep onset forward) on the three nights
    remove = {}
    for md, target in C.AN01_SLEEP_H.items():
        night = [r for r in rows if at(md - 1, 18) <= true_time(r) < at(md, 12) and r["activity_label"] == "sleep"]
        remove[md] = {r["sample_id"] for r in night[:max(0, len(night) - round(target * 60))]}
    return {"hr": hr, "resp": resp, "core": core, "spo2": spo2, "remove": set().union(*remove.values())}


def h2_co2_factor(t):
    a = AN["AN06"]
    if not a["start"] <= t < a["end"]:
        return 0.0
    return smoothstep(at(148, 9), at(148, 12), t) * (1 - smoothstep(at(148, 12, 30), at(148, 13), t))


def apply_vitals(rows, seed, plan, hz):
    r = rng(seed, "inject", "hz" if hz else "min")
    spikes = {(t, col): v for t, col, v in C.SF03_SPIKES}
    for row in rows:
        t0 = true_time(row)
        t = t0 if hz else t0 + timedelta(seconds=30)  # a minute row is the mean of its minute
        cid = row["crew_id"]
        if cid == "C1" and AN["AN01"]["start"] <= t0 < AN["AN01"]["end"]:
            if row["sample_id"] in plan["remove"]:
                wake_effect(row)
            add(row, "hr_bpm", piecewise(plan["hr"], t))
            add(row, "resp_rpm", piecewise(plan["resp"], t))
            add(row, "core_temp_c", piecewise(plan["core"], t))
            add(row, "spo2_pct", piecewise(plan["spo2"], t))
            tag(row, "injected:AN01")
        if cid == "C3" and AN["AN02"]["start"] <= t < AN["AN02"]["end"]:
            f = smoothstep(at(150, 14), at(150, 15), t) * (1 - smoothstep(at(150, 15, 10), at(150, 15, 30), t))
            add(row, "spo2_pct", -9.0 * f)
            add(row, "hr_bpm", 15 * f)
            add(row, "resp_rpm", 6 * f)
            add(row, "bp_sys_est_mmhg", 6 * f)
            tag(row, "injected:AN02")
        if cid == "C2" and AN["AN03"]["start"] <= t < AN["AN03"]["end"]:
            a, b = AN["AN03"]["start"], AN["AN03"]["end"]
            g = min(1.0, (t - a).total_seconds() / 20, (b - t).total_seconds() / 20)
            sec = (t - a).total_seconds()
            target = 133 + 4 * math.sin(2 * math.pi * sec / 97) + r.gauss(0, 1.5)
            row["hr_bpm"] = (1 - g) * num(row, "hr_bpm") + g * target
            row["activity_g"] = min(num(row, "activity_g"), 0.06)
            add(row, "resp_rpm", 2 * g)
            tag(row, "injected:AN03")
        if cid == "C4" and AN["AN04"]["start"] <= t < AN["AN04"]["end"]:
            a, b = AN["AN04"]["start"], AN["AN04"]["end"]
            g = smoothstep(a, a + timedelta(minutes=3), t) * (1 - smoothstep(b - timedelta(minutes=3), b, t))
            row["hr_bpm"] = (1 - g) * num(row, "hr_bpm") + g * (37 + r.gauss(0, 0.7))
            tag(row, "injected:AN04")
        if cid == "C2" and AN["AN05"]["start"] <= t < AN["AN05"]["end"]:
            ft = 1.8 * smoothstep(at(146, 8), at(146, 14), t) * (1 - smoothstep(at(146, 18), at(146, 23), t))
            add(row, "core_temp_c", ft)
            add(row, "skin_temp_c", 1.2 * ft / 1.8)
            add(row, "hr_bpm", 10 * ft)
            add(row, "resp_rpm", 3 * ft / 1.8)
            tag(row, "injected:AN05")
        if row["habitat_id"] == "H2" and h2_co2_factor(t) > 0:
            g = h2_co2_factor(t)
            add(row, "resp_rpm", 4 * g)
            add(row, "hr_bpm", 5 * g)
            tag(row, "injected:AN06")
        if cid == "C4" and AN["AN09"]["start"] <= t < AN["AN09"]["end"]:
            add(row, "hr_bpm", 30 * math.exp(-(t - AN["AN09"]["start"]).total_seconds() / 360))
            tag(row, "injected:AN09")
        if cid == "C4" and at(155, 16, 19, 30) <= t < at(155, 16, 21, 30):
            row["activity_g"] = 0.6 * math.exp(r.gauss(0, 0.3))
            tag(row, "injected:AN09")
        if cid == "C3" and AN["AN10"]["start"] <= t < AN["AN10"]["end"]:
            f = smoothstep(at(157, 3), at(157, 3, 30), t) * (1 - smoothstep(at(157, 3, 40), at(157, 4), t))
            if t >= at(157, 3, 35) and row["activity_label"] == "sleep":
                wake_effect(row)
            add(row, "spo2_pct", -9.0 * f)
            add(row, "hr_bpm", 20 * f)
            tag(row, "injected:AN10")
        if cid == "C3" and AN["SF01"]["start"] <= t0 < AN["SF01"]["end"]:
            row["hr_bpm"], row["resp_rpm"], row["signal_quality"], row["signal_ok"] = "", "", 0.0, "false"
            tag(row, "fault:SF01")
        if cid == "C2" and not hz and AN["SF02"]["start"] <= t0 < AN["SF02"]["end"]:
            row["spo2_pct"] = 97.0
            tag(row, "fault:SF02")
        if cid == "C1" and not hz:
            for col in ("hr_bpm", "skin_temp_c", "spo2_pct", "core_temp_c"):
                if (t0, col) in spikes:
                    row[col] = spikes[(t0, col)]
                    tag(row, "fault:SF03")
        if cid == "C3" and AN["SF04"]["start"] <= t0 < AN["SF04"]["end"]:
            row["signal_quality"], row["signal_ok"] = 0.45, "false"
            add(row, "hr_bpm", r.uniform(-10, 40))
            tag(row, "fault:SF04")
        sp = num(row, "spo2_pct")
        if sp is not None and "fault" not in row["provenance"]:
            row["spo2_pct"] = float(round(min(100.0, sp))) if hz else min(100.0, sp)
    return rows


def to_numbers(rows, cols):
    for row in rows:
        for k in cols:
            if row[k] != "":
                row[k] = float(row[k])
    return rows


# ---------------------------------------------------------------- cabin and radiation
def apply_cabin(rows):
    for row in rows:
        t = C.parse_ts(row["ts"])
        g = h2_co2_factor(t) if row["habitat_id"] == "H2" else 0.0
        if g > 0:
            c = float(row["co2_mmhg"])
            p_mmhg = float(row["pressure_kpa"]) * 7.50062
            new = c + (5.2 - c) * g
            row["co2_mmhg"], row["co2_ppm"] = new, new * 1e6 / p_mmhg
            row["provenance"] += "|injected:AN06"
    return rows


def apply_radiation(rows):
    md = C.mission_day(AN["AN07"]["start"])
    extra = 0.0
    for row in rows:
        if int(row["mission_day"]) == md:
            extra = 2.4 - float(row["dose_msv_day"])
            row["sep_mgy"] = 0.8
            row["total_mgy"] = float(row["total_mgy"]) + 0.8
            row["dose_msv_day"] = 2.4
            row["provenance"] += "|injected:AN07"
        if int(row["mission_day"]) >= md:
            row["dose_msv_mission"] = float(row["dose_msv_mission"]) + extra
    return rows


def space_weather():
    rows = []
    for aid, flare, state, headline, advisory in [
        ("AN07", "12:48", "ALERT", "Large SEP event in progress",
         "Shelter advisory: stay in the shielded module until the proton flux drops"),
        ("AN08", "05:31", "WATCH", "SEP event in progress", "Shelter advisory: stay in the shielded module"),
    ]:
        a = AN[aid]
        t = a["start"]
        rows.append({
            "sep_id": f"{t:%Y-%m-%dT%H:%M:%S}-SEP-001", "event_time": iso(t), "end_time": iso(a["end"]),
            "instruments": ["GOES >10 MeV proton flux (simulated)"],
            "linked_events": [f"{t:%Y-%m-%d}T{flare}:00-FLR-001 (simulated)"],
            "link": "none: simulated event in DONKI SEP layout (https://ccmc.gsfc.nasa.gov/DONKI/)",
            "state": state, "headline": headline, "advisory": advisory, "anomaly_id": aid,
            "simulated": True, "provenance": f"injected:{aid}",
        })
    return rows


# ---------------------------------------------------------------- events
def update_checkins(rows):
    by = {(r["crew_id"], int(C.mission_day(C.parse_ts(r["date"] + "T00:00:00Z")))): r for r in rows}

    def change(cid, md, aid, **kw):
        r = by[(cid, md)]
        r.update({k: v for k, v in kw.items()})
        r["provenance"] += f"|injected:{aid}"
    change("C1", 156, "AN01", sleep_h=5.6, symptoms="short sleep", mood=3, pvt_ms=290)
    change("C1", 157, "AN01", sleep_h=5.4, symptoms="headache|short sleep", mood=3, pvt_ms=301)
    change("C1", 158, "AN01", sleep_h=5.1, symptoms="headache", mood=2, pvt_ms=312, cuff_bp_sys_mmhg=128.0,
           cuff_bp_dia_mmhg=82.0, completed_at=iso(at(158, 6, 38)))
    change("C2", 147, "AN05", sleep_h=5.9, symptoms="headache|nausea", mood=2, note="Felt feverish yesterday.")
    change("C3", 149, "AN06", symptoms="headache", note="Headache after the CO2 alarm in Hab B.")
    change("C4", 149, "AN06", symptoms="headache")
    change("C3", 151, "AN02", mood=3, note="Tired after yesterday's low oxygen.")
    change("C3", 157, "AN10", sleep_h=round(float(by[("C3", 157)]["sleep_h"]) - 1.0, 1), symptoms="short sleep",
           note="Woke at 03:30 short of breath; oxygen given.")
    change("C4", 156, "AN09", symptoms="back pain", note="Left hand bruised after yesterday's trap.")
    return rows


def first_time(rows, crew, a, b, test):
    for r in rows:
        if r["crew_id"] == crew and a <= true_time(r) < b and test(r):
            return true_time(r)
    raise ValueError(f"no trigger row for {crew} {a}")


def build_alerts(vit, link):
    cmo = next(c for c in C.CREW if c["is_cmo"])
    commander = C.CREW_BY_ID["C1"]
    alerts, msgs, reminders = [], [], []

    def author_for(cid):
        return commander["name"] if cid == cmo["crew_id"] else cmo["name"]

    def add_alert(aid, an, cid, metric, value, unit, state, level, reason, rule, source, risk, steps_key, raised,
                  *, ack_s=45, send_after_s=180, auto=False, resolve_s=240, resolved_at=None, crew_msg="",
                  reply="", symptoms=()):
        steps = PROCEDURES.get(steps_key, PROCEDURES["default"])
        ack = raised + timedelta(seconds=ack_s)
        report_created = raised if auto else raised + timedelta(seconds=send_after_s)
        sent, delay, deliver = link.send(report_created)
        report = {"alert_id": aid, "direction": "to_earth", "kind": "report", "from_side": "crew",
                  "author": "Ship (auto SOS)" if auto else author_for(cid), "priority": 0,
                  "created_at": report_created, "sent_at": sent, "delay_s": delay, "deliver_at": deliver,
                  "_parent": None, "provenance": f"injected:{an}",
                  "text": f"{C.CREW_BY_ID[cid]['name']}: {reason}. Handoff report with the last 30 readings attached."}
        msgs.append(report)
        if crew_msg:
            c_created = report_created + timedelta(minutes=8)
            s2, d2, del2 = link.send(c_created)
            msgs.append({"alert_id": aid, "direction": "to_earth", "kind": "message", "from_side": "crew",
                         "author": author_for(cid), "priority": 2, "created_at": c_created, "sent_at": s2,
                         "delay_s": d2, "deliver_at": del2, "_parent": None, "text": crew_msg,
                         "provenance": f"injected:{an}"})
        reply_created = deliver + timedelta(minutes=6)
        s3, d3, reply_at = link.send(reply_created)
        msgs.append({"alert_id": aid, "direction": "to_ship", "kind": "reply", "from_side": "ground",
                     "author": C.FLIGHT_SURGEON, "priority": 0, "created_at": reply_created, "sent_at": s3,
                     "delay_s": d3, "deliver_at": reply_at, "_parent": report, "text": reply,
                     "provenance": f"injected:{an}"})
        resolved = resolved_at or reply_at + timedelta(seconds=resolve_s)
        s4, d4, del4 = link.send(resolved)
        msgs.append({"alert_id": aid, "direction": "to_earth", "kind": "update", "from_side": "crew",
                     "author": author_for(cid), "priority": 1, "created_at": resolved, "sent_at": s4,
                     "delay_s": d4, "deliver_at": del4, "_parent": None, "provenance": f"injected:{an}",
                     "text": f"Resolved by {author_for(cid)}."})
        alerts.append({
            "alert_id": aid, "crew_id": cid, "metric": metric, "value": value, "unit": unit, "state": state,
            "level": level, "stage": "resolved", "reason": reason, "rule": rule, "source": source, "nasa_risk": risk,
            "symptoms": list(symptoms), "steps_done": [str(i) for i in range(len(steps))], "raised_at": iso(raised),
            "acknowledged_at": iso(ack), "sent_at": iso(sent), "earth_at": iso(deliver), "reply_at": iso(reply_at),
            "resolved_at": iso(resolved), "anomaly_id": an, "simulated": True, "provenance": f"injected:{an}"})
        return resolved

    pending = "pending: Light Time/data/thresholds.json (frontend repo)"
    hypoxia, cardio = "Risk of Hypoxia", "Risk of Cardiovascular Adaptations"
    events = []
    t = first_time(vit, "C3", AN["AN02"]["start"], AN["AN02"]["end"], lambda r: num(r, "spo2_pct") < 94)
    events.append(("AN02", t, dict(cid="C3", metric="spo2", value=93.0, unit="%", state="ALERT", level="warning",
                                   reason="Blood oxygen 93 %, under 94 % at rest", rule="SpO2 under 94 %",
                                   source=pending, risk=hypoxia, steps_key="spo2",
                                   crew_msg="Mask on at 2 L/min. SpO2 back to 95 % after four minutes.",
                                   reply="Agree with oxygen. Check the cabin O2 sensor in Hab A and recheck SpO2 hourly today.")))
    t = first_time(vit, "C2", AN["AN03"]["start"], AN["AN03"]["end"], lambda r: num(r, "hr_bpm") >= 120)
    events.append(("AN03", t, dict(cid="C2", metric="hr", value=133.0, unit="bpm", state="ALERT", level="warning",
                                   reason="Heart rate 133 bpm at rest, no exercise", rule="HR far over band at rest",
                                   source=pending, risk=cardio, steps_key="heart_rate",
                                   crew_msg="Ended on its own after 20 min. ECG strip attached.",
                                   reply="Looks like a paroxysmal tachycardia. No caffeine today; record an ECG if it returns.")))
    t = first_time(vit, "C4", AN["AN04"]["start"], AN["AN04"]["end"], lambda r: num(r, "hr_bpm") < 40)
    events.append(("AN04", t, dict(cid="C4", metric="hr", value=37.0, unit="bpm", state="ALERT", level="emergency",
                                   reason="Heart rate 37 bpm in sleep, under the personal sleeping range",
                                   rule="HR far under band", source=pending, risk=cardio, steps_key="heart_rate",
                                   crew_msg="Woke up fine, no dizziness.",
                                   reply="Probably vagal in sleep. Repeat the overnight ECG tonight.")))
    t = first_time(vit, "C2", AN["AN05"]["start"], AN["AN05"]["end"], lambda r: num(r, "core_temp_c") > 38.0)
    events.append(("AN05", t, dict(cid="C2", metric="temp_c", value=38.1, unit="C", state="ALERT", level="warning",
                                   reason="Core temperature 38.1 C, over 38.0 C", rule="over 38.0 C", source=pending,
                                   risk="", steps_key="default", crew_msg="Paracetamol given. Fluids up.",
                                   reply="Temperature every 4 hours. 500 mL more fluids today. Report if over 39 C.")))
    events.append(("AN09", AN["AN09"]["start"] + timedelta(seconds=7),
                   dict(cid="C4", metric="manual", value=None, unit="", state="SOS", level="emergency",
                        reason="Manual SOS: triple glove tap", rule="manual SOS", source="crew", risk="",
                        steps_key="default", auto=True, crew_msg="Hand trapped in the rack, freed. Bruising only.",
                        reply="Ice for 20 min, check grip strength and sensation, photo of the hand please.")))
    t = first_time(vit, "C3", AN["AN10"]["start"], AN["AN10"]["end"], lambda r: num(r, "spo2_pct") < 94)
    events.append(("AN10", t, dict(cid="C3", metric="spo2", value=91.0, unit="%", state="SOS", level="emergency",
                                   reason="Blood oxygen 91 % in sleep, link down", rule="SpO2 under 94 %",
                                   source=pending, risk=hypoxia, steps_key="spo2", auto=True,
                                   resolved_at=at(157, 4, 20),
                                   crew_msg="Treated on board during the blackout: oxygen, SpO2 97 % by 04:00.",
                                   reply="Reviewed the queued report. Agree with what you did. Send a 24 h SpO2 trend.")))
    events.sort(key=lambda e: e[1])
    for k, (an, raised, kw) in enumerate(events, start=2):  # A1 is the demo alert
        resolved = add_alert(f"A{k}", an, raised=raised, **kw)
        if an == "AN05":
            for n in range(4):
                due = resolved + timedelta(hours=4 * (n + 1))
                done = due + timedelta(minutes=5 + 4 * n)
                reminders.append({"reminder_id": f"R{len(reminders) + 1}", "crew_id": "C2", "alert_id": f"A{k}",
                                  "text": "Take temperature", "due_at": iso(due),
                                  "done_at": iso(done) if done <= C.DEMO_NOW else "",
                                  "simulated": True, "provenance": "injected:AN05"})
    # A1: the demo morning. Raised, nothing else yet.
    alerts.insert(0, {
        "alert_id": "A1", "crew_id": "C1", "metric": "hr_rest", "value": 84.0, "unit": "bpm", "state": "ALERT",
        "level": "warning", "stage": "raised", "reason": "Resting heart rate 84 bpm, 3rd day over baseline",
        "rule": "resting HR > baseline + 20 bpm for 3 consecutive days",
        "source": "OCHMO Exercise Overview brief (TB-031); Cardiovascular evidence report", "nasa_risk": cardio,
        "symptoms": ["headache"], "steps_done": [], "raised_at": iso(at(158, 6, 12)), "acknowledged_at": "",
        "sent_at": "", "earth_at": "", "reply_at": "", "resolved_at": "", "anomaly_id": "AN01",
        "simulated": True, "provenance": "injected:AN01"})
    return alerts, msgs, reminders


def ground_truth(link):
    rows = []
    for a in C.ANOMALIES:
        rows.append({**a, "start": iso(a["start"]), "end": iso(a["end"]),
                     "link_state_at_start": "up" if link.up(a["start"]) else "down"})
    write_csv(C.OUT_TRUTH / "anomalies.csv", columns("anomalies"), rows)


# ---------------------------------------------------------------- main
def run(seed):
    link = Link()
    src, out = C.OUT_CLEAN, C.OUT_ANOM
    clean_min = to_numbers(read_csv(src / "vitals_1min.csv"), NUM)
    plan = an01_plan(clean_min)
    vit = apply_vitals(clean_min, seed, plan, hz=False)
    write_csv(out / "vitals_1min.csv", columns("vitals_1min"), vit)
    hz = apply_vitals(to_numbers(read_csv(src / "vitals_1hz_demo.csv"), NUM), seed, plan, hz=True)
    write_csv(out / "vitals_1hz_demo.csv", columns("vitals_1hz_demo"), hz)
    cabin = apply_cabin(read_csv(src / "cabin_env.csv"))
    write_csv(out / "cabin_env.csv", columns("cabin_env"), cabin)
    write_csv(out / "radiation_daily.csv", columns("radiation_daily"), apply_radiation(read_csv(src / "radiation_daily.csv")))
    checkins = update_checkins(read_csv(src / "checkins.csv"))
    write_csv(out / "checkins.csv", columns("checkins"), checkins)
    write_csv(out / "space_weather_events.csv", columns("space_weather_events"), space_weather())
    sos_t = AN["AN09"]["start"] + timedelta(seconds=7)
    write_csv(out / "sos_events.csv", columns("sos_events"), [{
        "event_id": "E1", "crew_id": "C4", "suit_id": "LT-04", "sensor_ts": C.iso_ms(M.sensor_time("C4", sos_t)),
        "gateway_ts": C.iso_ms(sos_t + timedelta(milliseconds=180)), "trigger": "glove_triple_tap",
        "anomaly_id": "AN09", "simulated": True, "provenance": "injected:AN09"}])
    alerts, alert_msgs, reminders = build_alerts(vit, link)
    write_csv(out / "alerts_seed.csv", columns("alerts_seed"), alerts)
    write_csv(out / "reminders.csv", columns("reminders"), reminders)
    msgs = G.daily_messages(checkins, link) + alert_msgs
    write_csv(out / "messages.csv", columns("messages"), G.finish_messages(msgs))
    ground_truth(link)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--seed", type=int, default=C.DEFAULT_SEED)
    run(p.parse_args().seed)
    print("anomalous build written to", C.OUT_ANOM)
