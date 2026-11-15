# Backend Finish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make a second story behave like the first, give the console the true length of each link leg, guard the wall between ship and Earth with a test, and correct the words and records the reference check found wrong.

**Architecture:** Four small changes on `Tj-Backend`, each test-first. No rule, threshold or clock changes. The spec is `docs/specs/2026-11-15-finish-design.md` (decisions F2, F6 and F8); the findings behind it are in `docs/reviews/2026-11-15-overnight-review.md`.

**Tech Stack:** Python 3.12, Flask, Flask-SQLAlchemy, pytest. SQLite for every command here.

---

## Before you start

Rules from `CLAUDE.md` that bind every task: tests first; run `python -m pytest -q` after every task and stop if the count differs from the one stated; build what the task says and nothing else; never open, print or edit `.env`; log the work in `AI_USE.md`.

Every command is PowerShell, run from the repository root with the virtual environment active. Each test command forces SQLite, so a `DATABASE_URL` left in `.env` cannot send a test run to the hosted database:

```powershell
$env:DATABASE_URL = 'sqlite:///:memory:'; python -m pytest -q
```

Expected before Task 1: `192 passed`.

Tasks 1 to 3 are independent of each other. Task 1 matters most for the pitch.

## File map

| File | Task | Change |
|---|---|---|
| `base_station/scenario.py` | 1 | New `close_last_run()`. `start()` calls it and defaults to `full` |
| `base_station/routes.py` | 1, 2 | Story default `full`. Two new keys on the alert timeline |
| `tests/test_scenario.py` | 1 | Two tests |
| `tests/test_demo_day.py` | 2 | One test |
| `tests/test_contract.py` | 2 | Two names added to `TIMELINE` |
| `docs/frontend/lighttime-api.ts` | 2 | Two fields on `Timeline` |
| `docs/specs/2026-11-14-backend-design.md` | 1, 2 | The story row and the timeline sentence of the API table |
| `tests/test_wall.py` | 3 | New |
| `common/sources.py`, `common/dsn.py`, `common/modes.py`, `command_center/routes.py` | 4 | Words only |
| `AI_USE.md`, `docs/data-sources.md`, `data/README.md`, `data/ppg_dalia/README.md`, `data/spo2_apnea_ecg/README.md`, `docs/specs/2026-11-14-data-sources-design.md` | 4 | Records and citations |

---

### Task 1: A second story raises its own alert, and the story with no name is `full`

Why: a story's SOS stays open until a person resolves it. An open alert cannot be raised again, so a second story raises nothing, and `treated()` looks only at alerts raised since the new story began, so ticking the oxygen step on the old alert no longer ends the fall. Separately, `POST /api/base/scenario/start` with no name plays `stage`, which has no early warning.

**Files:**
- Modify: `base_station/scenario.py` (after `treated()`, and in `start()`)
- Modify: `base_station/routes.py:426`
- Modify: `docs/specs/2026-11-14-backend-design.md` (the `scenario/start` row of the API table)
- Test: `tests/test_scenario.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_scenario.py`:

```python
def test_a_new_story_closes_the_alert_the_last_one_left_open(client, app):
    low = {"crew_id": 1, "spo2": 86, "heart_rate": 88, "source": "scenario"}
    for _ in range(rules.LIMITS["sustain_n"]):
        client.post("/api/base/readings", json=low)
    left = client.get("/api/base/alerts?open=1").get_json()
    assert [a["vital"] for a in left] == ["spo2"]
    with app.app_context():
        assert scenario.close_last_run() == 1
    closed = client.get(f"/api/base/alerts/{left[0]['id']}").get_json()
    assert closed["cleared_by"] == "auto: a new story started" and closed["stage"] == "resolved"
    again = []
    for _ in range(rules.LIMITS["sustain_n"]):
        again += client.post("/api/base/readings", json=low).get_json()["alerts"]
    assert len(again) == 1 and again[0]["id"] != left[0]["id"]


def test_the_story_with_no_name_is_the_one_with_the_early_warning(client, monkeypatch):
    started = []
    monkeypatch.setattr(scenario, "start", lambda app, name, real: started.append(name))
    assert client.post("/api/base/scenario/start", json={}).get_json()["name"] == "full"
    assert started == ["full"]
```

- [ ] **Step 2: Run them and watch them fail**

```powershell
$env:DATABASE_URL = 'sqlite:///:memory:'; python -m pytest tests/test_scenario.py -q
```

Expected: 2 failed. The first with `AttributeError: module 'base_station.scenario' has no attribute 'close_last_run'`, the second with `assert 'stage' == 'full'`.

