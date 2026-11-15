# Plan B: the research paper (LaTeX)

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. Run `docs/plans/2026-11-15-docs-00-overview.md` Task 0 first. One writer (lane W-B) writes the whole paper. Load: scientific-writing, bio-research:scientific-problem-selection, scientific-brainstorming, literature-review, citation-management, scientific-visualization, scientific-critical-thinking, avoid-ai-writing, human-rewrite. Lane K2 runs citation-check on the finished draft. This is Tier 2: if Plans A and C are behind at 21:00, stop here and pick up tomorrow.

**Goal:** A short, honest, reproducible paper that describes LIGHT-TIME's decision layer and its check on public recordings, ready for team review tonight and for a preprint once the team agrees authorship.

**Architecture:** `paper/` in the backend repo. `main.tex` holds the preamble and the order; each section is its own file under `paper/sections/`; diagrams are TikZ files under `paper/figures/`; data figures are PDFs from `scripts/paper_figures.py`; every number is a macro from `paper/generated/numbers.tex` and the results table is `paper/generated/table_events.tex`, both from `scripts/paper_numbers.py`.

**Tech Stack:** LaTeX `article`, two columns, natbib with `unsrtnat`, TikZ and pgfplots, latexmk. BibTeX entries fetched by DOI.

**Length:** about 5,000 words, six to eight pages in two columns plus references.

---

## What this paper can claim, and what it cannot

From bio-research:scientific-problem-selection: the question is real (who acts when Earth cannot answer in time), the evidence is small, so the claim must be small.

**It can claim:**

1. A decision layer that sets who acts from the one-way light time, computed from an ephemeris for the mission date, with the threshold stated as a design choice.
2. A time-left estimate (a Theil-Sen slope with an agreement gate) that is compared with the round trip, so the warning says whether Earth can answer before the red line.
3. Trust rules that remove false alarms before any trend is fitted.
4. A replay of public recordings through the same code the ship runs, reported event by event: 6 of 6 low-oxygen events warned before the SOS (median lead 97 s, range 14 to 159 s); false SOS on a healthy 7.8-hour night went from 4 to 1 to 0 as the trust rules were added; the settings chosen without each recording still warned on all six.
5. An open implementation with role-based views and a test suite.

**It must not claim:** clinical validity; accuracy on astronauts; that the autonomy idea is new (NASA's Earth-independent medical operations work, CSA's C2M2 framework and Cypko et al. describe it); that NEWS2 applies in spaceflight; that the views are secure; any number another team or paper produced.

**Objections a reviewer will raise, and where the paper answers them:**

| Objection | Answer in |
|---|---|
| Six events is nothing | Results report every event; Discussion says so first among the limits; no p-values anywhere |
| The settings were tuned on the same six | Methods: leave-one-recording-out choice over 18 settings with at most 3 trend warnings allowed on the control night; Results: held-out outcome |
| Light time is not the whole latency | Discussion: relay scheduling, DSN coverage, conjunction and ground processing add to it; light time is the floor, so the conclusion holds |
| Healthy volunteers breathing low-oxygen gas in a lab are not crew in flight | Discussion, limits |
| 300 s is arbitrary | System: it is a design choice following Rader et al. 2013, and the code makes it one constant |
| The predicted time left differs from the actual lead | Results: show both columns of Table 2; Discussion: the SOS needs five readings in the red, so it lands a few seconds after the line is crossed, and the slope changes as the fall steepens. If the paper quotes a prediction-error figure, add it to `paper_numbers.py` first |
| Continuous monitoring intrudes on privacy | System: role-based views; Discussion: the proportionality point from the mentors, and the assumption that the crew wear the shirt |

**Where it goes:** a preprint first. Recommended arXiv primary category cs.HC (decision support used by people), cross-list eess.SP; first-time submitters may need an endorsement, so check before planning a date. A later venue could be a student paper at the International Astronautical Congress 2027 through the CSA student conference grant; read the IAF call for its dates before planning anything around it.

---

