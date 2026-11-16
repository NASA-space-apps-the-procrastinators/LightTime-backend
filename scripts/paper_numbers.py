"""Every number the concept document and the paper quote, worked out from the code and the data.

    python scripts/paper_numbers.py            about four minutes (the cross-check replays 18 settings)
    python scripts/paper_numbers.py --quick    skips the cross-check

Writes docs/generated/numbers.json (for the Markdown documents) and paper/generated/numbers.tex
(one \\newcommand per number, for the LaTeX paper) and
paper/generated/table_events.tex (one row per low-oxygen recording). Nothing in either document is typed by hand:
if a rule or a dataset changes, run this again and rebuild.
"""
import argparse
import itertools
import json
import pathlib
import statistics
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from base_station import lookahead                                   # noqa: E402
from base_station.rules import LIMITS                                # noqa: E402
from common import lighttime, link, modes                            # noqa: E402
from scripts.build_clean_data import read_uw                         # noqa: E402
from scripts.check_spo2_rules import HIGH, LOW, SETTLE, one_hz, play  # noqa: E402

C_KM_S = 299_792.458             # speed of light, exact by definition (BIPM)
MISSION_DAY = "2026-11-14"
SUBJECTS = range(100001, 100007)


def volunteer(subject):
    text = (ROOT / "data" / "spo2_uw" / f"{subject}.csv").read_text(encoding="utf-8")
    return [row[0] for row in read_uw(text)]


def lead(values):
    sos, warnings = play(values)
    before = [w for w in warnings if w[0] < sos[0]]
    return (sos[0] - before[-1][0], before[-1][1], sos[0]) if before else (None, None, sos[0])


def crosscheck(volunteers, control):
    """Choose the time-left settings on five volunteers, test on the sixth (scripts/crossval_lookahead.py)."""
    saved = lookahead.WINDOW, lookahead.MIN_DROP, lookahead.MIN_AGREEMENT
    table = {}
    for setting in itertools.product((45, 60), (1.5, 2.0, 2.5), (0.4, 0.5, 0.6)):
        lookahead.WINDOW, lookahead.MIN_DROP, lookahead.MIN_AGREEMENT = setting
        table[setting] = (len(play(control)[1]), {s: lead(v)[0] for s, v in volunteers.items()})
    lookahead.WINDOW, lookahead.MIN_DROP, lookahead.MIN_AGREEMENT = saved
    allowed = {k: v[1] for k, v in table.items() if v[0] <= 3}

    def score(leads):
        got = [x for x in leads if x is not None]
        return len(got), statistics.median(got) if got else 0

    held = [allowed[max(allowed, key=lambda k: score([allowed[k][s] for s in volunteers if s != out]))][out]
            for out in volunteers]
    got = [x for x in held if x is not None]
    # Added for the paper (lane W-B): how many settings passed the control-night gate, and how many of the
    # held-out rounds chose the setting the ship runs today.
    chosen = [max(allowed, key=lambda k: score([allowed[k][s] for s in volunteers if s != out])) for out in volunteers]
    return {"heldout_warned": len(got), "heldout_median_lead_s": statistics.median(got) if got else 0,
            "grid_size": len(table),
            "grid_allowed": len(allowed),
            "heldout_rounds": len(chosen),
            "heldout_rounds_ship_setting": sum(c == saved for c in chosen)}