- [ ] **Step 3: Write the code**

In `base_station/scenario.py`, add this function directly after `treated()`:

```python
def close_last_run():
    """Resolve the patient's blood-oxygen alert that an earlier story left open, and tell Earth.
    An open alert cannot be raised again, so without this a second story raises nothing.
    Returns how many were closed."""
    from base_station import routes

    left = Alert.query.filter_by(crew_id=PATIENT, vital="spo2", cleared_at=None, auto=True).all()
    for alert in left:
        alert.cleared_at, alert.cleared_by = utcnow(), "auto: a new story started"
    db.session.commit()
    for alert in left:
        routes.tell_earth(alert, {"event": "resolved", "by": alert.cleared_by, "note": None})
    return len(left)
```

In the same file, change the first line of `start()` and its body. Replace:

```python
def start(app, name="stage", real=False):
```

with:

```python
def start(app, name="full", real=False):
```

and replace:

```python
        real = real or name == "real"
        if real:
            with app.app_context():
                if Reading.query.filter_by(source="replay").count() == 0:
                    backfill()
        _since = utcnow()
```

with:

```python
        real = real or name == "real"
        with app.app_context():
            close_last_run()
            if real and Reading.query.filter_by(source="replay").count() == 0:
                backfill()
        _since = utcnow()
```

In `base_station/routes.py`, in `scenario_start()`, replace:

```python
    name, real = sent.get("name", "stage"), bool(sent.get("replay"))
```

with:

```python
    name, real = sent.get("name", "full"), bool(sent.get("replay"))
```

- [ ] **Step 4: Change the API table in the same commit**

In `docs/specs/2026-11-14-backend-design.md`, find the row that begins ``| `POST /api/base/scenario/start` `{name, replay}` and `/scenario/stop` `` and replace its last cell with:

```
starts or stops the scripted story ("stage", "full" or "real"; `replay: true` plays real wrist data). Changed: with no name the story is `full`, the one with the early warning. Changed: starting a story resolves the patient's blood-oxygen alert that an earlier story left open (`cleared_by` is `auto: a new story started`) and tells Earth, so the new story raises its own alert |
```

- [ ] **Step 5: Run the whole suite**

```powershell
$env:DATABASE_URL = 'sqlite:///:memory:'; python -m pytest -q
```

Expected: `194 passed`.

- [ ] **Step 6: Commit**

```powershell
git add base_station/scenario.py base_station/routes.py tests/test_scenario.py docs/specs/2026-11-14-backend-design.md
git commit -m "fix: a new story closes the alert the last one left open; the story with no name is full"
```

---

### Task 2: The alert's timeline gives each link leg its true length

Why: `timeline.earliest_reply_at` and `earth_at` are stamps on the demo clock, where a Mars leg plays in 11 seconds. The console printed them as clock times, so a report sent at 06:31 showed its earliest reply at 06:31. The stamps stay as they are, because the link uses them to decide when a message is visible. The console needs the true length of each leg beside them (spec, decisions F1 and F2). The values already exist on the report in `link.to_dict()`.

**Files:**
- Modify: `base_station/routes.py` (`timeline()`, lines 20 to 41)
- Modify: `tests/test_contract.py` (`TIMELINE`)
- Modify: `docs/frontend/lighttime-api.ts` (`Timeline`)
- Modify: `docs/specs/2026-11-14-backend-design.md` (the sentence that begins "The `timeline` holds")
- Test: `tests/test_demo_day.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_demo_day.py`:

```python
def test_the_timeline_gives_each_leg_its_true_length(morning):
    before = morning.get("/api/base/alerts/A1").get_json()["timeline"]
    assert before["earth_after_s"] is None and before["earliest_reply_after_s"] is None
    morning.post("/api/base/alerts/A1/ack", json={"by": "Okafor"})
    morning.post("/api/base/alerts/A1/send", json={})
    line = morning.get("/api/base/alerts/A1").get_json()["timeline"]
    state = morning.get("/api/base/state").get_json()
    assert state["stop"] == "mars"
    assert line["earth_after_s"] == state["delay_s"]
    assert line["earliest_reply_after_s"] == state["round_trip_s"]
```

- [ ] **Step 2: Run it and watch it fail**

```powershell
$env:DATABASE_URL = 'sqlite:///:memory:'; python -m pytest tests/test_demo_day.py -q
```

Expected: 1 failed with `KeyError: 'earth_after_s'`.

- [ ] **Step 3: Write the code**