## The outline, section by section

| File | Section | Words | Must contain | Cite (keys from the reference table) |
|---|---|---|---|---|
| `abstract.tex` | Abstract | ≤ 250 | One paragraph, no headings: the problem, what was built, how it was checked, the four headline numbers as macros, the main limit, where the code is | none |
| `introduction.tex` | 1 Introduction | 600 | ISS care is ground-directed in near real time; at Mars light time alone is 3 to 22 minutes one way; NASA lists distance from Earth as a hazard and plans for Earth-independent care; alarm fatigue means more alarms are not the answer; the gap: monitoring software that treats light time as an input and changes who acts. Contributions as four sentences of prose, not a list | hrpDistance, lemery2024eimo, levin2023eimo, drew2014alarm, rader2013delay |
| `related.tex` | 2 Related work | 700 | Autonomy frameworks; onboard decision support; wearables in flight; early warning from wearables; alarm design; operations under delay. Table 1 compares the nearest systems on: who decides changes with distance, store and forward, trend with time left, never decides, open code. Only systems K2 verifies stay in the table | lemery2024eimo, levin2023eimo, the C2M2 and Cypko entries if verified, krihak cdss if verified, csaBioMonitor, mastrandrea2021 if verified, mishra2020, alavi2022, drew2014alarm, gorges2009alarm, rader2013delay |
| `system.tex` | 3 System | 700 | Figure 1 (architecture). The link model: each message stamped with sent, lands, earliest reply; the demo plays legs of a minute or more 60 times faster and keeps the true values. The mode rule and Figure 2. Role-based views (what each role sees; not authentication). Implementation in one paragraph: Flask, Next.js, Cloud Run, the test count from Task 0 Step 1. The crew month is simulated and labelled | giorginiHorizons, bipmSI, rader2013delay |
| `methods.tex` | 4 Methods | 900 | Figure 3 (pipeline). Equations for: trust filters, bands with the sustain count, the usual range, the Theil-Sen slope, the agreement statistic, time left, the Earth-in-time test. Table 3: every parameter, its value as a macro, and its source (limits.json, lookahead.py, modes.py, NEWS2, our choice). Datasets (UW induced hypoxemia, 6 recordings; Apnea-ECG control c01r; PPG-DaLiA, 15 people) with licences. Protocol: replay at one reading a second through the same function the ship uses; outcomes (lead before SOS, false SOS, trend warnings); the leave-one-out choice; the heart-rate adviser's leave-one-person-out check. Statistics: descriptive only | rcp2017news2, theil1950, sen1968, kendall1938, hoffman2022oximetry, penzel2000apnea, physionetApnea, reiss2019ppg, ppgDaliaData |
| `results.tex` | 5 Results | 600 | Table 2 (`generated/table_events`), Figure 4 (one event), Figure 5 (leads; false SOS by stage). The control night: trend warnings. Held-out result. The heart-rate adviser: its limit and worst held-out flagged minutes an hour, and that it is not wired in. Every number a macro | none new |
| `discussion.tex` | 6 Discussion | 800 | What the numbers mean against a 22-minute round trip; design lessons (authority switching, trust before trend, store and forward); limits in order of weight (sample size, lab hypoxemia on Earth, healthy volunteers, tuning, one vital sign for the trend, NEWS2 not validated in space, simulated crew data, light time is only the floor of latency, the 300 s choice, continuous-wear assumption and proportionality, no human-factors study, views are not authentication); ethics (public de-identified data) | hrpDistance, drew2014alarm |
| `conclusion.tex` | 7 Conclusion | 250 | What was shown, at its true size, and what would test it properly: hardware in an analog habitat, an emergency unlock for the person helping, a study with crews in training | none |
| back matter in `main.tex` | Availability; AI use; acknowledgements; author contributions | 250 | Repository links and commit; the dataset links; a plain AI-use statement (which tools, for what, how outputs were checked); acknowledgements that name no mentor without their permission; author contributions only after team question 1 | |

### The references

