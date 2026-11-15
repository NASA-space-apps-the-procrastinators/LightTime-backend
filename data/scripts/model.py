"""The physiology and schedule model behind the clean data.

Every channel is: personal baseline + slow microgravity drift + circadian term +
activity term (with first-order lag) + slow AR(1) wander. A second, faster noise is
added when a value is written out. All randomness comes from util.rng streams.
"""
import math
from datetime import timedelta

import config as C
from util import read_csv, rng

N_MIN = int((C.DEMO_NOW - C.START).total_seconds() // 60)


def t_of(i):
    return C.START + timedelta(minutes=i)


def idx(t):
    return int((t - C.START).total_seconds() // 60)


def drift(md):
    """0 at launch, about 1 after day 60. Microgravity adaptation, settled before our window."""
    return 1.0 - math.exp(-md / 20.0)


def mid(band):
    return (band[0] + band[1]) / 2.0


def hours(t):
    return t.hour + t.minute / 60.0 + t.second / 3600.0


# ---- schedule ---------------------------------------------------------------
def _set(labels, a, b, label):
    for i in range(max(0, idx(a)), min(N_MIN, idx(b))):
        labels[i] = label


def exercise_slots(seed, crew_id, md):
    if (crew_id, md) in C.EXERCISE_OVERRIDE:
        return [(C.at(md, *hm), C.EXERCISE_MIN, kind) for hm, kind in C.EXERCISE_OVERRIDE[(crew_id, md)]]
    k = C.CREW_IDS.index(crew_id)
    if (md + k) % 7 == 0:
        return []  # one rest day a week
    r = rng(seed, "exercise", crew_id, md)
    out = []
    for hm, kind in C.EXERCISE[crew_id]:
        start = C.at(md, *hm) + timedelta(minutes=round(r.gauss(0, 8)))
        out.append((start, r.randint(60, 75), kind))
    return out


def build_schedule(seed, crew_id):
    """Per-minute activity label and habitat for one crew member, plus suit-measured
    sleep (hours) for each night, keyed by the mission day the night ends on."""
    labels = ["work"] * N_MIN
    first_md, last_md = C.mission_day(C.START), C.mission_day(C.DEMO_NOW)
    for md in range(first_md - 1, last_md + 1):
        _set(labels, C.at(md, 0), C.at(md, 6), "sleep")
        _set(labels, C.at(md, 6), C.at(md, 7), "post_sleep")
        _set(labels, C.at(md, 7), C.at(md, 7, 30), "meal")
        _set(labels, C.at(md, 12, 30), C.at(md, 13, 15), "meal")
        _set(labels, C.at(md, 19), C.at(md, 19, 30), "meal")
        _set(labels, C.at(md, 19, 30), C.at(md, 21, 30), "pre_sleep")
        _set(labels, C.at(md, 21, 30), C.at(md + 1, 0), "sleep")
    lo, hi = C.BASELINES[crew_id]["sleep_h"]
    sleep_target = {}
    for md in range(first_md, last_md + 1):
        r = rng(seed, "sleep", crew_id, md)
        wake = C.at(md, 6) + timedelta(minutes=round(r.gauss(0, 4)))
        hours_asleep = min(7.9, max(5.8, r.gauss(mid((lo, hi)) - 0.3 * drift(md), 0.35)))
        bouts = [(r.uniform(0.15, 0.85), r.randint(3, 9)) for _ in range(2)]
        bout_min = sum(b for _, b in bouts)
        onset = wake - timedelta(hours=hours_asleep, minutes=bout_min)
        onset = max(onset, C.at(md - 1, 21, 45))
        _set(labels, C.at(md - 1, 21, 30), onset, "awake_in_bed")
        _set(labels, onset, wake, "sleep")
        span = (wake - onset).total_seconds() / 60
        for frac, length in bouts:
            a = onset + timedelta(minutes=round(frac * span))
            _set(labels, a, a + timedelta(minutes=length), "awake_in_bed")
        _set(labels, wake, C.at(md, 7), "post_sleep")
        sleep_target[md] = (onset, wake)
        for start, length, kind in exercise_slots(seed, crew_id, md):
            _set(labels, start, start + timedelta(minutes=length), kind)
    home = C.CREW_BY_ID[crew_id]["home_habitat_id"]
    habitat = [("H1" if lab in ("meal", "exercise_ared", "exercise_cevis") else home) for lab in labels]
    for (cid, md), ((h0, m0), (h1, m1), hab) in C.HABITAT_HOLD.items():
        if cid == crew_id:
            for i in range(max(0, idx(C.at(md, h0, m0))), min(N_MIN, idx(C.at(md, h1, m1)))):
                habitat[i] = hab
    return labels, habitat


def suit_sleep_hours(labels, md):
    """Minutes labelled sleep between 18:00 the evening before and 12:00 on day md."""
    a, b = max(0, idx(C.at(md - 1, 18))), min(N_MIN, idx(C.at(md, 12)))
    return sum(1 for i in range(a, b) if labels[i] == "sleep") / 60.0


# ---- physiology -------------------------------------------------------------
class AR1:
    def __init__(self, r, sd, tau_min):
        self.r, self.phi = r, math.exp(-1.0 / tau_min)
        self.sd = sd * math.sqrt(1 - self.phi ** 2)
        self.x = r.gauss(0, sd)

    def step(self):
        self.x = self.phi * self.x + self.r.gauss(0, self.sd)
        return self.x


def lag(state, target, tau_up, tau_down):
    tau = tau_up if target > state else tau_down
    return state + (target - state) * (1 - math.exp(-1.0 / tau))


SQ_BASE = {"sleep": 0.96, "awake_in_bed": 0.95, "post_sleep": 0.94, "pre_sleep": 0.94, "work": 0.92,
           "meal": 0.91, "exercise_ared": 0.76, "exercise_cevis": 0.73}
ACT_BASE = {"sleep": 0.012, "awake_in_bed": 0.03, "post_sleep": 0.06, "pre_sleep": 0.06, "work": 0.09,
            "meal": 0.07, "exercise_ared": 0.40, "exercise_cevis": 0.55}


def simulate(seed, crew_id, labels):
    """Smooth per-minute signals (lists) for one crew member."""
    b = C.BASELINES[crew_id]
    r = rng(seed, "physio", crew_id)
    noise = {k: AR1(rng(seed, "ar", crew_id, k), sd, tau) for k, sd, tau in [
        ("hr", 1.5, 10), ("resp", 0.6, 8), ("spo2", 0.35, 15), ("core", 0.05, 30), ("skin", 0.15, 20),
        ("bp", 2.0, 15), ("sq", 0.015, 5)]}
    hr_s, resp_s, bp_s = mid(b["hr_rest"]), mid(b["resp"]), mid(b["bp_sys"])
    core_ex, skin_sleep = 0.0, 0.0
    out = {k: [0.0] * N_MIN for k in ("hr", "resp", "spo2", "core", "skin", "act", "bp", "sq")}
    ex_minute = 0
    for i in range(N_MIN):
        t = t_of(i)
        lab, md, h = labels[i], C.mission_day(t), hours(t)
        f = drift(md)
        rest = mid(b["hr_rest"]) - 2.0 * f
        circ = 2.5 * math.cos(2 * math.pi * (h - 16) / 24)
        ex_minute = ex_minute + 1 if lab.startswith("exercise") else 0
        if lab == "sleep":
            hr_t = b["hr_rest"][0] + 0.5 - 1.0 * f - 1.0 * math.cos(2 * math.pi * (h - 4) / 24)
        elif lab == "awake_in_bed":
            hr_t = rest - 2
        elif lab == "post_sleep":
            hr_t = rest + 4 + 0.4 * circ
        elif lab == "pre_sleep":
            hr_t = rest + circ
        elif lab == "work":
            hr_t = rest + 6 + circ
        elif lab == "meal":
            hr_t = rest + 8 + circ
        elif lab == "exercise_ared":
            hr_t = rest + 0.45 * (C.HR_MAX[crew_id] - rest) + 8 * max(0.0, math.sin(2 * math.pi * ex_minute / 4))
        else:  # exercise_cevis
            hr_t = rest + 0.65 * (C.HR_MAX[crew_id] - rest)
        hr_s = lag(hr_s, hr_t, 1.5, 3.0)
        out["hr"][i] = hr_s + noise["hr"].step()

        resp_t = {"sleep": resp_s * 0 + mid(b["resp"]) - 1.5, "awake_in_bed": mid(b["resp"]) - 0.5,
                  "work": mid(b["resp"]) + 1, "meal": mid(b["resp"]) + 1.5,
                  "exercise_ared": 22.0, "exercise_cevis": 26.0}.get(lab, mid(b["resp"]))
        resp_s = lag(resp_s, resp_t, 1.0, 2.0)
        out["resp"][i] = resp_s + noise["resp"].step()

        spo2 = mid(b["spo2"]) + 0.1 - (0.8 if lab == "sleep" else 0.3 if lab.startswith("exercise") else 0.0)
        out["spo2"][i] = min(100.0, spo2 + noise["spo2"].step())

        core_ex = lag(core_ex, 0.4 if lab.startswith("exercise") else 0.0, 15, 25)
        core = mid(b["temp_c"]) + 0.15 * f + 0.25 * math.cos(2 * math.pi * (h - 18) / 24) + core_ex
        out["core"][i] = core + noise["core"].step()

        skin_sleep = lag(skin_sleep, 0.9 if lab in ("sleep", "awake_in_bed") else 0.0, 30, 30)
        skin = (33.4 + C.SKIN_OFFSET[crew_id] + skin_sleep + 0.2 * math.cos(2 * math.pi * (h - 20) / 24)
                + (0.2 if lab.startswith("exercise") else 0.0))
        out["skin"][i] = skin + noise["skin"].step()

        out["act"][i] = ACT_BASE[lab] * math.exp(r.gauss(0, 0.35))

        bp_t = bp_s * 0 + mid(b["bp_sys"]) - 4 * f + 3 * math.cos(2 * math.pi * (h - 10) / 24) + {
            "sleep": -10, "awake_in_bed": -6, "work": 3, "exercise_ared": 30, "exercise_cevis": 18}.get(lab, 0)
        bp_s = lag(bp_s, bp_t, 2.0, 3.0)
        out["bp"][i] = bp_s + noise["bp"].step()

        sq = SQ_BASE[lab] + noise["sq"].step() + (r.gauss(0, 0.05) if lab.startswith("exercise") else 0.0)
        if lab.startswith("exercise") and r.random() < 0.02:
            sq = r.uniform(0.45, 0.58)  # motion artifact, normal during exercise
        out["sq"][i] = min(0.99, max(0.0, sq))
    return out


# ---- suit clock -------------------------------------------------------------
def sensor_time(crew_id, t):
    """What the suit's own clock says at true time t. The suit syncs once a day at 00:00,
    keeping a fixed offset, and drifts in between."""
    elapsed = (t - t.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds()
    off = C.SUIT_CLOCK_OFFSET_S[crew_id] + C.SUIT_CLOCK_DRIFT_PPM[crew_id] * 1e-6 * elapsed
    return t + timedelta(seconds=off)


# ---- PPG-DaLiA texture --------------------------------------------------------
def _segment(subject, label):
    starts = []
    for line in (C.RAW_PPG / f"{subject}_activity.csv").read_text().splitlines():
        name, _, sec = line.lstrip("# ").partition(",")
        if name.strip() != "SUBJECT_ID" and sec.strip():
            starts.append((name.strip(), int(float(sec))))
    for (name, s0), (_, s1) in zip(starts, starts[1:]):
        if name == label:
            return s0, s1
    raise ValueError(f"{subject} has no {label} segment")


def _highpass(values, width=60):
    half, out = width // 2, []
    prefix = [0.0]
    for v in values:
        prefix.append(prefix[-1] + v)
    for i in range(len(values)):
        a, b = max(0, i - half), min(len(values), i + half + 1)
        out.append(values[i] - (prefix[b] - prefix[a]) / (b - a))
    return out


def ppg_texture(subject):
    """Second-by-second variation (mean removed) from a volunteer's calm sitting segment:
    heart rate (1 Hz) and wrist skin temperature (4 Hz, taken every 4th sample)."""
    s0, s1 = _segment(subject, "BASELINE")
    hr = [float(x) for x in (C.RAW_PPG / f"{subject}_HR.csv").read_text().split()[2:]]
    tmp = [float(x) for x in (C.RAW_PPG / f"{subject}_TEMP.csv").read_text().split()[2:]]
    hr_seg = hr[max(0, s0 - 10):s1 - 10]          # HR.csv starts 10 s after the session start
    tmp_seg = tmp[s0 * 4:s1 * 4:4]
    return _highpass(hr_seg), _highpass(tmp_seg)


# ---- days before the minute data (daily resolution only) -------------------------
def pre_window_daily(seed, crew_id, last_md):
    """Daily summary rows for mission days 1..last_md (simulated, daily resolution).
    The point is to show the slow drift; values come from the same baselines."""
    b = C.BASELINES[crew_id]
    rows = []
    for md in range(1, last_md + 1):
        r = rng(seed, "daily", crew_id, md)
        f = drift(md)
        rows.append({
            "crew_id": crew_id, "date": C.md_date(md).isoformat(), "mission_day": md,
            "hr_rest_bpm": float(round(mid(b["hr_rest"]) + 4 - 2 * f - 1.0 + r.gauss(0, 1.5))),
            "bp_sys_mmhg": float(round(mid(b["bp_sys"]) - 4 * f + r.gauss(0, 3))),
            "bp_dia_mmhg": float(round(mid(b["bp_dia"]) + r.gauss(0, 2.5))),
            "spo2_pct": float(round(min(99.0, mid(b["spo2"]) + r.gauss(0, 0.5)))),
            "core_temp_c": round(mid(b["temp_c"]) + 0.15 * f - 0.24 + r.gauss(0, 0.07), 2),
            "skin_temp_c": round(33.85 + C.SKIN_OFFSET[crew_id] + r.gauss(0, 0.2), 2),
            "resp_rpm": float(round(mid(b["resp"]) + r.gauss(0, 0.7))),
            "sleep_h": round(min(7.9, max(5.8, r.gauss(mid(b["sleep_h"]) - 0.3 * f, 0.35))), 1),
            "sleep_h_suit": None,
            "mood": r.choices([3, 4, 5], [0.3, 0.5, 0.2])[0],
            "pvt_ms": int(round(b["pvt_ms"] * (1 + r.gauss(0, 0.04)))),
            "dose_msv_day": station_doses(seed)[0][md],
            "symptoms": [], "resolution": "daily", "simulated": True, "provenance": "sim:daily",
        })
    return rows


_DOSES = {}


def station_doses(seed):
    """Station dose in mSv a day: (days before the window, days in the window, clean build).

    In the window the day-to-day shape is the real EDA RR-1 total (mGy a day), scaled so
    day 158 is the contract's 0.51 mSv. That's a scaling, not a unit conversion, and it
    is labelled simulated. Days before the window are scaled so that the anomalous build
    (with the AN07 SEP day at 2.4 mSv) reaches the contract's 81.0 mSv on day 158."""
    if seed in _DOSES:
        return _DOSES[seed]
    rad = load_eda_radiation()
    first = C.mission_day(C.START)
    last = C.mission_day(C.DEMO_NOW)
    totals = [row["total"] for row in rad[: last - first + 1]]
    window = {first + k: round(C.DOSE_MEAN_MSV_DAY * v / totals[-1], 3) for k, v in enumerate(totals)}
    an07_md = C.mission_day(next(a for a in C.ANOMALIES if a["id"] == "AN07")["start"])
    window_anom_sum = sum(window.values()) - window[an07_md] + 2.4
    raw = {md: max(0.3, rng(seed, "dose", md).gauss(C.DOSE_MEAN_MSV_DAY, 0.03)) for md in range(1, first)}
    k = (C.DOSE_MISSION_AT_DEMO - window_anom_sum) / sum(raw.values())
    pre = {md: round(v * k, 3) for md, v in raw.items()}
    # put the rounding remainder on day 1 so the sum is exact
    pre[1] = round(pre[1] + (C.DOSE_MISSION_AT_DEMO - window_anom_sum - sum(pre.values())), 3)
    _DOSES[seed] = (pre, window)
    return _DOSES[seed]


def load_eda_telemetry():
    import json
    return json.loads((C.RAW_EDA / "rr1_telemetry.json").read_text())


def load_eda_radiation():
    import json
    return json.loads((C.RAW_EDA / "rr1_radiation.json").read_text())


__all__ = ["N_MIN", "t_of", "idx", "build_schedule", "simulate", "sensor_time", "ppg_texture",
           "pre_window_daily", "suit_sleep_hours", "read_csv"]
