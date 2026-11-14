# Console Contract: Serve the Generated Month to the Console

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Use superpowers:test-driven-development inside every task and superpowers:systematic-debugging whenever a count differs.

**Goal:** The backend returns what the console's first four screens need (crew overview, astronaut page, check-in, alert loop) from the generated dataset, on one crew and one clock, without breaking the ship AI.

**Architecture:** Static data (baselines, daily history, cabin air, rule text) is read once from files in `data/processed/` and `data/reference/`. Only what the crew can change is a table: check-ins, reminders, alerts, link messages. A mission clock starts at 14 November 2026, 06:30 UTC when the demo morning is loaded. Console rules live in one pure module that mirrors the console's `scoring.ts`. The ship AI's rules are untouched except one line for blood pressure.

**Tech Stack:** Python 3.13, Flask 3, Flask-SQLAlchemy 3.1, pytest. No new dependency.

**Specs:** `docs/specs/2026-11-14-console-data-design.md` (decisions D1 to D14, requirements R1 to R5), `docs/specs/2026-11-14-lighttime-ai-design.md` (A1 to A5, A10), `docs/reviews/2026-11-14-dataset-review.md` (findings F1 to F6).

**Status of this plan:** written on Saturday evening against `main` at `75d6c5f` and the dataset at `a25791f`, by reading both. **None of this code has been run.** The data checks behind it were run (see the review). Treat every code block as a careful draft: write the test, watch it fail for the stated reason, then make it pass. The test counts are sums, not measurements.

## Rules for the person or agent running this

1. One task at a time, in order. Each task ends with the full suite green and a commit.
2. Test first. If a new test passes before the code is written, the test is wrong: stop and fix the test.
3. When an old test fails after a change, read the failure before touching anything. It must be one of the kinds the step names (a crew name, a string id, a longer field list). If it is any other kind, stop and report it. Do not edit a route to make an old test pass.
4. Three failed attempts at the same step means the plan is wrong there. Stop and report what was tried.
5. Build what the step says. An idea goes in a note to the backend owner.
6. No team member's name in code, tests, comments or commit messages. Crew are Okafor, Lindqvist, Sato and Mensah.
7. Never print or commit the value of `DATABASE_URL`.

## File map

| File | New or changed | What it holds |
| --- | --- | --- |
| `common/dataset.py` | new | Reads the dataset's CSV files once. Refuses the answer key |
| `common/models.py` | changed | Mission clock; `Crew.code`, `Crew.suit_id`; `Alert.ref`, `metric`, `symptoms`; tables `Checkin`, `Reminder`; crew seeded from the dataset |
| `base_station/scoring.py` | new | The console's state rules and their printed text. Pure functions |
| `base_station/morning.py` | new | Loads the demo morning into the tables and starts the clock |
| `base_station/console.py` | new | Crew objects, history, thresholds, station, space weather, check-ins, threads, plan, reminders |
| `base_station/routes.py` | changed | Ids, alert shape, JSON errors, state, acknowledge, send, messages, reset. The crew board moves to `console.py` |
| `base_station/rules.py`, `limits.json` | changed | Estimated blood pressure no longer alarms |
| `app.py` | changed | `morning` switch; imports `console` |
| `data/reference/console_thresholds.json` | new | Copy of the console's `thresholds.json` |
| `tests/conftest.py` | changed | Clock reset; `morning` fixture |
| `tests/test_clock.py`, `test_dataset.py`, `test_scoring.py`, `test_morning.py`, `test_console.py` | new | 33 tests |
| `tests/test_rules.py`, `test_tonight.py`, `test_contract.py` and five more | changed | One new test, four from the earlier plan, and the expectations listed in Tasks 2, 4, 5, 6 |

Test counts by task: start 110, then 112, 116, 121, 125, 128, 133, 135, 139, 143, 144, 148.

---

### Task 0: Bring the dataset onto this branch

**Files:** merge only, plus `data/reference/console_thresholds.json` and one row in `data/README.md`.

- [ ] **Step 1:** `git status`. The working tree holds uncommitted document edits. Commit them first: `git add docs CLAUDE.md AI_USE.md` then `git commit -m "docs: specs, plans and review for the console contract"`.
- [ ] **Step 2:** `python -m pytest -q`. Expected: `110 passed`. If not, stop and report.
- [ ] **Step 3:** `git fetch origin` then `git merge a25791f`. Expected: one conflict, in `AI_USE.md`, where both sides added lines at the end. Keep every line from both sides, write the new line's author as "data owner", then `git add AI_USE.md` and `git commit`. If any other file conflicts, stop and report: nothing else should, because the commit only adds files under `data/` and two notes at the root.
- [ ] **Step 4:** Check the merge brought the files: `python -c "import csv; print(len(list(csv.DictReader(open('data/processed/anomalous/daily_summary.csv')))))"`. Expected: `632`.
- [ ] **Step 5:** Copy the rule text: `Copy-Item docs\plans\2026-11-14-console-contract-files\console_thresholds.json data\reference\console_thresholds.json`. Add a row to the table in `data/README.md`: file `reference/console_thresholds.json`, from the console repo's `src/data/thresholds.json` (branch `feat/alert-loop-and-log`), 14 Nov 2026.
- [ ] **Step 6:** `python -m pytest -q`. Expected: `110 passed` (the merge adds data, not code). Commit: `chore: bring in the generated dataset and the console's rule text`.

---

### Task 1: The mission clock

Spec D7. One offset inside the function every part of the backend already uses for "now".

**Files:** `common/models.py`, `tests/conftest.py`, new `tests/test_clock.py`.

- [ ] **Step 1: Write the failing tests.** Create `tests/test_clock.py`:

```python
from datetime import datetime, timezone

from common import models

MORNING = datetime(2026, 11, 14, 6, 30)


def test_the_mission_clock_starts_where_it_is_told_and_keeps_running():
    models.set_clock(MORNING)
    try:
        first = models.utcnow()
        assert MORNING <= first < datetime(2026, 11, 14, 6, 30, 5)
        assert models.utcnow() >= first
    finally:
        models.set_clock(None)


def test_without_a_mission_clock_the_ship_keeps_real_time():
    models.set_clock(None)
    real = datetime.now(timezone.utc).replace(tzinfo=None)
    assert abs((models.utcnow() - real).total_seconds()) < 5
```

- [ ] **Step 2:** `python -m pytest tests/test_clock.py -q`. Expected: 2 failed, `AttributeError: module 'common.models' has no attribute 'set_clock'`.
- [ ] **Step 3:** In `common/models.py`, change the first import to `from datetime import datetime, timedelta, timezone` and replace `utcnow` with:

```python
_clock_offset = timedelta(0)


def utcnow():
    """The ship's clock: real time, or the mission clock once set_clock has started one."""
    return datetime.now(timezone.utc).replace(tzinfo=None) + _clock_offset


def set_clock(now=None):
    """Start the mission clock at `now` (naive UTC). None goes back to the real clock."""
    global _clock_offset
    real = datetime.now(timezone.utc).replace(tzinfo=None)
    _clock_offset = now - real if now else timedelta(0)
```

- [ ] **Step 4:** In `tests/conftest.py`, add `from common import dsn, lighttime, models` in place of the existing `from common import dsn, lighttime`, and add `models.set_clock(None)` as the line after `usual.clear()`. A test that starts the clock must not change the next test.
- [ ] **Step 5:** `python -m pytest -q`. Expected: `112 passed`. Commit: `feat: a mission clock the demo can start`.

---

### Task 2: The dataset reader, four crew, new tables

Spec D1, D5, D10. All table changes happen here, once.

**Files:** new `common/dataset.py`; `common/models.py`; `base_station/routes.py`; new `tests/test_dataset.py`; name changes in six test files.

- [ ] **Step 1: Write the failing tests.** Create `tests/test_dataset.py`:

```python
import hashlib
import json
import os

import pytest

from common import dataset
from common.models import Crew

READ = ["reference/mission", "reference/crew", "reference/baselines", "reference/link_windows",
        "anomalous/daily_summary", "anomalous/checkins", "anomalous/alerts_seed", "anomalous/messages",
        "anomalous/reminders", "anomalous/cabin_env", "anomalous/radiation_daily",
        "anomalous/space_weather_events"]


def test_the_files_the_ship_reads_are_the_build_they_say_they_are():
    folder = os.path.join(dataset.ROOT, "processed")
    with open(os.path.join(folder, "BUILD_INFO.json")) as f:
        expected = json.load(f)["outputs_sha256"]
    for name in READ:
        with open(os.path.join(folder, name + ".csv"), "rb") as f:
            found = hashlib.sha256(f.read().replace(b"\r\n", b"\n")).hexdigest()   # a Windows checkout adds \r
        assert found == expected[name + ".csv"], name


def test_the_ship_cannot_open_the_answer_key():
    for name in ("ground_truth/anomalies", "reports/replay_alerts_clean", "clean/daily_summary"):
        with pytest.raises(ValueError):
            dataset.table(name)


def test_the_ship_starts_with_the_four_crew_from_the_dataset(app):
    with app.app_context():
        crew = [(c.id, c.code, c.name, c.suit_id) for c in Crew.query.order_by(Crew.id)]
    assert crew == [(1, "C1", "Okafor", "LT-01"), (2, "C2", "Lindqvist", "LT-02"),
                    (3, "C3", "Sato", "LT-03"), (4, "C4", "Mensah", "LT-04")]


def test_a_reading_can_name_its_crew_member_either_way(client):
    by_code = client.post("/api/base/readings", json={"crew_id": "C2", "heart_rate": 70})
    by_number = client.post("/api/base/readings", json={"crew_id": 2, "heart_rate": 71})
    assert by_code.status_code == by_number.status_code == 201
    assert by_code.get_json()["reading"]["crew_id"] == by_number.get_json()["reading"]["crew_id"] == 2
    assert client.post("/api/base/readings", json={"crew_id": "C9", "heart_rate": 70}).status_code == 400
```

- [ ] **Step 2:** `python -m pytest tests/test_dataset.py -q`. Expected: an import error for `common.dataset` (4 errors).
- [ ] **Step 3:** Create `common/dataset.py`:

```python
"""The generated crew month, read once from data/processed (built by data/scripts/build_all.py).

The ship reads reference/ and anomalous/ only. clean/ is a healthy crew for testing tools, and
ground_truth/ and reports/ are the answer key: the ship must never see them."""
import csv
import functools
import os
from datetime import date

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
ALLOWED = ("reference", "anomalous")


@functools.lru_cache(maxsize=None)
def table(name):
    """The rows of data/processed/<name>.csv as dicts, for example table("reference/crew")."""
    if name.split("/")[0] not in ALLOWED:
        raise ValueError(f"the ship does not read {name}")
    with open(os.path.join(ROOT, "processed", name + ".csv"), newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def num(text):
    return None if text in ("", None) else float(text)


def listed(text):
    """A cell like "headache|short sleep" as a list."""
    return [item for item in (text or "").split("|") if item]


def mission():
    return table("reference/mission")[0]


def mission_day(now):
    """Day 1 is the launch date."""
    return (now.date() - date.fromisoformat(mission()["launch_date"])).days + 1
```