In `base_station/routes.py`, in the dictionary that `timeline()` returns, replace:

```python
        "earliest_reply_at": iso(earliest),
```

with:

```python
        "earliest_reply_at": iso(earliest),
        # the true length of each leg, in mission seconds: the stamps above are on the demo clock
        "earth_after_s": sent.get("arrives_after_s"),
        "earliest_reply_after_s": sent.get("earliest_reply_after_s"),
```

- [ ] **Step 4: Change the contract test, the typed client and the API table in the same commit**

In `tests/test_contract.py`, replace:

```python
TIMELINE = {"raised_at", "acknowledged_at", "sent_at", "earth_eta_s", "earth_at", "earliest_reply_at",
            "reply_at", "resolved_at"}
```

with:

```python
TIMELINE = {"raised_at", "acknowledged_at", "sent_at", "earth_eta_s", "earth_at", "earliest_reply_at",
            "earth_after_s", "earliest_reply_after_s", "reply_at", "resolved_at"}
```

In `docs/frontend/lighttime-api.ts`, in `export interface Timeline`, replace:

```ts
  reply_at: string | null; resolved_at: string | null;
```

with:

```ts
  earth_after_s: number | null;           // true one-way seconds the report left with. Print this, not earth_at
  earliest_reply_after_s: number | null;  // true round-trip seconds. Print this, not earliest_reply_at
  reply_at: string | null; resolved_at: string | null;
```

In `docs/specs/2026-11-14-backend-design.md`, in the sentence that begins "The `timeline` holds", replace:

```
`earliest_reply_at`, `reply_at` and `resolved_at`.
```

with:

```
`earliest_reply_at`, `earth_after_s`, `earliest_reply_after_s`, `reply_at` and `resolved_at`. New: `earth_after_s` and `earliest_reply_after_s` are the true one-way and round-trip lengths in mission seconds, null until the report has left; a screen prints these for a leg and never the two stamps, which are on the demo clock.
```

- [ ] **Step 5: Run the whole suite**

```powershell
$env:DATABASE_URL = 'sqlite:///:memory:'; python -m pytest -q
```

Expected: `195 passed` (194 if Task 1 was skipped).

- [ ] **Step 6: Commit**

```powershell
git add base_station/routes.py tests/test_demo_day.py tests/test_contract.py docs/frontend/lighttime-api.ts docs/specs/2026-11-14-backend-design.md
git commit -m "feat: the alert timeline carries the true length of each link leg"
```

---

### Task 3: A test guards the wall between Earth and the ship

Why: `CLAUDE.md` says `command_center/` may read only the link, and never import the ship's tables. Today that holds, and nothing checks it. The data owner's Earth case routes are about to be merged into that folder.

**Files:**
- Create: `tests/test_wall.py`

- [ ] **Step 1: Write the test**

Create `tests/test_wall.py`:

```python
"""Earth's code may read the link and the dial, never the ship's own tables (CLAUDE.md)."""
import ast
import pathlib

EARTH = pathlib.Path(__file__).resolve().parent.parent / "command_center"
SHIP_TABLES = {"Crew", "Reading", "Alert", "Checkin", "Reminder"}


def test_earth_never_imports_the_ships_tables_or_the_ships_code():
    files = sorted(EARTH.glob("*.py"))
    assert files, "command_center/ has no Python files to check"
    for path in files:
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                names = {alias.name for alias in node.names}
                assert not module.startswith("base_station"), f"{path.name} imports {module}"
                assert not (module == "" and "base_station" in names), f"{path.name} imports base_station"
                assert not names & SHIP_TABLES, f"{path.name} imports {sorted(names & SHIP_TABLES)}"
            elif isinstance(node, ast.Import):
                assert not any(alias.name.startswith("base_station") for alias in node.names), \
                    f"{path.name} imports base_station"
```

- [ ] **Step 2: Run it**

```powershell
$env:DATABASE_URL = 'sqlite:///:memory:'; python -m pytest tests/test_wall.py -q
```

Expected: `1 passed`.

- [ ] **Step 3: Prove it can fail**

Add this line to the end of the imports in `command_center/routes.py`:

```python
from common.models import Crew  # noqa: F401
```

Run the same command. Expected: 1 failed with `routes.py imports ['Crew']`. Remove the line and run again. Expected: `1 passed`. Check that `git diff command_center/routes.py` prints nothing.

- [ ] **Step 4: Run the whole suite**

```powershell
$env:DATABASE_URL = 'sqlite:///:memory:'; python -m pytest -q
```

Expected: `196 passed`.

