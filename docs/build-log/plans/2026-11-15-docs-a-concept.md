# Plan A: the concept document

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. Run `docs/plans/2026-11-15-docs-00-overview.md` Task 0 first. One writer (lane W-A) writes the whole document; critics K1, K2, K3 and reader R1 review it. Load: engineering:documentation, scientific-writing (section 5 only), human-rewrite, avoid-ai-writing, citation-check (lane K2).

**Goal:** One document that a judge, a mentor or a new team member can read to understand what LIGHT-TIME is, why it exists, every word it uses, and every piece of math it does, with each number traceable to the code.

**Architecture:** `docs/concept.md` in the backend repo, built to `docs/concept.pdf` with pandoc. Figures are PNGs rendered from code (Mermaid sources in `docs/diagrams/`, plots from `scripts/paper_figures.py`). It replaces `docs/how-it-works.md` and the idea half of `docs/project-documentation.md`; both become pointers.

**Tech Stack:** Markdown with GitHub math (`$...$`), Mermaid, pandoc with xelatex, `scripts/docs_check.py`.

**Length and reader:** 5,000 to 6,500 words. The reader knows high-school algebra and nothing about spaceflight medicine. Three ways in: a two-minute summary at the top, the story in section 4, and the math in section 5 for whoever wants it. Section 5 is the one part allowed to be dense.

---

## The outline, and what each section must contain

Copy this outline into `docs/concept.md` in Task A1. Every bullet is a requirement. The source column is where the writer gets the fact; if a fact has no source, it does not go in.

| § | Heading | Must contain | Source |
|---|---|---|---|
| 0 | LIGHT-TIME in two minutes | Four short paragraphs: the problem, the idea, what we built, what the evidence shows. Figure A1. Live link and both repo links | `docs/submission.md` summary; numbers.json |
| 1 | The problem | The challenge in one paragraph (quote at most one line, cite the page). Today on the ISS: near real-time link, a flight surgeon on Earth, health checked periodically, not streamed. At Mars: about 3 to 22 minutes one way, and roughly two weeks of no link around solar conjunction. NASA lists distance from Earth as one of five hazards. Analogy: lightning, then thunder | challenge page (verify by hand); NASA HRP hazard page; the mentor notes of 14 Nov (periodic checks); reference list |
| 2 | The idea | Who decides depends on how long the light takes. The three cases as a table (no link, one way of 5 minutes or more, less). Say plainly that the 300 s switch is our design choice, following a recommendation in Rader et al. 2013 for more crew autonomy at five minutes or more. Name the frameworks that already describe the idea (NASA EIMO, CSA C2M2) and say what we add: software that switches by itself. Figure A3. Analogy: a phone call versus a letter | `common/modes.py` comment; Rader 2013; the team document's background check |
| 3 | What we built, and what we did not | Two-column table, **built** and **proposed**. Built: ship console, Earth console, the dial, the delayed link, LIGHTTIME, the scripted story with the console's click-through tour, daily check-in, reaction test, space-weather tab, role-based views. Proposed: the suit hardware (`docs/hardware.md`), glove controls, head-up display, MQTT, FHIR packets, five-colour alerts, an offline assistant, the learned heart-rate adviser in the loop. The assumption, in bold: the crew wear the shirt for the whole mission | the code; `docs/hardware.md`; the team document; reviewer notes |
| 4 | One emergency, second by second | The story as a numbered walk-through: calm, drift, the time-left warning, the SOS, the crew acts, Earth hears, Earth's reply lands. Use the crew and ground names exactly as they are in `crew.csv` and `command_center/routes.py` today. Figure A2. One paragraph on what the console's tour shows | `base_station/scenario.py`; `src/components/shared/tour.tsx` in the console repo; Figure A2 |
| 5 | The math, one piece at a time | 5.1 to 5.10 below. Each piece in the same order: one plain sentence, the formula, a worked example with real numbers, and one line on what it is not | below |
| 6 | What the evidence shows, and what it does not | Every number from numbers.json, in words. Figures A4 and A5. Then the limits: six events from one lab study on Earth, induced low oxygen, healthy volunteers, settings chosen on the same data (and the held-out check that answers part of that), no astronaut data, no clinical validation | numbers.json; `docs/how-it-works.md` §5 and §6 |
| 7 | Privacy and safety by design | A table of who sees what (the crew member, the CMO, the medical station, Earth). Earth's code cannot read the ship's tables, and a test enforces it. No language model in the path of a reading. Impossible readings are refused. What is not done: no login, the viewer is not proven, and the mentors' point about proportionality (continuous monitoring has to earn its place against the intrusion) | `base_station/access.py`; `tests/test_wall.py`; `tests/test_access.py`; CLAUDE.md rules; mentor notes of 14 and 15 Nov |
| 8 | What is real and what is simulated | Table: real (JPL Horizons distance, NEWS2 bands, the three public recordings, NASA cabin limits) and simulated (the crew's month, the story's readings), with how each is labelled on screen | `docs/data-sources.md`; `base_station/limits.json` |
| 9 | What comes next | Five items at most, each one sentence: hardware, an emergency unlock for the person helping, a sign-in, learned advisers that only advise, testing in an analog such as HERA | team document §10; mentor notes |
| 10 | Glossary | Task A6 | below |
| 11 | References | Numbered, the same style as `docs/how-it-works.md`. Only references that passed lane K2 | `docs/submission.md`; the team document; K2 |