- [ ] **Step 4:** In `common/models.py`:

Add `from common import dataset` under the Flask-SQLAlchemy import.

In `Crew`, add two columns:

```python
    code = db.Column(db.String(4), unique=True)          # "C1": the id every screen uses
    suit_id = db.Column(db.String(8))
```

In `Alert`, add three columns after `report_id`:

```python
    ref = db.Column(db.String(8), unique=True)           # "A1" for an alert loaded with the demo morning
    metric = db.Column(db.String(16))                    # set when a console rule raised it, e.g. "hr_rest"
    symptoms = db.Column(db.JSON, nullable=False, default=list)
```

Add two tables after `LinkMessage`:

```python
class Checkin(db.Model):
    """One morning check-in. One row per person per mission date."""
    id = db.Column(db.Integer, primary_key=True)
    crew_id = db.Column(db.Integer, db.ForeignKey("crew.id"), nullable=False, index=True)
    day = db.Column(db.String(10), nullable=False, index=True)      # "2026-11-14"
    completed_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    mood = db.Column(db.Integer)
    sleep_h = db.Column(db.Float)
    pvt_ms = db.Column(db.Integer)
    bp_sys = db.Column(db.Float)                                    # the morning cuff reading
    bp_dia = db.Column(db.Float)
    symptoms = db.Column(db.JSON, nullable=False, default=list)
    note = db.Column(db.String(500), nullable=False, default="")


class Reminder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    crew_id = db.Column(db.Integer, db.ForeignKey("crew.id"), nullable=False, index=True)
    alert_id = db.Column(db.Integer)
    text = db.Column(db.String(120), nullable=False)
    due_at = db.Column(db.DateTime, nullable=False)
    done_at = db.Column(db.DateTime)
```

Replace the crew lines of `seed()`:

```python
    if Crew.query.count() == 0:
        db.session.add_all([Crew(code=row["crew_id"], name=row["name"], role=row["role"], suit_id=row["suit_id"])
                            for row in dataset.table("reference/crew")])
```

- [ ] **Step 5:** In `base_station/routes.py`, replace `crew_id_or_400` with:

```python
def find_crew(ref):
    """A crew member from "C1" or from the row number, or None."""
    text = str(ref)
    crew = Crew.query.filter_by(code=text).first()
    if crew is None and text.isdigit():
        crew = db.session.get(Crew, int(text))
    return crew


def crew_or_404(ref):
    crew = find_crew(ref)
    if crew is None:
        abort(404)
    return crew


def crew_id_or_400(data):
    crew = find_crew(data.get("crew_id"))
    if crew is None:
        abort(400, "unknown crew_id")
    return crew.id
```

and change the readings route so it takes either form:

```python
@bp.get("/crew/<ref>/readings")
def crew_readings(ref):
    crew = crew_or_404(ref)
    limit = min(request.args.get("limit", 120, type=int), 600)
    rows = (Reading.query.filter_by(crew_id=crew.id)
            .order_by(Reading.at.desc(), Reading.id.desc()).limit(limit).all())
    return jsonify([row.to_dict() for row in reversed(rows)])
```

- [ ] **Step 6: Databases.** The tables changed, and `create_all` does not alter a table that exists.
  - Local SQLite: `Remove-Item instance\lighttime.db -ErrorAction SilentlyContinue`.
  - Hosted Postgres: this empties the demo tables for everyone, so tell the reviewer first. Then, once:

    `python -c "import os; from dotenv import load_dotenv; from sqlalchemy import create_engine, text; load_dotenv(); c = create_engine(os.environ['DATABASE_URL']).connect(); c.execute(text('DROP TABLE IF EXISTS reminder, checkin, link_message, alert, reading, crew, mission_state CASCADE')); c.commit(); print('dropped')"`

    Expected: `dropped`. The app recreates them at its next start.
- [ ] **Step 7: Old tests.** `python -m pytest -q`. The four new tests pass. Old tests fail only because the crew changed. Fix expectations, not code, with this rule: the person with the same number takes the old name's place (crew 1 is Okafor, crew 2 is Lindqvist, crew 3 is Sato), and there are now four. The known places:
  - `tests/test_app.py`: the names are `["Okafor", "Lindqvist", "Sato", "Mensah"]`; rename the test to say four crew.
  - `tests/test_base_api.py`: `board[0]["name"]`, the situation line that starts with the name, and the summary's `payload["crew"]` for crew 2.
  - `tests/test_earth_api.py`: the situation line.
  - `tests/test_lookahead.py`: the spoken line ends "check on Okafor now."
  - `tests/test_recorder.py`: `{"sent": 4, "pruned": 0}` and the sorted names `["Lindqvist", "Mensah", "Okafor", "Sato"]`.
  - Anywhere a test passes an old name as free text (`"by": ...`), or a comment uses one: replace it by the same rule.

  Then `Select-String -Path tests\*.py,base_station\*.py,common\*.py,scripts\*.py -Pattern "David|Damola|Youssef"` must print nothing. If a test fails for a reason other than a name or the count of crew, stop and report.
- [ ] **Step 8:** `python -m pytest -q`. Expected: `116 passed`. Commit: `feat: the dataset reader, four crew with console ids, and the new tables`.

---

### Task 3: The console's rules

Spec section 7 and D11. Pure functions, no database, no Flask.

**Files:** new `base_station/scoring.py`, new `tests/test_scoring.py`.

- [ ] **Step 1: Write the failing tests.** Create `tests/test_scoring.py`:

```python
from base_station import scoring

BAND = [52, 64]


def test_a_value_inside_the_persons_band_is_ok():
    assert scoring.score("hr_rest", 60, BAND, 0, False) == "OK"


def test_out_of_band_once_is_a_watch_and_three_days_or_a_symptom_make_it_an_alert():
    assert scoring.score("hr_rest", 80, BAND, 1, False) == "WATCH"
    assert scoring.score("hr_rest", 84, BAND, 3, False) == "ALERT"
    assert scoring.score("hr_rest", 80, BAND, 1, True) == "ALERT"


def test_three_limits_alert_on_their_own():
    assert scoring.score("spo2", 93, [96, 99], 0, False) == "ALERT"
    assert scoring.score("temp_c", 38.1, [36.3, 36.9], 0, False) == "ALERT"
    assert scoring.score("dose_mSv_day", 2.4, None, 0, False) == "ALERT"


def test_each_measurement_goes_out_of_range_its_own_way():
    assert scoring.score("spo2", 100, [96, 99], 0, False) == "OK"           # only low oxygen counts
    assert scoring.score("temp_c", 36.0, [36.3, 36.9], 0, False) == "OK"    # only a high temperature counts
    assert scoring.score("resp", 21, [12, 16], 0, False) == "WATCH"
    assert scoring.score("resp", 18, [12, 16], 0, False) == "OK"            # the band is not the rule for breathing
    assert scoring.score("sleep_h", 6.4, [6.0, 7.0], 0, False) == "WATCH"   # under 6.5 h, even inside the band
    assert scoring.score("mood", 2, None, 0, False) == "WATCH"
    assert scoring.score("pvt_ms", 312, None, 0, True, pvt_baseline=265) == "ALERT"
    assert scoring.score("pvt_ms", 300, None, 0, True, pvt_baseline=265) == "OK"
    assert scoring.score("dose_mSv_day", 1.9, None, 0, True) == "OK"
    assert scoring.score("mood", None, None, 0, False) is None              # nothing measured, nothing judged


def test_days_out_of_band_count_back_from_today_and_the_rules_have_their_words():
    assert scoring.days_out_of_band([60, 59, 58, 59, 80, 82, 84], BAND) == 3
    assert scoring.days_out_of_band([80, 60, 84], BAND) == 1
    assert scoring.days_out_of_band([80, None, 84], BAND) == 1
    assert scoring.worst(["OK", "ALERT", "WATCH"]) == "ALERT" and scoring.worst([]) == "OK"
    text = scoring.rule_text()
    assert text["hr_rest"]["unit"] == "bpm" and text["co2_mmHg"]["source"] and "pending" not in str(text)
```

- [ ] **Step 2:** `python -m pytest tests/test_scoring.py -q`. Expected: an import error (5 errors).
- [ ] **Step 3:** Create `base_station/scoring.py`:

```python
"""The console's state rules: OK, WATCH or ALERT for a daily value against the person's own band.

This follows src/lib/scoring.ts in the console repo step for step, so the ship and the screen
give the same answer. The words and the source for each rule are in
data/reference/console_thresholds.json, a copy of the console's thresholds.json."""
import functools
import json
import os

from common import dataset

METRICS = ["hr_rest", "bp_sys", "bp_dia", "spo2", "temp_c", "resp", "sleep_h", "mood", "pvt_ms", "dose_mSv_day"]
BANDED = {"hr_rest", "bp_sys", "bp_dia", "spo2", "temp_c", "resp", "sleep_h"}
RANK = {"OK": 0, "WATCH": 1, "ALERT": 2}
INDICATOR = {"hr_rest": "heart_rate_rest", "bp_sys": "blood_pressure", "bp_dia": "blood_pressure", "spo2": "spo2",
             "temp_c": "core_temperature", "resp": "respiratory_rate", "sleep_h": "sleep_hours", "mood": "mood",
             "pvt_ms": "reaction_time_pvt", "dose_mSv_day": "radiation_daily_dose", "co2_mmHg": "cabin_co2"}


def worst(states):
    return max(states, key=RANK.get, default="OK")


def hard_alert(metric, value):
    """The three limits that alert on their own."""
    return ((metric == "spo2" and value < 94) or (metric == "temp_c" and value > 38.0)
            or (metric == "dose_mSv_day" and value > 2))


def out_of_range(metric, value, band, pvt_baseline=None):
    below = band is not None and value < band[0]
    above = band is not None and value > band[1]
    if metric == "spo2":
        return below
    if metric == "temp_c":
        return above
    if metric == "resp":
        return value > 20
    if metric == "sleep_h":
        return below or value < 6.5
    if metric == "mood":
        return value <= 2
    if metric == "pvt_ms":
        return pvt_baseline is not None and value > pvt_baseline * 1.15
    if metric == "dose_mSv_day":
        return False
    return below or above            # resting heart rate and blood pressure


def days_out_of_band(series, band):
    """Days in a row outside the band, counted back from today. A day with no value ends the run."""
    days = 0
    for value in reversed(series):
        if value is None or band[0] <= value <= band[1]:
            break
        days += 1
    return days


def score(metric, value, band, days_out, has_symptom, pvt_baseline=None):
    if value is None:
        return None
    if hard_alert(metric, value):
        return "ALERT"
    if not out_of_range(metric, value, band, pvt_baseline):
        return "OK"
    return "ALERT" if days_out >= 3 or has_symptom else "WATCH"


@functools.lru_cache(maxsize=None)
def rule_text():
    """{metric: {unit, watch, alert, source}}: the words the console prints for each rule."""
    with open(os.path.join(dataset.ROOT, "reference", "console_thresholds.json"), encoding="utf-8") as f:
        indicators = json.load(f)["indicators"]
    return {metric: {"unit": indicators[key]["unit"], "watch": indicators[key]["watch"],
                     "alert": indicators[key]["alert"],
                     # the console prints this wording for the standard's section 3004, so the ship does too
                     "source": indicators[key]["source"].replace("V1 3004 vital-sign trending",
                                                                 "V1 3004 In-Mission Medical Care")}
            for metric, key in INDICATOR.items()}
```

