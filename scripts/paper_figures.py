"""Data figures for the concept document and the paper, drawn from the same code and recordings.

    python scripts/paper_figures.py

Writes PDF (for LaTeX) and PNG (for Markdown) into paper/figures/ and docs/figures/concept/:
  timeleft_worked   the five-reading Theil-Sen example from the concept document, by hand
  timeleft_event    one real low-oxygen recording: the warning, the SOS and the line the ship fitted
  lead_times        how far ahead of the SOS each of the six recordings was warned
  false_sos         false SOS on a healthy night as each trust rule is added
Okabe-Ito colours, so the figures read for colour-blind readers and in grayscale.
"""
import itertools
import json
import pathlib
import statistics
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from base_station import lookahead                                   # noqa: E402
from scripts.check_spo2_rules import RED_LINE, SETTLE, one_hz, play  # noqa: E402
from scripts.paper_numbers import volunteer                          # noqa: E402

BLUE, ORANGE, VERM, GREEN, GREY = "#0072B2", "#E69F00", "#D55E00", "#009E73", "#666666"
# Drawn at the size they are printed in the paper (one column is about 3.4 in), so 7 pt here is 7 pt on paper.
plt.rcParams.update({"font.family": "sans-serif", "font.size": 7, "axes.titlesize": 7, "axes.labelsize": 7,
                     "xtick.labelsize": 6.5, "ytick.labelsize": 6.5, "legend.fontsize": 6.5,
                     "axes.spines.top": False, "axes.spines.right": False, "savefig.bbox": "tight"})
WORKED = [97.0, 96.8, 96.5, 96.4, 96.0]          # the readings used in the concept document, section 5.7
OUT = [ROOT / "paper" / "figures", ROOT / "docs" / "figures" / "concept"]


def save(fig, name):
    for folder in OUT:
        folder.mkdir(parents=True, exist_ok=True)
        fig.savefig(folder / f"{name}.pdf")
        fig.savefig(folder / f"{name}.png", dpi=200)
    plt.close(fig)


def theil_sen(values):
    """The same arithmetic as base_station/lookahead.falling, without its minimum-length gate."""
    slopes = sorted((values[j] - values[i]) / (j - i) for i, j in itertools.combinations(range(len(values)), 2))
    agreement = (sum(s < 0 for s in slopes) - sum(s > 0 for s in slopes)) / len(slopes)
    return slopes, slopes[len(slopes) // 2], agreement


def worked():
    slopes, slope, agreement = theil_sen(WORKED)
    now = statistics.median(WORKED[-5:])
    eta = (now - RED_LINE) / -slope
    fig, (a, b) = plt.subplots(1, 2, figsize=(6.6, 2.4), gridspec_kw={"width_ratios": [1.3, 1]})
    a.plot(range(5), WORKED, "o", color=BLUE, label="readings")
    a.plot([0, 4], [WORKED[0], WORKED[0] + 4 * slope], color=VERM, label=f"median slope {slope:g} per s")
    a.set(xlabel="second", ylabel="blood oxygen (%)", title="Five readings")
    a.legend(frameon=False, fontsize=7)
    b.bar(range(len(slopes)), slopes, color=[VERM if s == slope else GREY for s in slopes])
    b.set(xlabel="the 10 pairs, sorted", ylabel="slope (% per s)", title="Every pair's slope")
    save(fig, "timeleft_worked")
    return {"slopes": [round(s, 4) for s in slopes], "median_slope": slope, "agreement": agreement,
            "now": now, "eta_s": round(eta, 1)}


def event(subject=100001):
    values = volunteer(subject)
    sos, warnings = play(values)
    at = [t for t, _ in warnings if t < sos[0]][-1]
    window = values[max(0, at - lookahead.WINDOW + 1):at + 1]
    look = lookahead.falling(window, RED_LINE)
    fig, ax = plt.subplots(figsize=(3.4, 1.8))
    ax.plot(range(len(values)), values, color=BLUE, lw=1, label="SpO$_2$, one reading a second")
    ax.axhline(RED_LINE, color=VERM, ls="--", lw=1, label=f"red line ({RED_LINE}%)")
    start, slope = at - len(window) + 1, look["per_min"] / 60      # the fitted line passes through (now, at)
    xs = [start, at + look["eta_s"]]
    ax.plot(xs, [look["now"] + slope * (x - at) for x in xs], color=ORANGE, lw=1.5,
            label=f"line fitted at the warning: {look['eta_s']} s left")
    ax.axvline(at, ymin=0.4, color=ORANGE, lw=1)        # stop above the legend so no label is crossed
    ax.axvline(sos[0], ymin=0.4, color=VERM, lw=1)
    ax.text(at, ax.get_ylim()[1], " warning", color=ORANGE, va="top")
    ax.text(sos[0], ax.get_ylim()[1], " SOS", color=VERM, va="top")
    ax.set(xlabel="time into the recording (s)", ylabel="SpO$_2$ (%)", xlim=(max(0, at - 240), sos[0] + 120))
    ax.legend(frameon=False, loc="lower left", handlelength=1.5)
    save(fig, "timeleft_event")
    return {"subject": subject, "warning_at": at, "sos_at": sos[0], "eta_s": look["eta_s"]}


def leads_and_false():
    numbers = json.loads((ROOT / "docs" / "generated" / "numbers.json").read_text(encoding="utf-8"))
    fig, ax = plt.subplots(figsize=(1.45, 1.6))
    ax.bar(range(1, len(numbers["uw_leads_s"]) + 1), numbers["uw_leads_s"], color=BLUE)
    ax.axhline(numbers["uw_median_lead_s"], color=GREY, ls=":", lw=1)
    ax.set_xticks(range(1, len(numbers["uw_leads_s"]) + 1))
    ax.set(xlabel="recording (sorted)", ylabel="warned ahead of SOS (s)", title="Low-oxygen recordings")
    save(fig, "lead_times")
    stages = ["none", "range\ncheck", f"+ {SETTLE} s\nsettle"]
    counts = [numbers["control_false_sos_raw"], numbers["control_false_sos_reject"], numbers["control_false_sos_settle"]]
    fig, ax = plt.subplots(figsize=(1.45, 1.6))
    ax.bar(stages, counts, color=[GREY, ORANGE, GREEN])
    for x, c in enumerate(counts):
        ax.text(x, c, str(c), ha="center", va="bottom")
    ax.set_ylim(0, max(counts) * 1.3)
    ax.set(xlabel="trust rules applied", ylabel=f"false SOS in {numbers['control_hours']} h", title="A healthy night")
    save(fig, "false_sos")
    return {"leads": numbers["uw_leads_s"], "false": counts}


if __name__ == "__main__":
    print(json.dumps({"worked": worked(), "event": event(), "summary": leads_and_false()}, indent=2))
    assert one_hz  # the control recording loader is shared with scripts/check_spo2_rules.py
