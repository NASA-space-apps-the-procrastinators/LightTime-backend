# Documentation for submission: overview plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (or subagent-driven-development, one fresh agent per lane) to run this plan and the three plans it points to. Steps use checkbox (`- [ ]`) syntax. Also load: avoid-ai-writing, human-rewrite, verification-before-completion, karpathy-guidelines.

**Goal:** Three documents that agree with the code and with each other, ready for the Space Apps submission at 23:59 on 15 November: a concept document (the idea, the words, the math, a glossary), an academic paper in LaTeX, and a technical documentation set.

**Architecture:** One source for every fact. Numbers come from a script that runs the ship's own rules on the recordings (`scripts/paper_numbers.py`), names come from `data/processed/reference/crew.csv` and `command_center/routes.py`, and every document passes one checker (`scripts/docs_check.py`) before it is called done. The concept document and the technical docs are Markdown in the backend repo, so the submission can link to them; the paper is LaTeX under `paper/`.

**Tech Stack:** Markdown on GitHub, Mermaid (GitHub draws it; `mmdc` renders PNG for PDFs), pandoc with xelatex for PDFs, LaTeX (`article`, natbib, TikZ, pgfplots) built with latexmk, matplotlib with the Okabe-Ito palette.

**The plans:**

| Plan | File | Output | When |
|---|---|---|---|
| This one | `docs/plans/2026-11-15-docs-00-overview.md` | Task 0: the shared scripts | first, about 20 minutes |
| A | `docs/plans/2026-11-15-docs-a-concept.md` | `docs/concept.md` and `docs/concept.pdf` | tonight |
| B | `docs/plans/2026-11-15-docs-b-paper.md` | `paper/main.pdf` | full draft tonight if the lanes allow; public only after the team agrees authorship |
| C | `docs/plans/2026-11-15-docs-c-technical.md` | `README.md`, `docs/index.md`, `docs/tech/*.md`, three new ADRs | tonight |

Everything in Task 0 and in the code steps of A, B and C was run on a copy of the backend at `890fb21` with the repo's own recordings. It produced the numbers quoted below, a two-page PDF with all figures, and a 49-route API reference. It was not run on the commits made after 13:20 (`4636f27` renamed the ground replies, `3c80901` removed the backend tour), so Task 0 Step 1 checks the start state.

---

## What exists, and what happens to it

| File | Words | Becomes |
|---|---|---|
| `docs/how-it-works.md` | 5,119 | Source for concept sections 5 and 6, and paper Methods and Results. Then a three-line pointer to `docs/concept.md`, so old links still work |
| `docs/project-documentation.md` | 3,621 | Idea parts go to the concept document, architecture parts to `docs/tech/architecture.md`. Then a pointer |
| `docs/submission.md` | 2,907 | Kept. Updated in Plan C Task C9 with the corrections below and links to the new documents |
| `docs/deployment.md`, `docs/deployment-commands.md` | 12,489 bytes, 73,683 bytes | Kept. Checked against today's hosting in Plan C |
| `docs/data-sources.md`, `docs/data-verification.md` | 1,277 and about 300 | Merged into `docs/tech/data.md`, then pointers |
| `docs/system.md` | 102 | Replaced by `docs/tech/architecture.md` |
| `docs/hardware.md` | about 450 | Kept, linked from the concept document as the proposed suit |
| `CONTEXT.md` | about 800 | Kept as the developers' word list. The concept glossary must not contradict it |
| The team's Google document (`Nasa_Hackathon_2026_7.docx`, about 20,000 words) | | Source for analogies, prior work, the "say this, not that" table and the resource links. Features it describes that were never built (glove controls, MQTT, FHIR packets, five NASA alert colours, a head-up display) are labelled **proposed** wherever they appear |
| `docs/plans`, `docs/specs`, `docs/reviews`, `docs/handoff` | | Left as written. `docs/index.md` lists them as history |

## Decisions already made

