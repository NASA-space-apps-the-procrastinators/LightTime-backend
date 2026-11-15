"""The evidence figure for the pitch. Run from the repo root: python scripts/make_figures.py"""
import pathlib
import sys

import matplotlib.pyplot as plt

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.build_clean_data import read_uw            # noqa: E402
from scripts.check_spo2_rules import one_hz, play       # noqa: E402

BLUE, ORANGE, RED, GREY = "#0072B2", "#E69F00", "#D55E00", "#666666"      # Okabe-Ito, safe for colour blindness
plt.rcParams.update({"font.family": "sans-serif", "font.size": 11, "axes.spines.top": False,
                     "axes.spines.right": False})


def volunteer(subject):
    return [row[0] for row in read_uw((ROOT / "data" / "spo2_uw" / f"{subject}.csv").read_text(encoding="utf-8"))]


if __name__ == "__main__":
    fig, (trace, leads, false) = plt.subplots(1, 3, figsize=(13, 3.8), gridspec_kw={"width_ratios": [2.2, 1.3, 1.4]})

    values = volunteer(100001)
    sos, warnings = play(values)
    warned = [t for t, _ in warnings if t < sos[0]][-1]
    trace.plot(range(len(values)), values, color=BLUE, linewidth=1.5)
    trace.axhline(91, color=RED, linestyle="--", linewidth=1)
    trace.axvline(warned, color=ORANGE, linewidth=2)
    trace.axvline(sos[0], color=RED, linewidth=2)
    trace.text(warned - 8, 70, "ship warns", color=ORANGE, ha="right")
    trace.text(sos[0] + 8, 70, "SOS rule", color=RED)
    trace.set(xlim=(60, 500), ylim=(66, 100), xlabel="Time (s)", ylabel="Blood oxygen (%)",
              title=f"A  One recorded fall: warned {sos[0] - warned} s early")

    names, ahead = [], []
    for subject in range(100001, 100007):
        sos, warnings = play(volunteer(subject))
        names.append(str(subject)[-1])
        ahead.append(sos[0] - [t for t, _ in warnings if t < sos[0]][-1])
    leads.bar(names, ahead, color=ORANGE)
    for x, y in zip(names, ahead):
        leads.text(x, y + 3, str(y), ha="center")
    leads.set(xlabel="Volunteer", ylabel="Warning before the SOS (s)", title="B  All six volunteers")

    control = one_hz("c01r")
    counts = [len(play(control, reject=False, settle=0, trend=False)[0]),
              len(play(control, settle=0, trend=False)[0]), len(play(control, trend=False)[0])]
    labels = ["every number\nbelieved", "impossible\nnumbers out", "and 10 s\nto settle"]
    false.bar(labels, counts, color=[GREY, GREY, BLUE])
    for x, y in zip(labels, counts):
        false.text(x, y + 0.08, str(y), ha="center")
    false.set(ylabel="False SOS in 7.8 hours", title="C  A healthy sleeper")
    false.tick_params(axis="x", labelsize=9)             # three two-line labels side by side

    fig.tight_layout()
    out = ROOT / "docs" / "figures"
    out.mkdir(parents=True, exist_ok=True)
    fig.savefig(out / "lighttime_evidence.png", dpi=300)
    fig.savefig(out / "lighttime_evidence.pdf")
    print("saved", out / "lighttime_evidence.png")
