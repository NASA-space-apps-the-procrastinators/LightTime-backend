"""Step 4: check every output CSV against schema.py, the keys across files, the
raw-file hashes, the clean/anomalous difference, the contract's demo numbers, and the
frontend coverage map. Writes processed/reports/validation.txt and coverage.md.
Exits 1 if anything fails.

python data/scripts/validate.py
"""
import re
import sys
from collections import defaultdict
from datetime import timedelta

import config as C
from schema import TABLES, columns
from util import fnum, read_csv, sha256

TS_RE = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(\.\d{3})?Z$")
DATE_RE = re.compile(r"^\d{4}-\d\d-\d\d$")
MANIFEST = C.DATA / "raw_manifest.csv"
fails, notes = [], []


def fail(msg):
    fails.append(msg)


def raw_files():
    return sorted([p for p in C.RAW_PPG.iterdir() if p.is_file()] + [p for p in C.RAW_EDA.iterdir() if p.is_file()])


def check_manifest(write=False):
    current = {p.relative_to(C.DATA).as_posix(): (sha256(p), p.stat().st_size) for p in raw_files()}
    if write or not MANIFEST.exists():
        with open(MANIFEST, "w", encoding="utf-8", newline="\n") as f:
            f.write("path,sha256,bytes\n")
            for k, (h, n) in current.items():
                f.write(f"{k},{h},{n}\n")
        notes.append(f"raw manifest written: {len(current)} files")
        return
    saved = {r["path"]: r["sha256"] for r in read_csv(MANIFEST)}
    for k, h in saved.items():
        if k not in current:
            fail(f"raw file missing: {k}")
        elif current[k][0] != h:
            fail(f"raw file changed: {k}")
    for k in current:
        if k not in saved:
            fail(f"raw file not in manifest: {k}")
    notes.append(f"raw manifest: {len(saved)} files unchanged" if not fails else "raw manifest: see failures")


def parse(typ, v):
    if typ == "int":
        return int(v)
    if typ == "float":
        return float(v)
    if typ == "bool":
        if v not in ("true", "false"):
            raise ValueError(v)
        return v == "true"
    if typ == "ts":
        if not TS_RE.match(v):
            raise ValueError(v)
        return C.parse_ts(v)
    if typ == "date":
        if not DATE_RE.match(v):
            raise ValueError(v)
        return v
    return v


def path_of(table, build):
    folder = TABLES[table]["folder"]
    base = {"reference": C.OUT_REF, "ground_truth": C.OUT_TRUTH}.get(folder)
    return (base or (C.OUT_CLEAN if build == "clean" else C.OUT_ANOM)) / f"{table}.csv"


def check_table(table, build, cache):
    spec = TABLES[table]
    p = path_of(table, build)
    if not p.exists():
        fail(f"{build}/{table}: file missing")
        return []
    rows = read_csv(p)
    with open(p, encoding="utf-8") as f:
        header = f.readline().strip().split(",")
    if header != columns(table):
        fail(f"{build}/{table}: header {header} != schema")
    bad = defaultdict(int)
    for r in rows:
        fault = "fault:" in r.get("provenance", "")
        for c in spec["cols"]:
            v = r.get(c["name"], "")
            if v == "":
                if c["required"]:
                    bad[f"required {c['name']} empty"] += 1
                continue
            if c["type"] == "list":
                continue
            try:
                x = parse(c["type"], v)
            except ValueError:
                bad[f"{c['name']} not {c['type']}"] += 1
                continue
            if c["type"] in ("int", "float") and not fault:
                if (c["min"] is not None and x < c["min"]) or (c["max"] is not None and x > c["max"]):
                    bad[f"{c['name']} out of range [{c['min']},{c['max']}]"] += 1
    for k, n in bad.items():
        fail(f"{build}/{table}: {k} in {n} rows")
    keys = [tuple(r[k] for k in spec["pk"]) for r in rows]
    if len(keys) != len(set(keys)):
        fail(f"{build}/{table}: primary key {spec['pk']} not unique")
    cache[(table, build)] = rows
    return rows


def check_fks(build, cache):
    for table, spec in TABLES.items():
        rows = cache.get((table, build))
        if rows is None:
            continue
        for col, (ref, refcol) in spec["fk"].items():
            target = cache.get((ref, build)) or cache.get((ref, "clean"))
            have = {r[refcol] for r in target}
            missing = {r[col] for r in rows if r[col] and r[col] not in have}
            if missing:
                fail(f"{build}/{table}.{col} -> {ref}.{refcol}: {len(missing)} unknown, e.g. {sorted(missing)[:3]}")