Fetch each DOI's BibTeX with content negotiation, then tidy keys to the ones below:

```bash
curl -sLH "Accept: application/x-bibtex" https://doi.org/10.1109/CIC.2000.898505 >> paper/refs.bib
```

Web pages and reports without a DOI are `@misc` with `howpublished = {\url{...}}` and `note = {Accessed 15 November 2026}`.

| Key | Identifier | Status |
|---|---|---|
| penzel2000apnea | doi:10.1109/CIC.2000.898505 | verified this morning |
| physionetApnea | doi:10.13026/C23W2R | verified this morning |
| hoffman2022oximetry | doi:10.1038/s41746-022-00665-y; data github.com/ubicomplab/oximetry-phone-cam-data | verified this morning |
| reiss2019ppg | doi:10.3390/s19143079 | verified this morning |
| ppgDaliaData | doi:10.24432/C53890 | verified this morning |
| sen1968 | doi:10.1080/01621459.1968.10480934 | verified this morning |
| theil1950 | Proc. KNAW 53: 386-392, 521-525, 1397-1412 (no DOI) | verified this morning |
| kendall1938 | Biometrika 30(1/2): 81-93 | K2 must confirm the DOI before use |
| rcp2017news2 | rcp.ac.uk NEWS2 page | verified this morning |
| rader2013delay | doi:10.2514/6.2013-3520; NTRS 20130011552 | verified this morning |
| lemery2024eimo | NTRS 20240002454 | verified this morning |
| levin2023eimo | doi:10.1109/OJEMB.2023.3255513 | verified this morning |
| drew2014alarm | doi:10.1371/journal.pone.0110274 | verified this morning |
| gorges2009alarm | doi:10.1213/ane.0b013e31819bdfbb | verified this morning |
| mishra2020 | doi:10.1038/s41551-020-00640-6 | verified this morning |
| alavi2022 | doi:10.1038/s41591-021-01593-2 | verified this morning |
| antonsen2017 | NTRS 20170004604 | verified this morning |
| valinia2022 | NTRS 20220002905 | verified this morning |
| giorginiHorizons | ssd.jpl.nasa.gov/horizons | verified this morning |
| bipmSI | bipm.org SI defining constants | verified this morning |
| hrpDistance | nasa.gov/hrp/hazard-distance-from-earth | verified this morning |
| nasaStd3001v1 | nasa.gov/reference/nasa-std-3001v1 | verified this morning |
| csaBioMonitor | asc-csa.gc.ca/eng/sciences/bio-monitor.asp | verified this afternoon |
| csaDeepSpace2019 | asc-csa.gc.ca Canadian Healthcare in Deep Space | verified this morning |
| mastrandrea2021, C2M2 framework, Cypko et al. 2025, Krihak et al. CDSS concept, NASA and Google CMO-DA, ESA CHIMS, Scott et al. 2023 | from the team document's background check | **not yet verified**: K2 checks each; anything not found is cut from the paper and from Table 1 |

---

### Task B1: The scaffold that compiles

**Files:** Create `paper/main.tex`, `paper/sections/*.tex`, `paper/figures/architecture.tex`, `paper/figures/authority.tex`, `paper/figures/pipeline.tex`, `paper/refs.bib`, `paper/.gitignore`

- [ ] **Step 1: `paper/main.tex`**