1. **Markdown in the repo is the source** for the concept document and the technical docs, because the submission needs public links and GitHub renders Markdown and Mermaid. PDFs are built from it with pandoc. A Google Docs copy is optional and made last, from the finished Markdown.
2. **No number is typed by hand.** `scripts/paper_numbers.py` writes `docs/generated/numbers.json` and `paper/generated/numbers.tex`. If a document needs a number that the script does not produce, add it to the script first. A result that no script in the repo can reproduce stays out of the paper.
3. **Diagrams are code.** TikZ in the paper, Mermaid in Markdown, matplotlib for anything that plots data. The scientific-schematics skill's AI image generator needs `OPENROUTER_API_KEY`, which is not set, and an AI-drawn picture cannot be checked line by line. It is not used for any figure that carries a number or a claim.
4. **Two tiers.** Tier 1 must be done before 23:59: Plan A, Plan C, and the submission text. Tier 2 is the paper: a full draft tonight if time allows, then team review, then a preprint. Nothing is posted publicly until the team has agreed authors and order.
5. **Plain, human prose.** One writer per document. Every document gets an avoid-ai-writing audit and a human-rewrite cold read. No em dashes. Match the spelling already used in `docs/how-it-works.md`.
6. **Corrections from the mentors' and reviewer's feedback are rules, not suggestions.** They are in the table below and enforced by `scripts/docs_check.py`.

## Words to use

The writers, the critics and `scripts/docs_check.py` all work from this table.

| Say | Not | Why |
|---|---|---|
| crew medical officer (CMO), on board | flight surgeon on board | The flight surgeon is a physician on Earth in mission control; the CMO is a crew member with some medical training, who may or may not be a doctor (reviewer, 15 Nov) |
| flight surgeon, on Earth | doctor on the ship | Same |
| a few dozen hours of medical training | 40 hours | Sources disagree: up to 40 hours in a NASA Johnson interview, about 15 hours of CMO training in a NASA abstract |
| one-way light time; round trip | "the delay" without saying which | The answer takes twice as long as the message |
| 11 minutes one way on our mission date (14 Nov 2026); about 3 to 22 minutes over the years | 11 minutes at closest; 4 to 24 minutes | Our date is not closest approach |
| distance from JPL Horizons divided by the speed of light | the DSN measures the delay | The Deep Space Network carries the signal |
| LIGHTTIME, the ship's rules and statistics | an AI model that decides | No trained model decides; one learned heart-rate adviser exists offline and is not wired in |
| caution, warning, emergency (SOS) | NASA's five alert colours | Five colours were proposed, not built |
| tiers inspired by NEWS2 | NEWS2-validated | NEWS2 is a hospital score, not checked in spaceflight |
| role-based views | secure, login, access control | The screen says who is looking and the ship believes it |
| simulated | real (for the crew month and the story) | Only the test recordings are real, and they are from volunteers on Earth |
| CSA Bio-Monitor, a smart shirt | Bio-Monitor vest | CSA calls it a smart shirt |
| we assume the crew wear the shirt for the whole mission | (unstated) | The reviewer asked for this assumption to be written down |
| the crew's names as in `crew.csv`; the ground names as in `command_center/routes.py` | any name from an older document | Both changed today |

## Lanes

| Lane | Who | Skills to load | Reads | Writes |
|---|---|---|---|---|
| W-A | one writer | engineering:documentation, scientific-writing (for section 5), human-rewrite, avoid-ai-writing | Plan A, the sources it names | `docs/concept.md` |
| W-B | one writer | scientific-writing, bio-research:scientific-problem-selection, scientific-brainstorming, literature-review, citation-management, scientific-visualization | Plan B | `paper/` |
| W-C | one writer | engineering:documentation, searchfit-seo:technical-seo (checklist only) | Plan C | `README.md`, `docs/index.md`, `docs/tech/` |
| K1 accuracy | a critic who did not write the document | (none extra) | the document and the code | a list: each claim it could not trace to a file and line |
| K2 citations | a separate agent | citation-check (search mode) | each reference list and every sentence that cites one | the citation-check report; nothing unverified survives |
| K3 voice | a critic | avoid-ai-writing (detect), human-rewrite (cold read) | finished drafts | marked lines to fix |
| R1 reader | a reader-sim | (none extra) | `docs/concept.md` and `README.md` as a hackathon judge with five minutes; `paper/main.pdf` as a space-medicine reviewer | what they understood, where they stopped, what they doubted |

W-A and W-C can start at the same time once Task 0 is done. W-B starts in parallel but its Tier 2 work yields to A and C if time runs short.

## Gates (a document is done only when all pass)

