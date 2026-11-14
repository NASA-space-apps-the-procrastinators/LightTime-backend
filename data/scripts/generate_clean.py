"""Step 1: the reference tables and the clean build (no anomalies).

python data/scripts/generate_clean.py --seed 2026
"""
import argparse
import math
from datetime import timedelta

import config as C
import model as M
from schema import columns
from config import iso_ms
from util import Link, rng, write_csv

SPEC = "OCHMO Exercise Overview brief (TB-031); Cardiovascular evidence report"


# ---------------------------------------------------------------- reference
def write_reference(seed):
    out = C.OUT_REF
    write_csv(out / "mission.csv", columns("mission"), [{
        "mission_id": C.MISSION_ID, "launch_date": C.LAUNCH.isoformat(), "platform": C.PLATFORM,
        "demo_now": C.iso(C.DEMO_NOW),
        "link_model": "ISS platform with a Mars-distance link (the backend dial's analogue); see link_windows.csv",
        "simulated": True, "provenance": "sim"}])
    write_csv(out / "crew.csv", columns("crew"), C.CREW)
    write_csv(out / "habitats.csv", columns("habitats"), C.HABITATS)
    metrics = [
        ("hr_bpm", "bpm", "hr", "heart_rate", 25, 230, "Heart rate from the shirt ECG"),
        ("hr_rest_bpm", "bpm", "hr_rest", "heart_rate", 25, 150,
         "Morning resting HR: median of the first 20 min after waking, at rest"),
        ("resp_rpm", "/min", "resp", "", 4, 60, "Breathing rate from the chest bands"),
        ("spo2_pct", "%", "spo2", "spo2", 50, 100, "Blood oxygen from the headband pulse oximeter"),
        ("skin_temp_c", "C", "skin_temp_c", "skin_temp", 25, 42, "Skin temperature, headband"),
        ("core_temp_c", "C", "temp_c", "", 34, 42.5, "Core temperature, heat-flux sensor"),
        ("activity_g", "g", "activity_g", "", 0, 4, "Accelerometer magnitude above gravity-free rest"),
        ("bp_sys_est_mmhg", "mmHg", "bp_sys", "bp_sys", 60, 230, "Systolic BP estimated by the shirt"),
        ("bp_sys_mmhg", "mmHg", "bp_sys", "bp_sys", 60, 230, "Systolic BP, morning cuff"),
        ("bp_dia_mmhg", "mmHg", "bp_dia", "bp_dia", 30, 140, "Diastolic BP, morning cuff"),
        ("sleep_h", "h", "sleep_h", "sleep_hours", 0, 24, "Sleep, self-reported at check-in"),
        ("mood", "1-5", "mood", "mood", 1, 5, "Mood at check-in"),
        ("pvt_ms", "ms", "pvt_ms", "", 100, 3000, "Psychomotor vigilance test mean reaction time"),
        ("dose_msv_day", "mSv/day", "dose_mSv_day", "", 0, 50, "Radiation dose, station"),
        ("co2_mmhg", "mmHg", "co2_mmHg", "", 0.1, 10, "Cabin CO2 partial pressure"),
        ("signal_quality", "0-1", "signal_quality", "signal_ok", 0, 1, "Worst channel quality; ok is >= 0.6"),
    ]
    write_csv(out / "metrics.csv", columns("metrics"), [dict(zip(
        ["metric", "unit", "api_name", "backend_name", "min_possible", "max_possible", "description"],
        [m[0], m[1], m[2], m[3], float(m[4]), float(m[5]), m[6]])) for m in metrics])
    channels = [
        ("ecg", "CSA Bio-Monitor (Astroskin) shirt ECG", ["hr_bpm"], "1 Hz (beat-derived)", ""),
        ("chest_band", "Bio-Monitor shirt respiratory inductance bands", ["resp_rpm"], "1 Hz", ""),
        ("pulse_ox", "Bio-Monitor headband pulse oximeter", ["spo2_pct"], "1 Hz", "whole percent"),
        ("skin_temp", "Bio-Monitor headband skin sensor", ["skin_temp_c"], "1 Hz", ""),
        ("core_temp", "Heat-flux core temperature sensor", ["core_temp_c"], "1/min",
         "Bio-Monitor does not list core temp; modelled on ISS heat-flux sensors. Check before citing"),
        ("accel", "Bio-Monitor shirt 3-axis accelerometer", ["activity_g"], "1 Hz", ""),
        ("bp_est", "Bio-Monitor shirt systolic BP estimate", ["bp_sys_est_mmhg"], "1/min", "estimate, systolic only"),
        ("cuff", "Manual BP cuff at the morning check-in", ["bp_sys_mmhg", "bp_dia_mmhg"], "daily", ""),
        ("cabin", "Cabin environment sensors", ["co2_mmhg"], "5 min", "EDA RR-1 replay in H1"),
    ]
    write_csv(out / "channels.csv", columns("channels"), [dict(zip(
        ["source", "device_model", "metrics", "native_rate", "note"], c)) for c in channels])
    rows = []
    for cid, b in C.BASELINES.items():
        src = "backend-api-contract.md" if cid == "C1" else "draft (crew-seed.json not in this repo)"
        for metric, unit in [("hr_rest", "bpm"), ("bp_sys", "mmHg"), ("bp_dia", "mmHg"), ("spo2", "%"),
                             ("temp_c", "C"), ("resp", "/min"), ("sleep_h", "h")]:
            rows.append({"crew_id": cid, "metric": metric, "low": float(b[metric][0]), "high": float(b[metric][1]),
                         "unit": unit, "set_on": C.BASELINE_SET_ON.isoformat(), "source": src})
        for metric, unit in [("pvt_ms", "ms"), ("vo2max_ml_min_kg", "mL/min/kg")]:
            rows.append({"crew_id": cid, "metric": metric, "point": float(b[metric]), "unit": unit,
                         "set_on": C.BASELINE_SET_ON.isoformat(), "source": src})
    write_csv(out / "baselines.csv", columns("baselines"), rows)
    pending = "pending: Light Time/data/thresholds.json (frontend repo)"
    th = [
        ("hr_rest", "bpm", "outside baseline band", "resting HR > baseline + 20 bpm for 3 consecutive days",
         None, 20, False, 3, SPEC, "from contract (/thresholds example)"),
        ("bp_sys", "mmHg", "outside baseline band", "out of band 3 days running, or out of band with any symptom",
         None, None, False, 3, pending, "rule from contract scoring table; source pending"),
        ("bp_dia", "mmHg", "outside baseline band", "out of band 3 days running, or out of band with any symptom",
         None, None, False, 3, pending, "rule from contract scoring table; source pending"),
        ("spo2", "%", "below baseline band", "under 94 %", None, 94, False, None, pending,
         "rule from contract scoring table; source pending"),
        ("temp_c", "C", "above baseline band", "over 38.0 C", None, 38.0, False, None, pending,
         "rule from contract scoring table; source pending"),
        ("resp", "/min", "over 20/min", "over 20/min with a symptom", 20, 20, True, None, pending,
         "rule from contract scoring table; source pending"),
        ("sleep_h", "h", "below baseline band or under 6.5 h", "with a symptom, or 3 days running", 6.5, None, True,
         3, pending, "rule from contract scoring table; source pending"),
        ("mood", "1-5", "2 or lower", "2 or lower with a symptom", 2, 2, True, None, pending,
         "rule from contract scoring table; source pending"),
        ("pvt_ms", "ms", "over baseline + 15 %", "over baseline + 15 % with a symptom", 0.15, 0.15, True, None,
         pending, "rule from contract scoring table; source pending"),
        ("dose_mSv_day", "mSv/day", "never", "over 2 mSv", None, 2, False, None, pending,
         "rule from contract scoring table; source pending"),
        ("co2_mmHg", "mmHg", "from 2.8 mmHg", "over 4.5 mmHg", 2.8, 4.5, False, None,
         "OCHMO Carbon Dioxide brief", "from contract (/station)"),
        ("signal_quality", "0-1", "RECHECK under 0.6, never an ALERT on its own", "never", 0.6, None, False, None,
         "backend-api-contract.md conventions", "from contract"),
    ]
    keys = ["metric", "unit", "watch_rule", "alert_rule", "watch_param", "alert_param", "needs_symptom",
            "consecutive_days", "source", "source_status"]
    write_csv(out / "thresholds.csv", columns("thresholds"), [
        {k: (float(v) if k in ("watch_param", "alert_param") and v is not None else v) for k, v in zip(keys, t)}
        for t in th])
    windows = [dict(w, start=C.iso(w["start"]), end=C.iso(w["end"])) for w in Link().windows]
    write_csv(out / "link_windows.csv", columns("link_windows"), windows)