```latex
\documentclass[10pt,twocolumn]{article}
\usepackage[margin=0.75in]{geometry}
\usepackage[T1]{fontenc}
\usepackage{lmodern,microtype,amsmath,amssymb,booktabs,graphicx,xcolor}
\usepackage[hidelinks]{hyperref}
\usepackage[numbers,sort&compress]{natbib}
\usepackage{tikz,pgfplots}
\pgfplotsset{compat=1.18}
\usetikzlibrary{arrows.meta,positioning,fit,calc}
% Okabe-Ito colours, safe for colour-blind readers
\definecolor{oiblue}{HTML}{0072B2}\definecolor{oiorange}{HTML}{E69F00}
\definecolor{oiverm}{HTML}{D55E00}\definecolor{oigreen}{HTML}{009E73}\definecolor{oigrey}{HTML}{666666}
\input{generated/numbers}

\title{Who decides when Earth is minutes away?\\ Latency-aware decision support for crew health monitoring}
\author{LIGHT-TIME team\\\small Authors and affiliations to be confirmed by the team before submission}
\date{}

\begin{document}
\maketitle
\input{sections/abstract}
\input{sections/introduction}
\input{sections/related}
\input{sections/system}
\input{sections/methods}
\input{sections/results}
\input{sections/discussion}
\input{sections/conclusion}
\bibliographystyle{unsrtnat}
\bibliography{refs}
\end{document}
```

- [ ] **Step 2: Figure 1, `paper/figures/architecture.tex`**

```latex
% Figure 1. Three layers and the delayed link. Drawn in TikZ so it stays sharp and editable.
\begin{figure*}[t]\centering
\begin{tikzpicture}[font=\small, box/.style={draw, rounded corners=2pt, align=center, minimum height=11mm, inner sep=4pt, text width=30mm},
  arr/.style={-{Latex[length=2mm]}, thick}]
\node[box, fill=oiblue!12] (suit) {\textbf{Suit}\\one reading a second per crew member};
\node[box, fill=oigreen!12, right=12mm of suit, text width=42mm] (ship) {\textbf{Ship computer (LIGHTTIME)}\\trust $\rightarrow$ usual range $\rightarrow$ time left $\rightarrow$ who decides};
\node[box, fill=oiorange!15, right=12mm of ship] (link) {\textbf{Delayed link}\\stamps sent, lands, earliest reply};
\node[box, fill=oigrey!12, right=12mm of link] (earth) {\textbf{Earth}\\flight surgeon sees only what crossed the link};
\node[box, fill=oiverm!10, below=8mm of ship, text width=42mm] (crew) {\textbf{Crew and crew medical officer}\\alerts, SOS, checklist};
\draw[arr] (suit) -- (ship);
\draw[arr] (ship) -- node[above]{report} (link);
\draw[arr] (link) -- node[above]{$\Delta t$} (earth);
\draw[arr] (ship) -- (crew);
\draw[arr, dashed] (earth.south) |- node[pos=0.75, below]{reply after another $\Delta t$} (crew.east);
\end{tikzpicture}
\caption{The three layers. The ship decides who acts from the one-way light time $\Delta t$; Earth reads only what crossed the link.}
\label{fig:architecture}
\end{figure*}
```

- [ ] **Step 3: Figure 2, `paper/figures/authority.tex`**

```latex
% Figure 2. Who decides, against one-way delay (log scale). Every number comes from generated/numbers.tex.
\begin{figure}[t]\centering
\begin{tikzpicture}
\begin{semilogxaxis}[width=\columnwidth, height=46mm, xmin=0.1, xmax=3000, ymin=0, ymax=1, ytick=\empty,
  xlabel={One-way light time (s, log scale)}, axis lines=left, clip=false]
\fill[oiblue!15] (axis cs:0.1,0) rectangle (axis cs:\numCrewFirstAtS,1);
\fill[oiverm!15] (axis cs:\numCrewFirstAtS,0) rectangle (axis cs:3000,1);
\node[align=center, font=\scriptsize] at (axis cs:5,0.88) {flight surgeon directs care};
\node[align=center, font=\scriptsize] at (axis cs:950,0.88) {crew medical\\officer decides};
\draw[thick] (axis cs:\numStationOneWayS,0) -- (axis cs:\numStationOneWayS,0.55)
  node[above, font=\scriptsize]{station};
\draw[thick] (axis cs:\numMoonOneWayS,0) -- (axis cs:\numMoonOneWayS,0.35)
  node[above, font=\scriptsize]{Moon};
\draw[thick] (axis cs:\numMarsOneWayS,0) -- (axis cs:\numMarsOneWayS,0.45)
  node[above, font=\scriptsize, align=center]{Mars\\(our date)};
\draw[dashed] (axis cs:\numCrewFirstAtS,0) -- (axis cs:\numCrewFirstAtS,1)
  node[pos=0.62, left, font=\scriptsize]{\numCrewFirstAtS~s};
\end{semilogxaxis}
\end{tikzpicture}
\caption{Decision authority by one-way delay. With no link at all the crew acts alone.}
\label{fig:authority}
\end{figure}
```

