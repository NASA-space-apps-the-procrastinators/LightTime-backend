"""Replay a build through the real backend, in-process, and score it against
ground_truth/anomalies.csv. No backend code is changed: the harness only calls the
public HTTP routes through Flask's test client, the way tests/conftest.py does.

    .venv/Scripts/python data/scripts/replay.py --build anomalous
    .venv/Scripts/python data/scripts/replay.py --build clean

Writes processed/reports/replay_<build>.md and replay_alerts_<build>.csv.
"""
import argparse
import sys
import time
from bisect import bisect_right
from collections import Counter, defaultdict
from datetime import timedelta

import config as C
from util import read_csv, write_csv

sys.path.insert(0, str(C.REPO))

CLEAR_AFTER = timedelta(minutes=10)   # data-time in range before the harness clears an alert
GRACE = timedelta(minutes=15)         # detection may come up to 15 min after an anomaly ends
VITAL_OF = {"hr": "heart_rate", "spo2": "spo2", "bp_sys": "bp_sys", "sos": "manual", "hr_rest": "heart_rate"}
LEVELS = ["none", "advisory", "caution", "warning", "emergency"]


def load_stream(build):
    folder = C.OUT_CLEAN if build == "clean" else C.OUT_ANOM
    windows = defaultdict(list)
    for cid, a, b in C.HZ_WINDOWS:
        windows[cid].append((a, b))

    def in_hz(cid, t):
        return any(a <= t < b for a, b in windows[cid])

    events = []
    for r in read_csv(folder / "vitals_1min.csv"):
        t = C.parse_ts(r["sensor_ts"])
        if not in_hz(r["crew_id"], t.replace(microsecond=0) - timedelta(seconds=t.second)):
            events.append((C.parse_ts(r["gateway_ts"]), "reading", r))
    for r in read_csv(folder / "vitals_1hz_demo.csv"):
        events.append((C.parse_ts(r["gateway_ts"]), "reading", r))
    for k in read_csv(folder / "checkins.csv"):
        t = C.parse_ts(k["completed_at"])
        if t <= C.DEMO_NOW:
            events.append((t, "checkin", k))
    for s in read_csv(folder / "sos_events.csv"):
        events.append((C.parse_ts(s["gateway_ts"]), "sos", s))
    last = None
    for w in read_csv(C.OUT_REF / "link_windows.csv"):
        if w["stop"] != last:
            events.append((C.parse_ts(w["start"]), "dial", w))
            last = w["stop"]
    order = {"dial": 0, "checkin": 1, "sos": 2, "reading": 3}
    events.sort(key=lambda e: (e[0], order[e[1]]))
    return events


def make_app():
    import requests
    from app import create_app
    from common import lighttime
    from common.models import Crew, db

    def offline(day):
        raise requests.ConnectionError("replay does not use the network")
    lighttime.fetch = offline
    lighttime._cache.clear()
    app = create_app("sqlite:///:memory:")
    app.config["TESTING"] = True
    with app.app_context():
        # Replay database only: name the backend's crew rows after our crew, and add C4.
        for c in C.CREW:
            row = db.session.get(Crew, c["backend_id"])
            if row is None:
                db.session.add(Crew(id=c["backend_id"], name=c["name"], role="cmo" if c["is_cmo"] else "crew"))
            else:
                row.name, row.role = c["name"], "cmo" if c["is_cmo"] else "crew"
        db.session.commit()
    return app


KEEP_READINGS = 4000


def prune(app):
    """Scratch-database upkeep, not a backend change: drop all but the newest readings.
    The backend only ever looks back 5 readings (sustained check) or 30 (a report), so
    the rules behave the same; without this each query slows as the table grows."""
    from common.models import Reading, db
    with app.app_context():
        top = db.session.query(db.func.max(Reading.id)).scalar() or 0
        Reading.query.filter(Reading.id < top - KEEP_READINGS).delete()
        db.session.commit()


def fnum(v):
    return None if v in ("", None) else float(v)