def paper_extras(volunteers, rows):
    """Numbers added for the paper (lane W-B). Each is read from the code or worked out from the recordings."""
    from base_station import usual                                 # noqa: E402
    from scripts.crossval_lookahead import GRID, MAX_FALSE         # noqa: E402
    bands = {level: limit for limit, level in LIMITS["vitals"]["spo2"]["bands"] if limit}
    x = {
        "spo2_caution": bands[1], "spo2_warning": bands[2], "spo2_emergency": bands[3],
        "quiet_s": LIMITS["quiet_s"],
        "window_pairs": lookahead.WINDOW * (lookahead.WINDOW - 1) // 2,
        "now_median_n": 5,                     # base_station/lookahead.py: statistics.median(values[-5:])
        "usual_min_readings": usual.MIN_READINGS, "usual_refresh_s": usual.REFRESH_S,
        "usual_hours": 24,                     # base_station/usual.py: timedelta(hours=24)
        "usual_low_pct": 1, "usual_high_pct": 99,   # base_station/usual.py: len(values) // 100 from each end
        "grid_window_short": min(g[0] for g in GRID), "grid_window_long": max(g[0] for g in GRID),
        "grid_drop_low": min(g[1] for g in GRID), "grid_drop_high": max(g[1] for g in GRID),
        "grid_agree_low": min(g[2] for g in GRID), "grid_agree_high": max(g[2] for g in GRID),
        "grid_max_control_warnings": MAX_FALSE,
        "uw_minutes_min": round(min(len(v) for v in volunteers.values()) / 60),
        "uw_minutes_max": round(max(len(v) for v in volunteers.values()) / 60),
    }
    # How far the stated time left was from the lead the ship actually had (Table 2, last two columns).
    errors = [predicted - gap for gap, predicted, _ in rows.values() if gap is not None]
    x["uw_pred_abs_err_median_s"] = statistics.median(abs(e) for e in errors)
    x["uw_pred_abs_err_max_s"] = max(abs(e) for e in errors)
    x["uw_pred_short_n"] = sum(e < 0 for e in errors)          # stated less time than there was
    x["uw_pred_long_n"] = sum(e > 0 for e in errors)           # stated more time than there was
    x["uw_pred_long_max_s"] = max([e for e in errors if e > 0], default=0)
    # Was a fixed band already held when the counted trend warning came? And did any trend warning come before
    # the first caution band (the band rule alone, five clean readings in a row at or below 95)?
    from base_station.rules import band                            # noqa: E402
    from scripts.check_spo2_rules import HOLD                      # noqa: E402
    normal, earlier = 0, 0
    for subject, values in volunteers.items():
        gap, _, sos_at = rows[subject]
        if gap is None:
            continue
        at = sos_at - gap
        normal += band("spo2", statistics.median(values[at - 4:at + 1])) == 0
        caution = next(t for t in range(HOLD - 1, len(values))
                       if all(LOW <= v <= HIGH and band("spo2", v) >= 1 for v in values[t - HOLD + 1:t + 1]))
        first_trend = min(t for t, _ in play(values)[1])
        earlier += first_trend < caution
    x["uw_warn_normal_band_n"] = normal
    x["uw_trend_before_caution_n"] = earlier
    # The sleep apnoea night (scripts/check_spo2_rules.py, last block): fast falls the trend rule cannot see.
    patient = one_hz("a01r")
    sos, warnings = play(patient)
    lookback = 120
    leads = [s - max(t for t, _ in warnings if s - lookback <= t < s)
             for s in sos if any(s - lookback <= t < s for t, _ in warnings)]
    x["apnea_hours"] = round(sum(LOW <= v <= HIGH for v in patient) / 3600, 1)
    x["apnea_sos_n"] = len(sos)
    x["apnea_warned_first_n"] = len(leads)
    x["apnea_warned_first_pct"] = round(100 * len(leads) / len(sos))
    x["apnea_median_lead_s"] = statistics.median(leads)
    x["apnea_lookback_s"] = lookback
    # The offline heart-rate adviser (scripts/learn_hr_normal.py).
    x["hr_people"] = len(list((ROOT / "data" / "clean" / "wrist").glob("S*.csv")))
    x["hr_sustain_s"] = 60                     # scripts/learn_hr_normal.py: SUSTAIN_S
    x["hr_gate_min_per_h"] = 1                 # scripts/learn_hr_normal.py: the gate in main()
    x["hr_limit_percentile"] = 99.9            # scripts/learn_hr_normal.py: gaps[int(len(gaps) * 0.999)]
    # The test suite (collected, not run: run python -m pytest to see them pass).
    import subprocess                                              # noqa: E402
    out = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider"],
                         cwd=ROOT, capture_output=True, text=True).stdout
    x["test_count"] = int(next(line.split()[0] for line in out.splitlines() if "collected" in line))
    from base_station import recorder                              # noqa: E402
    x["recorder_hours"] = round(recorder.KEEP.total_seconds() / 3600)
    # The five-reading worked example of the time-left rule (scripts/paper_figures.py WORKED, concept document
    # section 5.7), worked out the way base_station/lookahead.py does it: sorted pair slopes, the middle one
    # (index len // 2), the median of the last five readings as the level, then (level - red line) / -slope.
    worked = [97.0, 96.8, 96.5, 96.4, 96.0]
    for name, value in zip(("one", "two", "three", "four", "five"), worked):
        x[f"worked_reading_{name}"] = value
    pairs = sorted((worked[j] - worked[i]) / (j - i) for i in range(len(worked)) for j in range(i + 1, len(worked)))
    slope = pairs[len(pairs) // 2]
    level = statistics.median(worked[-5:])
    x["worked_n"] = len(worked)
    x["worked_pairs"] = len(pairs)
    x["worked_slope"] = slope
    x["worked_agreement"] = (sum(p < 0 for p in pairs) - sum(p > 0 for p in pairs)) / len(pairs)
    x["worked_level"] = level
    x["worked_gap"] = round(level - bands[3], 10)
    x["worked_time_left_s"] = round((level - bands[3]) / -slope, 10)
    x["worked_drop"] = round(-slope * (len(worked) - 1), 10)
    return x


def main(quick):
    mars = lighttime.FALLBACK_S[MISSION_DAY]
    n = {
        "speed_of_light_km_s": C_KM_S,
        "mission_day": MISSION_DAY,
        "mars_one_way_s": mars,
        "mars_round_trip_s": round(2 * mars, 2),
        "mars_distance_million_km": round(mars * C_KM_S / 1e6, 1),
        "mars_plays_as_s": round(link.SPEEDUP and mars / link.SPEEDUP, 2),
        "moon_one_way_s": modes.FIXED_DELAY_S["moon"],
        "station_one_way_s": modes.FIXED_DELAY_S["station"],
        "crew_first_at_s": modes.CREW_FIRST_AT_S,
        "speedup": link.SPEEDUP,
        "sustain_n": LIMITS["sustain_n"],
        "settle_n": LIMITS["settle_n"],
        "plausible_spo2_low": LOW,
        "plausible_spo2_high": HIGH,
        "spo2_bands": {str(level): limit for limit, level in LIMITS["vitals"]["spo2"]["bands"] if limit},
        "window_n": lookahead.WINDOW,
        "min_readings": lookahead.MIN_READINGS,
        "min_drop": lookahead.MIN_DROP,
        "min_agreement": lookahead.MIN_AGREEMENT,
        "horizon_s": lookahead.HORIZON_S,
    }
    control = one_hz("c01r")
    n["control_hours"] = round(sum(LOW <= v <= HIGH for v in control) / 3600, 1)
    n["control_false_sos_raw"] = len(play(control, reject=False, settle=0, trend=False)[0])
    n["control_false_sos_reject"] = len(play(control, settle=0, trend=False)[0])
    sos, warnings = play(control)
    n["control_false_sos_settle"] = len(sos)
    n["control_trend_warnings"] = len(warnings)

    volunteers = {s: volunteer(s) for s in SUBJECTS}
    rows = {s: lead(v) for s, v in volunteers.items()}
    table = ["% Written by scripts/paper_numbers.py. Do not edit by hand.",
             "\\begin{tabular}{@{}lrrrr@{}}\\toprule",
             "Recording & Warning (s) & SOS (s) & Lead (s) & Predicted left (s)\\\\ \\midrule"]
    for subject, (gap, predicted, sos_at) in rows.items():
        cells = [str(sos_at - gap), str(sos_at), str(gap), str(predicted)] if gap is not None else ["none", str(sos_at), "none", "none"]
        table.append(f"{subject} & " + " & ".join(cells) + " \\\\")
    table.append("\\bottomrule\\end{tabular}")
    leads = sorted((r[0] for r in rows.values() if r[0] is not None), reverse=True)
    n["uw_events"] = len(rows)
    n["uw_warned"] = len(leads)
    n["uw_leads_s"] = leads
    n["uw_median_lead_s"] = statistics.median(leads)
    n["uw_min_lead_s"], n["uw_max_lead_s"] = min(leads), max(leads)

    hr = json.loads((ROOT / "base_station" / "hr_normal.json").read_text(encoding="utf-8"))
    n["hr_limit_bpm"] = hr["limit_bpm"]
    n["hr_worst_flagged_min_per_h"] = hr["worst_flagged_minutes_per_hour"]
    if not quick:
        n.update(crosscheck(volunteers, control))
    n.update(paper_extras(volunteers, rows))

    (ROOT / "docs" / "generated").mkdir(parents=True, exist_ok=True)
    (ROOT / "docs" / "generated" / "numbers.json").write_text(json.dumps(n, indent=2) + "\n", encoding="utf-8")
    macros = ["% Written by scripts/paper_numbers.py. Do not edit by hand."]
    for key, value in n.items():
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            words = key.replace("spo2", "spo two").replace("_", " ").split()
            name = "num" + "".join(word.capitalize() for word in words)      # mars_one_way_s -> numMarsOneWayS
            text = f"{value:.1f}" if key.startswith("worked_reading") else f"{value:.10g}"
            macros.append(f"\\newcommand{{\\{name}}}{{{text}}}")
    (ROOT / "paper" / "generated").mkdir(parents=True, exist_ok=True)
    (ROOT / "paper" / "generated" / "numbers.tex").write_text("\n".join(macros) + "\n", encoding="utf-8")
    (ROOT / "paper" / "generated" / "table_events.tex").write_text("\n".join(table) + "\n", encoding="utf-8")
    print(json.dumps(n, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true")
    main(parser.parse_args().quick)