# ---------------------------------------------------------------- vitals
def gateway_times(seed, crew_id, times):
    """Arrival time at the base station: 50-400 ms after the true time, and about one
    store-and-forward burst a day where 2-8 min of samples arrive together."""
    r = rng(seed, "gateway", crew_id)
    bursts = []
    for md in range(C.mission_day(C.START), C.mission_day(C.DEMO_NOW) + 1):
        if r.random() < 0.5:
            a = C.at(md, r.randint(8, 18), r.randint(0, 59))
            bursts.append((a, a + timedelta(minutes=r.randint(2, 8))))
    out, k = [], 0
    for t in times:
        while k < len(bursts) and bursts[k][1] <= t:
            k += 1
        latency = timedelta(milliseconds=min(400, 50 + r.lognormvariate(4.3, 0.5)))
        if k < len(bursts) and bursts[k][0] <= t < bursts[k][1]:
            out.append(bursts[k][1] + latency)
        else:
            out.append(t + latency)
    return out


def minute_rows(seed, crew_id, labels, habitat, sig):
    r = rng(seed, "minute_noise", crew_id)
    times = [M.t_of(i) for i in range(M.N_MIN)]
    gws = gateway_times(seed, crew_id, times)
    rows = []
    for i, t in enumerate(times):
        sq = round(sig["sq"][i], 2)
        rows.append({
            "sample_id": f"{crew_id}-M-{t:%Y%m%dT%H%M}Z", "crew_id": crew_id,
            "sensor_ts": iso_ms(M.sensor_time(crew_id, t)), "gateway_ts": iso_ms(gws[i]),
            "mission_day": C.mission_day(t), "habitat_id": habitat[i], "activity_label": labels[i],
            "hr_bpm": sig["hr"][i] + r.gauss(0, 0.6), "resp_rpm": sig["resp"][i] + r.gauss(0, 0.3),
            "spo2_pct": min(100.0, sig["spo2"][i] + r.gauss(0, 0.2)),
            "skin_temp_c": sig["skin"][i] + r.gauss(0, 0.05), "core_temp_c": sig["core"][i] + r.gauss(0, 0.02),
            "activity_g": sig["act"][i], "bp_sys_est_mmhg": sig["bp"][i] + r.gauss(0, 1.0),
            "signal_quality": sq, "signal_ok": sq >= 0.6, "simulated": True, "provenance": "sim",
        })
    return rows


