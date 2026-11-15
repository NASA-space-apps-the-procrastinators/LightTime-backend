# Ship AI and Data Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replay real recordings as the crew's suit data, add the ship AI's time-left test and asked-ahead report, keep a 24-hour recorder, and fix the ten code-review findings.

**Architecture:** Same Flask app and tables. One new column (`reading.context`). Five new modules in `base_station/` (`lookahead`, `replay`, `usual`, `habitat`, `recorder`), one cleaning script, one evidence script. Spec: `docs/specs/2026-11-14-ship-ai-and-data-design.md`.

**Tech Stack:** Python 3.10+, Flask, Flask-SQLAlchemy, pytest. No new packages.

**Where the code is:** every file this plan creates or changes is already written, in its final form, under `docs/plans/2026-11-14-ship-ai-and-data-files/`, laid out like the repo. Copy the files, do not retype them. As a set they passed 91 tests on SQLite and on Postgres 16 before this plan was written. They have not been run on this machine yet, so the test steps below still count.

---

## File map

| File | New or changed | What it does |
|---|---|---|
| `scripts/build_clean_data.py` | new | Raw downloads in `data/` to tables in `data/clean/` |
| `scripts/check_spo2_rules.py` | new | Replays real oxygen recordings through the rules and prints the results |
| `base_station/lookahead.py` | new | Time left until a falling reading reaches its red line |
| `base_station/replay.py` | new | Real wrist rows and the recorded oxygen fall |
| `base_station/usual.py` | new | Each person's own usual range from the last 24 hours |
| `base_station/habitat.py` | new | Cabin and radiation from NASA EDA |
| `base_station/recorder.py` | new | Daily summary and the 24-hour prune |
| `base_station/limits.json` | changed | Heart rate no longer alerts, oxygen gets the time-left test, settle time, plausible range |
| `base_station/rules.py` | changed | Settle time, one sender at a time, falling-trend caution |
| `base_station/reports.py` | changed | `deadline`, `asked_ahead`, `speak_falling` |
| `base_station/routes.py` | changed | Early report, input checks, `/habitat`, `/summary/send`, story options |
| `base_station/scenario.py` | changed | `real` story, history backfill, one story at a time, survives a bad reading |
| `command_center/routes.py` | changed | A reply needs text |
| `common/models.py` | changed | `Reading.context` |
| `app.py` | changed | Ask JPL once at start-up |
| `tests/` | 8 new files, 3 changed | 91 tests in all |

---

### Task 0: Check the starting point

- [ ] **Step 1: Confirm the branch and that the code is unchanged since the last commit**

Run: `git status --short` and `git diff --stat aa0fdb9 -- app.py common base_station command_center tests`
Expected: the second command prints nothing. Untracked files under `docs/` and `data/` are fine.

If the second command prints anything, stop and tell the backend owner. The files in this plan replace whole files, and local edits would be lost.

- [ ] **Step 2: Confirm the new raw data is in place**

Run: `ls data/spo2_uw data/spo2_apnea_ecg`
Expected: `100001.csv` to `100006.csv`, `LICENSE`, `README.md`, and `a01r_SpO2_1Hz.csv`, `c01r_SpO2_1Hz.csv`, `README.md`.

- [ ] **Step 3: Confirm the old tests pass**

Run: `python -m pytest -q`
Expected: `45 passed`

---

### Task 1: Clean the data

**Files:**
- Create: `scripts/build_clean_data.py`
- Test: `tests/test_clean_data.py`

- [ ] **Step 1: Copy the test and watch it fail**

```bash
cp docs/plans/2026-11-14-ship-ai-and-data-files/tests/test_clean_data.py tests/
python -m pytest tests/test_clean_data.py -q
```
Expected: an error, `No module named 'scripts.build_clean_data'`.

- [ ] **Step 2: Copy the script and run the test**

```bash
mkdir -p scripts
cp docs/plans/2026-11-14-ship-ai-and-data-files/scripts/build_clean_data.py scripts/
python -m pytest tests/test_clean_data.py -q
```
Expected: `5 passed`

- [ ] **Step 3: Build the clean tables**