### Section 5 in detail

Every number below is in `docs/generated/numbers.json` or printed by `scripts/paper_figures.py`. Write the number from there, not from this table.

| Piece | Plain sentence | Formula | Worked example to show |
|---|---|---|---|
| 5.1 Light time | Light needs time to cross a distance | $\Delta t = d / c$ | $c$ = 299,792.458 km/s (exact by definition). On 14 Nov 2026, JPL Horizons gives 660.86 s one way, so $d \approx 198.1$ million km |
| 5.2 Round trip | An answer needs the message to arrive and the reply to come back | $T = 2\Delta t$ | 1,321.72 s, about 22 minutes. Moon: 2.6 s of light time alone; with relays NASA plans for several seconds (cite the source K2 confirms) |
| 5.3 Who decides | One rule picks who acts | no link: crew alone; $\Delta t \ge 300$ s: CMO decides, Earth advises after; else: flight surgeon directs | station 0.25 s, Moon 1.3 s, Mars 660.86 s, behind the Sun: no link |
| 5.4 The demo clock | On stage, long legs play faster; the true numbers stay on screen | shown $= \Delta t / 60$ when $\Delta t \ge 60$ s | 660.86 / 60 = 11.01 s. Explain the two kinds of stamp: demo-clock times and true mission seconds |
| 5.5 Can a reading be trusted? | Three filters before a number counts | plausible 50 to 100 %; good signal; 10 readings to settle after a dropout | Effect on a healthy 7.8-hour night: false SOS 4, then 1, then 0 (Figure A5) |
| 5.6 How bad is it? | Bands, held for five readings in a row | caution ≤ 95, warning ≤ 93, emergency ≤ 91; 5 readings | Why five: one bad reading cannot raise an SOS. Say the bands are inspired by NEWS2 and not validated in space |
| 5.7 Is this normal for this person? | Each person's own usual range | 1st to 99th percentile of the last 24 hours, once there are enough readings | Confirm the count and the window in `base_station/usual.py` before writing them. Explain a percentile by sorting 100 readings |
| 5.8 How long is left? | Draw the line the readings follow, and see where it hits the red line | slope = median of $(v_j - v_i)/(j - i)$ over all pairs; time left $= (\text{now} - 91)/(-\text{slope})$ | The five readings 97.0, 96.8, 96.5, 96.4, 96.0 give 10 pair slopes, median −0.25 % a second, now 96.5 (median of the last five), time left 22 s (Figure A4, left). Then say why the ship would stay quiet on these five: it needs at least 15 readings and a fall of at least 2 points across the window. Analogy: judging when a bath will be empty from the water line, where one splash cannot fool a median |
| 5.9 Do the readings agree? | Most pairs must fall, not just the ends | agreement = share of pairs falling − share rising; needs ≥ 0.5 | In the example all 10 fall, so agreement = 1.0. Name it: a form of Kendall's tau |
| 5.10 Can Earth answer first? | Compare the time left with the round trip | Earth in time if $T <$ time left | Recording 100001: warning at 162 s with 142 s predicted; the SOS came at 321 s. At Mars $T$ = 1,321.72 s, so the crew must act; at the Moon $T$ = 2.6 s, so Earth can answer |

### Figures

| # | What | Made by | File |
|---|---|---|---|
| A1 | The three layers | Mermaid flowchart, Task A2 | `docs/diagrams/layers.mmd` → `docs/figures/concept/layers.png` |
| A2 | The alert round trip | Mermaid sequence, Task A2 | `docs/diagrams/alert-round-trip.mmd` → `docs/figures/concept/alert-round-trip.png` |
| A3 | Who decides against one-way delay | the paper's TikZ Figure 2, rendered to PNG in Task A2 | `docs/figures/concept/authority.png` |
| A4 | The worked example, and one real recording | `scripts/paper_figures.py` | `timeleft_worked.png`, `timeleft_event.png` |
| A5 | Warning leads and false SOS | `scripts/paper_figures.py` | `lead_times.png`, `false_sos.png` |
| A6 | Who sees what | a Markdown table in §7, not an image | |