| Gate | Command or check | Pass |
|---|---|---|
| G1 numbers | `python scripts/paper_numbers.py` | runs; the values match the table in Task 0 Step 4, or the change is explained |
| G2 checker | `python scripts/docs_check.py <files>` | `0 to fix`; every REVIEW line read and either kept as accurate or rewritten |
| G3 accuracy | K1 report | empty, or each item fixed |
| G4 citations | K2 report | every claim Verified or removed |
| G5 voice | K3 report | P0 and P1 items fixed |
| G6 builds | pandoc and latexmk commands in A and B | exit 0, no `??` in the PDF |
| G7 eyes | open each PDF and look at every page and figure | no overlap, no cut-off label, figures readable in grayscale |

## Questions for the team (ask one at a time, only when the plan reaches them)

1. Who are the paper's authors, in what order, and with which affiliations? (Plan B, before anything is posted.)
2. Can both repositories be made public now? The submission's links need it. (Plan C, Task C9.)
3. Which licence goes in the repositories? There is no `LICENSE` file, and a public repo without one is "all rights reserved". (Plan C, Task C8.)
4. Should the concept document also live in the team's Google Drive? (Plan A, last step.)

---

### Task 0: The shared scripts

**Files:**
- Create: `scripts/paper_numbers.py`
- Create: `scripts/paper_figures.py`
- Create: `scripts/docs_check.py`
- Generated (committed): `docs/generated/numbers.json`, `paper/generated/numbers.tex`, `paper/figures/*.pdf|png`, `docs/figures/concept/*.pdf|png`

- [ ] **Step 1: Check the start state**

Run: `git status --short`, `git log --oneline -1`, `python -m pytest -q`
Expected: a clean tree on `Tj-Backend` (untracked docs are fine), and the test count CLAUDE.md gives for the latest work. Write the count down: the technical docs quote it. If tests fail, stop and tell the backend owner.

Also confirm matplotlib is installed: `python -c "import matplotlib"`. If it is not, `pip install matplotlib` (it is a script dependency, not an app dependency; add it to a new `requirements-docs.txt` with that one line).

- [ ] **Step 2: Create `scripts/paper_numbers.py`**

```python
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
    return {"heldout_warned": len(got), "heldout_median_lead_s": statistics.median(got) if got else 0,
            "grid_size": len(table)}


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

    (ROOT / "docs" / "generated").mkdir(parents=True, exist_ok=True)
    (ROOT / "docs" / "generated" / "numbers.json").write_text(json.dumps(n, indent=2) + "\n", encoding="utf-8")
    macros = ["% Written by scripts/paper_numbers.py. Do not edit by hand."]
    for key, value in n.items():
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            words = key.replace("spo2", "spo two").replace("_", " ").split()
            name = "num" + "".join(word.capitalize() for word in words)      # mars_one_way_s -> numMarsOneWayS
            macros.append(f"\\newcommand{{\\{name}}}{{{value:.10g}}}")
    (ROOT / "paper" / "generated").mkdir(parents=True, exist_ok=True)
    (ROOT / "paper" / "generated" / "numbers.tex").write_text("\n".join(macros) + "\n", encoding="utf-8")
    (ROOT / "paper" / "generated" / "table_events.tex").write_text("\n".join(table) + "\n", encoding="utf-8")
    print(json.dumps(n, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true")
    main(parser.parse_args().quick)
```

- [ ] **Step 3: Create `scripts/paper_figures.py`**