- [ ] **Step 4: Figure 3, `paper/figures/pipeline.tex`**

```latex
% Figure 3. The three questions LIGHTTIME asks of every reading, in order.
\begin{figure}[t]\centering
\begin{tikzpicture}[font=\scriptsize, node distance=4mm,
  q/.style={draw, rounded corners=2pt, fill=oigreen!12, align=center, text width=0.82\columnwidth, inner sep=3pt},
  outbox/.style={draw, dashed, rounded corners=2pt, align=left, text width=0.82\columnwidth, inner sep=3pt},
  arr/.style={-{Latex[length=1.6mm]}, thick}]
\node[q] (trust) {\textbf{1. Can this reading be trusted?}\\plausible range \numPlausibleSpoTwoLow--\numPlausibleSpoTwoHigh\%, signal good, \numSettleN{} readings to settle after a dropout};
\node[q, below=of trust] (usual) {\textbf{2. Is it normal for this person?}\\band (caution $\le$95, warning $\le$93, emergency $\le$91), held for \numSustainN{} readings; personal usual range};
\node[q, below=of usual] (left) {\textbf{3. How long is left, and can Earth answer first?}\\Theil--Sen slope over the last \numWindowN{} readings; time left $=(\text{now}-\text{red line})/(-\text{slope})$; compare with $2\Delta t$};
\node[outbox, below=of left] (act) {caution with time left $\rightarrow$ SOS $\rightarrow$ report to Earth; who decides follows $\Delta t$};
\draw[arr] (trust) -- (usual); \draw[arr] (usual) -- (left); \draw[arr] (left) -- (act);
\end{tikzpicture}
\caption{The order in which the ship checks a reading. Each step can stop a false alarm before the next one runs.}
\label{fig:pipeline}
\end{figure}
```

- [ ] **Step 5: The section files.** Create `abstract.tex` (inside `\begin{abstract}...\end{abstract}`), and `introduction.tex`, `related.tex`, `system.tex`, `methods.tex`, `results.tex`, `discussion.tex`, `conclusion.tex`, each starting with its `\section{...}` and a comment naming its row in the outline. `system.tex` inputs `figures/architecture` and `figures/authority`; `methods.tex` inputs `figures/pipeline`; `results.tex` holds:

```latex
\begin{table}[t]\centering\small
\caption{Each low-oxygen recording replayed through the ship.}\label{tab:events}
\input{generated/table_events}
\end{table}
\begin{figure}[t]\centering
\includegraphics[width=\columnwidth]{figures/timeleft_event.pdf}
\caption{One recording of induced low oxygen. The ship warned at the orange line with a fitted time left; the SOS followed when five readings sat in the red.}
\label{fig:event}
\end{figure}
\begin{figure}[t]\centering
\includegraphics[width=0.49\columnwidth]{figures/lead_times.pdf}\hfill
\includegraphics[width=0.49\columnwidth]{figures/false_sos.pdf}
\caption{Left: warning lead before the SOS in each of the \numUwEvents{} recordings (median \numUwMedianLeadS~s). Right: false SOS on a healthy \numControlHours-hour night as each trust rule is added.}
\label{fig:evidence}
\end{figure}
```

- [ ] **Step 6: `paper/.gitignore`**

```text
*.aux
*.bbl
*.blg
*.fdb_latexmk
*.fls
*.log
*.out
*.synctex.gz
```

Commit `main.pdf` only at the end of Task B8, not on every build.

- [ ] **Step 7: Compile**