def replay(build, limit=None):
    from base_station import rules
    app = make_app()
    client = app.test_client()
    crew_of = {c["crew_id"]: c["backend_id"] for c in C.CREW}
    cid_of = {v: k for k, v in crew_of.items()}
    alerts = {}            # backend alert id -> record
    open_ = defaultdict(dict)   # crew -> vital -> alert id
    last_bad = {}
    link_log = []
    events = load_stream(build)[:limit]
    t0 = time.time()

    def note_alerts(payloads, ts, row, how):
        for a in payloads:
            rec = alerts.get(a["id"])
            if rec is None:
                rec = alerts[a["id"]] = {
                    "alert_id": a["id"], "crew_id": cid_of[a["crew_id"]], "vital": a["vital"],
                    "first_ts": ts, "first_level": a["level"], "max_level": a["level"], "events": [],
                    "label": row.get("activity_label", how) if row else how,
                    "habitat_id": row.get("habitat_id", "") if row else "",
                    "sample_id": row.get("sample_id", "") if row else "", "provenance": row.get("provenance", "") if row else "",
                    "cleared_ts": None, "reason": a["reason"], "value": a["value"]}
                open_[rec["crew_id"]][a["vital"]] = a["id"]
            if LEVELS.index(a["level"]) > LEVELS.index(rec["max_level"]):
                rec["max_level"] = a["level"]
            rec["events"].append((ts, a["level"], row.get("activity_label", how) if row else how))
            last_bad[a["id"]] = ts

    def clear(aid, ts):
        client.post(f"/api/base/alerts/{aid}/clear", json={"by": "auto: replay"})
        rec = alerts[aid]
        rec["cleared_ts"] = ts
        open_[rec["crew_id"]].pop(rec["vital"], None)

    for k, (ts, kind, r) in enumerate(events):
        if kind == "dial":
            before = client.get("/api/base/outbox").get_json()
            queued = [m for m in before if m["status"] == "queued"]
            resp = client.post("/api/base/dial", json={"stop": r["stop"]}).get_json()
            link_log.append({"ts": ts, "stop": r["stop"], "queued_before": len(queued),
                             "queued_kinds": [(m["kind"], m["priority"], m["payload"].get("alert_id")) for m in queued],
                             "flushed": resp["flushed"]})
            continue
        if kind == "checkin":
            body = {"crew_id": crew_of[r["crew_id"]], "source": "typed", "sleep_hours": fnum(r["sleep_h"]),
                    "mood": fnum(r["mood"]), "bp_sys": fnum(r["cuff_bp_sys_mmhg"]), "bp_dia": fnum(r["cuff_bp_dia_mmhg"])}
            out = client.post("/api/base/readings", json=body).get_json()
            note_alerts(out["alerts"], ts, None, "typed_checkin")
            continue
        if kind == "sos":
            out = client.post("/api/base/sos", json={"crew_id": crew_of[r["crew_id"]]}).get_json()
            note_alerts([out], C.parse_ts(r["sensor_ts"]), None, "sos")
            continue
        cid = r["crew_id"]
        body = {"crew_id": crew_of[cid], "source": "suit", "signal_ok": r["signal_ok"] == "true",
                "heart_rate": fnum(r["hr_bpm"]), "spo2": fnum(r["spo2_pct"]), "skin_temp": fnum(r["skin_temp_c"]),
                "bp_sys": fnum(r["bp_sys_est_mmhg"])}
        st = C.parse_ts(r["sensor_ts"])
        out = client.post("/api/base/readings", json=body).get_json()
        note_alerts(out["alerts"], st, r, "reading")
        # the backend clears a signal alert by itself on the next clean reading
        if body["signal_ok"] and "signal" in open_[cid]:
            alerts[open_[cid].pop("signal")]["cleared_ts"] = st
        for vital, aid in list(open_[cid].items()):
            if vital == "signal":
                continue
            value = body.get(vital)
            if vital in rules.LIMITS["vitals"] and value is not None and body["signal_ok"]:
                if rules.band(vital, value) > 0:
                    last_bad[aid] = st
            if st - last_bad[aid] >= CLEAR_AFTER:
                clear(aid, st)
        if k and k % 10000 == 0:
            prune(app)
        if k and k % 50000 == 0:
            print(f"  {build}: {k}/{len(events)} events, {time.time() - t0:.0f} s", flush=True)
    return alerts, link_log, len(events), time.time() - t0


# ---------------------------------------------------------------- scoring
def anomaly_vitals(a):
    if a["kind"] == "sensor_fault":
        return {"signal"}
    return {VITAL_OF[m] for m in a["metrics"].split("|") if m in VITAL_OF}