- [ ] **Step 4:** `python -m pytest -q`. Expected: `121 passed`. Commit: `feat: the console's state rules on the ship`.

---

### Task 4: Alerts in the console's shape

Spec D2, D5, section 7. Alerts gain `state`, `stage`, `metric`, `rule`, `symptoms`; ids become `A1` and `C1`; errors become JSON.

**Files:** `base_station/routes.py`, new `tests/test_console.py`, `tests/test_contract.py`, `tests/test_tonight.py`.

- [ ] **Step 1: Write the failing tests.** Create `tests/test_console.py`:

```python
LOW = {"crew_id": 1, "spo2": 86}


def sos(client):
    for _ in range(5):
        raised = client.post("/api/base/readings", json=LOW).get_json()["alerts"]
    return raised[0]


def test_a_live_alert_speaks_the_consoles_language(client):
    alert = sos(client)
    assert alert["id"].startswith("A") and alert["crew_id"] == "C1" and alert["crew"] == "Okafor"
    assert (alert["state"], alert["level"], alert["metric"]) == ("SOS", "emergency", "spo2")
    assert alert["stage"] == "sent" and alert["symptoms"] == [] and alert["rule"]     # an SOS sends itself


def test_a_sensor_check_is_a_recheck_and_never_an_alert(client):
    raised = client.post("/api/base/readings",
                         json={"crew_id": 1, "spo2": 98, "signal_ok": False}).get_json()["alerts"]
    assert (raised[0]["state"], raised[0]["metric"], raised[0]["stage"]) == ("RECHECK", "signal", "raised")


def test_one_alert_can_be_fetched_by_its_code_or_its_number(client):
    alert = sos(client)
    assert client.get(f"/api/base/alerts/{alert['id']}").get_json()["id"] == alert["id"]
    assert client.get(f"/api/base/alerts/{alert['id'][1:]}").get_json()["id"] == alert["id"]
    missing = client.get("/api/base/alerts/A999")
    assert missing.status_code == 404 and missing.get_json() == {"error": "not found"}


def test_symptoms_given_at_acknowledge_stay_on_the_alert(client):
    alert = sos(client)
    acked = client.post(f"/api/base/alerts/{alert['id']}/ack",
                        json={"by": "Okafor", "symptoms": ["headache"]}).get_json()
    assert acked["symptoms"] == ["headache"] and acked["timeline"]["acknowledged_at"] is not None
```

- [ ] **Step 2:** `python -m pytest tests/test_console.py -q`. Expected: 4 failed (`'int' object has no attribute 'startswith'`, `KeyError: 'state'`, a 404 or 405 on the new route, `KeyError: 'symptoms'`).
- [ ] **Step 3:** In `base_station/routes.py`:

Add `scoring` to the `from base_station import ...` line.

Above `alert_dict`, add:

```python
STATE = {"advisory": "WATCH", "caution": "WATCH", "warning": "ALERT", "emergency": "SOS"}
NOT_A_DIAGNOSIS = "This is a fixed rule, not a diagnosis. A person, not the ship, decides."


def alert_code(alert):
    """The id the screens use: "A1" for an alert loaded with the morning, "A" and the row number otherwise."""
    return alert.ref or f"A{alert.id}"


def find_alert(ref):
    """An alert from "A1" or from the row number, or None."""
    text = str(ref)
    alert = Alert.query.filter_by(ref=text).first()
    number = text[1:] if text[:1] == "A" else text
    if alert is None and number.isdigit():
        alert = Alert.query.filter_by(id=int(number), ref=None).first()
    return alert


def alert_or_404(ref):
    alert = find_alert(ref)
    if alert is None:
        abort(404)
    return alert


def stage(alert, line):
    """Where the alert is on its round trip. Worked out from the times, never stored."""
    if alert.cleared_at is not None:
        return "resolved"
    if line["reply_at"]:
        return "replied"
    if line["sent_at"]:
        return "sent"
    return "acknowledged" if alert.acknowledged_at is not None else "raised"
```

Replace `alert_dict` with:

```python
def alert_dict(alert):
    crew = db.session.get(Crew, alert.crew_id)
    cfg = rules.LIMITS["vitals"].get(alert.vital)
    report = db.session.get(LinkMessage, alert.report_id) if alert.report_id else None
    look = report.payload.get("lookahead") if report else None     # as it stood when the report left
    line = timeline(alert)
    text = scoring.rule_text().get(alert.metric) if alert.metric else None
    if text:                                    # a console rule raised it: a daily value against the person's band
        unit, rule, source, speak = text["unit"], text["alert"], text["source"], None
        why = [f"What was seen: {alert.reason}.", f"Rule: {rule}.", f"Source: {source}.", NOT_A_DIAGNOSIS]
    else:                                       # the ship AI raised it, or a person pressed SOS
        why = reports.why(alert)
        unit = cfg["unit"].strip() if cfg else None
        rule = next((item[6:] for item in why if item.startswith("Rule: ")), None)
        source = rules.LIMITS["source"] if cfg else None
        if alert.level == "emergency":
            speak = reports.speak(alert, crew, current_state())
        else:
            speak = reports.speak_falling(crew, cfg["label"], look) if look else None
    return {
        "id": alert_code(alert), "crew_id": crew.code, "crew": crew.name, "at": iso(alert.at),
        "level": alert.level, "state": "RECHECK" if alert.vital == "signal" else STATE[alert.level],
        "stage": stage(alert, line), "vital": alert.vital, "metric": alert.metric or alert.vital,
        "value": alert.value, "unit": unit, "reason": alert.reason, "rule": rule, "source": source,
        "auto": alert.auto, "nasa_risk": alert.nasa_risk, "symptoms": alert.symptoms or [],
        "steps": reports.steps_for(alert.vital), "steps_done": alert.steps_done,
        "acknowledged_by": alert.acknowledged_by,
        "cleared_at": iso(alert.cleared_at), "cleared_by": alert.cleared_by,
        "cleared_note": alert.cleared_note, "why": why,
        "timeline": line,
        "lookahead": look,
        "speak": speak,
    }
```

In the four alert routes (`ack`, `steps`, `send`, `clear`) change the rule from `<int:alert_id>` to `<alert_id>` and the first line from `alert = db.get_or_404(Alert, alert_id)` to `alert = alert_or_404(alert_id)`.

In `acknowledge`, read the body once and keep the symptoms. The route becomes:

```python
@bp.post("/alerts/<alert_id>/ack")
def acknowledge(alert_id):
    alert = alert_or_404(alert_id)
    sent = body()
    if isinstance(sent.get("symptoms"), list):
        alert.symptoms = [item for item in sent["symptoms"] if isinstance(item, str)][:6]
        db.session.commit()
    if alert.acknowledged_at is None:
        alert.acknowledged_at = utcnow()
        alert.acknowledged_by = person(sent.get("by"))
        db.session.commit()
        tell_earth(alert, {"event": "acknowledged", "by": alert.acknowledged_by})
    return jsonify(alert_dict(alert))
```

After the `alerts` list route, add:

```python
@bp.get("/alerts/<alert_id>")
def one_alert(alert_id):
    return jsonify(alert_dict(alert_or_404(alert_id)))
```

In `crew_message`, a message may name its alert as `A1`. Replace the `"alert_id": data.get("alert_id")` entry with `"alert_id": about.id if about else None` and add this line above the `link.send` call:

```python
    about = find_alert(data["alert_id"]) if data.get("alert_id") is not None else None
```

At the end of the file, add the two error shapes the console expects:

```python
@bp.errorhandler(404)
def not_found(error):
    return jsonify(error="not found"), 404


@bp.errorhandler(400)
def bad_request(error):
    return jsonify(error=error.description, field=None), 400
```

- [ ] **Step 4: Old tests.** `python -m pytest -q`. Old failures must be only these two kinds:
  - `tests/test_contract.py`: add `"state", "stage", "metric", "rule", "symptoms"` to the `ALERT` set.
  - `tests/test_tonight.py`, the test that matches reports to alerts: the report's payload keeps the row number, so compare `f"A{m['payload']['alert_id']}" == a["id"]`.

  Any other failure that compares an alert's `id` or `crew_id` to a number is the same kind: the alert now says `"A3"` and `"C1"`. Anything else, stop and report.
- [ ] **Step 5:** `python -m pytest -q`. Expected: `125 passed`. Commit: `feat: alerts carry the console's state, stage, rule and ids`.

---

### Task 5: The demo morning, and a reset that replays it

Spec D7, D8, D12, D13, R4 last line.

**Files:** new `base_station/morning.py`; `app.py`; `base_station/routes.py`; `tests/conftest.py`; new `tests/test_morning.py`; `tests/test_contract.py`.

- [ ] **Step 1:** In `tests/conftest.py`, the `app` fixture must never load the morning, even when `.env` asks for it, and a second fixture gives a client on the morning. Replace the file with:

```python
import pytest
import requests

from app import create_app
from base_station import usual
from common import dsn, lighttime, models


def _offline(monkeypatch):
    def offline(*args):
        raise requests.ConnectionError("tests do not use the network")

    monkeypatch.setattr(lighttime, "fetch", offline)
    monkeypatch.setattr(dsn, "fetch", offline)
    lighttime._cache.clear()
    dsn._cache.clear()
    usual.clear()
    models.set_clock(None)


@pytest.fixture
def app(monkeypatch):
    _offline(monkeypatch)
    app = create_app("sqlite:///:memory:", morning=False)
    app.config["TESTING"] = True
    return app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def morning(monkeypatch):
    """A client on the demo morning: 14 November 2026, 06:30 UTC, alert A1 just raised."""
    _offline(monkeypatch)
    app = create_app("sqlite:///:memory:", morning=True)
    app.config["TESTING"] = True
    yield app.test_client()
    models.set_clock(None)
```