def check_series(build, cache):
    for table in ("vitals_1min", "vitals_1hz_demo"):
        last, worst = {}, timedelta(0)
        for r in cache[(table, build)]:
            s, g = C.parse_ts(r["sensor_ts"]), C.parse_ts(r["gateway_ts"])
            key = (r["crew_id"], r["sample_id"][3])
            if key in last and s <= last[key] and table == "vitals_1min":
                fail(f"{build}/{table}: sensor_ts not increasing for {r['crew_id']} at {r['sample_id']}")
                break
            last[key] = s
            lag = g - s
            if lag < timedelta(seconds=-2) or lag > timedelta(minutes=15):
                fail(f"{build}/{table}: gateway-sensor gap {lag} at {r['sample_id']}")
                break
            worst = max(worst, lag)
        notes.append(f"{build}/{table}: largest gateway lag {worst}")
    wins = cache[("link_windows", "clean")]
    for a, b in zip(wins, wins[1:]):
        if a["end"] != b["start"]:
            fail(f"link_windows: {a['window_id']} end != {b['window_id']} start")
    if wins[0]["start"] != C.iso(C.START) or wins[-1]["end"] != C.iso(C.DEMO_NOW):
        fail("link_windows do not cover the data span")


def windows_for(row, anomalies, ts_key, span=timedelta(0)):
    """True if the row's time [t, t + span] overlaps an anomaly window for its crew or habitat."""
    t = C.parse_ts(row[ts_key])
    for a in anomalies:
        if a["kind"] == "negative_control":
            continue
        s, e = C.parse_ts(a["start"]), C.parse_ts(a["end"])
        if not (s - timedelta(minutes=1) <= t + span and t < e + timedelta(minutes=1)):
            continue
        crew_ok = not a["crew_member"] or row.get("crew_id") == a["crew_member"]
        hab_ok = not a["habitat_id"] or row.get("habitat_id") == a["habitat_id"]
        if crew_ok and hab_ok:
            return True
    return False


def check_diff(cache):
    anomalies = cache[("anomalies", "clean")]
    for table, key, ts_key, skip in [("vitals_1min", "sample_id", "sensor_ts", {"provenance"}),
                                     ("vitals_1hz_demo", "sample_id", "sensor_ts", {"provenance"}),
                                     ("cabin_env", "ts", "ts", {"provenance"}),
                                     ("radiation_daily", "date", "date", {"provenance", "dose_msv_mission"})]:
        clean = {r[key] + r.get("habitat_id", ""): r for r in cache[(table, "clean")]}
        changed = outside = 0
        for r in cache[(table, "anomalous")]:
            c = clean.get(r[key] + r.get("habitat_id", ""))
            if c is None:
                fail(f"diff {table}: row {r[key]} only in anomalous")
                continue
            if any(r[k] != c[k] for k in r if k not in skip):
                changed += 1
                rr, span = dict(r), timedelta(0)
                if table == "radiation_daily":
                    rr["date"], span = r["date"] + "T00:00:00Z", timedelta(days=1)
                if not windows_for(rr, anomalies, ts_key, span):
                    outside += 1
        if outside:
            fail(f"diff {table}: {outside} changed rows fall outside every anomaly window")
        notes.append(f"diff {table}: {changed} rows changed, all inside anomaly windows" if not outside else "")


def check_clean_quiet(cache):
    """The clean build must not trip a frontend ALERT rule on drift alone."""
    base = {(r["crew_id"], r["metric"]): r for r in cache[("baselines", "clean")]}
    for cid in C.CREW_IDS:
        lo, hi = float(base[(cid, "hr_rest")]["low"]), float(base[(cid, "hr_rest")]["high"])
        run = worst = 0
        for r in cache[("daily_summary", "clean")]:
            if r["crew_id"] != cid or not r["hr_rest_bpm"]:
                continue
            out = not lo <= float(r["hr_rest_bpm"]) <= hi
            run = run + 1 if out else 0
            worst = max(worst, run)
        if worst >= 3:
            fail(f"clean: {cid} hr_rest out of band {worst} days running (drift would ALERT)")
        notes.append(f"clean: {cid} longest hr_rest run out of band = {worst} day(s)")
    lowest = min(float(r["spo2_pct"]) for r in cache[("vitals_1min", "clean")] if r["spo2_pct"])
    hottest = max(float(r["core_temp_c"]) for r in cache[("vitals_1min", "clean")] if r["core_temp_c"])
    if lowest < 94:
        fail(f"clean: SpO2 reaches {lowest}")
    if hottest > 38.0:
        fail(f"clean: core temp reaches {hottest}")
    notes.append(f"clean: lowest SpO2 {lowest}, highest core temp {hottest}")