### Analogies (use where they help, never more than one per idea)

Lightning then thunder (light time). A letter and its reply (round trip). A phone call versus a letter (who decides). The red zone on a rev counter (bands). Knowing your car's usual hum (usual range). When a bath will be empty (time left). A smoke alarm that waits for a second whiff before ringing (sustain). Voicemail (store and forward). A ship's logbook (the outbox). The team document's "Think of it like" column has more; take from it, check each against what the code does.

---

### Task A1: The skeleton

**Files:** Create `docs/concept.md`

- [ ] **Step 1:** Write the title, a one-line purpose, the date, and the twelve headings from the outline as `##` headings, each followed by the "Must contain" text as an HTML comment so it does not render.
- [ ] **Step 2:** Run `python scripts/docs_check.py docs/concept.md`. Expected: `0 to fix`.
- [ ] **Step 3:** Commit: `git add docs/concept.md && git commit -m "docs: concept document skeleton"`

### Task A2: The figures

**Files:** Create `docs/diagrams/layers.mmd`, `docs/diagrams/alert-round-trip.mmd`; generate `docs/figures/concept/*.png`

- [ ] **Step 1: Create `docs/diagrams/layers.mmd`**

```text
flowchart LR
    S["Suit<br/>one reading a second"] --> B["Ship computer: LIGHTTIME<br/>trust, usual range, time left, who decides"]
    B --> C["Crew and crew medical officer<br/>caution, SOS, checklist"]
    B -- "report, stamped" --> L["Delayed link<br/>sent, lands, earliest reply"]
    L -- "one-way light time" --> E["Earth: flight surgeon<br/>sees only what crossed the link"]
    E -. "reply, one more one-way light time" .-> C
```

- [ ] **Step 2: Create `docs/diagrams/alert-round-trip.mmd`**

```text
sequenceDiagram
    autonumber
    participant S as Suit
    participant B as Ship (LIGHTTIME)
    participant C as Crew and CMO
    participant L as Delayed link
    participant E as Earth (flight surgeon)
    S->>B: one reading a second
    B->>B: trust, usual range, time left
    B-->>C: caution: "falling, about N s left"
    B->>L: report (sent_at)
    B-->>C: SOS after 5 readings in the red
    Note over C: Crew acts now (one-way delay of 5 min or more)
    L->>E: report lands (earth_at = sent_at + one-way delay)
    E->>L: reply
    L->>C: reply lands (one more one-way delay)
```

- [ ] **Step 3: Render**

Run (macOS or Linux shell; on Windows use the same `mmdc` from `npm i -g @mermaid-js/mermaid-cli`):

```bash
mmdc -i docs/diagrams/layers.mmd -o docs/figures/concept/layers.png -b white -w 1400
mmdc -i docs/diagrams/alert-round-trip.mmd -o docs/figures/concept/alert-round-trip.png -b white -w 1400
```

If `mmdc` cannot start a browser, add `-p puppeteer.json` with `{"args": ["--no-sandbox"]}`. Expected: two PNGs. Open both and read every label.

- [ ] **Step 4: Figure A3 from the paper's TikZ.** After Plan B Task B1 exists, run `pdftoppm -r 200 -png -f 2 -l 2 paper/main.pdf /tmp/p` and crop the authority figure, or compile `paper/figures/authority.tex` alone with a `standalone` wrapper. If Plan B has not reached B1, use the Markdown table from §2 instead and add the figure later.
- [ ] **Step 5:** Commit the `.mmd` sources and the PNGs.

### Task A3: Sections 0 to 4

- [ ] **Step 1:** Write §1 to §4 first, §0 last (a summary is easier once the rest exists).
- [ ] **Step 2:** In §4, read the names from the files, not from this plan: `python -c "import csv;[print(r['crew_id'],r['name'],r['role']) for r in csv.DictReader(open('data/processed/reference/crew.csv'))]"` and `grep -n FLIGHT_SURGEON command_center/routes.py`.
- [ ] **Step 3:** Run `python scripts/docs_check.py docs/concept.md`. Fix every FAIL; read every REVIEW.
- [ ] **Step 4:** Commit.

### Task A4: Section 5, the math

- [ ] **Step 1:** Write 5.1 to 5.10 from the table above, each with plain sentence, formula, worked example, and what it is not.
- [ ] **Step 2: Check every worked example by running it.** Paste this and compare with the text:

```bash
python -c "
import json, statistics
n = json.load(open('docs/generated/numbers.json'))
print('d =', round(n['mars_one_way_s'] * 299792.458 / 1e6, 1), 'million km; T =', n['mars_round_trip_s'], 's; shown =', n['mars_plays_as_s'], 's')
v = [97.0, 96.8, 96.5, 96.4, 96.0]
s = sorted((v[j] - v[i]) / (j - i) for i in range(5) for j in range(i + 1, 5))
slope = s[len(s) // 2]
print('slopes', [round(x, 3) for x in s], 'median', slope, 'agreement', (sum(x < 0 for x in s) - sum(x > 0 for x in s)) / len(s))
print('time left', (statistics.median(v[-5:]) - 91) / -slope, 's')
"
```