def hz_rows(seed, crew_id, labels, habitat, sig, a, b):
    subject = C.PPG_TEXTURE_SUBJECT[crew_id]
    tex_hr, tex_skin = M.ppg_texture(subject)
    r = rng(seed, "hz", crew_id, a.isoformat())
    off = r.randrange(len(tex_hr))
    n = int((b - a).total_seconds())
    times = [a + timedelta(seconds=s) for s in range(n)]
    gws = gateway_times(seed, crew_id + "hz" + a.isoformat(), times)
    rows = []
    for s, t in enumerate(times):
        i = M.idx(t)
        j = min(i + 1, M.N_MIN - 1)
        w = (t - M.t_of(i)).total_seconds() / 60.0

        def interp(k):
            return sig[k][i] * (1 - w) + sig[k][j] * w
        sq = round(min(0.99, max(0.0, interp("sq") + r.gauss(0, 0.01))), 2)
        rows.append({
            "sample_id": f"{crew_id}-S-{t:%Y%m%dT%H%M%S}Z", "crew_id": crew_id,
            "sensor_ts": iso_ms(M.sensor_time(crew_id, t)), "gateway_ts": iso_ms(gws[s]),
            "mission_day": C.mission_day(t), "habitat_id": habitat[i], "activity_label": labels[i],
            "hr_bpm": interp("hr") + tex_hr[(s + off) % len(tex_hr)] + r.gauss(0, 0.5),
            "resp_rpm": interp("resp") + r.gauss(0, 0.4),
            "spo2_pct": float(min(100, round(interp("spo2") + r.gauss(0, 0.25)))),
            "skin_temp_c": interp("skin") + tex_skin[(s + off) % len(tex_skin)] + r.gauss(0, 0.02),
            "core_temp_c": interp("core"),
            "activity_g": M.ACT_BASE[labels[i]] * math.exp(r.gauss(0, 0.5)),
            "bp_sys_est_mmhg": interp("bp") + r.gauss(0, 1.0),
            "signal_quality": sq, "signal_ok": sq >= 0.6, "simulated": True,
            "provenance": f"sim+ppg_dalia_texture:{subject}",
        })
    return rows