```python
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
plt.rcParams.update({"font.family": "sans-serif", "font.size": 9, "axes.spines.top": False,
                     "axes.spines.right": False, "savefig.bbox": "tight"})
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
    fig, ax = plt.subplots(figsize=(6.6, 2.4))
    ax.plot(range(len(values)), values, color=BLUE, lw=1, label="blood oxygen, 1 reading a second")
    ax.axhline(RED_LINE, color=VERM, ls="--", lw=1, label=f"red line ({RED_LINE}%)")
    start, slope = at - len(window) + 1, look["per_min"] / 60      # the fitted line passes through (now, at)
    xs = [start, at + look["eta_s"]]
    ax.plot(xs, [look["now"] + slope * (x - at) for x in xs], color=ORANGE, lw=1.5,
            label=f"line fitted at the warning: {look['eta_s']} s left")
    ax.axvline(at, color=ORANGE, lw=1)
    ax.axvline(sos[0], color=VERM, lw=1)
    ax.text(at, ax.get_ylim()[1], " warning", color=ORANGE, va="top", fontsize=7)
    ax.text(sos[0], ax.get_ylim()[1], " SOS", color=VERM, va="top", fontsize=7)
    ax.set(xlabel="seconds into the recording", ylabel="%", xlim=(max(0, at - 240), sos[0] + 120))
    ax.legend(frameon=False, fontsize=7, loc="lower left")
    save(fig, "timeleft_event")
    return {"subject": subject, "warning_at": at, "sos_at": sos[0], "eta_s": look["eta_s"]}


def leads_and_false():
    numbers = json.loads((ROOT / "docs" / "generated" / "numbers.json").read_text(encoding="utf-8"))
    fig, ax = plt.subplots(figsize=(3.2, 2.4))
    ax.bar(range(1, 7), numbers["uw_leads_s"], color=BLUE)
    ax.axhline(numbers["uw_median_lead_s"], color=GREY, ls=":", lw=1)
    ax.set(xlabel="recording (sorted)", ylabel="warned ahead of SOS (s)", title="Six low-oxygen recordings")
    save(fig, "lead_times")
    stages = ["all\nbelieved", "impossible\nremoved", f"+{SETTLE} s\nsettle"]
    counts = [numbers["control_false_sos_raw"], numbers["control_false_sos_reject"], numbers["control_false_sos_settle"]]
    fig, ax = plt.subplots(figsize=(3.2, 2.4))
    ax.bar(stages, counts, color=[GREY, ORANGE, GREEN])
    for x, c in enumerate(counts):
        ax.text(x, c, str(c), ha="center", va="bottom")
    ax.set(ylabel=f"false SOS in {numbers['control_hours']} h", title="A healthy night")
    save(fig, "false_sos")
    return {"leads": numbers["uw_leads_s"], "false": counts}


if __name__ == "__main__":
    print(json.dumps({"worked": worked(), "event": event(), "summary": leads_and_false()}, indent=2))
    assert one_hz  # the control recording loader is shared with scripts/check_spo2_rules.py
```

- [ ] **Step 4: Run both and compare**

Run: `python scripts/paper_numbers.py` (about two minutes), then `python scripts/paper_figures.py`
Expected, from the run on `890fb21`:

| Key | Value |
|---|---|
| `mars_one_way_s`, `mars_round_trip_s` | 660.86, 1321.72 |
| `mars_distance_million_km` | 198.1 |
| `mars_plays_as_s` | 11.01 |
| `crew_first_at_s`, `speedup` | 300, 60 |
| `sustain_n`, `settle_n`, plausible range | 5, 10, 50 to 100 |
| `spo2_bands` | caution 95, warning 93, emergency 91 |
| `window_n`, `min_readings`, `min_drop`, `min_agreement`, `horizon_s` | 60, 15, 2.0, 0.5, 600 |
| `control_hours`, false SOS raw, rejected, settled, trend warnings | 7.8, 4, 1, 0, 2 |
| `uw_warned` of `uw_events`, `uw_leads_s`, median | 6 of 6; 159, 106, 98, 96, 68, 14; 97 |
| `heldout_warned`, `heldout_median_lead_s`, `grid_size` | 6, 97, 18 |
| `hr_limit_bpm`, `hr_worst_flagged_min_per_h` | 72.9, 0.39 |

`paper_figures.py` prints the worked example (median slope −0.25 % a second, agreement 1.0, now 96.5, time left 22.0 s) and the event (recording 100001: warning at 162 s, SOS at 321 s, 142 s predicted). If any value differs, the code changed since `890fb21`: find out why before writing a word.

- [ ] **Step 5: Create `scripts/docs_check.py`**