BAND_KEY = {"heart_rate": "hr_rest", "bp_sys": "bp_sys", "spo2": "spo2"}


def in_personal_band(rec):
    key = BAND_KEY.get(rec["vital"])
    if key is None or rec.get("value") is None:
        return False
    lo, hi = C.BASELINES[rec["crew_id"]][key]
    return lo <= rec["value"] <= hi


def score(build, alerts):
    truth = read_csv(C.OUT_TRUTH / "anomalies.csv")
    if build == "clean":
        truth = [a for a in truth if a["kind"] == "negative_control"]
    hab_members = defaultdict(set)  # (habitat, minute) -> crew, from the alert rows themselves
    results = {a["id"]: {"anomaly": a, "hits": []} for a in truth}
    unmatched = []
    for rec in alerts.values():
        for ts, level, label in rec["events"]:
            matched = False
            for a in truth:
                if a["kind"] == "negative_control":
                    continue
                s, e = C.parse_ts(a["start"]), C.parse_ts(a["end"])
                if not (s - timedelta(minutes=1) <= ts <= e + GRACE):
                    continue
                if a["type"] == "spike" and not C.near_spike(ts):
                    continue
                who = a["crew_member"]
                if who and who != rec["crew_id"]:
                    continue
                if a["habitat_id"] and rec["habitat_id"] != a["habitat_id"]:
                    continue
                if rec["vital"] not in anomaly_vitals(a):
                    continue
                results[a["id"]]["hits"].append((ts, level, rec["alert_id"]))
                matched = True
            if not matched and (ts, level) == (rec["first_ts"], rec["first_level"]):
                unmatched.append(rec)
    fa = Counter()
    for rec in unmatched:
        in_fault = any(a["kind"] == "sensor_fault" and a["crew_member"] == rec["crew_id"]
                       and C.parse_ts(a["start"]) <= rec["first_ts"] <= C.parse_ts(a["end"]) + GRACE for a in truth)
        if rec["vital"] == "signal":
            cls = "sensor check (signal) outside a fault"
        elif in_fault:
            cls = "medical alarm during a sensor fault"
        elif rec["label"].startswith("exercise") and rec["vital"] in ("heart_rate", "bp_sys"):
            cls = "NC01 exercise HR/BP"
        elif rec["label"] in ("sleep", "awake_in_bed") and rec["vital"] in ("heart_rate", "bp_sys"):
            cls = "NC02 sleeping HR/BP (normal night dip)"
        elif in_personal_band(rec):
            cls = "inside the personal band, outside NEWS2"
        elif rec["label"] == "typed_checkin":
            cls = "typed check-in value"
        else:
            cls = "unexplained"
        rec["false_alarm_class"] = cls
        fa[(cls, rec["crew_id"], rec["vital"], rec["first_level"])] += 1
    return results, unmatched, fa


def clean_alerts():
    """First-raise times of the clean replay, to tell a real catch from an alert that
    would have fired on that day anyway."""
    path = C.OUT_REPORTS / "replay_alerts_clean.csv"
    if not path.exists():
        return None
    out = defaultdict(list)
    for r in read_csv(path):
        out[(r["crew_id"], r["vital"])].append(C.parse_ts(r["first_ts"]))
    return out


def coincident(clean, crew, vital, ts, window=timedelta(minutes=15)):
    return clean is not None and any(abs(t - ts) <= window for t in clean.get((crew, vital), []))