# ---------------------------------------------------------------- cabin and radiation
def cabin_rows(seed):
    tele = M.load_eda_telemetry()
    t0 = C.parse_ts(tele[0]["time"])
    rows = []
    for hab, offset_days in (("H1", 0), ("H2", C.CABIN_H2_OFFSET_DAYS)):
        r = rng(seed, "cabin", hab)
        origin = t0 + timedelta(days=offset_days)
        shift = C.START - origin
        p_dev, o2_dev = 0.0, 0.0
        for rec in tele:
            orig = C.parse_ts(rec["time"])
            if orig < origin:
                continue
            ts = orig + shift
            if ts >= C.DEMO_NOW:
                break
            p_dev = 0.98 * p_dev + r.gauss(0, 0.03)
            o2_dev = 0.98 * o2_dev + r.gauss(0, 0.0006)
            pressure = 101.3 + p_dev
            co2 = rec["co2_iss"]
            temp, rh = rec["temperature_iss"], rec["humidity_iss"]
            if hab == "H2":
                co2 = co2 * (1 + r.gauss(0, 0.02)) + 60
                temp, rh = temp - 0.3 + r.gauss(0, 0.1), rh + 2 + r.gauss(0, 1)
                real, prov = [], "sim:eda_rr1_shape_plus_7d"
            else:
                real, prov = ["co2_ppm", "temp_c", "rh_pct"], "eda_rr1_replay(co2_ppm,temp_c,rh_pct)+sim(pressure,ppo2)"
            p_mmhg = pressure * 7.50062
            rows.append({
                "habitat_id": hab, "ts": C.iso(ts), "mission_day": C.mission_day(ts), "co2_ppm": float(co2),
                "co2_mmhg": co2 * p_mmhg / 1e6, "ppo2_mmhg": p_mmhg * (0.208 + o2_dev), "pressure_kpa": pressure,
                "temp_c": float(temp), "rh_pct": float(rh), "orig_ts": rec["time"], "real_fields": real,
                "simulated": True, "provenance": prov,
            })
    return rows


def radiation_rows(seed):
    rad = M.load_eda_radiation()
    pre, window = M.station_doses(seed)
    cum = sum(pre.values())
    rows = []
    for k, md in enumerate(sorted(window)):
        rec = rad[k]
        cum += window[md]
        rows.append({
            "date": C.md_date(md).isoformat(), "mission_day": md, "gcr_mgy": rec["gcr"], "saa_mgy": rec["saa"],
            "sep_mgy": 0.0, "total_mgy": rec["total"], "dose_msv_day": window[md], "dose_msv_mission": cum,
            "orig_date": rec["time"][:10], "simulated": True,
            "provenance": "eda_rr1_replay(gcr,saa,total mGy)+sim(dose_msv: EDA shape scaled so day 158 = 0.51)",
        })
    return rows


# ---------------------------------------------------------------- events
def wake_time(labels, md):
    for i in range(max(0, M.idx(C.at(md, 5))), min(M.N_MIN, M.idx(C.at(md, 8)))):
        if labels[i] == "post_sleep":
            return M.t_of(i)
    return C.at(md, 6)


DEMO_CHECKIN = {"C2": (6, 8), "C3": (6, 15), "C4": (6, 24), "C1": (6, 38)}


def checkin_rows(seed, schedules):
    rows = []
    for cid in C.CREW_IDS:
        labels = schedules[cid][0]
        b = C.BASELINES[cid]
        for md in range(C.mission_day(C.START), C.mission_day(C.DEMO_NOW) + 1):
            if (cid, md) == ("C4", 145):
                continue  # missed check-in: breaks the crew streak, which is 12 on day 158
            r = rng(seed, "checkin", cid, md)
            f = M.drift(md)
            done = (C.at(md, *DEMO_CHECKIN[cid]) if md == 158
                    else wake_time(labels, md) + timedelta(minutes=r.randint(15, 55)))
            first = True
            if (cid, md) == ("C3", 153):
                done, first = C.at(md, 7, 20), False  # redone later the same morning; replaces the first
            rows.append({
                "checkin_id": f"K-{cid}-{C.md_date(md):%Y%m%d}", "crew_id": cid, "date": C.md_date(md).isoformat(),
                "completed_at": C.iso(done), "mood": r.choices([3, 4, 5], [0.3, 0.5, 0.2])[0],
                "sleep_h": round(max(0.0, M.suit_sleep_hours(labels, md) + r.gauss(0, 0.2)), 1),
                "pvt_ms": int(round(b["pvt_ms"] * (1 + r.gauss(0, 0.04)))), "symptoms": [], "note": "",
                "first_today": first,
                "cuff_bp_sys_mmhg": float(round(M.mid(b["bp_sys"]) - 4 * f + r.gauss(0, 3))),
                "cuff_bp_dia_mmhg": float(round(M.mid(b["bp_dia"]) + r.gauss(0, 2.5))),
                "live_demo": done > C.DEMO_NOW, "simulated": True, "provenance": "sim",
            })
    return rows


