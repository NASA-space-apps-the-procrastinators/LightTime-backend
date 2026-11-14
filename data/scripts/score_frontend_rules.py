"""Score a build against the frontend's Scoring table (backend-api-contract.md), as a
yardstick for what the backend should catch once it applies those rules. This is an
evaluation tool working on the CSVs; it is not backend code and is not called by it.

python data/scripts/score_frontend_rules.py --build anomalous

Assumptions, written down because the contract leaves them open:
- Continuous rules (SpO2, core temp, resp, signal) need 5 consecutive minute samples with
  a clean signal, the same hold the backend uses.
- resp WATCH is checked at rest only (not during exercise). "With a symptom" means that
  day's or the next day's check-in lists a symptom.
- Daily rules use daily_summary.csv (morning rest values and the check-in). The band
  WATCH rules for SpO2 and temperature are read on the daily morning value, like the
  contract's `today` object; the absolute ALERT lines (SpO2 < 94, temp > 38.0) are continuous.
- A sensor fault counts as caught only by a RECHECK.
- Cabin CO2 needs 2 consecutive 5-min samples.
"""
import argparse
from collections import Counter, defaultdict
from datetime import timedelta

import config as C
from util import fnum, read_csv

HOLD = 5


def episodes(rows, test, key="sensor_ts", hold=HOLD, gap=timedelta(minutes=10)):
    """Start times of runs where test(row) holds for `hold` rows in a row."""
    out, run, last_end = [], [], None
    for r in rows:
        if test(r):
            run.append(r)
            if len(run) == hold:
                t = C.parse_ts(run[0][key])
                if last_end is None or t - last_end > gap:
                    out.append(t)
            last_end = C.parse_ts(r[key]) if len(run) >= hold else last_end
        else:
            run = []
    return out


def score(build):
    folder = C.OUT_CLEAN if build == "clean" else C.OUT_ANOM
    base = C.BASELINES
    vit = defaultdict(list)
    for r in read_csv(folder / "vitals_1min.csv"):
        vit[r["crew_id"]].append(r)
    daily = [r for r in read_csv(folder / "daily_summary.csv") if int(r["mission_day"]) >= C.mission_day(C.START)]
    symptom_days = {(r["crew_id"], r["date"]) for r in daily if r["symptoms"]}
    events = []  # (state, metric, crew, habitat, time, granularity)

    def has_symptom(cid, t):
        d0 = t.date()
        return any((cid, (d0 + timedelta(days=k)).isoformat()) in symptom_days for k in (0, 1))

    for cid, rows in vit.items():
        ok = [r for r in rows if r["signal_ok"] == "true"]
        for t in episodes(ok, lambda r: r["spo2_pct"] and float(r["spo2_pct"]) < 94):
            events.append(("ALERT", "spo2", cid, "", t, "minute"))
        for t in episodes(ok, lambda r: r["core_temp_c"] and float(r["core_temp_c"]) > 38.0):
            events.append(("ALERT", "temp_c", cid, "", t, "minute"))
        rest = [r for r in ok if not r["activity_label"].startswith("exercise")]
        for t in episodes(rest, lambda r: r["resp_rpm"] and float(r["resp_rpm"]) > 20):
            events.append(("ALERT" if has_symptom(cid, t) else "WATCH", "resp", cid, "", t, "minute"))
        for t in episodes(rows, lambda r: float(r["signal_quality"]) < 0.6, hold=1):
            events.append(("RECHECK", "signal", cid, "", t, "minute"))
    for cid in C.CREW_IDS:
        days = [r for r in daily if r["crew_id"] == cid]
        b = base[cid]
        runs = Counter()
        for r in days:
            t = C.parse_ts(r["date"] + "T06:30:00Z")
            sym = bool(r["symptoms"])
            for metric, col, band in (("hr_rest", "hr_rest_bpm", b["hr_rest"]), ("bp_sys", "bp_sys_mmhg", b["bp_sys"]),
                                      ("bp_dia", "bp_dia_mmhg", b["bp_dia"])):
                v = fnum(r[col])
                out = v is not None and not band[0] <= v <= band[1]
                runs[metric] = runs[metric] + 1 if out else 0
                if out:
                    events.append(("ALERT" if runs[metric] >= 3 or sym else "WATCH", metric, cid, "", t, "day"))
            v = fnum(r["spo2_pct"])
            if v is not None and 94 <= v < b["spo2"][0]:
                events.append(("WATCH", "spo2", cid, "", t, "day"))
            v = fnum(r["core_temp_c"])
            if v is not None and b["temp_c"][1] < v <= 38.0:
                events.append(("WATCH", "temp_c", cid, "", t, "day"))
            s = fnum(r["sleep_h"])
            low = s is not None and (s < b["sleep_h"][0] or s < 6.5)
            runs["sleep_h"] = runs["sleep_h"] + 1 if low else 0
            if low:
                events.append(("ALERT" if sym or runs["sleep_h"] >= 3 else "WATCH", "sleep_h", cid, "", t, "day"))
            m = fnum(r["mood"])
            if m is not None and m <= 2:
                events.append(("ALERT" if sym else "WATCH", "mood", cid, "", t, "day"))
            p = fnum(r["pvt_ms"])
            if p is not None and p > b["pvt_ms"] * 1.15:
                events.append(("ALERT" if sym else "WATCH", "pvt_ms", cid, "", t, "day"))
            d = fnum(r["dose_msv_day"])
            if d is not None and d > 2:
                events.append(("ALERT", "dose_mSv_day", cid, "", t, "day"))
    cab = defaultdict(list)
    for r in read_csv(folder / "cabin_env.csv"):
        cab[r["habitat_id"]].append(r)
    for hab, rows in cab.items():
        for t in episodes(rows, lambda r: float(r["co2_mmhg"]) > 4.5, key="ts", hold=2, gap=timedelta(hours=1)):
            events.append(("ALERT", "co2_mmHg", "", hab, t, "minute"))
        for t in episodes(rows, lambda r: 2.8 <= float(r["co2_mmhg"]) <= 4.5, key="ts", hold=2, gap=timedelta(hours=1)):
            events.append(("WATCH", "co2_mmHg", "", hab, t, "minute"))
    for s in read_csv(folder / "sos_events.csv"):
        events.append(("SOS", "sos", s["crew_id"], "", C.parse_ts(s["sensor_ts"]), "minute"))
    for w in read_csv(folder / "space_weather_events.csv"):
        events.append((w["state"], "space_weather", "", "", C.parse_ts(w["event_time"]), "minute"))
    return events