Run: `python scripts/build_clean_data.py`
Expected, last three lines:
```
cabin (NASA EDA, RR-1): 12087 rows in, 12087 kept, 0 dropped for gaps
radiation (NASA EDA, RR-1): 39 days
blood oxygen event (UW, volunteer 100001): 769 seconds, 98% down to 67% and back to 96%
```
and `data/clean/` now holds `wrist/S1.csv` to `S15.csv`, `cabin_rr1.csv`, `radiation_rr1.csv`, `spo2_event.csv`.

- [ ] **Step 4: Commit**

```bash
git add scripts/build_clean_data.py tests/test_clean_data.py data/clean data/spo2_uw data/spo2_apnea_ecg
git commit -m "data: cleaning script, clean tables, blood-oxygen recordings"
```

---

### Task 2: Ship AI, replay, recorder and review fixes

The modules import each other, so they go in together.

**Files:**
- Create: `base_station/lookahead.py`, `replay.py`, `usual.py`, `habitat.py`, `recorder.py`
- Modify: `base_station/limits.json`, `rules.py`, `reports.py`, `routes.py`, `scenario.py`, `command_center/routes.py`, `common/models.py`, `app.py`
- Test: `tests/test_lookahead.py`, `test_signal.py`, `test_replay.py`, `test_usual.py`, `test_habitat.py`, `test_recorder.py`, `test_hardening.py` (new); `tests/conftest.py`, `test_base_api.py`, `test_rules.py` (changed)

- [ ] **Step 1: Copy the tests and watch them fail**

```bash
cp docs/plans/2026-11-14-ship-ai-and-data-files/tests/*.py tests/
python -m pytest -q
```
Expected: collection errors, the first being `cannot import name 'usual' from 'base_station'`.

- [ ] **Step 2: Copy the code**

```bash
cp docs/plans/2026-11-14-ship-ai-and-data-files/app.py .
cp docs/plans/2026-11-14-ship-ai-and-data-files/common/models.py common/
cp docs/plans/2026-11-14-ship-ai-and-data-files/command_center/routes.py command_center/
cp docs/plans/2026-11-14-ship-ai-and-data-files/base_station/* base_station/
cp docs/plans/2026-11-14-ship-ai-and-data-files/scripts/check_spo2_rules.py scripts/
```

- [ ] **Step 3: The local database needs the new column**

`reading.context` is new and `create_all` does not add columns to an existing table. On the laptop's SQLite file:

Run: `rm -f instance/lighttime.db`

On a Postgres that already has the tables, once:

Run: `python -c "from app import create_app; from common.models import db; a = create_app(); a.app_context().push(); db.session.execute(db.text('ALTER TABLE reading ADD COLUMN IF NOT EXISTS context VARCHAR(12)')); db.session.commit()"`

- [ ] **Step 4: Run every test**

Run: `python -m pytest -q`
Expected: `91 passed` (about 15 seconds)

If a test fails, use systematic-debugging before changing anything. Read the failure, find the cause, then fix. These files passed as a set, so a failure here is most likely an environment difference (line endings, a stale database file, a missing `data/clean/`).

- [ ] **Step 5: Commit**

```bash
git add app.py common base_station command_center scripts tests
git commit -m "feat: ship AI time-left test, real-data replay, 24 h recorder, review fixes"
```

---

### Task 3: Print the evidence

- [ ] **Step 1: Run the check**

Run: `python scripts/check_spo2_rules.py`
Expected (about 15 seconds):
```
Control sleeper (Apnea-ECG c01r), 7.8 hours of readings, nothing wrong with them:
  false SOS, every number believed:            4
  false SOS, impossible numbers rejected:      1
  false SOS, and 10 s to settle after a dropout: 0
  falling-trend warnings:                      2 (at seconds [1532, 1651])

Six healthy volunteers breathing low-oxygen gas (UW, Masimo oximeter):
  volunteer  warning at  SOS at  warning ahead by  ship predicted
  100001       162 s   321 s         159 s          142 s
  100002       235 s   341 s         106 s           56 s
  100003       138 s   236 s          98 s           87 s
  100004       221 s   317 s          96 s           58 s
  100005       112 s   180 s          68 s           84 s
  100006       114 s   128 s          14 s           26 s
  warned before the SOS: 6 of 6, median 97 s ahead

Sleep apnoea patient (Apnea-ECG a01r), fast falls: 579 SOS, trend warning came first in 185 (32%), median 42 s ahead
```

