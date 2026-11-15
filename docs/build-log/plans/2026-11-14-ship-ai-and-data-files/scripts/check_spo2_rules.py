"""Check the blood-oxygen rules on real recordings. Run from the repo root:

    python scripts/check_spo2_rules.py

It plays each recording, one reading a second, through the same band table, settle time and
trend code the ship uses, and prints what would have been raised. Takes about a minute.
"""
import csv
import pathlib
import statistics
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from base_station import lookahead                # noqa: E402
from base_station.rules import LIMITS, band       # noqa: E402
from scripts.build_clean_data import read_uw      # noqa: E402

RED_LINE = LIMITS["vitals"]["spo2"]["bands"][0][0]
LOW, HIGH = LIMITS["plausible"]["spo2"]
HOLD, SETTLE = LIMITS["sustain_n"], LIMITS["settle_n"]


def play(values, reject=True, settle=SETTLE, trend=True):
    """Returns (the second each SOS started, [(second, predicted seconds left)] for each trend warning)."""
    clean_values, last, since_bad, in_sos, last_warning, sos, warnings = [], [], settle + 1, False, -999, [], []
    for t, value in enumerate(values):
        clean = LOW <= value <= HIGH or not reject
        since_bad = since_bad + 1 if clean else 0
        last = (last + [(value, clean)])[-HOLD:]
        if not clean:
            continue
        clean_values = (clean_values + [value])[-lookahead.WINDOW:]
        if since_bad <= settle:
            continue
        emergency = len(last) == HOLD and all(ok and band("spo2", v) == 3 for v, ok in last)
        if emergency and not in_sos:
            sos.append(t)
        in_sos = emergency or (in_sos and band("spo2", value) == 3)
        look = lookahead.falling(clean_values, RED_LINE) if trend and not emergency else None
        if look:
            if t - last_warning > 60:
                warnings.append((t, look["eta_s"]))
            last_warning = t
    return sos, warnings


def one_hz(name):
    with open(ROOT / "data" / "spo2_apnea_ecg" / f"{name}_SpO2_1Hz.csv", newline="") as f:
        return [float(r["SpO2_pct"]) for r in csv.DictReader(f)]


if __name__ == "__main__":
    control = one_hz("c01r")
    hours = sum(LOW <= v <= HIGH for v in control) / 3600
    print(f"Control sleeper (Apnea-ECG c01r), {hours:.1f} hours of readings, nothing wrong with them:")
    print(f"  false SOS, every number believed:            {len(play(control, reject=False, settle=0, trend=False)[0])}")
    print(f"  false SOS, impossible numbers rejected:      {len(play(control, settle=0, trend=False)[0])}")
    sos, warnings = play(control)
    print(f"  false SOS, and {SETTLE} s to settle after a dropout: {len(sos)}")
    print(f"  falling-trend warnings:                      {len(warnings)} (at seconds {[t for t, _ in warnings]})")

    print("\nSix healthy volunteers breathing low-oxygen gas (UW, Masimo oximeter):")
    print("  volunteer  warning at  SOS at  warning ahead by  ship predicted")
    leads = []
    for subject in range(100001, 100007):
        values = [row[0] for row in read_uw((ROOT / "data" / "spo2_uw" / f"{subject}.csv").read_text(encoding="utf-8"))]
        sos, warnings = play(values)
        before = [w for w in warnings if w[0] < sos[0]]
        if before:
            at, predicted = before[-1]
            leads.append(sos[0] - at)
            print(f"  {subject}     {at:5d} s  {sos[0]:4d} s       {sos[0] - at:5d} s        {predicted:5d} s")
        else:
            print(f"  {subject}        none  {sos[0]:4d} s")
    print(f"  warned before the SOS: {len(leads)} of 6, median {statistics.median(leads):g} s ahead")

    patient = one_hz("a01r")
    sos, warnings = play(patient)
    leads = [s - max(t for t, _ in warnings if s - 120 <= t < s) for s in sos if any(s - 120 <= t < s for t, _ in warnings)]
    print(f"\nSleep apnoea patient (Apnea-ECG a01r), fast falls: {len(sos)} SOS, "
          f"trend warning came first in {len(leads)} ({100 * len(leads) / len(sos):.0f}%), median {statistics.median(leads):g} s ahead")