def check_demo(cache):
    """The anomalous build is the demo build: it must match backend-api-contract.md."""
    d = {(r["crew_id"], r["date"]): r for r in cache[("daily_summary", "anomalous")]}
    c1 = d[("C1", "2026-11-14")]
    expect = {"hr_rest_bpm": 84, "spo2_pct": 97, "core_temp_c": 37.2, "resp_rpm": 17, "sleep_h": 5.1,
              "dose_msv_day": 0.51}
    for k, v in expect.items():
        if abs(float(c1[k]) - v) > 1e-6:
            fail(f"demo: C1 today {k} = {c1[k]}, contract says {v}")
    for day, v in (("2026-11-12", 80), ("2026-11-13", 82)):
        if float(d[("C1", day)]["hr_rest_bpm"]) != v:
            fail(f"demo: C1 hr_rest on {day} = {d[('C1', day)]['hr_rest_bpm']}, want {v}")
    rad = {r["date"]: r for r in cache[("radiation_daily", "anomalous")]}
    if abs(float(rad["2026-11-14"]["dose_msv_mission"]) - 81.0) > 1e-6:
        fail(f"demo: dose_mSv_mission {rad['2026-11-14']['dose_msv_mission']} != 81.0")
    a1 = next(a for a in cache[("alerts_seed", "anomalous")] if a["alert_id"] == "A1")
    if (a1["stage"], a1["raised_at"], a1["value"]) != ("raised", "2026-11-14T06:12:00Z", "84.00"):
        fail(f"demo: A1 is {a1['stage']} at {a1['raised_at']} value {a1['value']}")
    done = defaultdict(set)
    for k in cache[("checkins", "anomalous")]:
        if C.parse_ts(k["completed_at"]) <= C.DEMO_NOW:
            done[k["date"]].add(k["crew_id"])
    today = done["2026-11-14"]
    if today != {"C2", "C3", "C4"}:
        fail(f"demo: done today {sorted(today)}, contract says C2, C3, C4")
    streak, md = 0, 157
    while len(done[C.md_date(md).isoformat()]) == 4:
        streak, md = streak + 1, md - 1
    if streak != 12:
        fail(f"demo: crew streak {streak}, contract says 12")
    sw = cache[("space_weather_events", "anomalous")]
    if not any(r["event_time"] == "2026-11-14T05:58:00Z" for r in sw):
        fail("demo: no SEP event at 2026-11-14T05:58:00Z")
    last = max(r["sensor_ts"] for r in cache[("vitals_1min", "anomalous")] if r["crew_id"] == "C1")
    notes.append(f"demo: C1 today matches the contract; streak {streak}; last C1 packet {last}")


