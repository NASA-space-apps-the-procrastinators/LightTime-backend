# Backend Polish: What the Console, the Suit and the Log Still Need

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Use superpowers:test-driven-development inside every task and superpowers:systematic-debugging whenever a count differs.

**Goal:** The backend runs the demo morning as one process, and gives the console, the suit and the health log the fields they still lack.

**Architecture:** One new module, `base_station/log.py`, for the health log. Everything else is a small addition to `base_station/routes.py`, `base_station/console.py`, `base_station/reports.py` and `common/dataset.py`. No table changes, so no database has to be rebuilt for this plan.

**Tech Stack:** Python 3.12 or later (the cloud image is `python:3.12-slim`), Flask 3, Flask-SQLAlchemy 3.1, pytest. No new dependency.

**Spec:** `docs/specs/2026-11-15-demo-day-design.md` (decisions D1 to D16, requirements R1 to R10). Words: `CONTEXT.md`. Why no trained model decides: `docs/adr/0001-rules-decide-learned-models-advise.md`.

**Status of this plan:** written Saturday 14 November at 22:30 by reading the code and the data at `039607f`, and checked against `5c5eff3`, where `main` is merged in (175 tests; pull request #6 has put this branch on `main`). **None of this code has been run.** Counts are sums. Tasks 0 to 5 are yours. Only the host list in Task 4 needs the deployment owner. Tasks 6 and 7 wait for the data owner. Task 8 is optional and has a gate.

## Rules for the person or agent running this

1. One task at a time, in order. Each task ends with the full suite green and a commit.
2. Test first. A new test that passes before the code is written is a wrong test, unless the step says it is a guard.
3. When an old test fails after a change, it must be one of the kinds the step names. If it is another kind, stop and report it.
4. Three failed attempts at one step: stop and report.
5. Build what the step says. Ideas go in a note to the backend owner.
6. No team member's name in code, tests, comments or commit messages.
7. Never print or commit the value of `DATABASE_URL`.
8. A changed or new API field goes into the API table in `docs/specs/2026-11-14-backend-design.md` in the same commit.
9. One line in `AI_USE.md` for each task: date, who, tool, what for.

## File map

| File | Change |
|---|---|
| `base_station/routes.py` | `now` on the state; `raised_by` on an alert; the suit's field names; suit ids |
| `base_station/console.py` | Crew state during a live alert; `simulated` on crew objects and thread messages; `week` on the crew object |
| `base_station/reports.py` | Closing lines for a manual SOS and a sensor check |
| `common/dataset.py` | `last_minutes()`: the last day of the suits' minute rows |
| `base_station/log.py` | new: `GET /api/base/packets`, `GET /api/base/stream-health` |
| `app.py` | imports `base_station.log` so its routes are added |
| `tests/test_demo_day.py` | new, 11 tests |
| `tests/test_log.py` | new, 5 tests |
| `tests/test_contract.py` | three key sets grow |
| `docs/hardware.md`, `docs/specs/2026-11-14-backend-design.md`, `docs/frontend/lighttime-api.ts` | The new fields and routes |
| `Dockerfile` | One worker |

Test counts: start 175, then 182 (Task 1), 186 (Task 2), 191 (Task 3).

---

### Task 0: Start from the merged branch

`main` was merged into this branch at `5c5eff3`, and pull request #6 then put the branch on `main`. So there is nothing to merge. `main` deploys to the host by itself, so one line goes to `main` first, from its own branch and in its own small pull request (Step 3). The rest of this plan goes through a second pull request, opened at the end of Task 5.

- [ ] **Step 1:** `git pull`. `git log --oneline -1` shows `5c5eff3` or a later commit. `python -m pytest -q`. Expected: `175 passed`.
- [ ] **Step 2:** `git status` shows only documents: `CONTEXT.md`, `docs/adr/`, the three `docs/plans/2026-11-15-*.md` files, `docs/specs/2026-11-15-demo-day-design.md`, and one added line in `CLAUDE.md`. Commit them: `docs: the plans and the spec for finishing the app`. Push. If other files show as changed with no real difference, it is line endings: `git add --renormalize .` and look at `git status` again before committing.
- [ ] **Step 3: One worker, now, on its own branch.** The fix must reach `main` tonight without waiting for the rest of this plan, so it gets a branch of its own: `git switch -c fix/one-worker origin/main`. In `Dockerfile`, change `--workers 2 --threads 4` to `--workers 1 --threads 8`, and add a comment above the line: the mission clock lives in the process, so a second worker would run a second clock, reload the morning, and hold a story the other worker cannot stop. Commit: `fix: run the ship as one process`. `git push -u origin fix/one-worker`, and open a pull request from it into `main` that says it is one line, changes no test, and why. Then come back and take the same commit here: `git switch Tj-Backend`, `git cherry-pick fix/one-worker`. `python -m pytest -q`. Expected: `175 passed`.
- [ ] **Step 4:** Tell the data owner, in your own words:
  - Yes to the Earth console routes (the question marked Q6). Conditions: rebase onto `Tj-Backend`; stay inside `command_center/`; read only `link_message`; bring tests; keep the rows already added to the API table.
  - `raised_at` is on every report payload (commit `66b2e8a`), including the ones loaded with the demo morning.
  - Base station ids are strings now: `C1`, `A1`. The new routes already take both forms.
  - One known gap for the rewrite of `/reply`: a reply that names a thread message such as `M75` loses its alert.
  - The request in Task 7 of this plan.

---

### Task 1: What the console still needs: the ship's clock, a red card during a live alert, honest labels, the week

Spec decisions D8 and D12, requirements R2, R3 and R7. Six small things, all read by the console's wiring plan.

**Files:** `base_station/routes.py`, `base_station/console.py`, `base_station/reports.py`, new `tests/test_demo_day.py`, `tests/test_contract.py`.

- [ ] **Step 1: Write the failing tests.** Create `tests/test_demo_day.py`:

```python
from base_station import reports

POOR = {"crew_id": "C3", "spo2": 98, "signal_ok": False}


def test_the_state_carries_the_ships_clock(morning):
    assert morning.get("/api/base/state").get_json()["now"].startswith("2026-11-14T06:30")


def test_a_live_emergency_turns_the_crew_card_red(client):
    before = client.get("/api/base/crew/C3").get_json()["state"]
    for _ in range(5):
        client.post("/api/base/readings", json={"crew_id": "C3", "spo2": 86})
    card = client.get("/api/base/crew/C3").get_json()
    assert before != "ALERT" and (card["state"], card["level"]) == ("ALERT", "emergency")


def test_a_sensor_check_does_not_colour_the_card(client):
    before = client.get("/api/base/crew/C3").get_json()["state"]
    client.post("/api/base/readings", json=POOR)
    assert client.get("/api/base/crew/C3").get_json()["state"] == before


def test_generated_values_say_so(morning):
    assert morning.get("/api/base/crew/C1").get_json()["simulated"] is True
    old = morning.get("/api/base/alerts/A7/thread").get_json()["messages"]
    assert old and all(message["simulated"] for message in old)
    morning.post("/api/base/messages", json={"text": "Checking in.", "from": "Okafor", "alert_id": "A1"})
    assert morning.get("/api/base/alerts/A1/thread").get_json()["messages"][-1]["simulated"] is False


def test_every_alert_ends_by_saying_who_decides(client):
    pressed = client.post("/api/base/sos", json={"crew_id": "C2"}).get_json()
    check = client.post("/api/base/readings", json=POOR).get_json()["alerts"][0]
    assert pressed["why"][-1] == "A person raised this, and a person decides what happens next."
    assert check["why"][-1] == reports.NOT_A_DIAGNOSIS and check["rule"].startswith("a reading with a poor signal")


def test_an_alert_says_who_raised_it(morning):
    assert morning.get("/api/base/alerts/A1").get_json()["raised_by"] == "console"
    pressed = morning.post("/api/base/sos", json={"crew_id": "C2"}).get_json()
    for _ in range(5):
        raised = morning.post("/api/base/readings", json={"crew_id": "C3", "spo2": 86}).get_json()["alerts"]
    assert (pressed["raised_by"], raised[0]["raised_by"]) == ("crew", "lighttime")


def test_the_crew_object_carries_the_week(morning):
    okafor = morning.get("/api/base/crew/C1").get_json()
    week = okafor["week"]
    assert set(week) == set(okafor["metric_states"]) and all(len(days) == 7 for days in week.values())
    assert week["hr_rest"] == [60, 59, 58, 59, 80, 82, 84] and week["hr_rest"][-1] == okafor["today"]["hr_rest"]
    chart = morning.get("/api/base/crew/C1/history?metric=bp_sys&days=7").get_json()
    assert week["bp_sys"] == [day["value"] for day in chart["days"]]
    assert week["bp_sys"][-1] == 110            # no cuff reading yet today, so yesterday's stands
```

- [ ] **Step 2:** `python -m pytest tests/test_demo_day.py -q`. Expected: 6 failed (`KeyError: 'now'`, a state that is not `ALERT`, `KeyError: 'simulated'`, a `why` list that ends with the wrong line, `KeyError: 'raised_by'`, `KeyError: 'week'`), 1 passed. The sensor-check test passes already: it is a guard for the change in Step 4.
- [ ] **Step 3:** In `base_station/routes.py`, in the `state` route, after `out["platform"] = ...`, add:

```python
    out["now"] = iso(utcnow())           # the ship's clock, so a screen never counts down on its own
```

In `alert_dict`, add one entry to the returned dict, after `"auto"`:

```python
        "raised_by": "console" if text else "crew" if alert.vital == "manual" else "lighttime",
```

- [ ] **Step 4:** In `base_station/console.py`, above `states_of`, add:

```python
def week_of(rows, values, metric):
    """Seven daily values, oldest first. The last is today's, with what the person typed carried forward."""
    return [dataset.num(row[COLUMN[metric]]) for row in rows[:-1]] + [values[metric]]
```

and in `states_of` replace the line that builds `week` with `week = week_of(rows, values, metric)`.

Above `crew_dict`, add:

```python
# What an open LIGHTTIME alert does to the person's card. A sensor check is not about the person.
LIVE = {"nominal": "OK", "advisory": "OK", "caution": "WATCH", "warning": "ALERT", "emergency": "ALERT"}
```

In `crew_dict`, add a line after `latest = _latest(crew.id, typed=False)`:

```python
    level = _level(crew.id)
```

change the `"state"` entry to:

```python
        "state": scoring.worst([state for state in states.values() if state] + [LIVE[level]]), "note": note,
```

change `"level": _level(crew.id)` to `"level": level`, and add two entries at the end of the returned dict:

```python
        "week": {metric: week_of(rows, values, metric) for metric in scoring.METRICS},
        "simulated": True,               # the daily values come from the generated month
```

In `thread_message`, add one entry to the returned dict:

```python
            "simulated": bool(payload.get("simulated")),
```

- [ ] **Step 5:** In `base_station/reports.py`, in `why`, replace the two short returns:

```python
    if alert.vital == "manual":
        return ["A crew member pressed SOS. No rule was involved.",
                "A person raised this, and a person decides what happens next."]
    cfg = rules.LIMITS["vitals"].get(alert.vital)
    if cfg is None:
        return ["The sensor signal was not clean, so no reading was judged.",
                "Rule: a reading with a poor signal is never judged, and nothing may alarm for the next ten readings.",
                NOT_A_DIAGNOSIS]
```

- [ ] **Step 6: Old tests.** `python -m pytest -q`. Old failures must be only these kinds:
  - `tests/test_contract.py`: the state's key set gains `"now"`; the crew member's key set gains `"simulated"` and `"week"`; the `ALERT` set gains `"raised_by"`.
  - `tests/test_tonight.py`, the test that compares the whole `why` list of a manual SOS (line 70 today): the list gains the new second line.
  - A test that compares the whole `why` list of a sensor check, if there is one, gains the rule line and the closing line.

  Anything else, stop and report.
- [ ] **Step 7:** `python -m pytest -q`. Expected: `182 passed`. Add `now`, `simulated`, `raised_by` and `week` to the API table in `docs/specs/2026-11-14-backend-design.md`. In `docs/frontend/lighttime-api.ts` add `now: string` to `MissionState`, `raised_by: "console" | "lighttime" | "crew"` to `Alert`, and `week: Record<string, (number | null)[]>` and `simulated: boolean` to the crew type. Commit: `feat: the ship's clock, a red card during a live alert, simulated labels, the week`.

---

### Task 2: The suit keeps its own field names

Spec decision D3, requirement R6. The suit's firmware sends `astronaut_id`, `heart_rate_bpm`, `spo2_percent`, `skin_temp_c`, `radiation_dose_msv` and `radiation_rate_usvh`. The ship takes the first four as its own fields, says which fields it did not store, and finds the crew member by suit id.

**Files:** `base_station/routes.py`, `tests/test_demo_day.py`, `docs/hardware.md`.

- [ ] **Step 1: Write the failing tests.** Add to the end of `tests/test_demo_day.py`:

```python
SUIT = {"astronaut_id": "LT-04", "heart_rate_bpm": 76, "spo2_percent": 98, "skin_temp_c": 33.9,
        "radiation_dose_msv": 84.2, "radiation_rate_usvh": 12.5}


def test_the_suit_can_use_its_own_field_names(client):
    sent = client.post("/api/base/readings", json=SUIT)
    answer = sent.get_json()
    assert sent.status_code == 201 and answer["reading"]["crew_id"] == 4
    reading = answer["reading"]
    assert (reading["heart_rate"], reading["spo2"], reading["skin_temp"]) == (76, 98, 33.9)
    assert answer["ignored"] == ["radiation_dose_msv", "radiation_rate_usvh"]      # said, not silently dropped
    assert client.get("/api/base/crew/C4").get_json()["latest"]["heart_rate"] == 76


def test_the_ships_own_names_still_work_and_win(client):
    answer = client.post("/api/base/readings",
                         json={"crew_id": "C4", "heart_rate": 70, "heart_rate_bpm": 99}).get_json()
    assert answer["reading"]["heart_rate"] == 70 and answer["ignored"] == []


def test_a_suit_nobody_wears_is_refused_by_name(client):
    refused = client.post("/api/base/readings", json={"astronaut_id": "S1", "heart_rate_bpm": 76})
    assert refused.status_code == 400 and refused.get_json()["field"] == "crew_id"


def test_five_low_readings_in_the_suits_words_still_raise_the_sos(client):
    for _ in range(5):
        raised = client.post("/api/base/readings",
                             json={"astronaut_id": "LT-04", "spo2_percent": 86}).get_json()["alerts"]
    assert [(alert["crew_id"], alert["state"]) for alert in raised] == [("C4", "SOS")]
```

- [ ] **Step 2:** `python -m pytest tests/test_demo_day.py -q`. Expected: 3 failed (the first and fourth with a 400 for an unknown crew, the second with `KeyError: 'ignored'`), 8 passed. The third passes already, because a missing `crew_id` is refused today: it is a guard.
- [ ] **Step 3:** In `base_station/routes.py`, above `find_crew`, add:

```python
SUIT_NAMES = {"astronaut_id": "crew_id", "heart_rate_bpm": "heart_rate", "spo2_percent": "spo2",
              "skin_temp_c": "skin_temp"}              # the suit firmware's names for the ship's fields
READ = set(VITALS) | {"crew_id", "source", "signal_ok", "context"} | set(SUIT_NAMES)


def in_our_words(data):
    """The suit's firmware has its own field names. The ship's own name wins where both are sent."""
    return {**{ours: data[theirs] for theirs, ours in SUIT_NAMES.items() if theirs in data}, **data}
```

Replace `find_crew` with:

```python
def find_crew(ref):
    """A crew member from "C1", from a suit id such as "LT-04", or from the row number. Or None."""
    text = str(ref)
    crew = Crew.query.filter((Crew.code == text) | (Crew.suit_id == text)).first()
    number = row_number(ref, "")
    if crew is None and number is not None:
        crew = db.session.get(Crew, number)
    return crew
```

In `post_reading`, change the first line to `data = in_our_words(body())` and the last line to:

```python
    ignored = sorted(key for key in data if key not in READ)      # for example the suit's radiation fields
    return jsonify(reading=reading.to_dict(), alerts=[alert_dict(a) for a in raised], ignored=ignored), 201
```

- [ ] **Step 4: Old tests.** `python -m pytest -q`. The only old failure allowed: `tests/test_contract.py`, where the answer to `POST /readings` is pinned as `{"reading", "alerts"}`, gains `"ignored"`. Anything else, stop and report.
- [ ] **Step 5:** `python -m pytest -q`. Expected: `186 passed`.
- [ ] **Step 6:** In `docs/hardware.md`, replace the example and the "Not stored" line so they say:
  - Either set of names works. The suit's own: `{"astronaut_id": "LT-04", "heart_rate_bpm": 76, "spo2_percent": 98, "skin_temp_c": 33.9}`.
  - `astronaut_id` is the suit id (`LT-01` to `LT-04`) or the crew id (`C1` to `C4`). The live sensor uses `LT-04`, because the scripted story plays on `C1`. `S1` is refused with a 400 naming `crew_id`.
  - Send one reading a second. The alarm rules count readings, so a slower sender makes every alarm slower by the same factor.
  - The answer lists `ignored`: fields the ship does not store. Today that includes `radiation_dose_msv`, `radiation_rate_usvh` and muscle activity.
  - Add `"signal_ok": false` when no finger is on the sensor. The crew card then says to check the sensor.

  Add the `ignored` field and the suit's names to the `POST /readings` row of the API table. Commit: `feat: the suit can post with its own field names and suit id`.
- [ ] **Step 7:** Tell the hardware owner the three lines that matter: post to `http://<the ship's machine>:5000/api/base/readings`, use `"astronaut_id": "LT-04"`, once a second. Ask for the `curl` line in `docs/hardware.md` to be tried from the sensor's own machine on the same network.

---

### Task 3: The health log's two read routes

Spec decisions D5 and D11, requirement R9. The console's log page asks for `GET /api/base/packets` and `GET /api/base/stream-health`. The ship builds both from the suits' minute stream that is already in git (`data/processed/anomalous/vitals_1min.csv`), so nothing waits for `packets.csv`.

Three things decided in the spec, so they are not decided again here:

- A packet is one sensor stream for one minute. The six streams and their names are fixed below. The suit's blood pressure estimate is left out: the ship does not judge it (`limits.json`, `typed_only`), and the console has no sensor name for it.
- Only a limit that holds for a single value is checked on a packet: blood oxygen under 94 % and core temperature over 38.0 °C. The band rules are for a morning's resting value. On the last generated day, core temperature sits above the resting band for a third to two thirds of each person's minutes, so judging a minute against the band would cry wolf.
- `sent_to_ground` is always false. The ship sends reports and summaries, never a raw packet.

**Files:** `common/dataset.py`, new `base_station/log.py`, `app.py`, new `tests/test_log.py`.

- [ ] **Step 1: Write the failing tests.** Create `tests/test_log.py`:

```python
"""The health log: the suits' minute packets and each sensor's lowest signal."""
from datetime import datetime

from common import models

SENSORS = ["chest_band", "ecg", "imu", "ppg", "thermistor"]


def test_the_log_lists_the_suits_packets_newest_first(morning):
    log = morning.get("/api/base/packets?limit=48").get_json()
    packets = log["packets"]
    stamps = [packet["ts"][:19] for packet in packets]
    assert len(packets) == 48 and stamps == sorted(stamps, reverse=True) and stamps[0] == "2026-11-14T06:29:00"
    assert log["simulated"] is True and log["transmitted_to_ground_today"] == 0
    assert {packet["crew_id"] for packet in packets} == {"C1", "C2", "C3", "C4"}
    assert sorted({packet["source"] for packet in packets}) == SENSORS
    assert all(packet["window_s"] == 60 and packet["sent_to_ground"] is False for packet in packets)
    morning.post("/api/base/alerts/A1/send")
    assert morning.get("/api/base/packets?limit=1").get_json()["transmitted_to_ground_today"] == 1


def test_only_a_hard_limit_is_judged_on_a_single_packet(morning):
    packets = morning.get("/api/base/packets?crew=C1&limit=6").get_json()["packets"]
    by_metric = {packet["metric"]: packet for packet in packets}
    assert set(by_metric) == {"hr", "resp", "spo2", "temp_c", "skin_temp_c", "activity_g"}
    oxygen, core, heart = by_metric["spo2"], by_metric["temp_c"], by_metric["hr"]
    assert (oxygen["baseline"], oxygen["rule"], oxygen["state"]) == ([96.0, 99.0], "< 94", "OK")
    assert (core["baseline"], core["rule"], core["state"]) == ([36.3, 36.9], "> 38.0", "OK")
    assert "state" not in heart and "rule" not in heart and heart["suit_id"] == "LT-01"


def test_a_poor_signal_is_a_recheck_whatever_the_value(morning):
    poor = morning.get("/api/base/packets?crew=C1&state=RECHECK").get_json()["packets"]
    assert {packet["ts"][:16] for packet in poor} == {"2026-11-13T07:58", "2026-11-13T08:28", "2026-11-13T15:45"}
    assert all(packet["signal_quality"] < 0.6 and "rule" not in packet for packet in poor)
    assert morning.get("/api/base/packets?crew=C9").status_code == 400
    assert morning.get("/api/base/packets?state=FINE").status_code == 400


def test_the_log_never_shows_a_packet_from_after_the_ships_clock(morning):
    models.set_clock(datetime(2026, 11, 14, 3, 0))
    newest = morning.get("/api/base/packets?limit=1").get_json()["packets"][0]
    assert newest["ts"][:16] == "2026-11-14T03:00"


def test_stream_health_gives_each_sensors_lowest_signal(morning):
    health = morning.get("/api/base/stream-health").get_json()
    assert health["window_minutes"] == 60 and health["simulated"] is True
    assert [sensor["source"] for sensor in health["sensors"]] == SENSORS
    assert all(sensor["state"] == "OK" and 0.6 <= sensor["lowest_signal_quality"] <= 1
               for sensor in health["sensors"])
```

The numbers in these tests were read from the data: the newest minute row is 06:29 for three of the crew and 06:28:59 for the fourth, `C1` has three minutes with a signal quality under 0.6 in the last day (all during exercise), and nobody is under 94 % or over 38.0 °C in it.

- [ ] **Step 2:** `python -m pytest tests/test_log.py -q`. Expected: 5 failed, each on a 404 (`KeyError: 'packets'`, `KeyError: 'window_minutes'`, or a status that is not 400).
- [ ] **Step 3:** In `common/dataset.py`, change the import line `from datetime import date` to `from datetime import date, datetime, timedelta`, and add after `table`:

```python
@functools.lru_cache(maxsize=None)
def last_minutes(hours=24):
    """The suits' minute rows for the last `hours` before the demo morning, oldest first.
    The file holds a month (168,600 rows). The log needs a day, so the rest is read past, not kept."""
    stop = datetime.fromisoformat(mission()["demo_now"].replace("Z", ""))
    since = (stop - timedelta(hours=hours)).isoformat()
    with open(os.path.join(ROOT, "processed", "anomalous", "vitals_1min.csv"), newline="", encoding="utf-8") as f:
        rows = [row for row in csv.DictReader(f) if row["sensor_ts"] >= since]
    return sorted(rows, key=lambda row: (row["sensor_ts"][:19], row["crew_id"]))
```

The first call reads the whole file once and takes about a second. After that the answer is kept.

- [ ] **Step 4:** Create `base_station/log.py`:

```python
"""The health log: the suits' minute stream as packets, newest first.

The rows are the generated month (anomalous/vitals_1min.csv), so every answer says simulated.
A packet is not a reading: LIGHTTIME never judges one. Only the two limits the console's rules
apply to a single value are checked here: blood oxygen under 94 % and core temperature over 38.0.
The band rules are for a morning's resting value, and a minute during exercise is not that."""
from datetime import timedelta

from flask import jsonify, request

from base_station import scoring
from base_station.console import bands
from base_station.morning import when
from base_station.routes import bad, bp, find_crew
from common import dataset
from common.models import LinkMessage, db, utcnow

RECHECK_BELOW = 0.6       # the console's packet-schema.json: under this a packet is shown as RECHECK
WINDOW_MINUTES = 60
STATES = ("OK", "WATCH", "ALERT", "RECHECK")
# column in vitals_1min.csv, the console's name for the sensor, the packet's metric, its unit,
# and the console rule whose hard limit holds for one value (None: logged, not judged)
STREAMS = [
    ("hr_bpm", "ecg", "hr", "bpm", None),
    ("resp_rpm", "chest_band", "resp", "/min", None),
    ("spo2_pct", "ppg", "spo2", "%", "spo2"),
    ("core_temp_c", "thermistor", "temp_c", "°C", "temp_c"),
    ("skin_temp_c", "thermistor", "skin_temp_c", "°C", None),
    ("activity_g", "imu", "activity_g", "g", None),
]


def _rows(now):
    """The minute rows at or before the ship's clock, oldest first."""
    stamp = now.isoformat()[:19]      # whole seconds: as text, "06:29:00Z" would sort after "06:29:00.3Z"
    return [row for row in dataset.last_minutes() if row["sensor_ts"][:19] <= stamp]


def packets_of(row, own, suit_id):
    """One minute row from a suit as packets: one for each sensor stream that has a value."""
    quality = dataset.num(row["signal_quality"]) or 0.0      # no figure at all is treated as unreadable
    for column, source, metric, unit, rule in STREAMS:
        value = dataset.num(row[column])
        if value is None:
            continue
        packet = {"crew_id": row["crew_id"], "suit_id": suit_id, "ts": row["sensor_ts"],
                  "mission_day": int(row["mission_day"]), "location": dataset.mission()["platform"],
                  "source": source, "metric": metric, "value": value, "unit": unit,
                  "signal_quality": quality, "window_s": 60,
                  "sent_to_ground": False,     # the ship sends reports and summaries, never a raw packet
                  "ack": None}
        if quality < RECHECK_BELOW:
            packet["state"] = "RECHECK"
        elif rule:
            packet.update(baseline=own[rule], rule=scoring.rule_text()[rule]["alert"],
                          state="ALERT" if scoring.hard_alert(rule, value) else "OK")
        yield packet


def sent_today():
    """How many messages the ship has sent toward Earth on the ship's date."""
    day = utcnow().date()
    sent = db.session.query(LinkMessage.sent_at).filter(LinkMessage.direction == "to_earth",
                                                        LinkMessage.sent_at.isnot(None))
    return sum(1 for (at,) in sent if at.date() == day)


@bp.get("/packets")
def packets():
    crew, state = request.args.get("crew"), request.args.get("state")
    member = find_crew(crew) if crew else None
    if crew and member is None:
        return bad("unknown crew", "crew")
    if state and state not in STATES:
        return bad("state is one of " + ", ".join(STATES), "state")
    limit = min(max(request.args.get("limit", 200, type=int), 1), 1000)
    suits = {row["crew_id"]: row["suit_id"] for row in dataset.table("reference/crew")}
    own, out = {}, []
    for row in reversed(_rows(utcnow())):
        code = row["crew_id"]
        if member is not None and code != member.code:
            continue
        if code not in own:
            own[code] = bands(code)
        out += [packet for packet in packets_of(row, own[code], suits[code])
                if not state or packet.get("state") == state]
        if len(out) >= limit:
            break
    return jsonify(packets=out[:limit], transmitted_to_ground_today=sent_today(), simulated=True)


@bp.get("/stream-health")
def stream_health():
    """The lowest signal quality each sensor reported over the newest hour of packets."""
    rows, lowest = _rows(utcnow()), {}
    if rows:
        since = (when(rows[-1]["sensor_ts"]) - timedelta(minutes=WINDOW_MINUTES)).isoformat()[:19]
        for row in rows:
            if row["sensor_ts"][:19] <= since:
                continue
            quality = dataset.num(row["signal_quality"]) or 0.0
            for column, source, *_ in STREAMS:
                if row[column] != "":
                    lowest[source] = min(lowest.get(source, 1.0), quality)
    return jsonify(sensors=[{"source": source, "lowest_signal_quality": quality,
                             "state": "RECHECK" if quality < RECHECK_BELOW else "OK"}
                            for source, quality in sorted(lowest.items())],
                   window_minutes=WINDOW_MINUTES, simulated=True)
```

- [ ] **Step 5:** In `app.py`, change `from base_station import console  # noqa: F401 ...` to:

```python
    from base_station import console, log  # noqa: F401  (each adds its routes to the ship's blueprint)
```

- [ ] **Step 6:** `python -m pytest tests/test_log.py -q`. Expected: 5 passed. If the first test fails on the count of crew or sensors, print the eight newest rows of `dataset.last_minutes()` and compare them with what the test's note says before changing anything.
- [ ] **Step 7: Old tests.** `python -m pytest -q`. Expected: `191 passed`. No old test should change. If a test that lists every route or counts them fails, add the two routes to its list.
- [ ] **Step 8:** Add both routes to the API table in `docs/specs/2026-11-14-backend-design.md` (query parameters `crew`, `state`, `limit` with default 200 and maximum 1000; the answer's three keys; that `POST /api/base/packets` is not built because nothing sends packets). Add `Packet` and `StreamHealth` to `docs/frontend/lighttime-api.ts`. Commit: `feat: the health log's packets and stream health`.

---

### Task 4: The local run, and what the host needs

Spec decisions D7, D15 and D16, requirements R8 and R10. Both repos deploy to Google Cloud Run by themselves on every merge to `main`. The load balancer points at the console only, the backend cannot be reached from a browser, and the database takes connections only from listed addresses. So most of this task is a list for the deployment owner, not code.

- [ ] **Step 1: The local run.** `.env` has `LIGHTTIME_MORNING=1` and **no `DATABASE_URL`**, so the database is SQLite. With the hosted database's address in `.env`, `python app.py` either fails at start, because this network is not on the database's list, or, from a listed network, empties the hosted demo tables and runs a second ship with a second clock on the same database. `Remove-Item instance\lighttime.db -ErrorAction SilentlyContinue`, then `python app.py`. Both browser windows read `http://localhost:5000`. A second machine uses this machine's address in place of `localhost`: check it from there with `irm http://<address>:5000/api/base/health`.
- [ ] **Step 2: Send the deployment owner this list.** Each line is a setting on the host. None of it is in this repo.
  1. **The tables.** The backend has no migrations: it creates missing tables and never changes one. `main` took new columns and two new tables with pull request #6 (22:03 on 14 November). If the hosted database was made before that, the newest revision cannot start against it, and Cloud Run keeps serving the revision before it with no error on the site. Run once, from an address the database allows: `DROP TABLE IF EXISTS reminder, checkin, link_message, alert, reading, crew, mission_state CASCADE;` It empties demo data only. Then deploy again and check that the newest revision is the one serving.
  2. **One ship.** Maximum instances 1 and minimum instances 1 on the backend service. Each instance has its own mission clock and reloads the morning when it starts, so a second instance means times that jump and a database emptied while someone is using it.
  3. **CPU between requests.** Billing set to instance-based: `gcloud run services update <service> --no-cpu-throttling`. The scripted story is a thread inside the web process. With the default, request-based setting a thread only runs while a request is being answered.
  4. **The morning.** `LIGHTTIME_MORNING=1` in the backend's environment.
  5. **A way in from a browser.** The console asks the ship from the browser, and today the ship cannot be reached from outside. Either the load balancer sends `/api/*` to the backend and the console is built with `--build-arg NEXT_PUBLIC_API_URL=/` (console plan, Task 11), or the backend gets its own public address and the console is built with that address. The first keeps one address. Until one of them is done the hosted console is the built-in demo, which is a fine thing for it to be. The suit can only reach a hosted ship the same way.
  6. **Merges are deploys.** A merge to the backend's `main` starts a new revision, which restarts the demo at 06:30. A merge to the console's `main` rebuilds the console.
- [ ] **Step 3: Check the hosted ship,** when the deployment owner says it is up and has given its address. Each line must print what follows it:

```powershell
$site = "<the address the deployment owner gave>"
(irm "$site/api/base/state") | select stop, mission_day, light_time_source      # mars 158 JPL Horizons, live
1..10 | % { (irm "$site/api/base/state").now; Start-Sleep -Milliseconds 400 }   # ten times, each later than the one before
(irm "$site/api/base/alerts?open=1") | select id, stage                         # A1 raised
```

  If a time is earlier than the one before it, there are two clocks: two workers or two instances. If `light_time_source` says `read on 2026-11-13`, the backend has no way out to the internet. The delay is then the stored JPL figure for the day, which is correct, and the Earth console's Deep Space Network line will be empty.

---

### Task 5: The end-to-end run-through

Run this before telling anyone the backend is ready, and again after every later task.

- [ ] **Step 1:** `python app.py` on the morning. In a second terminal, each line must print what follows it:

```powershell
$api = "http://localhost:5000/api/base"; $earth = "http://localhost:5000/api/earth"
(irm "$api/state") | select stop, mission_day, now                   # mars 158 2026-11-14T06:3...
(irm "$api/alerts?open=1") | select id, metric, stage, raised_by     # A1 hr_rest raised console
(irm "$api/crew/C1").week.hr_rest -join " "                          # 60 59 58 59 80 82 84
irm -Method Post "$api/alerts/A1/ack" -ContentType application/json -Body '{"by":"Okafor"}' | select stage   # acknowledged
irm -Method Post "$api/alerts/A1/send" | select stage                # sent
Start-Sleep 12
$report = (irm "$earth/inbox").messages[0]; $report.payload.raised_at   # 2026-11-14T06:12:00Z
irm -Method Post "$earth/reply" -ContentType application/json -Body (@{message_id=$report.id; text="Temperature every 4 hours."; from="Dr. Adeyemi"} | ConvertTo-Json) | select status   # in_flight
Start-Sleep 12
(irm "$api/alerts/A1") | select stage                                # replied
irm -Method Post "$api/scenario/start" -ContentType application/json -Body '{"name":"stage"}'
```

- [ ] **Step 2:** Watch `(irm "$api/alerts?open=1") | select id, state, metric, raised_by, speak` every few seconds. Expected within about a minute: a second alert for `C1` with metric `spo2` and `raised_by` `lighttime`, first state `WATCH` with a `speak` line that names the time left and says Earth's reply would be too late, then `SOS`. While it is `SOS`, `(irm "$api/crew/C1").level` prints `emergency`. Write down how many seconds after the start each appears: the console's run-through uses those two numbers.
- [ ] **Step 3:** `irm -Method Post "$api/dial" -ContentType application/json -Body '{"stop":"sun"}' | % state | select link_up` prints `False`. `irm -Method Post "$api/messages" -ContentType application/json -Body '{"text":"Still here.","from":"Okafor"}' | select status` prints `queued`. Dial back to `mars`: `flushed` is 1 or more.
- [ ] **Step 4: The suit and the log.**

```powershell
irm -Method Post "$api/readings" -ContentType application/json -Body '{"astronaut_id":"LT-04","heart_rate_bpm":76,"spo2_percent":98,"skin_temp_c":33.9,"radiation_dose_msv":84.2}' | select ignored   # {radiation_dose_msv}
(irm "$api/crew/C4").latest | select heart_rate, spo2                # 76 98
(irm "$api/packets?limit=6").packets | select crew_id, metric, value, state
(irm "$api/stream-health").sensors | select source, lowest_signal_quality, state   # five sensors, all OK
```

- [ ] **Step 5:** `irm -Method Post "$api/reset"`, then the first three lines of Step 1 again: same answers. `python -m pytest -q` one last time. Push. Open the pull request into `main`. In its description: the new fields (`now`, `raised_by`, `week`, `simulated`, `ignored`), the two log routes, that the suit may post with its own field names, and that no table changed in this pull request, so the host needs nothing new for it. Merging it restarts the hosted demo at 06:30.

---

### Task 6: When the data owner's Earth console routes are pushed

Spec decision D2, requirement R4. No code of ours. Until this is done the Earth console runs on the four routes that exist (`/inbox`, `/outbox`, `/reply`, `/network`): the console plan's Task 6 is written for those and needs nothing from this task.

- [ ] **Step 1:** `git fetch origin`, then read before merging: `git log --oneline Tj-Backend..origin/<the branch>` and `git diff --stat Tj-Backend...origin/<the branch>`. Expected: changes under `command_center/`, `tests/`, the API table, and nothing under `base_station/`. If `base_station/` or `common/models.py` changed, stop and talk to the data owner first.
- [ ] **Step 2: The wall.** `Select-String -Path command_center\*.py -Pattern "import"`. The only names from `common.models` may be `LinkMessage`, `MissionState`, `db` and the clock helpers. If `Crew`, `Reading`, `Alert`, `Checkin` or `Reminder` appears, it does not merge until it is gone: Earth knows only what the link delivered.
- [ ] **Step 3:** Merge. Expected conflicts: `docs/specs/2026-11-14-backend-design.md` (both sides added rows: keep both) and `AI_USE.md`. `python -m pytest -q`: the count before the merge plus the new tests, all passing. Write the new count in `CLAUDE.md`.
- [ ] **Step 4: Three checks by hand,** with the app running on the morning at Mars:
  - Send A1 from the ship. After 12 seconds the case list shows one new case whose raised time is 06:12, not the send time.
  - Reply to it by alert id through `/reply`. After 12 more seconds `GET /api/base/alerts/A1` has stage `replied`, and the reply is in `GET /api/base/alerts/A1/thread`.
  - Turn the dial to the Sun, reply again, and check the reply is `queued`. Turn back to Mars: it leaves.
- [ ] **Step 5:** Commit the merge. Send the frontend owner the exact routes and the "A case carries" section of the API table. The Earth console then reads cases from them in place of grouping inbox messages in the browser.

---

### Task 7: When the generated month is rebuilt from the console's seed

Spec decision D4. The data owner's work, then one small job here. Nothing else in this plan or the console plan waits for it.

Why it is still worth asking for: in the generated month `C4` sleeps under her own band every night of the last week, so the ship scores her card `ALERT`, and no alert was ever raised for it. Once the crew cards read the ship (console plan, Task 8) that shows as a red card with an empty alert list. The console's seed has her in band.

- [ ] **Step 1: The request to the data owner.** In `data/scripts/config.py`, set `CREW` and `BASELINES` for `C2`, `C3` and `C4` from the console's `src/data/crew-seed.json` (roles, the nine baselines each, and the crew medical officer, who is `C4` in the seed). Run `python data/scripts/build_all.py` and `python data/scripts/validate.py`. Add one check to `validate.py` for the demo morning under the console's rules: `C1` is ALERT, `C2` is WATCH on sleep only, `C3` and `C4` are OK. Commit `data/processed/` with the new `BUILD_INFO.json`. `packets.csv` is no longer needed in git: the ship builds the log from the minute stream.
- [ ] **Step 2:** After merging that commit: `python -m pytest -q`. Expected failures, and only these, because they pin generated values:
  - `tests/test_console.py`, the list of crew states: read the new states from the API by hand (`(irm http://localhost:5000/api/base/crew) | select id, state`) and check them against the seed (`C2` WATCH, `C3` OK, `C4` OK) before changing the expectation. If they differ from the seed, the rebuild is wrong: tell the data owner, do not change the test.
  - `tests/test_review.py`, the "Last check-in" sentence for `C2`: read `C2`'s row for 14 November in `data/processed/anomalous/checkins.csv` and put its sleep and mood in the expectation.
  - `tests/test_log.py`: the three minutes with a poor signal for `C1`, and the two baselines in the hard-limit test. Read the new values the same way the note under those tests says the old ones were read.
  - `tests/test_demo_day.py`, the week test, only if `C1`'s blood pressure history changed.

  The hash test passes by itself: `BUILD_INFO.json` changed with the files. If a `C1` daily value fails (`hr_rest` 84, the week `60 59 58 59 80 82 84`), the rebuild changed the demo morning: stop and tell the data owner.
- [ ] **Step 3:** `python -m pytest -q` green. Commit: `chore: the generated month rebuilt from the console's seed`.

---

### Task 8 (optional, only if everything else in both plans is done by 10:00 on Sunday): A learned normal heart rate, as an adviser

ADR 0001 and spec decision D6. One number beside the heart rate: how far it is from what is normal for this activity. It never raises, changes or silences an alert. Steps 1 and 2 are safe to run at any time as a background job, because they change nothing the app reads.

- [ ] **Step 1: Learn and test, offline.** Create `scripts/learn_hr_normal.py`. The 15 wrist recordings are in `data/clean/wrist/S*.csv` with columns `t_s, heart_rate, skin_temp, activity, context, signal_ok`.

```python
"""Learn how far heart rate normally sits above a person's resting rate in each activity.

Fifteen real wrist recordings (PPG-DaLiA). Leave one person out, learn on fourteen, test on the
one left out, fifteen times. Prints the result and writes base_station/hr_normal.json.
This is an adviser: it can say "unusual", never "dangerous". No recording holds an emergency."""
import csv
import glob
import json
import statistics
import sys

REST = "BASELINE"
SUSTAIN_S = 60


def load(path):
    with open(path, newline="") as f:
        return [(row["activity"], float(row["heart_rate"])) for row in csv.DictReader(f)
                if row["signal_ok"] == "1" and row["heart_rate"]]


def resting(rows):
    return statistics.median(rate for activity, rate in rows if activity == REST)


def learn(people):
    """{activity: beats above resting}, and the size of the largest normal gap, from these people."""
    offsets, gaps = {}, []
    for rows in people:
        rest = resting(rows)
        for activity in {a for a, _ in rows}:
            offsets.setdefault(activity, []).append(statistics.median(r for a, r in rows if a == activity) - rest)
    effect = {activity: statistics.median(values) for activity, values in offsets.items()}
    for rows in people:
        rest = resting(rows)
        gaps += [abs(rate - rest - effect[activity]) for activity, rate in rows]
    gaps.sort()
    return effect, gaps[int(len(gaps) * 0.999)]


def flagged_minutes(rows, effect, limit):
    """Whole minutes in which every second sat further from normal than the limit."""
    rest, run, minutes = resting(rows), 0, 0
    for activity, rate in rows:
        run = run + 1 if abs(rate - rest - effect.get(activity, 0.0)) > limit else 0
        if run == SUSTAIN_S:
            minutes, run = minutes + 1, 0
    return minutes


def main():
    paths = sorted(glob.glob("data/clean/wrist/S*.csv"))
    people = [load(path) for path in paths]
    worst = 0.0
    for index, held_out in enumerate(people):
        effect, limit = learn(people[:index] + people[index + 1:])
        per_hour = flagged_minutes(held_out, effect, limit) / (len(held_out) / 3600)
        worst = max(worst, per_hour)
        print(f"{paths[index]}: limit {limit:.0f} bpm, flagged {per_hour:.2f} minutes an hour")
    effect, limit = learn(people)
    print(f"worst held-out person: {worst:.2f} flagged minutes an hour")
    if worst > 1.0:
        sys.exit("Gate failed: more than one flagged minute an hour on a healthy person. Do not ship it.")
    with open("base_station/hr_normal.json", "w") as f:
        json.dump({"effect": effect, "limit_bpm": round(limit, 1), "worst_flagged_minutes_per_hour": round(worst, 2),
                   "source": "PPG-DaLiA wrist recordings, 15 people, each held out in turn"}, f, indent=2)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: The gate.** `python scripts/learn_hr_normal.py`. If it exits with "Gate failed", this task ends here: write the printed numbers into `docs/specs/2026-11-14-ship-ai-and-data-design.md` as a negative result and move on. That is a finding, not a failure.
- [ ] **Step 3: Only if the gate passed, and only once everything else is done,** test first: the crew object's `usual` gains `"heart_rate_for_activity": {"expected": n, "limit_bpm": n, "unusual": true or false}` from the latest reading's `context` (only `rest` and `exercise` reach the ship today, so map `rest` to `BASELINE` and `exercise` to `CYCLING`, and say so in the code). A test proves that no alert is raised, changed or cleared by it.
- [ ] **Step 4:** Wherever it is shown, label it as exactly what it is: "unusual for this activity, learned from 15 people, advice only". Add it to the words to avoid in `CONTEXT.md`: it has seen no emergency, so it never says "dangerous".

## Not in this plan

- `POST /api/base/packets` and the three `/push` routes of the console's contract. Nothing sends packets, and push needs keys and a service worker.
- One-a-second readings in the log. The newest reading shows on the crew card; the log is the minute stream.
- The suit's blood pressure estimate as a packet (Task 3 says why).
- Storing the suit's radiation. The fields are accepted and reported back as ignored. Storing them needs two columns and a rebuilt table.
- Guards against two requests at the same instant (spec D9).
- A console rule raising an alert by itself when a daily value scores `ALERT`. Only the alerts loaded with the morning exist, which is why `C4`'s red card has no alert (Task 7).
- A cuff blood pressure typed at check-in is judged by the console's daily rule, not by LIGHTTIME. That is the design.
- `/habitat` running on process uptime: nothing reads it.

## Self-review

- Spec coverage: R2's backend half and R3's `raised_by` are Task 1; R6 is Task 2; R7's backend half (`week`, the red card) is Task 1; R8 is Task 0 (one worker), Task 4 (the local run) and Task 5; R10's backend half is Task 4, Steps 2 and 3; R9's backend half is Task 3; R4's later half is Task 6; D4 is Task 7; D6 is Task 8.
- Names used: `week_of`, `LIVE`, `SUIT_NAMES`, `READ`, `in_our_words`, `find_crew`, `last_minutes`, `STREAMS`, `packets_of`, `sent_today`, `_rows`; existing ones relied on: `_level`, `_latest`, `scoring.worst`, `scoring.hard_alert`, `scoring.rule_text`, `bands`, `when`, `row_number`, `bad`, `body`, `iso`, `utcnow`, `reports.NOT_A_DIAGNOSIS`, the `morning` and `client` fixtures, `models.set_clock`.
- Checked by reading, not by running: the manual SOS `why` list is pinned in `tests/test_tonight.py` (Task 1, Step 6 names it); the answer to `POST /readings` is pinned in `tests/test_contract.py` (Task 2, Step 4); the console rule words are exactly `< 94` and `> 38.0` in `data/reference/console_thresholds.json`; the eight newest minute rows all carry six values.
- Known weak points, because nothing was run: the time the first call to `last_minutes()` takes on a slow disk; the exact timing of the scripted story in Task 5, Step 2; everything in Task 8, which is why it has a gate.