def daily_messages(checkins, link):
    """A daily summary from the crew medical officer at 20:00 and the ground's reply."""
    cmo = next(c for c in C.CREW if c["is_cmo"])
    msgs = []
    for md in range(C.mission_day(C.START), C.mission_day(C.DEMO_NOW) + 1):
        created = C.at(md, 20)
        if created > C.DEMO_NOW:
            break
        n = sum(1 for k in checkins if k["date"] == C.md_date(md).isoformat())
        sent, delay, deliver = link.send(created)
        up = {"alert_id": "", "direction": "to_earth", "kind": "message", "from_side": "crew",
              "author": cmo["name"], "priority": 2, "created_at": created, "sent_at": sent, "delay_s": delay,
              "deliver_at": deliver, "_parent": None,
              "text": f"Daily crew health summary for mission day {md}: {n} of 4 check-ins complete. "
                      "Table attached."}
        msgs.append(up)
        reply_created = deliver + timedelta(minutes=5)
        if reply_created <= C.DEMO_NOW:
            s2, d2, del2 = link.send(reply_created)
            msgs.append({"alert_id": "", "direction": "to_ship", "kind": "reply", "from_side": "ground",
                         "author": C.FLIGHT_SURGEON, "priority": 0, "created_at": reply_created, "sent_at": s2,
                         "delay_s": d2, "deliver_at": del2, "_parent": up,
                         "text": "Received, thank you. No change to the plan."})
    return msgs


def finish_messages(msgs):
    """Number the messages by creation time and work out their status at demo_now."""
    from util import status_at
    msgs = sorted(msgs, key=lambda m: (m["created_at"], m["direction"]))
    for k, m in enumerate(msgs, 1):
        m["message_id"] = f"M{k}"
    out = []
    for m in msgs:
        sent = m["sent_at"] if m["sent_at"] and m["sent_at"] <= C.DEMO_NOW else None
        out.append({**{k: v for k, v in m.items() if not k.startswith("_")},
                    "created_at": C.iso(m["created_at"]), "sent_at": C.iso(sent),
                    "delay_s": m["delay_s"] if sent else None,
                    "deliver_at": C.iso(m["deliver_at"]) if sent else "",
                    "status_at_demo_now": status_at(sent, m["deliver_at"]),
                    "in_reply_to": m["_parent"]["message_id"] if m["_parent"] else "",
                    "simulated": True, "provenance": m.get("provenance", "sim")})
    return out


# ---------------------------------------------------------------- main
def run(seed):
    write_reference(seed)
    link = Link()
    schedules, signals = {}, {}
    vit_min, vit_hz = [], []
    for cid in C.CREW_IDS:
        labels, habitat = M.build_schedule(seed, cid)
        sig = M.simulate(seed, cid, labels)
        schedules[cid], signals[cid] = (labels, habitat), sig
        vit_min += minute_rows(seed, cid, labels, habitat, sig)
        for wcid, a, b in C.HZ_WINDOWS:
            if wcid == cid:
                vit_hz += hz_rows(seed, cid, labels, habitat, sig, a, b)
    out = C.OUT_CLEAN
    write_csv(out / "vitals_1min.csv", columns("vitals_1min"), vit_min)
    write_csv(out / "vitals_1hz_demo.csv", columns("vitals_1hz_demo"), vit_hz)
    write_csv(out / "cabin_env.csv", columns("cabin_env"), cabin_rows(seed))
    write_csv(out / "radiation_daily.csv", columns("radiation_daily"), radiation_rows(seed))
    checkins = checkin_rows(seed, schedules)
    write_csv(out / "checkins.csv", columns("checkins"), checkins)
    write_csv(out / "messages.csv", columns("messages"), finish_messages(daily_messages(checkins, link)))
    for empty in ("sos_events", "space_weather_events", "alerts_seed", "reminders"):
        write_csv(out / f"{empty}.csv", columns(empty), [])
    return schedules


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--seed", type=int, default=C.DEFAULT_SEED)
    run(p.parse_args().seed)
    print("clean build written to", C.OUT_CLEAN)