# Frontend fields -> (table, column). Anything listed in OUTSTANDING is not data's to supply.
COVERAGE = [
    ("state.mission_day", "mission", "launch_date"), ("state.platform", "mission", "platform"),
    ("state.link_up / delay_s over time", "link_windows", "one_way_delay_s"),
    ("crew.id", "crew", "crew_id"), ("crew.name", "crew", "name"), ("crew.role", "crew", "role"),
    ("crew.suit_id", "crew", "suit_id"), ("crew.baseline.*", "baselines", "low"),
    ("crew.baseline.pvt_ms / vo2max", "baselines", "point"),
    ("crew.today.hr_rest", "daily_summary", "hr_rest_bpm"), ("crew.today.bp", "daily_summary", "bp_sys_mmhg"),
    ("crew.today.spo2", "daily_summary", "spo2_pct"), ("crew.today.temp_c", "daily_summary", "core_temp_c"),
    ("crew.today.resp", "daily_summary", "resp_rpm"), ("crew.today.sleep_h", "daily_summary", "sleep_h"),
    ("crew.today.mood", "daily_summary", "mood"), ("crew.today.pvt_ms", "daily_summary", "pvt_ms"),
    ("crew.today.symptoms", "daily_summary", "symptoms"), ("crew.today.dose_mSv_day", "daily_summary", "dose_msv_day"),
    ("crew.today.dose_mSv_mission", "radiation_daily", "dose_msv_mission"),
    ("crew.last_packet_at", "vitals_1min", "sensor_ts"),
    ("history.days[] (30 days)", "daily_summary", "date"), ("history.band", "baselines", "high"),
    ("packets.*", "packets", "signal_quality"), ("packets.sent_to_ground", "packets", "sent_to_ground"),
    ("stream-health.lowest_signal_quality", "packets", "signal_quality"),
    ("station.co2_mmHg", "cabin_env", "co2_mmhg"), ("station.ppo2_mmHg", "cabin_env", "ppo2_mmhg"),
    ("station.pressure_kPa", "cabin_env", "pressure_kpa"), ("station.temp_c", "cabin_env", "temp_c"),
    ("station.rh_pct", "cabin_env", "rh_pct"), ("station.dose_mSv_today", "radiation_daily", "dose_msv_day"),
    ("station.simulated / source", "cabin_env", "real_fields"),
    ("space-weather.*", "space_weather_events", "headline"), ("thresholds.*", "thresholds", "alert_rule"),
    ("checkins (body)", "checkins", "pvt_ms"), ("checkins/today done, due, streak", "checkins", "completed_at"),
    ("alert A1 and history (stage, rule, symptoms, timeline)", "alerts_seed", "stage"),
    ("alert.steps", None, "base_station/procedures.json (unchanged)"),
    ("thread messages (from, author, sent_at, arrived_at, status)", "messages", "status_at_demo_now"),
    ("reminders", "reminders", "due_at"), ("sos / glove tap", "sos_events", "trigger"),
    ("earth: created_at, sent_at, received (deliver_at)", "messages", "deliver_at"),
    ("earth: sensor-side data age", "vitals_1min", "gateway_ts"),
    ("earth: alert status", "messages", "kind"), ("earth: sync status", "messages", "status_at_demo_now"),
    ("earth: link status over time", "link_windows", "link_up"),
]
OUTSTANDING = [
    ("crew.state, metric_states, note, days_out_of_band, streak, next_badge_at, transmitted_to_ground_today",
     "Derived by the backend at request time from the tables above (API work, not data)."),
    ("thresholds.source text for every metric but hr_rest and co2", "Needs thresholds.json from the frontend repo."),
    ("crew names/roles/baselines for C2-C4", "Draft; replace from crew-seed.json (frontend repo)."),
    ("packet field names", "Checked against the contract only; packet-schema.json not in this repo."),
    ("bp_dia source", "Modelled as a morning cuff in checkins.csv; the contract's check-in body has no BP (F2)."),
    ("space-weather simulated:false", "Our SEP records are injected, so simulated is true (F7)."),
    ("push subscriptions", "Not data."),
]


def coverage():
    lines = ["# Frontend coverage", "", "Generated by validate.py from backend-api-contract.md fields.", "",
             "| Frontend field | Table | Column | Status |", "| --- | --- | --- | --- |"]
    for field, table, col in COVERAGE:
        if table is None:
            status = "covered (existing file)"
        else:
            status = "covered" if col in columns(table) else "MISSING"
            if status == "MISSING":
                fail(f"coverage: {field} -> {table}.{col} not in schema")
        lines.append(f"| {field} | {table or ''} | {col} | {status} |")
    lines += ["", "## Outstanding (not data, or blocked on a file we don't have)", "",
              "| Item | Why |", "| --- | --- |"]
    lines += [f"| {a} | {b} |" for a, b in OUTSTANDING]
    C.OUT_REPORTS.mkdir(parents=True, exist_ok=True)
    (C.OUT_REPORTS / "coverage.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run():
    check_manifest()
    cache = {}
    for table, spec in TABLES.items():
        builds = ["clean", "anomalous"] if spec["folder"] == "series" else ["clean"]
        for b in builds:
            check_table(table, b, cache)
    for table, spec in TABLES.items():
        if spec["folder"] != "series":
            cache[(table, "anomalous")] = cache[(table, "clean")]
    for b in ("clean", "anomalous"):
        check_fks(b, cache)
        check_series(b, cache)
    check_diff(cache)
    check_clean_quiet(cache)
    check_demo(cache)
    coverage()
    rows = {(f"{b}/{t}" if TABLES[t]["folder"] == "series" else f"{TABLES[t]['folder']}/{t}"): len(v)
            for (t, b), v in cache.items() if TABLES[t]["folder"] == "series" or b == "clean"}
    report = ["LIGHT-TIME data validation", "=" * 26, "", "Rows per file:"]
    report += [f"  {k}: {n}" for k, n in sorted(rows.items())]
    report += ["", "Checks:"] + [f"  ok   {n}" for n in notes if n]
    report += [f"  FAIL {f}" for f in fails]
    report += ["", "RESULT: " + ("PASS" if not fails else f"FAIL ({len(fails)})")]
    C.OUT_REPORTS.mkdir(parents=True, exist_ok=True)
    (C.OUT_REPORTS / "validation.txt").write_text("\n".join(report) + "\n", encoding="utf-8")
    print("\n".join(report))
    return not fails


if __name__ == "__main__":
    if "--write-manifest" in sys.argv:
        check_manifest(write=True)
        print("\n".join(notes))
        sys.exit(0)
    sys.exit(0 if run() else 1)