def report(build, alerts, link_log, n_events, secs):
    results, unmatched, fa = score(build, alerts)
    clean = clean_alerts() if build == "anomalous" else None
    lines = [f"# Replay through the backend: {build} build", "",
             f"{n_events} events replayed through the backend in {secs:.0f} s (in-process, SQLite in memory). "
             f"{len(alerts)} alerts raised. The harness clears an alert after {CLEAR_AFTER.seconds // 60} data-minutes "
             "back in range, with `by: \"auto: replay\"` so the backend's 60 s quiet window does not apply.",
             "", "An anomaly counts as caught only if at least one matching alert has no twin (same crew, same vital, "
             "within 15 min) in the clean replay; otherwise the alert would have fired anyway.", ""]
    if build == "anomalous":
        lines += ["## Anomalies", "", "| id | type | expected (correct system) | expected from current backend "
                  "| backend raised | first alert after start | verdict |", "| --- | --- | --- | --- | --- | --- | --- |"]
        caught = missed = 0
        for aid, res in results.items():
            a = res["anomaly"]
            if a["kind"] == "negative_control":
                continue
            hits = sorted(res["hits"])
            real = [h for h in hits if not coincident(clean, alerts[h[2]]["crew_id"], alerts[h[2]]["vital"], h[0])]
            only_coincident = bool(hits) and not real and a["kind"] != "sensor_fault"
            if a["kind"] != "sensor_fault":
                hits = real or hits
            exp = a["expected_backend_level"]
            if hits:
                top = max((h[1] for h in hits), key=LEVELS.index)
                delay = hits[0][0] - C.parse_ts(a["start"])
                first = f"{max(0, int(delay.total_seconds() // 60))} min" if delay.total_seconds() >= 0 else "already open"
            else:
                top, first = "none", ""
            if a["expected_alert"] == "none":
                verdict = "ok (stayed quiet)" if not hits else "FALSE ALARM"
            elif only_coincident:
                verdict = "MISSED (only alerts that also fire on the clean data)"
                missed += 1
            elif hits:
                verdict = "caught" + ("" if LEVELS.index(top) >= LEVELS.index(exp if exp in LEVELS else "none")
                                      else " (lower level than expected)")
                caught += 1
            else:
                verdict = "MISSED: channel not ingested" if exp == "not_ingested" else (
                    "MISSED: within NEWS2 bands" if exp == "none" else "MISSED")
                missed += 1
            lines.append(f"| {aid} | {a['type']} | {a['expected_alert']} | {exp} | {top} | {first} | {verdict} |")
        lines += ["", f"**Caught {caught}, missed {missed}** of the anomalies that should raise something.", ""]
    lines += ["## False alarms (alerts with no anomaly behind them)", "",
              f"Total: **{len(unmatched)}** alerts.", "", "| class | crew | vital | level | count |",
              "| --- | --- | --- | --- | --- |"]
    for (cls, cid, vital, level), n in sorted(fa.items(), key=lambda x: (-x[1], x[0])):
        lines.append(f"| {cls} | {cid} | {vital} | {level} | {n} |")
    by_class = Counter()
    for (cls, *_), n in fa.items():
        by_class[cls] += n
    lines += ["", "By class: " + ", ".join(f"{k} {v}" for k, v in by_class.most_common()), ""]
    lines += ["## Link (Earth outbox)", "", "| data time | dial | queued before | flushed | queued reports (flushed first, priority 0) |",
              "| --- | --- | --- | --- | --- |"]
    for l in link_log:
        def label(k, p, a):
            rec = alerts.get(a)
            who = f"{rec['crew_id']} {rec['vital']} {rec['max_level']} at {C.iso(rec['first_ts'])}" if rec else a
            return f"{k} (priority {p}): {who}"
        items = "; ".join(label(*q) for q in l["queued_kinds"] if q[0] == "report")
        lines.append(f"| {C.iso(l['ts'])} | {l['stop']} | {l['queued_before']} | {l['flushed']} | {items} |")
    lines.append("")
    out = C.OUT_REPORTS / f"replay_{build}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    rows = [{"alert_id": r["alert_id"], "crew_id": r["crew_id"], "vital": r["vital"], "first_ts": C.iso(r["first_ts"]),
             "first_level": r["first_level"], "max_level": r["max_level"], "label": r["label"],
             "cleared_ts": C.iso(r["cleared_ts"]) if r["cleared_ts"] else "",
             "false_alarm_class": r.get("false_alarm_class", ""), "sample_id": r["sample_id"], "reason": r["reason"]}
            for r in alerts.values()]
    write_csv(C.OUT_REPORTS / f"replay_alerts_{build}.csv", list(rows[0].keys()) if rows else ["alert_id"], rows)
    print("\n".join(lines))


def run(build, limit=None):
    alerts, link_log, n, secs = replay(build, limit)
    report(build, alerts, link_log, n, secs)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--build", choices=["clean", "anomalous"], required=True)
    p.add_argument("--limit", type=int, default=None, help="replay only the first N events (smoke test)")
    a = p.parse_args()
    run(a.build, a.limit)