Expected: `d = 198.1 million km; T = 1321.72 s; shown = 11.01 s`, median −0.25, agreement 1.0, time left 22.0 s.

- [ ] **Step 3:** Read `base_station/usual.py` and `base_station/lookahead.py` and confirm every constant the text names. Any mismatch: the code wins, and the text changes.
- [ ] **Step 4:** Commit.

### Task A5: Sections 6 to 9

- [ ] **Step 1:** Write them from the outline. Quote no number that is not in numbers.json. The desk-work heart-rate result in `docs/how-it-works.md` §5 may be described in words with its existing figure (`docs/figures/heart_rate_by_activity.png`), and says where it came from.
- [ ] **Step 2:** The privacy table in §7 must match `base_station/access.py`. Check it by running the app and calling `/api/base/crew` with and without `X-LightTime-Viewer: C3` and `C2`, as Plan C Task C4 does.
- [ ] **Step 3:** Commit.

### Task A6: The glossary

- [ ] **Step 1:** A table sorted alphabetically: **Term** | **Plain meaning** | **Think of it like** | **In LIGHT-TIME** (where it appears, and whether it is built or proposed).
- [ ] **Step 2:** Include at least these terms, and every other term the document uses: agreement (of a trend); alert level; band; baseline and usual range; caution; conjunction (solar); crew medical officer; delayed link; demo clock and mission seconds; dial; Deep Space Network; earliest reply; Earth-independent medical operations; emergency and SOS; flight surgeon; JPL Horizons; Kendall's tau; LIGHTTIME; light time (one-way); median; NEWS2; percentile; plausible range; playback speed; red line; role-based view; round trip; SBAR report; settle; simulated; smart shirt (CSA Bio-Monitor); space weather; SpO2 (blood oxygen); store and forward; sustain; telemetry; Theil-Sen line; time left; triage; viewer header; warning; who decides.
- [ ] **Step 3:** Compare every definition with `CONTEXT.md`. Where they differ, the code decides which is right, and the other file is corrected in the same commit.
- [ ] **Step 4:** Commit.

### Task A7: References (lane K2)

- [ ] **Step 1:** Collect every citation in the document into §11, numbered in order of first use.
- [ ] **Step 2:** Lane K2 runs citation-check in search mode on the whole document (two passes: extract, then verify). Every claim must come back Verified. Anything Unverified, Misquoted or Not Found is removed or replaced, never kept with a softer word.
- [ ] **Step 3:** Commit.

### Task A8: Voice, reader, checker, PDF

- [ ] **Step 1 (K3):** avoid-ai-writing in detect mode, then human-rewrite in `plain` then `cold read` mode. Fix P0 and P1. Keep every number and citation exactly.
- [ ] **Step 2 (R1):** A reader-sim reads it as a Space Apps judge with five minutes. Ask: what is the idea, what was built, what is proven, what is not. If any answer is wrong, the section it came from is rewritten.
- [ ] **Step 3:** `python scripts/docs_check.py docs/concept.md` → `0 to fix`.
- [ ] **Step 4: Build the PDF.** Check the tools first: `pandoc --version` and `xelatex --version`. On Windows, if missing: `winget install --id JohnMacFarlane.Pandoc` and `winget install --id MiKTeX.MiKTeX`.

```bash
cd docs
pandoc concept.md -o concept.pdf --pdf-engine=xelatex -V geometry:margin=1in -V mainfont="DejaVu Sans" -V mathfont="DejaVu Math TeX Gyre" --toc
```

If DejaVu is not installed, drop the two font options. This exact command, with a table, display math and a figure, built a PDF on the copy. Open every page.

- [ ] **Step 5:** Commit `docs/concept.md`, `docs/concept.pdf`.

### Task A9: Retire what it replaces

- [ ] **Step 1:** Replace the body of `docs/how-it-works.md` and `docs/project-documentation.md` with three lines each: what moved, and links to `concept.md` and `tech/architecture.md`.
- [ ] **Step 2:** `grep -rn "how-it-works\|project-documentation" README.md docs/*.md docs/tech 2>/dev/null` and point each link at the new file.
- [ ] **Step 3:** `python scripts/docs_check.py` on everything → `0 to fix`. Commit.
- [ ] **Step 4:** Ask the team question 4 from the overview. If yes, upload the finished Markdown to Google Drive as a Google Doc (no edits there; the repo stays the source).