- [ ] **Step 2: Write the failing tests.** Create `tests/test_morning.py`:

```python
def test_the_morning_starts_at_half_past_six_on_day_158_at_mars(morning):
    state = morning.get("/api/base/state").get_json()
    assert (state["mission_day"], state["platform"], state["stop"]) == (158, "ISS", "mars")


def test_the_one_open_alert_is_the_resting_heart_rate(morning):
    alerts = morning.get("/api/base/alerts?open=1").get_json()
    assert [a["id"] for a in alerts] == ["A1"]
    a1 = alerts[0]
    assert (a1["crew_id"], a1["metric"], a1["value"], a1["unit"]) == ("C1", "hr_rest", 84, "bpm")
    assert (a1["state"], a1["stage"], a1["symptoms"]) == ("ALERT", "raised", ["headache"])
    assert a1["timeline"]["raised_at"] == "2026-11-14T06:12:00Z"
    assert a1["rule"].startswith("resting HR") and a1["source"].startswith("OCHMO")
    assert a1["steps"][1] == "Have them stop work and rest"
    everything = morning.get("/api/base/alerts").get_json()
    assert [a["id"] for a in everything] == ["A1", "A7", "A6", "A3", "A2"]     # A4 and A5 have no rule behind them
    assert "pending" not in str(everything)


def test_restart_puts_the_same_morning_back(morning):
    morning.post("/api/base/alerts/A1/ack", json={"by": "Okafor"})
    morning.post("/api/base/readings", json={"crew_id": "C2", "spo2": 97})
    morning.post("/api/base/dial", json={"stop": "moon"})
    assert morning.post("/api/base/reset").get_json() == {"ok": True}
    a1 = morning.get("/api/base/alerts/A1").get_json()
    assert a1["stage"] == "raised" and a1["timeline"]["acknowledged_at"] is None
    state = morning.get("/api/base/state").get_json()
    assert (state["stop"], state["mission_day"]) == ("mars", 158)
    assert morning.get("/api/base/crew/C2/readings").get_json() == []
```

- [ ] **Step 3:** `python -m pytest tests/test_morning.py -q`. Expected: 3 errors, `create_app() got an unexpected keyword argument 'morning'`. (The whole suite errors the same way until Step 5: that is expected.)
- [ ] **Step 4:** Create `base_station/morning.py`:

```python
"""The demo morning: 14 November 2026, 06:30 UTC, mission day 158, alert A1 just raised.

Loaded at start and on every reset when the app is in morning mode, so a restarted demo
always begins at the same moment. Everything here comes from data/processed."""
from datetime import datetime

from common import dataset
from common.models import (Alert, Checkin, Crew, LinkMessage, MissionState, Reading, Reminder, db,
                           set_clock)

CHECKLIST = {"hr_rest": "heart_rate"}     # which checklist a console alert uses; others use their own name
SKIP = {"hr"}                             # alerts no rule on the ship or the console would raise (review F6d)


def when(text):
    """A dataset time such as "2026-11-14T06:12:00Z" as the naive UTC the tables use, or None."""
    return datetime.fromisoformat(text.replace("Z", "")) if text else None


def whole(text):
    return None if text in ("", None) else int(float(text))


def load():
    mission = dataset.mission()
    set_clock(when(mission["demo_now"]))
    for model in (Reminder, Checkin, LinkMessage, Alert, Reading):
        model.query.delete()
    crew = {member.code: member for member in Crew.query}

    for row in dataset.table("anomalous/checkins"):
        if row["live_demo"] == "true":
            continue                      # the presenter does this one on stage
        db.session.add(Checkin(
            crew_id=crew[row["crew_id"]].id, day=row["date"], completed_at=when(row["completed_at"]),
            mood=whole(row["mood"]), sleep_h=dataset.num(row["sleep_h"]), pvt_ms=whole(row["pvt_ms"]),
            bp_sys=dataset.num(row["cuff_bp_sys_mmhg"]), bp_dia=dataset.num(row["cuff_bp_dia_mmhg"]),
            symptoms=dataset.listed(row["symptoms"]), note=row["note"]))

    alerts = {}
    for row in dataset.table("anomalous/alerts_seed"):
        if row["metric"] in SKIP:
            continue
        done = bool(row["resolved_at"])
        alerts[row["alert_id"]] = alert = Alert(
            ref=row["alert_id"], crew_id=crew[row["crew_id"]].id, at=when(row["raised_at"]),
            level=row["level"], vital=CHECKLIST.get(row["metric"], row["metric"]), metric=row["metric"],
            value=dataset.num(row["value"]), reason=row["reason"], auto=row["metric"] != "manual",
            nasa_risk=row["nasa_risk"], steps_done=[int(i) for i in dataset.listed(row["steps_done"])],
            symptoms=dataset.listed(row["symptoms"]),
            acknowledged_at=when(row["acknowledged_at"]), acknowledged_by="crew" if row["acknowledged_at"] else None,
            cleared_at=when(row["resolved_at"]), cleared_by="crew" if done else None)
        db.session.add(alert)
    db.session.flush()

    numbers = {}                          # the dataset's "M12" to this table's row number
    for row in dataset.table("anomalous/messages"):
        if row["alert_id"] and row["alert_id"] not in alerts:
            continue                      # the thread of an alert that was not loaded
        about = alerts.get(row["alert_id"])
        message = LinkMessage(
            direction=row["direction"], kind=row["kind"], priority=int(row["priority"]),
            payload={"alert_id": about.id if about else None, "text": row["text"], "from": row["author"],
                     "simulated": True},
            created_at=when(row["created_at"]), sent_at=when(row["sent_at"]), delay_s=dataset.num(row["delay_s"]),
            deliver_at=when(row["deliver_at"]), in_reply_to=numbers.get(row["in_reply_to"]))
        db.session.add(message)
        db.session.flush()
        numbers[row["message_id"]] = message.id
        if about is not None and row["kind"] == "report":
            about.report_id = message.id

    for row in dataset.table("anomalous/reminders"):
        if row["alert_id"] in alerts:
            db.session.add(Reminder(crew_id=crew[row["crew_id"]].id, alert_id=alerts[row["alert_id"]].id,
                                    text=row["text"], due_at=when(row["due_at"]), done_at=when(row["done_at"])))

    stamp = mission["demo_now"]           # the dial starts where the dataset's link window puts it
    window = next((w for w in dataset.table("reference/link_windows") if w["start"] <= stamp <= w["end"]), None)
    if window:
        db.session.get(MissionState, 1).stop = window["stop"]
    db.session.commit()
```

- [ ] **Step 5:** In `app.py`, change the signature and add the switch. The function becomes:

```python
def create_app(database_url=None, morning=None):
    load_dotenv()
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = (
        database_url or os.getenv("DATABASE_URL", "sqlite:///lighttime.db"))
    # Morning mode loads the demo morning and starts the mission clock. Run one process only:
    # the clock lives in this process's memory.
    app.config["MORNING"] = os.getenv("LIGHTTIME_MORNING") == "1" if morning is None else morning
    CORS(app)
    db.init_app(app)

    from base_station.routes import bp as base_bp
    from command_center.routes import bp as earth_bp
    app.register_blueprint(base_bp, url_prefix="/api/base")
    app.register_blueprint(earth_bp, url_prefix="/api/earth")

    with app.app_context():
        db.create_all()
        seed()
        if app.config["MORNING"]:
            from base_station import morning as demo_morning
            demo_morning.load()
    lighttime.mars_seconds()    # ask JPL once now, so no screen waits on it later
    return app
```

- [ ] **Step 6:** In `base_station/routes.py`:

Add `morning` to the `from base_station import ...` line and `dataset` to the `from common import ...` line.

In the `state` route, after `out["speedup"] = link.SPEEDUP`, add:

```python
    out["mission_day"] = dataset.mission_day(utcnow())
    out["platform"] = dataset.mission()["platform"]
```

In `reset`, after `usual.clear()`, add:

```python
    if current_app.config.get("MORNING"):
        morning.load()       # the demo morning starts again, at 06:30, with its own dial stop
```

- [ ] **Step 7: Old tests.** In `tests/test_contract.py`, the state's key set gains two: change `STOP | {"speedup", "stops"}` to `STOP | {"speedup", "stops", "mission_day", "platform"}`.
- [ ] **Step 8:** `python -m pytest -q`. Expected: `128 passed`. If `test_the_one_open_alert_is_the_resting_heart_rate` fails on the order of ids, print the list and compare it with `raised_at` in `alerts_seed.csv` before changing anything.
- [ ] **Step 9:** Add `LIGHTTIME_MORNING=1` to `.env` (the file is git-ignored). Commit: `feat: the demo morning loads at start and on reset`.

---

### Task 6: Crew objects, history and rule text

Spec R1 (crew), R2, D9. Contract steps 1 and 2.

**Files:** new `base_station/console.py`; `app.py`; `base_station/routes.py` (the old crew board leaves); `tests/test_console.py`; `tests/test_contract.py`.

- [ ] **Step 1: Write the failing tests.** Add to the end of `tests/test_console.py`:

```python
def test_the_crew_overview_gets_the_cards_it_already_draws(morning):
    crew = morning.get("/api/base/crew").get_json()
    assert [member["id"] for member in crew] == ["C1", "C2", "C3", "C4"]
    c1 = crew[0]
    assert (c1["name"], c1["role"], c1["suit_id"], c1["state"]) == ("Okafor", "Commander", "LT-01", "ALERT")
    assert c1["baseline"]["hr_rest"] == [52, 64] and c1["baseline"]["bp"] == [[108, 122], [66, 78]]
    assert c1["baseline"]["pvt_ms"] == 265
    today = c1["today"]
    assert (today["hr_rest"], today["spo2"], today["temp_c"], today["resp"], today["sleep_h"]) == (84, 97, 37.2, 17, 5.1)
    assert (today["dose_mSv_day"], today["dose_mSv_mission"]) == (0.51, 81.0)
    # Okafor has not checked in yet today, so what he typed yesterday still stands
    assert today["symptoms"] == ["headache", "short sleep"] and c1["checkin_from"] == "2026-11-13"
    assert c1["metric_states"]["hr_rest"] == "ALERT" and c1["metric_states"]["spo2"] == "OK"
    assert all(member["state"] in ("OK", "WATCH", "ALERT") for member in crew)
    assert morning.get("/api/base/crew/C1").get_json()["today"] == today
    assert morning.get("/api/base/crew/C9").status_code == 404


def test_the_trend_chart_gets_seven_days_and_the_band(morning):
    history = morning.get("/api/base/crew/C1/history?metric=hr_rest").get_json()
    assert len(history["days"]) == 7 and [day["value"] for day in history["days"]][-3:] == [80, 82, 84]
    assert history["days"][-1]["date"] == "2026-11-14" and history["band"] == [52, 64]
    assert (history["unit"], history["days_out_of_band"], history["simulated"]) == ("bpm", 3, True)
    month = morning.get("/api/base/crew/C1/history?metric=mood&days=99").get_json()
    assert len(month["days"]) == 30 and month["band"] is None


def test_a_bad_history_request_says_which_field(morning):
    bad = morning.get("/api/base/crew/C1/history?metric=glucose")
    assert bad.status_code == 400 and bad.get_json()["field"] == "metric"
    assert morning.get("/api/base/crew/C9/history?metric=mood").status_code == 404


def test_every_rule_prints_its_words_and_its_source(morning):
    printed = morning.get("/api/base/thresholds").get_json()
    assert set(printed) == {"hr_rest", "bp_sys", "bp_dia", "spo2", "temp_c", "resp", "sleep_h", "mood", "pvt_ms",
                            "dose_mSv_day", "co2_mmHg"}
    assert all(set(rule) == {"unit", "watch", "alert", "source"} and rule["source"] for rule in printed.values())
    assert printed["hr_rest"]["source"].startswith("OCHMO Exercise Overview brief")


def test_a_normal_start_has_no_morning(client):
    assert client.get("/api/base/alerts").get_json() == []
    assert client.get("/api/base/state").get_json()["stop"] == "station"
    assert [member["id"] for member in client.get("/api/base/crew").get_json()] == ["C1", "C2", "C3", "C4"]
```

- [ ] **Step 2:** `python -m pytest tests/test_console.py -q`. Expected: 5 failed (the crew `id` is a number, 404 on the new routes), 4 passed.
- [ ] **Step 3:** In `base_station/routes.py`, delete the `crew_board` route (the function under `@bp.get("/crew")`). Keep `_latest` and `_level`: the new board uses them.
- [ ] **Step 4:** Create `base_station/console.py`:

```python
"""The console's side of the ship: each person's day against their own band, the trend chart
and the printed rules. Shapes follow the frontend owner's API contract of 14 November."""
import functools
from datetime import timedelta

from flask import jsonify, request

from base_station import scoring, usual
from base_station.morning import when
from base_station.routes import _latest, _level, bp, crew_or_404
from common import dataset
from common.models import Checkin, Crew, iso, utcnow

COLUMN = {"hr_rest": "hr_rest_bpm", "bp_sys": "bp_sys_mmhg", "bp_dia": "bp_dia_mmhg", "spo2": "spo2_pct",
          "temp_c": "core_temp_c", "resp": "resp_rpm", "sleep_h": "sleep_h", "mood": "mood", "pvt_ms": "pvt_ms",
          "dose_mSv_day": "dose_msv_day"}                 # console metric -> column in daily_summary.csv
LABEL = {"hr_rest": "resting heart rate", "bp_sys": "systolic blood pressure", "bp_dia": "diastolic blood pressure",
         "spo2": "blood oxygen", "temp_c": "temperature", "resp": "breathing rate", "sleep_h": "sleep",
         "mood": "mood", "pvt_ms": "reaction time", "dose_mSv_day": "radiation dose"}
TYPED = ("mood", "pvt_ms", "bp_sys", "bp_dia")            # what a check-in gives; the rest comes from the suit


def bad(message, field):
    return jsonify(error=message, field=field), 400


@functools.lru_cache(maxsize=None)
def _last_day():
    return max(row["date"] for row in dataset.table("anomalous/daily_summary"))


def today():
    """The mission date as text. The dataset stops on its last day, so a later clock shows that day."""
    return min(utcnow().date().isoformat(), _last_day())


def daily(code, day):
    """One person's daily rows up to and including `day`, oldest first."""
    return [row for row in dataset.table("anomalous/daily_summary")
            if row["crew_id"] == code and row["date"] <= day]


def bands(code):
    """{metric: [low, high]} from the pre-flight baselines, or one number where there is no band."""
    out = {}
    for row in dataset.table("reference/baselines"):
        if row["crew_id"] == code:
            out[row["metric"]] = [float(row["low"]), float(row["high"])] if row["low"] else float(row["point"])
    return out


def baseline(code):
    own = bands(code)
    out = {metric: own[metric] for metric in ("hr_rest", "spo2", "temp_c", "resp", "sleep_h")}
    out.update(bp=[own["bp_sys"], own["bp_dia"]], pvt_ms=own["pvt_ms"], vo2max_ml_min_kg=own["vo2max_ml_min_kg"])
    return out


def day_of(crew, day):
    """One person's day: the values, the symptoms, the date of the check-in they come from, the week's rows.
    Until today's check-in exists, what the person typed at the last one stands (spec D9)."""
    rows = daily(crew.code, day)[-7:]
    row = rows[-1] if rows and rows[-1]["date"] == day else None
    values = {metric: dataset.num(row[column]) if row else None for metric, column in COLUMN.items()}
    checkin = (Checkin.query.filter(Checkin.crew_id == crew.id, Checkin.day <= day)
               .order_by(Checkin.day.desc()).first())
    if checkin is None:
        return values, [], None, rows
    for metric in TYPED:
        if getattr(checkin, metric) is not None:
            values[metric] = getattr(checkin, metric)
    if checkin.day == day and checkin.sleep_h is not None:
        values["sleep_h"] = checkin.sleep_h
    return values, checkin.symptoms or [], checkin.day, rows


def states_of(crew, values, symptoms, rows):
    """OK, WATCH or ALERT for each of the ten daily measurements."""
    own, out = bands(crew.code), {}
    for metric in scoring.METRICS:
        band = own[metric] if metric in scoring.BANDED else None
        week = [dataset.num(row[COLUMN[metric]]) for row in rows[:-1]] + [values[metric]]
        days_out = scoring.days_out_of_band(week, band) if band else 0
        out[metric] = scoring.score(metric, values[metric], band, days_out, bool(symptoms), own["pvt_ms"])
    return out


def crew_dict(crew):
    day = today()
    values, symptoms, checkin_day, rows = day_of(crew, day)
    states = states_of(crew, values, symptoms, rows)
    flagged = [LABEL[metric] for metric in scoring.METRICS if states[metric] in ("WATCH", "ALERT")]
    note = "All in band"
    if flagged:
        note = "Out of band: " + ", ".join(flagged) + (". Symptoms: " + ", ".join(symptoms) if symptoms else "")
    dose = next((row for row in dataset.table("anomalous/radiation_daily") if row["date"] == day), None)
    latest = _latest(crew.id, typed=False)
    quiet = iso(when(dataset.mission()["demo_now"]) - timedelta(minutes=1))   # the dataset's last minute row
    return {
        "id": crew.code, "name": crew.name, "role": crew.role, "suit_id": crew.suit_id,
        "state": scoring.worst([state for state in states.values() if state]), "note": note,
        "baseline": baseline(crew.code),
        "today": {"hr_rest": values["hr_rest"], "bp": [values["bp_sys"], values["bp_dia"]],
                  "spo2": values["spo2"], "temp_c": values["temp_c"], "resp": values["resp"],
                  "sleep_h": values["sleep_h"], "mood": values["mood"], "pvt_ms": values["pvt_ms"],
                  "symptoms": symptoms, "dose_mSv_day": values["dose_mSv_day"],
                  "dose_mSv_mission": dataset.num(dose["dose_msv_mission"]) if dose else None},
        "metric_states": states, "checkin_from": checkin_day,
        "last_packet_at": latest["at"] if latest else quiet,
        # the ship AI's side of the same person
        "level": _level(crew.id), "latest": latest, "typed": _latest(crew.id, typed=True),
        "usual": {"heart_rate": usual.usual_range(crew.id)},
    }


def history(crew, metric, days):
    day = today()
    points = [{"date": row["date"], "value": dataset.num(row[COLUMN[metric]])}
              for row in daily(crew.code, day)[-days:]]
    if points and points[-1]["date"] == day:
        points[-1]["value"] = day_of(crew, day)[0][metric]
    band = bands(crew.code)[metric] if metric in scoring.BANDED else None
    return {"crew_id": crew.code, "metric": metric, "unit": scoring.rule_text()[metric]["unit"], "band": band,
            "days": points,
            "days_out_of_band": scoring.days_out_of_band([p["value"] for p in points], band) if band else 0,
            "simulated": True}


@bp.get("/crew")
def crew_board():
    return jsonify([crew_dict(crew) for crew in Crew.query.order_by(Crew.id)])


@bp.get("/crew/<ref>")
def one_crew(ref):
    return jsonify(crew_dict(crew_or_404(ref)))


@bp.get("/crew/<ref>/history")
def crew_history(ref):
    crew = crew_or_404(ref)
    metric = request.args.get("metric")
    if metric not in COLUMN:
        return bad("metric must be one of " + ", ".join(COLUMN), "metric")
    days = min(max(request.args.get("days", 7, type=int), 1), 30)
    return jsonify(history(crew, metric, days))


@bp.get("/thresholds")
def thresholds():
    return jsonify(scoring.rule_text())
```

- [ ] **Step 5:** In `app.py`, load the console's routes onto the same blueprint before it is registered. Change the first import inside `create_app` to:

```python
    from base_station import console  # noqa: F401  (adds the console's routes to the ship's blueprint)
    from base_station.routes import bp as base_bp
```

- [ ] **Step 6: Old tests.** In `tests/test_contract.py`, the crew member's key set becomes:

```python
    assert set(member) == {"id", "name", "role", "suit_id", "state", "note", "baseline", "today", "metric_states",
                           "checkin_from", "last_packet_at", "level", "latest", "typed", "usual"}
```

No other old test should change: the board still carries `name`, `level`, `latest`, `typed` and `usual`.
- [ ] **Step 7:** `python -m pytest -q`. Expected: `133 passed`. If Flask raises "The setup method 'route' can no longer be called on the blueprint", `console` was imported after the blueprint was registered: check Step 5. Commit: `feat: crew objects, history and rule text for the console`.

---

### Task 7: The station strip and space weather

Spec R1, D14. Review F6f. Real NASA values are marked as real.

**Files:** `base_station/console.py`, `tests/test_console.py`.

- [ ] **Step 1: Write the failing tests.** Add to the end of `tests/test_console.py`:

```python
def test_the_station_strip_says_which_numbers_are_nasas(morning):
    station = morning.get("/api/base/station").get_json()
    co2 = station["co2_mmHg"]
    assert 1.0 < co2["value"] < 6.0 and co2["simulated"] is False
    assert co2["state"] == ("ALERT" if co2["value"] >= 4.5 else "WATCH" if co2["value"] >= 2.8 else "OK")
    assert station["temp_c"]["simulated"] is False and station["rh_pct"]["simulated"] is False
    assert station["ppo2_mmHg"]["simulated"] is True and station["pressure_kPa"]["simulated"] is True
    assert station["ppo2_mmHg"]["state"] is None                     # the ship has no sourced limit for it
    assert station["dose_mSv_today"] == {"value": 0.51, "state": "OK", "note": "ALERT over 2", "simulated": True}
    assert station["updated_at"].startswith("2026-11-14T06:2") and "Environmental Data App" in station["source"]


def test_the_solar_event_is_shown_and_marked_simulated(morning):
    weather = morning.get("/api/base/space-weather").get_json()
    assert (weather["state"], weather["event_at"], weather["simulated"]) == ("WATCH", "2026-11-14T05:58:00Z", True)
    assert weather["headline"] == "SEP event in progress" and "DONKI" in weather["source"]
```

- [ ] **Step 2:** `python -m pytest tests/test_console.py -q`. Expected: 2 failed with 404, 9 passed.
- [ ] **Step 3:** Add to the end of `base_station/console.py`:

```python
CABIN_SOURCE = ("Cabin CO2, temperature and humidity: NASA OSDR Environmental Data App, Rodent Research 1 "
                "(2014), replayed. CO2 is NASA's ppm converted with the cabin pressure. Oxygen, pressure and "
                "the dose in mSv are simulated.")
WEATHER_SOURCE = "Simulated event, laid out like a NASA DONKI SEP record"


@functools.lru_cache(maxsize=None)
def _cabin():
    """Hab A's rows, oldest first. Its CO2, temperature and humidity are the NASA record."""
    return [row for row in dataset.table("anomalous/cabin_env") if row["habitat_id"] == "H1"]


@bp.get("/station")
def station():
    now = iso(utcnow())
    row = next((r for r in reversed(_cabin()) if r["ts"] <= now), _cabin()[0])
    real = dataset.listed(row["real_fields"])
    dose = next((r for r in dataset.table("anomalous/radiation_daily") if r["date"] == today()), None)
    co2, dose_day = dataset.num(row["co2_mmhg"]), dataset.num(dose["dose_msv_day"]) if dose else None

    def reading(column, field):
        return {"value": dataset.num(row[column]), "state": None, "simulated": field not in real}

    return jsonify({
        "co2_mmHg": {"value": co2, "state": "ALERT" if co2 >= 4.5 else "WATCH" if co2 >= 2.8 else "OK",
                     "note": "WATCH from 2.8, ALERT from 4.5", "simulated": "co2_ppm" not in real},
        "ppo2_mmHg": reading("ppo2_mmhg", "ppo2_mmhg"),
        "pressure_kPa": reading("pressure_kpa", "pressure_kpa"),
        "temp_c": reading("temp_c", "temp_c"),
        "rh_pct": reading("rh_pct", "rh_pct"),
        "dose_mSv_today": {"value": dose_day, "state": "ALERT" if dose_day is not None and dose_day > 2 else "OK",
                           "note": "ALERT over 2", "simulated": True},
        "updated_at": row["ts"], "habitat": row["habitat_id"], "simulated": True, "source": CABIN_SOURCE,
    })


@bp.get("/space-weather")
def space_weather():
    now = iso(utcnow())
    event = next((e for e in dataset.table("anomalous/space_weather_events")
                  if e["event_time"] <= now <= e["end_time"]), None)
    if event is None:
        return jsonify(state="OK", headline="No solar particle event", advisory=None, event_at=None,
                       source=WEATHER_SOURCE, simulated=True)
    return jsonify(state=event["state"], headline=event["headline"], advisory=event["advisory"],
                   event_at=event["event_time"], source=WEATHER_SOURCE, simulated=True)
```

- [ ] **Step 4:** `python -m pytest -q`. Expected: `135 passed`. Commit: `feat: station strip and space weather, each value marked real or simulated`.

---

### Task 8: Check-ins

Spec R3, D9. Contract step 3.

**Files:** `base_station/console.py`, `tests/test_console.py`.

- [ ] **Step 1: Write the failing tests.** Add to the end of `tests/test_console.py`:

```python
GOOD = {"mood": 2, "sleep_h": 5.1, "symptoms": ["headache"], "note": "", "pvt_ms": 312}


def test_the_morning_board_knows_who_has_checked_in(morning):
    assert morning.get("/api/base/checkins/today").get_json() == {
        "date": "2026-11-14", "done": ["C2", "C3", "C4"], "due": ["C1"], "streak": 12, "next_badge_at": 14}


def test_a_check_in_is_saved_scored_and_copied_to_the_open_alert(morning):
    saved = morning.post("/api/base/crew/C1/checkins", json={**GOOD, "bp_sys": 128, "bp_dia": 82})
    body = saved.get_json()
    assert saved.status_code == 201
    assert (body["crew_id"], body["first_today"], body["streak"], body["open_alert_id"]) == ("C1", True, 13, "A1")
    assert body["metric_states"] == {"sleep_h": "ALERT", "mood": "ALERT", "pvt_ms": "ALERT"}
    c1 = morning.get("/api/base/crew/C1").get_json()
    assert c1["today"]["bp"] == [128, 82] and c1["today"]["mood"] == 2 and c1["today"]["pvt_ms"] == 312
    assert c1["checkin_from"] == "2026-11-14"
    assert c1["metric_states"] == {      # the contract's own example for Okafor, value for value
        "hr_rest": "ALERT", "bp_sys": "ALERT", "bp_dia": "ALERT", "spo2": "OK", "temp_c": "ALERT", "resp": "OK",
        "sleep_h": "ALERT", "mood": "ALERT", "pvt_ms": "ALERT", "dose_mSv_day": "OK"}
    assert morning.get("/api/base/alerts/A1").get_json()["symptoms"] == ["headache"]
    assert morning.get("/api/base/checkins/today").get_json()["due"] == []


def test_a_second_check_in_the_same_day_replaces_the_first(morning):
    morning.post("/api/base/crew/C1/checkins", json=GOOD)
    again = morning.post("/api/base/crew/C1/checkins", json={**GOOD, "mood": 4}).get_json()
    assert (again["first_today"], again["streak"]) == (False, 13)
    today = morning.get("/api/base/crew/C1").get_json()["today"]
    assert today["mood"] == 4 and today["bp"] == [110, 71]      # no cuff reading was sent: yesterday's stands


def test_a_bad_check_in_names_the_field(morning):
    for field, value in (("mood", 6), ("mood", 2.5), ("sleep_h", 25), ("note", "x" * 501), ("pvt_ms", 50),
                         ("symptoms", ["dizzy"]), ("bp_sys", "high")):
        bad = morning.post("/api/base/crew/C1/checkins", json={**GOOD, field: value})
        assert bad.status_code == 400 and bad.get_json()["field"] == field, field
    assert morning.post("/api/base/crew/C9/checkins", json=GOOD).status_code == 404
    assert morning.get("/api/base/checkins/today").get_json()["due"] == ["C1"]
```

- [ ] **Step 2:** `python -m pytest tests/test_console.py -q`. Expected: 4 failed with 404 or 405, 11 passed.
- [ ] **Step 3:** In `base_station/console.py`:

Change the imports: add `import collections`; change `from datetime import timedelta` to `from datetime import date, timedelta`; add `alert_code` and `body` to the names imported from `base_station.routes`; add `Alert` and `db` to the names imported from `common.models`.

Add to the end of the file:

```python
SYMPTOMS = {"headache", "short sleep", "congestion", "nausea", "blurred vision", "back pain"}


def _number(value, low, high, whole=False):
    """True for a real number in range. JSON true and false are not numbers here."""
    kind = int if whole else (int, float)
    return isinstance(value, kind) and not isinstance(value, bool) and low <= value <= high


def streak(day):
    """Days in a row, ending today or yesterday, on which every crew member checked in."""
    everyone = Crew.query.count()
    done = collections.Counter(found for (found,) in db.session.query(Checkin.day))
    days, at = (1 if done[day] == everyone else 0), date.fromisoformat(day) - timedelta(days=1)
    while done[at.isoformat()] == everyone:
        days, at = days + 1, at - timedelta(days=1)
    return days


@bp.get("/checkins/today")
def checkins_today():
    day, crew = today(), Crew.query.order_by(Crew.id).all()
    done = {crew_id for (crew_id,) in db.session.query(Checkin.crew_id).filter_by(day=day)}
    days = streak(day)
    return jsonify(date=day, done=[c.code for c in crew if c.id in done],
                   due=[c.code for c in crew if c.id not in done], streak=days,
                   next_badge_at=(days // 7 + 1) * 7)       # assumed: a badge every seventh day (spec Q3)


@bp.post("/crew/<ref>/checkins")
def post_checkin(ref):
    crew, sent = crew_or_404(ref), body()
    symptoms, note = sent.get("symptoms", []), sent.get("note") or ""
    if not _number(sent.get("mood"), 1, 5, whole=True):
        return bad("mood is a whole number from 1 to 5", "mood")
    if not _number(sent.get("sleep_h"), 0, 24):
        return bad("sleep_h is from 0 to 24", "sleep_h")
    if not (isinstance(symptoms, list) and all(item in SYMPTOMS for item in symptoms)):
        return bad("symptoms come from: " + ", ".join(sorted(SYMPTOMS)), "symptoms")
    if not isinstance(note, str) or len(note) > 500:
        return bad("note is at most 500 characters", "note")
    if sent.get("pvt_ms") is not None and not _number(sent["pvt_ms"], 100, 3000, whole=True):
        return bad("pvt_ms is a whole number from 100 to 3000", "pvt_ms")
    for field in ("bp_sys", "bp_dia"):
        if sent.get(field) is not None and not _number(sent[field], 30, 260):
            return bad(f"{field} is a cuff reading in mmHg", field)

    day = today()
    row = Checkin.query.filter_by(crew_id=crew.id, day=day).first()
    first = row is None
    if first:
        row = Checkin(crew_id=crew.id, day=day)
        db.session.add(row)
    earlier = (Checkin.query.filter(Checkin.crew_id == crew.id, Checkin.day < day)
               .order_by(Checkin.day.desc()).first())
    for field in ("bp_sys", "bp_dia"):       # the last cuff reading stands until a new one is sent
        if sent.get(field) is not None:
            setattr(row, field, float(sent[field]))
        elif getattr(row, field) is None and earlier is not None:
            setattr(row, field, getattr(earlier, field))
    row.completed_at, row.mood, row.sleep_h = utcnow(), sent["mood"], float(sent["sleep_h"])
    row.pvt_ms, row.symptoms, row.note = sent.get("pvt_ms"), symptoms, note
    for alert in Alert.query.filter_by(crew_id=crew.id, cleared_at=None):
        alert.symptoms = symptoms
    db.session.commit()

    values, _, _, rows = day_of(crew, day)
    states = states_of(crew, values, symptoms, rows)
    open_alert = (Alert.query.filter_by(crew_id=crew.id, cleared_at=None)
                  .order_by(Alert.at.desc(), Alert.id.desc()).first())
    return jsonify(crew_id=crew.code, completed_at=iso(row.completed_at), first_today=first, streak=streak(day),
                   metric_states={metric: states[metric] for metric in ("sleep_h", "mood", "pvt_ms")},
                   open_alert_id=alert_code(open_alert) if open_alert else None), 201
```