If the numbers differ, do not edit the spec to match. Tell the backend owner.

---

### Task 4: Play it live

- [ ] **Step 1: Start the server**

Run: `python app.py`

- [ ] **Step 2: In a second terminal, play the stage story on real wrist data at Mars**

```bash
curl -s -X POST localhost:5000/api/base/reset
curl -s -X POST localhost:5000/api/base/dial -H "Content-Type: application/json" -d '{"stop":"mars"}'
curl -s -X POST localhost:5000/api/base/scenario/start -H "Content-Type: application/json" -d '{"name":"stage","replay":true}'
sleep 12
curl -s "localhost:5000/api/base/alerts?open=1"
curl -s localhost:5000/api/base/crew
curl -s localhost:5000/api/base/habitat
```
Expected: one alert, `"level": "emergency"`, and `speak` ends with `Earth will hear this in 11 minutes. Earliest reply in 22 minutes. Crew medical officer, start the checklist.` On the crew board each `latest.source` is `replay` and each `usual.heart_rate` has `low` and `high`. Habitat shows `temp_c` near 24 and `co2_ppm` near 2650.

- [ ] **Step 3: Play the recorded oxygen fall (about four minutes)**

```bash
curl -s -X POST localhost:5000/api/base/reset
curl -s -X POST localhost:5000/api/base/scenario/start -H "Content-Type: application/json" -d '{"name":"real"}'
sleep 100
curl -s "localhost:5000/api/base/alerts?open=1"
```
Expected: one alert at `caution` or `warning` with a `lookahead` object, `"earth_in_time": false`, and `speak` ending `That is too late. Crew medical officer, check on Okafor now.` The outbox already holds the report. About two minutes later the same alert becomes an `emergency`.

- [ ] **Step 4: Stop the story**

Run: `curl -s -X POST localhost:5000/api/base/scenario/stop`

---

### Task 5: Docs, database, push

- [ ] **Step 1: README**

Add the rows of the table in spec section 7 to the API table in `README.md`. Add one line under "Data": `python scripts/build_clean_data.py` rebuilds `data/clean/`, and `python scripts/check_spo2_rules.py` reprints the evidence.

- [ ] **Step 2: Data sources**

In `docs/data-sources.md` add the three blood-oxygen sources from spec section 2 with their licences and citations (they are in `data/spo2_uw/README.md` and `data/spo2_apnea_ecg/README.md`), plus CSA PRET and the report Canadian Healthcare in Deep Space from the frontend owner's list.

- [ ] **Step 3: AI use**

In `AI_USE.md` add: the time-left rule and its settings were designed with Claude and chosen on six real recordings; the results and their limits are in spec section 6.

- [ ] **Step 4: The reviewer's Postgres**

Do this only once the reviewer has confirmed the host name. `kyler.visserfamily.cs` does not resolve. Put one line in `.env` (git ignores it, never commit it):

`DATABASE_URL=postgresql+psycopg://svc-lighttime:<password>@<host>:5432/lighttime`

Then run Task 2 Step 3 (the Postgres line) and `python -m pytest -q` again.

- [ ] **Step 5: Commit, push, open the pull request**

```bash
git add README.md AI_USE.md docs
git commit -m "docs: ship AI and data spec, plan, sources"
git push
```
Open a pull request from `Tj-Backend` into `main` for the reviewer. Point him at spec section 1 (review fixes) and section 6 (evidence).

---

## For the frontend owner and the hardware owner

The frontend owner: spec section 7 is the full list of what changed for the screens. The three that matter most: show `lookahead` with a countdown to `red_line_at`, say `speak` once per alert id and level, and send empty form boxes as they are.

The hardware owner: your sensor can post for any crew member now without hiding the story's SOS. Send `{"crew_id": 2, "spo2": 97, "heart_rate": 71}` to `POST /api/base/readings` once a second. If the sensor has no reading, send `"signal_ok": false`.