- [ ] **Step 5: Commit**

```powershell
git add tests/test_wall.py
git commit -m "test: Earth's code never imports the ship's tables"
```

---

### Task 4: Words and records

Why: the reference check (`docs/reviews/2026-11-15-overnight-review.md`, section 8) found statements in our own files that their sources do not support. None changes behaviour. One string is shown on screen: the sources list.

**Files:**
- Modify: `common/sources.py:10`, `common/dsn.py:2`, `command_center/routes.py:52`, `common/modes.py:5-6`
- Modify: `AI_USE.md`, `docs/data-sources.md`, `data/README.md`, `data/ppg_dalia/README.md`, `data/spo2_apnea_ecg/README.md`, `docs/specs/2026-11-14-data-sources-design.md`

- [ ] **Step 1: The Deep Space Network "reports", it is not said to "measure"**

In `common/sources.py`, replace:

```python
     "used_for": "Round-trip light time NASA measures to its Mars spacecraft. A second check on the delay."},
```

with:

```python
     "used_for": "Round-trip light time NASA's network reports for its Mars spacecraft. A second check on the delay."},
```

In `common/dsn.py`, in the docstring at the top, replace `round-trip light time NASA measures to its spacecraft there` with `round-trip light time NASA reports for its spacecraft there`.

In `command_center/routes.py`, in the docstring of `network()`, replace `the Deep Space Network measures it to spacecraft that are there` with `the Deep Space Network reports it for spacecraft that are there`.

- [ ] **Step 2: Say what the NEEMO 16 source supports**

In `common/modes.py`, replace:

```python
# NASA's NEEMO 16 test (Rader et al. 2013): at about five minutes one way,
# critical medical advice cannot always get through.
```

with:

```python
# NASA's NEEMO 16 analog mission ran a simulated medical emergency at a five-minute delay and
# recommended more crew medical autonomy at five minutes or more (Rader et al. 2013, NTRS 20130011552).
# The switch at exactly 300 s is our design choice, not a measured threshold.
```

- [ ] **Step 3: One line for each AI use, with no names**

`AI_USE.md` holds six lines twice, once naming the role and once naming a person. Delete the six that name a person, then add today's lines. Run:

```powershell
$lines = Get-Content AI_USE.md | Where-Object { $_ -notmatch '^- 2026-11-14, (TJ|Ore),' }
$lines += '- 2026-11-15, the backend owner, Claude: reviewed the overnight work by running it (five parallel agents: backend audit, console audit, reference check, deployment research, evidence and figures), then wrote the project documentation, the how-it-works write-up and its figures, the deployment tutorial, the submission text, the finish spec and the two finish plans.'
$lines += '- 2026-11-15, the backend owner, Claude Code: ran the backend finish plan test-first: a new story closes the last one''s alert, the timeline carries each leg''s true length, a test guards the wall, and the words and citations the reference check found wrong were corrected.'
Set-Content AI_USE.md $lines
(Select-String -Path AI_USE.md -Pattern '^- 2026-11-14, (TJ|Ore),').Count
```

Expected: the last command prints `0`.

- [ ] **Step 4: Correct the citations**

In `docs/data-sources.md`:

- replace `Cite: Reiss, Indlekofer and Schmidt (2019), DOI 10.24432/C53890` with `Cite: Reiss A, Indlekofer I, Schmidt P, Van Laerhoven K (2019). Deep PPG: Large-Scale Heart Rate Estimation with Convolutional Neural Networks. Sensors 19(14): 3079. doi:10.3390/s19143079. Dataset: doi:10.24432/C53890`
- replace `Computers in Cardiology 27: 255-258. doi:10.13026/C23W2R` with `Computers in Cardiology 27: 255-258. doi:10.1109/CIC.2000.898505. Database: doi:10.13026/C23W2R` (it occurs once; the row below it says "Same citation")

In `data/README.md`, replace:

```
- PPG-DaLiA: Reiss, A., Indlekofer, I. and Schmidt, P. (2019). PPG-DaLiA. UCI Machine Learning Repository. https://doi.org/10.24432/C53890. Licence CC BY 4.0.
```

with:

```
- PPG-DaLiA: Reiss A, Indlekofer I, Schmidt P, Van Laerhoven K (2019). Deep PPG: Large-Scale Heart Rate Estimation with Convolutional Neural Networks. Sensors 19(14): 3079. https://doi.org/10.3390/s19143079. Dataset: UCI Machine Learning Repository, https://doi.org/10.24432/C53890. Licence CC BY 4.0.
```