- [ ] **Step 4:** `python -m pytest -q`. Expected: `139 passed`. If `streak` is 11 or 13 in the first test, print `collections.Counter` of check-in days from the morning before changing the rule: the dataset has one missed check-in on 1 November that ends the run, and the count of 12 depends on it. Commit: `feat: morning check-ins with the crew's streak`.

---

### Task 9: The alert loop

Spec R4. Contract step 4: the 7-day bundle, the thread, accepting the plan, reminders.

**Files:** `base_station/console.py`, `base_station/routes.py` (`send_report`), `tests/test_console.py`.

- [ ] **Step 1: Write the failing tests.** Add to the end of `tests/test_console.py`:

```python
from datetime import timedelta      # move these two imports to the top of the file

from common import models


def later(seconds):
    """Let mission time pass: long enough for a message to cross at 60 times speed."""
    models.set_clock(models.utcnow() + timedelta(seconds=seconds))


def reply_and_accept(morning):
    morning.post("/api/base/alerts/A1/ack", json={"by": "Okafor"})
    morning.post("/api/base/alerts/A1/send")
    later(30)
    report = morning.get("/api/earth/inbox").get_json()["messages"][0]
    morning.post("/api/earth/reply",
                 json={"message_id": report["id"], "text": "Temperature every 4 hours.", "from": "Dr. Adeyemi"})
    later(30)
    return morning.post("/api/base/alerts/A1/accept-plan", json={"by": "Okafor"}).get_json()


def test_sending_an_alert_puts_the_week_in_the_report_and_one_message_in_the_thread(morning):
    morning.post("/api/base/alerts/A1/ack", json={"by": "Okafor", "symptoms": ["headache"]})
    assert morning.post("/api/base/alerts/A1/send").get_json()["stage"] == "sent"
    report = morning.get("/api/base/outbox").get_json()[0]
    assert report["kind"] == "report" and report["payload"]["text"].startswith("Alert bundle")
    week = report["payload"]["bundle"]["days"]
    assert set(week) == {"hr_rest", "bp_sys", "bp_dia", "temp_c", "sleep_h"}
    assert [day["value"] for day in week["hr_rest"]][-3:] == [80, 82, 84]
    thread = morning.get("/api/base/alerts/A1/thread").get_json()
    assert thread["alert_id"] == "A1"
    assert [(m["from"], m["author"], m["status"]) for m in thread["messages"]] == [("crew", "Okafor", "in_flight")]


def test_a_reply_takes_the_light_time_and_only_then_can_the_plan_be_accepted(morning):
    morning.post("/api/base/alerts/A1/ack", json={"by": "Okafor"})
    morning.post("/api/base/alerts/A1/send")
    early = morning.post("/api/base/alerts/A1/accept-plan", json={"by": "Okafor"}).get_json()
    assert early["alert"]["stage"] == "sent" and early["reminders"] == []           # nothing to accept yet
    later(30)
    report = morning.get("/api/earth/inbox").get_json()["messages"][0]
    morning.post("/api/earth/reply",
                 json={"message_id": report["id"], "text": "Temperature every 4 hours.", "from": "Dr. Adeyemi"})
    assert morning.get("/api/base/alerts/A1").get_json()["stage"] == "sent"           # the reply is still on its way
    later(30)
    assert morning.get("/api/base/alerts/A1").get_json()["stage"] == "replied"
    thread = morning.get("/api/base/alerts/A1/thread").get_json()["messages"]
    assert [(m["from"], m["author"]) for m in thread] == [("crew", "Okafor"), ("ground", "Dr. Adeyemi")]


def test_accepting_the_plan_resolves_the_alert_and_sets_four_reminders(morning):
    done = reply_and_accept(morning)
    assert done["alert"]["stage"] == "resolved"
    assert [r["text"] for r in done["reminders"]] == ["Take temperature"] * 4
    waiting = morning.get("/api/base/reminders?crew=C1&open=1").get_json()
    assert len(waiting) == 4 and waiting[0]["due_at"] < waiting[1]["due_at"] and waiting[0]["crew_id"] == "C1"
    ticked = morning.post(f"/api/base/reminders/{waiting[0]['id']}/done").get_json()
    assert ticked["done_at"] is not None
    assert len(morning.get("/api/base/reminders?open=1").get_json()) == 3
    assert morning.post("/api/base/reminders/R999/done").status_code == 404
    assert morning.get("/api/base/alerts?open=1").get_json() == []


def test_a_typed_message_joins_its_alerts_thread(morning):
    morning.post("/api/base/messages", json={"text": "Headache is worse.", "from": "Okafor", "alert_id": "A1"})
    thread = morning.get("/api/base/alerts/A1/thread").get_json()["messages"]
    assert [(m["from"], m["text"], m["kind"]) for m in thread] == [("crew", "Headache is worse.", "message")]
    old = morning.get("/api/base/alerts/A7/thread").get_json()["messages"]
    assert old[0]["kind"] == "report" and old[-1]["from"] == "ground"       # the blackout alert's history
```

- [ ] **Step 2:** `python -m pytest tests/test_console.py -q`. Expected: 4 failed (`KeyError: 'text'` on the report, 404 on the new routes), 15 passed.
- [ ] **Step 3:** In `base_station/routes.py`, a console alert sends the week and not a strip of readings. Replace `send_report` with:

```python
def send_report(alert, look=None):
    state = current_state()
    crew = db.session.get(Crew, alert.crew_id)
    payload = reports.build(alert, crew, state, look, usual.usual_range(crew.id))
    if alert.metric:                       # a console rule raised it: Earth gets seven days and the check-in
        from base_station import console   # imported here because console imports this module
        payload.update(bundle=console.bundle(crew), text=console.BUNDLE_TEXT, asked_ahead=[])
    message = link.send("to_earth", "report", payload, state["delay_s"], state["link_up"], priority=0)
    alert.report_id = message.id
    db.session.commit()
```

- [ ] **Step 4:** In `base_station/console.py`:

Change the imports: add `alert_dict`, `alert_or_404`, `person`, `stage`, `tell_earth` and `timeline` to the names from `base_station.routes`; add `link` to `from common import dataset`; add `LinkMessage` and `Reminder` to the names from `common.models`.

Add to the end of the file:

```python
BUNDLE = ("hr_rest", "bp_sys", "bp_dia", "temp_c", "sleep_h")
BUNDLE_TEXT = "Alert bundle: 7 days of heart rate, blood pressure, temperature and sleep, plus today's check-in."


def bundle(crew):
    """What goes to the flight surgeon with a console alert."""
    day = today()
    values, symptoms, checkin_day, _ = day_of(crew, day)
    return {"days": {metric: history(crew, metric, 7)["days"] for metric in BUNDLE},
            "today": {**values, "symptoms": symptoms, "checkin_from": checkin_day}}


def _line(message):
    """One line of text for a message that carries none of its own."""
    payload = message.payload
    if payload.get("text"):
        return payload["text"]
    if message.kind == "report":
        return f"{payload.get('crew', 'Crew')}: {payload.get('reason', 'alert')}. Handoff report attached."
    event = payload.get("event")
    if event == "acknowledged":
        return f"Acknowledged by {payload.get('by', 'crew')}."
    if event == "step":
        return f"Step done: {payload.get('step')}."
    if event == "escalated":
        return f"Now {payload.get('level')}: {payload.get('reason')}."
    if event == "resolved":
        return f"Resolved by {payload.get('by', 'crew')}." + (f" {payload['note']}" if payload.get("note") else "")
    return message.kind


def thread_message(message, alert, now):
    sent, ours = link.to_dict(message, now), message.direction == "to_earth"
    payload = message.payload
    return {"id": f"M{message.id}", "alert_id": alert_code(alert), "from": "crew" if ours else "ground",
            "author": payload.get("from") or payload.get("crew") or payload.get("by")
                      or ("Ship" if ours else "Flight surgeon"),
            "text": _line(message), "kind": message.kind, "sent_at": sent["sent_at"],
            "arrived_at": sent["deliver_at"] if sent["status"] == "delivered" else None, "status": sent["status"]}


@bp.get("/alerts/<alert_id>/thread")
def alert_thread(alert_id):
    """Everything the ship sent about one alert, and everything from Earth that has arrived. Oldest first."""
    alert, now = alert_or_404(alert_id), utcnow()
    rows = [m for m in LinkMessage.query.order_by(LinkMessage.created_at, LinkMessage.id)
            if m.payload.get("alert_id") == alert.id
            and (m.direction == "to_earth" or (m.deliver_at is not None and m.deliver_at <= now))]
    return jsonify(alert_id=alert_code(alert), messages=[thread_message(m, alert, now) for m in rows])


def reminder_dict(reminder):
    return {"id": f"R{reminder.id}", "crew_id": db.session.get(Crew, reminder.crew_id).code,
            "text": reminder.text, "due_at": iso(reminder.due_at), "done_at": iso(reminder.done_at)}


@bp.post("/alerts/<alert_id>/accept-plan")
def accept_plan(alert_id):
    """The crew accepts the flight surgeon's reply. For the demo the plan is always the same four checks."""
    alert = alert_or_404(alert_id)
    if stage(alert, timeline(alert)) != "replied":
        return jsonify(alert=alert_dict(alert), reminders=[])      # a double click changes nothing
    now = utcnow()
    alert.cleared_at, alert.cleared_by = now, person(body().get("by"))
    alert.cleared_note = "Accepted the flight surgeon's plan"
    made = [Reminder(crew_id=alert.crew_id, alert_id=alert.id, text="Take temperature",
                     due_at=now + timedelta(hours=4 * n)) for n in (1, 2, 3, 4)]
    db.session.add_all(made)
    db.session.commit()
    tell_earth(alert, {"event": "resolved", "by": alert.cleared_by, "note": alert.cleared_note})
    return jsonify(alert=alert_dict(alert), reminders=[reminder_dict(r) for r in made])


@bp.get("/reminders")
def reminders():
    query = Reminder.query
    if request.args.get("crew"):
        query = query.filter_by(crew_id=crew_or_404(request.args["crew"]).id)
    if request.args.get("open") == "1":
        query = query.filter(Reminder.done_at.is_(None))
    return jsonify([reminder_dict(r) for r in query.order_by(Reminder.due_at, Reminder.id)])


@bp.post("/reminders/<ref>/done")
def reminder_done(ref):
    number = str(ref)[1:] if str(ref)[:1] == "R" else str(ref)
    reminder = db.session.get(Reminder, int(number)) if number.isdigit() else None
    if reminder is None:
        return jsonify(error="not found"), 404
    if reminder.done_at is None:
        reminder.done_at = utcnow()
        db.session.commit()
    return jsonify(reminder_dict(reminder))
```