Run: `cd paper && latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex`
Expected: exit 0 and a PDF with the three diagrams, the table and the two data figures. This scaffold compiled on the copy to two pages. On Windows without TeX, install MiKTeX (`winget install --id MiKTeX.MiKTeX`) or upload the `paper/` folder to Overleaf; both work with this preamble.

- [ ] **Step 8: Look.** Open the PDF. Every label in every figure readable, nothing overlapping. Commit the sources.

### Task B2: References first

- [ ] **Step 1:** Build `paper/refs.bib` from the table above. Every DOI by `curl` as shown; never type an entry from memory.
- [ ] **Step 2:** Lane K2 checks the "not yet verified" row now, before any section depends on it. Each one is kept with a confirmed identifier or dropped.
- [ ] **Step 3:** Commit `refs.bib`.

### Task B3: Methods and System (write these first: they are the facts)

- [ ] **Step 1:** Write `system.tex` and `methods.tex` from the outline. Every constant as a macro; read each from the code once to confirm.
- [ ] **Step 2:** Table 3 (parameters) as a `tabular` with three columns (parameter, value macro, source). Every row's source is a file or a citation.
- [ ] **Step 3:** Run the dataset licence check: read `data/spo2_uw/README.md`, `data/spo2_apnea_ecg/README.md`, `data/ppg_dalia/README.md` and quote each licence name exactly.
- [ ] **Step 4:** Compile, look, commit.

### Task B4: Results

- [ ] **Step 1:** Write `results.tex` around Table 2 and Figures 4 and 5. Every number a macro. Describe; do not interpret (that is the Discussion).
- [ ] **Step 2:** Compile, look, commit.

### Task B5: Introduction, related work, discussion, conclusion

- [ ] **Step 1:** Write them in that order, from the outline. Use scientific-critical-thinking on the Discussion: every limit in the table above appears, in order of weight, and nothing is softened.
- [ ] **Step 2:** Table 1 (related systems) holds only systems K2 verified.
- [ ] **Step 3:** Compile, look, commit.

### Task B6: Abstract and title

- [ ] **Step 1:** Write the abstract last, at most 250 words, one paragraph. Check the count: `pdftotext -f 1 -l 1 paper/main.pdf - | sed -n '/Abstract/,/Introduction/p' | wc -w`.
- [ ] **Step 2:** Keep the title unless the team prefers another: "Who decides when Earth is minutes away? Latency-aware decision support for crew health monitoring".
- [ ] **Step 3:** Commit.

### Task B7: Review lanes

- [ ] **Step 1 (K1):** A critic reads the PDF beside the code and lists each claim it cannot trace.
- [ ] **Step 2 (K2):** citation-check in search mode on the whole paper. Nothing Unverified survives.
- [ ] **Step 3 (R1):** a reader-sim as a space-medicine reviewer (the mentors' viewpoint: flight surgeon versus CMO, periodic versus continuous monitoring, privacy, explainability). Fix what they doubt, or answer it in the text.
- [ ] **Step 4 (K3):** avoid-ai-writing detect mode on each section file, then human-rewrite `plain` and `cold read`. Numbers, macros and citations stay exactly as they are.
- [ ] **Step 5:** `python scripts/docs_check.py paper/sections/*.tex` → `0 to fix`.

### Task B8: Final build and the preprint bundle

- [ ] **Step 1:** `cd paper && latexmk -C && latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex`
- [ ] **Step 2:** No warnings left: `grep -E "Warning: (Citation|Reference)|undefined" main.log` prints nothing, and `pdftotext main.pdf - | grep -c "??"` prints 0.
- [ ] **Step 3:** All fonts embedded: `pdffonts main.pdf` shows `yes` in the `emb` column for every font.
- [ ] **Step 4:** Commit `paper/main.pdf` and the sources.
- [ ] **Step 5 (only after team question 1 is answered):** fill the author block, then make the bundle: `zip -r lighttime-preprint.zip main.tex main.bbl refs.bib sections figures generated`. Do not upload anywhere until every author has read the PDF.