def match(build, events):
    truth = [a for a in read_csv(C.OUT_TRUTH / "anomalies.csv") if a["kind"] != "negative_control"]
    if build == "clean":
        truth = []
    hits, unmatched = defaultdict(list), []
    for ev in events:
        state, metric, cid, hab, t, gran = ev
        found = False
        for a in truth:
            s, e = C.parse_ts(a["start"]), C.parse_ts(a["end"])
            lo = s - (timedelta(hours=7) if gran == "day" else timedelta(minutes=1))
            hi = e + (timedelta(days=1, hours=7) if gran == "day" else timedelta(minutes=15))
            if not lo <= t <= hi or (a["type"] == "spike" and not C.near_spike(t)):
                continue
            if a["crew_member"] and cid and a["crew_member"] != cid:
                continue
            if a["habitat_id"] and hab and hab != a["habitat_id"]:
                continue
            if a["habitat_id"] and cid and cid not in ("C3", "C4"):
                continue
            if a["kind"] == "sensor_fault":
                ok = metric == "signal"
            else:
                ok = metric in a["metrics"].split("|")
            if ok:
                hits[a["id"]].append(ev)
                found = True
        if not found:
            unmatched.append(ev)
    return truth, hits, unmatched


def report(build):
    events = score(build)
    truth, hits, unmatched = match(build, events)
    order = ["RECHECK", "WATCH", "ALERT", "SOS"]
    lines = [f"# Frontend scoring rules on the {build} build", "",
             "The contract's Scoring table applied to the data by `score_frontend_rules.py` (not by the backend). "
             "The assumptions are at the top of the script.", ""]
    if truth:
        lines += ["| id | type | expected | rules gave | verdict |", "| --- | --- | --- | --- | --- |"]
        caught = 0
        for a in truth:
            hs = hits.get(a["id"], [])
            top = max((h[0] for h in hs), key=order.index) if hs else "none"
            want = a["expected_alert"]
            if want == "none":
                verdict = "ok" if not hs else "flagged"
            elif hs and order.index(top) >= order.index(want if want in order else "RECHECK"):
                verdict, caught = "caught", caught + 1
            elif hs:
                verdict = f"partly ({top})"
            else:
                verdict = "MISSED"
            lines.append(f"| {a['id']} | {a['type']} | {want} | {top} | {verdict} |")
        lines += ["", f"Caught {caught} of {sum(1 for a in truth if a['expected_alert'] != 'none')}.", ""]
    c = Counter((ev[0], ev[1]) for ev in unmatched)
    lines += ["## Flags with no anomaly behind them", "", "| state | metric | count |", "| --- | --- | --- |"]
    lines += [f"| {s} | {m} | {n} |" for (s, m), n in sorted(c.items(), key=lambda x: (-order.index(x[0][0]), -x[1]))]
    lines.append("")
    (C.OUT_REPORTS / f"frontend_rules_{build}.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--build", choices=["clean", "anomalous"], required=True)
    report(p.parse_args().build)