- [ ] **Step 5:** `python -m pytest -q`. Expected: `143 passed`. Two things to check by reading if a loop test fails. The reply reaches stage `replied` only because Earth's reply names the report (`message_id`), which is how the alert's number travels back. And 30 seconds of mission clock is enough only because a Mars delay plays 60 times faster (about 11 seconds): if the dial is not on Mars after the morning loads, Task 5 is where to look.
- [ ] **Step 6:** Commit: `feat: the alert loop: 7-day bundle, thread, accepted plan and reminders`.

---

### Task 10: An estimated blood pressure never alarms

Ship AI spec A10. Review F2: on 30 healthy days the shirt's once-a-minute estimate sat in the hospital bands on 54,021 of 168,600 minutes.

**Files:** `base_station/limits.json`, `base_station/rules.py`, `tests/test_rules.py`.

- [ ] **Step 1: Write the failing test.** Add to the end of `tests/test_rules.py`:

```python
def test_an_estimated_blood_pressure_from_the_suit_never_alarms(client):
    for _ in range(6):
        raised = client.post("/api/base/readings", json={"crew_id": 1, "bp_sys": 95}).get_json()["alerts"]
    assert raised == [] and client.get("/api/base/alerts").get_json() == []
    typed = client.post("/api/base/readings",
                        json={"crew_id": 1, "source": "typed", "bp_sys": 88}).get_json()["alerts"]
    assert [alert["level"] for alert in typed] == ["warning"]         # a cuff reading typed by the crew still counts
```

- [ ] **Step 2:** `python -m pytest tests/test_rules.py -q`. Expected: 1 failed (after five readings a warning is open, so the list of alerts is not empty), 9 passed. If `client` is not available in that file, it is: fixtures come from `conftest.py`.
- [ ] **Step 3:** In `base_station/limits.json`, inside `"bp_sys"`, after the `"bands"` list, add:

```json
      "typed_only": true,
      "why_typed_only": "The shirt estimates systolic pressure once a minute. Judged with these hospital bands on 30 healthy days for four crew, it sat in the caution band or worse on 54,021 of 168,600 minutes, mostly asleep (docs/reviews/2026-11-14-dataset-review.md, F2). A cuff reading typed by the crew is still judged."
```

In `base_station/rules.py`, in `evaluate`, change the skip line to:

```python
        if value is None or not cfg.get("alert", True) or (cfg.get("typed_only") and not typed):
            continue
```

- [ ] **Step 4:** `python -m pytest -q`. Expected: `144 passed`. Commit: `fix: the suit's blood pressure estimate no longer raises an alarm`.

---

### Task 11: LIGHTTIME by name

Ship AI spec A1 to A5. This is Task 1 of `docs/plans/2026-11-14-connect-everything.md`, unchanged in content. Do its Steps 1 to 7 as written there, with these differences:

- [ ] In its Step 1, the edit to `tests/test_contract.py` now reads: add `"ship_ai_role"` to `STOP`, add `"next_step"` to `ALERT`, and add `"ship_ai"` to the state's set beside `"mission_day"` and `"platform"`.
- [ ] Its Step 2 expects 5 failed and 143 passed. Its Step 7 expects `148 passed`.
- [ ] In its Step 4, `alert_dict` is the version from Task 4 of this plan. Put the `todo` line before the `return` and the `"next_step"` entry in the returned dict, as that step says.
- [ ] The `sos` helper its tests call is already in `tests/test_tonight.py`.

Commit: `feat: LIGHTTIME by name, with its parts, role and reasoning`.

---

### Task 12: Documents, then the run-through

**Files:** `docs/specs/2026-11-14-backend-design.md`, `docs/frontend/lighttime-api.ts`, `CLAUDE.md`, `AI_USE.md`, `README.md`.

- [ ] **Step 1: The API table.** In `docs/specs/2026-11-14-backend-design.md`, add one row for each new route (`GET /crew/<id>`, `GET /crew/<id>/history`, `GET /thresholds`, `GET /station`, `GET /space-weather`, `GET /checkins/today`, `POST /crew/<id>/checkins`, `GET /alerts/<id>`, `GET /alerts/<id>/thread`, `POST /alerts/<id>/accept-plan`, `GET /reminders`, `POST /reminders/<id>/done`) and note the changed ones (`GET /crew`, `GET /alerts`, `ack`, `send`, `GET /state`, `POST /reset`). Point to `docs/specs/2026-11-14-console-data-design.md` section 7 for the shapes.
- [ ] **Step 2: The typed client.** In `docs/frontend/lighttime-api.ts`: an alert's `id` and `crew_id` are `string`; add `state: "OK" | "WATCH" | "ALERT" | "RECHECK" | "SOS"`, `stage: "raised" | "acknowledged" | "sent" | "replied" | "resolved"`, `metric: string`, `rule: string | null`, `symptoms: string[]` to `Alert`; add `mission_day: number; platform: string` to `MissionState`. Add at the top: "The console's own types are the authority for Crew, history, station, check-in, thread and reminder shapes. See docs/specs/2026-11-14-console-data-design.md."
- [ ] **Step 3:** In `CLAUDE.md`, change the test count to 148, add `LIGHTTIME_MORNING=1` to the run line, and extend the wall rule: `command_center/` must never import `crew`, `reading`, `alert`, `checkin` or `reminder`. Add one line to `AI_USE.md` (date, backend owner, tool, "console contract: dataset reader, console rules, morning loader, alert loop"). Add the run line to `README.md`.
- [ ] **Step 4: Run it.** `python app.py`, with `LIGHTTIME_MORNING=1` in `.env`. In a second terminal, each line must print what follows it:

```powershell
$api = "http://localhost:5000/api/base"
(irm "$api/state") | select stop, mission_day, platform            # mars 158 ISS
(irm "$api/crew")[0] | select id, name, state                       # C1 Okafor ALERT
(irm "$api/checkins/today") | select due, streak                    # {C1} 12
(irm "$api/alerts?open=1") | select id, metric, stage               # A1 hr_rest raised
(irm "$api/crew/C1/history?metric=hr_rest").days.value              # ... 80 82 84
irm -Method Post "$api/crew/C1/checkins" -ContentType application/json -Body '{"mood":2,"sleep_h":5.1,"symptoms":["headache"],"pvt_ms":312,"bp_sys":128,"bp_dia":82}' | select streak, open_alert_id   # 13 A1
irm -Method Post "$api/alerts/A1/ack" -ContentType application/json -Body '{"by":"Okafor"}' | select stage    # acknowledged
irm -Method Post "$api/alerts/A1/send" | select stage                # sent
```

Wait 12 seconds, then reply as Earth and wait 12 more:

```powershell
$earth = "http://localhost:5000/api/earth"
$report = (irm "$earth/inbox").messages[0]
irm -Method Post "$earth/reply" -ContentType application/json -Body (@{message_id=$report.id; text="Temperature every 4 hours."; from="Dr. Adeyemi"} | ConvertTo-Json)
Start-Sleep 12
(irm "$api/alerts/A1") | select stage                                # replied
(irm -Method Post "$api/alerts/A1/accept-plan" -ContentType application/json -Body '{"by":"Okafor"}').reminders.Count   # 4
irm -Method Post "$api/reset"; (irm "$api/alerts/A1") | select stage # raised
```

- [ ] **Step 5: The ship AI still works beside it.** `irm -Method Post "$api/scenario/start" -ContentType application/json -Body '{"name":"stage"}'`, wait for the SOS, and check `(irm "$api/alerts?open=1") | select id, state, metric`: two alerts, `A1` and a new one with state `SOS` and metric `spo2`. Then `irm -Method Post "$api/reset"`.
- [ ] **Step 6:** `python -m pytest -q` one last time: `148 passed`. Commit: `docs: API table, typed client and run line for the console contract`. Push, and open the pull request into `main` for the reviewer.
- [ ] **Step 7:** Tell the frontend owner the four screens can switch, and send him section 9 of the console data spec. Tell the data owner findings F1, F3 and F4 of the review.

## Not in this plan

- The health data log, phone push and a parsed plan (spec section 8, P1 and P2).
- An Earth screen. The API for it exists and is tested here; who builds the page is spec question Q1.
- Replaying the dataset's vitals through the ship AI. The data owner's harness does that, on the 1 Hz windows only (review F3).
- A heart rate rule that knows the person's activity. It would be the first rule that could catch the dataset's two heart rate events, and it needs evidence on real recordings first (ship AI spec, Later).

## Self-review

- Spec coverage: R1 is Tasks 5, 6, 7 and 8 (first test); R2 is Task 6; R3 is Task 8; R4 is Tasks 4, 5 and 9; R5 is the old-test steps in Tasks 2, 4, 5 and 6. A10 is Task 10. A1 to A5 are Task 11.
- Names used across tasks: `find_crew`, `crew_or_404`, `find_alert`, `alert_or_404`, `alert_code`, `stage`, `alert_dict` (routes); `when`, `load` (morning); `today`, `daily`, `bands`, `day_of`, `states_of`, `crew_dict`, `history`, `bundle`, `BUNDLE_TEXT`, `bad` (console); `score`, `days_out_of_band`, `worst`, `rule_text`, `METRICS`, `BANDED` (scoring); `table`, `num`, `listed`, `mission`, `mission_day`, `ROOT` (dataset); `set_clock`, `Checkin`, `Reminder` (models).
- Known weak points, because nothing was run: the exact number of old tests that need a new expectation in Tasks 2 and 4; the order of `created_at` ties in the seeded threads; whether `reports.why` returns a line starting "Rule: " for every live vital (if not, `rule` is null for that alert, which the contract allows).