```python
"""Check the written documents before they are submitted. Run from the repo root:

    python scripts/docs_check.py                      README.md, docs/*.md, docs/tech/*.md, paper/sections/*.tex
    python scripts/docs_check.py docs/concept.md      one or more files

FAIL lines must be fixed. REVIEW lines are claims a mentor corrected on 15 November: read the
sentence and keep it only if it says what the note says. Exit code 1 if anything FAILs.
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT = ["README.md", "docs/*.md", "docs/tech/*.md", "paper/sections/*.tex"]

FAIL = [
    ("\u2014", "em dash: use a comma, a period, parentheses or a new sentence"),
    (" \u2013 ", "en dash used as a dash: rewrite the sentence"),
    (r"Okafor|Rodenburg|Rebecca Qi|Adeyemi|Lindqvist|Mensah|\bSato\b",
     "old crew name: use the names in data/processed/reference/crew.csv and command_center/routes.py"),
    (r"11 min\w*[^.]{0,20}\bclosest", "11 minutes is our mission date, not Mars at its closest (3 to 22 min one way)"),
    (r"\b(4|four) to 24 min", "Mars one-way light time is about 3 to 22 minutes"),
    (r"bio-?monitor\W+vest", "the CSA Bio-Monitor is a smart shirt, not a vest"),
    (r"\bDSN\b[^.]{0,40}\b(measur|calculat|comput|monitor)\w*[^.]{0,30}\b(time|delay)",
     "the delay comes from JPL Horizons distance divided by the speed of light; the DSN carries the signal"),
    (r"\b(first|only)\b[^.]{0,30}\bhealth monitor", "novelty claim the background check does not support"),
    (r"(?<!no )(?<!trained )(?<!learned )\b(AI|model|LIGHTTIME)\s+(decides|diagnoses|prescribes)\b",
     "no model decides: rules decide, people act"),
]
REVIEW = [
    (r"\b40[ -]hours?\b", "sources disagree on CMO training hours (up to 40 in one NASA interview, about 15 in a NASA abstract)"),
    (r"\bsecure\b|\bsecurity\b", "role-based views are not a login; say what is and is not protected"),
    (r"NEWS2[^.]{0,60}\b(valid|proven|approved)", "NEWS2 is a hospital score, not validated in spaceflight"),
    (r"flight surgeon[^.]{0,60}\b(on board|onboard|aboard)\b|\b(on board|onboard|aboard)\b[^.]{0,60}flight surgeon",
     "the flight surgeon is on Earth; on board it is the crew medical officer"),
    (r"\bmachine learning\b|\bneural\b|\bdeep learning\b", "describe LIGHTTIME as rules and statistics; learned models only advise, offline"),
    (r"\bcontinuous(ly)?\b[^.]{0,40}\b(monitor|wear|stream)", "pair continuous monitoring with the stated assumption that the crew wear the shirt"),
]
LINK = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")


def files(args):
    patterns = args or DEFAULT
    found = []
    for pattern in patterns:
        found += sorted(ROOT.glob(pattern)) if any(ch in pattern for ch in "*?[") else [ROOT / pattern]
    return [path for path in found if path.is_file()]


def broken_links(path, text):
    for target in LINK.findall(text):
        if re.match(r"(https?|mailto):|#", target):
            continue
        local = (path.parent / target.split("#")[0]).resolve()
        if not local.exists():
            yield target


def main(args):
    failed = 0
    for path in files(args):
        text = path.read_text(encoding="utf-8")
        name = path.relative_to(ROOT).as_posix()
        for number, line in enumerate(text.splitlines(), 1):
            if line.lstrip().startswith(("http", "|  http")):
                continue
            for pattern, note in FAIL:
                if re.search(pattern, line, flags=re.IGNORECASE):
                    print(f"FAIL   {name}:{number}: {note}")
                    failed += 1
            for pattern, note in REVIEW:
                if re.search(pattern, line, flags=re.IGNORECASE):
                    print(f"REVIEW {name}:{number}: {note}")
        for target in broken_links(path, text):
            print(f"FAIL   {name}: broken link {target}")
            failed += 1
    print(f"{failed} to fix")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

- [ ] **Step 6: Run the checker on today's documents**

Run: `python scripts/docs_check.py`
Expected: it runs and lists findings. On the copy it found no em dashes and no old names, five REVIEW lines about machine learning wording, and one about NEWS2 in `README.md`. Broken image links reported on the copy were only missing files in the copy; on the real repo, any broken link it reports is real.

- [ ] **Step 7: Commit**

```bash
git add scripts/paper_numbers.py scripts/paper_figures.py scripts/docs_check.py docs/generated paper/generated paper/figures docs/figures/concept
git commit -m "docs: one script for every number, one for the data figures, one checker for the written documents"
```

Add one line to `AI_USE.md` in its own format: today, the backend owner, Claude, "documentation plans and the scripts behind them".