In `data/ppg_dalia/README.md`, replace:

```
- Cite: Reiss, A., Indlekofer, I. and Schmidt, P. (2019). PPG-DaLiA. UCI Machine Learning Repository. https://doi.org/10.24432/C53890
```

with:

```
- Cite: Reiss A, Indlekofer I, Schmidt P, Van Laerhoven K (2019). Deep PPG: Large-Scale Heart Rate Estimation with Convolutional Neural Networks. Sensors 19(14): 3079. https://doi.org/10.3390/s19143079. Dataset: UCI Machine Learning Repository, https://doi.org/10.24432/C53890
```

In `data/spo2_apnea_ecg/README.md`, replace `Computers in Cardiology 27: 255-258. doi:10.13026/C23W2R` with `Computers in Cardiology 27: 255-258. doi:10.1109/CIC.2000.898505. Database: doi:10.13026/C23W2R`.

In `docs/specs/2026-11-14-data-sources-design.md`, replace `Wrist heart rate and skin temperature for three volunteers, cut from the PPG-DaLiA dataset` with `Wrist heart rate and skin temperature for fifteen volunteers, cut from the PPG-DaLiA dataset`.

- [ ] **Step 5: Run the whole suite and the checksums**

```powershell
$env:DATABASE_URL = 'sqlite:///:memory:'; python -m pytest -q
python scripts/verify_data.py --offline
```

Expected: `196 passed`. If `verify_data.py` reports a changed checksum for a README under `data/`, that is this task's edit: run `python scripts/verify_data.py --offline --write` once and include `data/CHECKSUMS.sha256` in the commit. If it reports anything else, stop and tell the backend owner.

- [ ] **Step 6: Commit**

```powershell
git add common/sources.py common/dsn.py common/modes.py command_center/routes.py AI_USE.md docs/data-sources.md data/README.md data/ppg_dalia/README.md data/spo2_apnea_ecg/README.md docs/specs/2026-11-14-data-sources-design.md
git status --short
git commit -m "docs: say what each source supports, and keep one line for each AI use"
```

If `git status --short` lists `data/CHECKSUMS.sha256`, add it before committing.

---

### Task 5: Run it once, the way the pitch will

This task changes no file. It checks Tasks 1 and 2 on a running ship. Use two PowerShell windows.

- [ ] **Step 1: Start the ship on the demo morning**

```powershell
$env:DATABASE_URL = 'sqlite:///lighttime.db'; $env:LIGHTTIME_MORNING = '1'; python app.py
```

- [ ] **Step 2: In the second window, run a story twice without a restart**

```powershell
$ship = 'http://localhost:5000/api/base'
(irm "$ship/state").stop
(irm -Method Post "$ship/scenario/start" -ContentType 'application/json' -Body '{}').name
Start-Sleep 50
irm "$ship/alerts?open=1" | Where-Object vital -eq 'spo2' | Select-Object id, level, stage
(irm -Method Post "$ship/scenario/start" -ContentType 'application/json' -Body '{}').name
Start-Sleep 50
irm "$ship/alerts" | Where-Object vital -eq 'spo2' | Select-Object id, level, stage, cleared_by
```

Expected: `mars`, then `full`. After the first wait, one blood-oxygen alert at level `emergency`, stage `sent`. Then `full` again. After the second wait, two blood-oxygen alerts: the first with stage `resolved` and `cleared_by` `auto: a new story started`, the second open at level `emergency` with a new id.

- [ ] **Step 3: Check the leg lengths**

```powershell
(irm "$ship/alerts?open=1" | Where-Object vital -eq 'spo2').timeline | Select-Object earth_after_s, earliest_reply_after_s
```

Expected: `660.86` and `1321.72`.

- [ ] **Step 4: Stop the story and the ship**

```powershell
irm -Method Post "$ship/scenario/stop" | Out-Null
```

Then Ctrl+C in the first window.

- [ ] **Step 5: Push and open the pull request**

```powershell
git push origin Tj-Backend
```

The pull request into `main` is the reviewer's to merge. Its description: "Backend finish: a second story raises its own alert, the timeline carries each leg's true length, a wall test, and corrected sources. 196 tests on SQLite. Spec: docs/specs/2026-11-15-finish-design.md."

---

## Not in this plan

The Earth case routes, the rebuilt month and the host settings stay in `docs/plans/2026-11-15-backend-polish.md` (Tasks 4, 6 and 7), with one correction to that plan: its run-through starts the story named `stage`, which has no early warning. Start `full`. The items under "Later, not today" in the finish spec are not planned.
