# Tonight: Integration, Light-Time Maths, NASA Data and Verification Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** By tonight the frontend can build against a fixed, typed contract, the light-time maths is visible and checked against two NASA sources, every alert explains itself, and the data is verified by a script.

**Architecture:** Same Flask app. Additive fields only, no renames. Two new modules in `common/` (`dsn`, `sources`), three new routes, one new column (`alert.cleared_note`), three scripts' worth of checks, and a typed client handed to the frontend from `docs/frontend/`.

**Tech Stack:** Python 3.13, Flask, Flask-SQLAlchemy, pytest, requests. Frontend side: TypeScript, React 19, Next.js 16 (client components only).

**Status of this plan:** written without running anything, at the backend owner's request. The code blocks are untested. Run every test step. Where a step says "stop and tell the backend owner", do that.

---

## Part A: where things stand (read this first, the backend owner)

### A1. Frontend and backend are not in tune yet, because the frontend has no screens

Checked at 15:00 on Saturday in your local clones.

| | Backend (`Tj-Backend`) | Frontend (`main`) |
|---|---|---|
| Last work | Ship AI plan executed and pushed, Postgres host confirmed | One scaffold commit: Next.js 16, shadcn, Biome, Husky |
| Routes or screens | 22 routes, 91 tests | One placeholder page ("Setup complete") |
| Calls to the API | n/a | None. No fetch, no API URL, no types |
| Levels | nominal, advisory, caution, warning, emergency | Tokens for OK, WATCH, ALERT only. No SOS colour |

Nothing conflicts, because nothing is wired. The risk tonight is all on the frontend side. What the backend can do about it is hand over a typed client, a polling hook and a fixed contract with a test behind it (Task 6), so the frontend owner builds screens and never guesses a field name.

Smallest set of screens that makes a working system tonight: (1) crew board with the dial and the story buttons, (2) the alert screen with checklist, timeline, countdown and voice, (3) the Earth console with inbox and reply. Everything else can wait.

### A2. How the light-time maths works today

There is no single "light-time module". The maths lives in three small files, and that is fine. It stays that way (decision D1).

1. **One-way delay.** `D = path / c`, with `c = 299,792.458 km/s`.
   - Station: fixed 0.25 s. The ISS talks through relay satellites in geostationary orbit, about 2 x 35,786 km of path, which is 0.24 s.
   - Moon: fixed 1.3 s. 384,400 km / c = 1.28 s.
   - Mars: from NASA JPL Horizons, quantity 21 (one-way light time in minutes, Earth centre to Mars), asked once per UTC day and cached, with a dated fallback table. Today: 660.86 s = 11 min 01 s, a path of 198.1 million km (1.324 AU). Over the years Mars swings between about 3 and 22 minutes.
   - Behind the Sun: link down. Code: `common/lighttime.py`, `common/modes.py`.
2. **Who decides.** Link down: the crew, alone. `D >= 300 s`: crew medical officer first. Otherwise: flight surgeon, live. Code: `modes.mode_for`.
3. **ETA for the doctor.** A message sent at `t0` lands at `t0 + D`. The earliest a reply can land is `t0 + 2D`, if the doctor answers the instant it arrives. A real reply lands at `t0 + 2D + the doctor's thinking time`. Code: `common/link.py`.
4. **Two clocks.** Bodies and people run in real time. Light legs of a minute or more are played 60 times faster so a demo fits on a stage: a leg of `D` seconds takes `D / 60` real seconds. The API always reports mission seconds: `eta_s = D x (time left on the demo clock / leg length on the demo clock)`.
5. **Time-left test.** `T_left = (reading now - red line) / fall rate`. Earth is in time only if `2D < T_left`. Example today: 96% falling 3 points a minute gives `T_left = 100 s`. `2D = 1,322 s`. So the crew acts.

Gaps found, each fixed below or noted:

| Gap | Fix |
|---|---|
| The working (path, round trip, demo seconds) is not in the API, so a screen would redo the maths | Task 1 |
| The alert timeline has no "earliest reply" time to count down to | Task 2 |
| Earth cannot see its own reply in flight | Task 2 |
| Only one source for the Mars figure | Task 5: NASA's Deep Space Network measures round-trip light time to its Mars spacecraft. On 13 November it read 1,330 s, which is 665 s one way. Horizons gave 665.1 s for that day |
| "Behind the Sun" reports today's Mars delay although no signal passes | Contract note: screens show "No link" and ignore the number |
| Doctor thinking time is not modelled | Left out. The earliest reply is the honest lower bound |

### A3. Ship AI and machine learning

What exists: rules tested on real recordings before they may alarm, the time-left test, each person's usual range, and the asked-ahead report. No model is trained anywhere, and no language model is called.

Ideas weighed for tonight:

| Idea | Verdict |
|---|---|
| Train a forecaster for time to the red line | No. Six recordings cannot train and test a model honestly |
| Anomaly detector on heart rate | No. Already shown to fail on 15 real people |
| Choose the time-left settings on five volunteers, test on the sixth, six times | Yes, Task 8. It turns "fitted" into a held-out number in three minutes of compute |
| Each alert shows how it was reached, in plain lines | Yes, Task 3. The CSA advisor asked for exactly this |
| Time-left test on cabin CO2 (NASA data) | Not tonight. The RR-1 record has no rise toward a limit to test it on |

For the pitch: the ship AI is explainable statistics, validated on real recordings, with the rule borrowed from NASA fault management. Say that. Do not call it machine learning.

### A4. What the CSA advisor said (15:16 today), and what it changes

| She said | What we do |
|---|---|
| Monitoring in space is periodic, not continuous. Crews resist being watched from a distance. The benefit has to justify the disclosure | This is now a design rule and a pitch line: **continuous on the ship, periodic to Earth.** The raw stream never leaves the ship and is deleted after 24 hours. Earth gets a report only when an alert fires or the crew presses send, plus a daily summary of low, middle and high. The ship's outbox is the complete list of what has left. Screens should show it as "What Earth has seen" |
| It must not distract the crew | Only an SOS or a falling trend speaks. Heart rate alone never alarms. False-alarm counts are in the spec |
| The crew must be able to trace how a recommendation was made | Task 3: every alert carries `why`, the rule, the readings and the source of the bands |
| If a person overrides the system, that has to be handled and owned | Task 3: resolving an alert stores who did it and their note in their own words, and Earth is told |
| Health data must not go to the public internet. Security matters | No language model, no cloud service. The only outbound calls go to NASA and carry no health data. All data here is open research data or simulated. The API has no login: say so if asked, and say a flight system would need one |
| On the ISS the surgeon is near real time, the Moon is 1.3 s, deep space is over 20 minutes | Matches our numbers |

The AI-generated cue list in that record mentions NASA's CMO-DA decision support and NASA-STD-3001 section 7.3. Those are not verified. Do not quote them in the pitch until someone opens the source (Task 7 checklist).

### A5. NASA data, in one place

| NASA source | Live or file | What it drives |
|---|---|---|
| JPL Horizons | Live, with fallback | The delay on every message and who decides |
| Deep Space Network Now | Live (Task 5) | Second check on the delay, and which antenna is on Mars |
| OSDR environmental data, mission RR-1 on the ISS | File | Cabin temperature, humidity, CO2, radiation dose |
| Human Research Program risk list | Copied by hand | The risk name on every alert. This is the challenge resource that makes us eligible for Global Awards |

Task 4 puts this list behind one route so a screen and a slide can show it.

### A6. Decisions that need your yes

- **D1. Light-time module.** Keep the three small files and expose the working (recommended). Merging them into one module changes nothing a judge can see and risks 91 passing tests.
- **D2. Machine learning.** None trained. Run the leave-one-out check (recommended).
- **D3. Frontend gap.** Hand the frontend owner the typed client (in this plan). A bare fallback console served by Flask is not in this plan. See the question at the end of the chat message.

---

## File map

| File | New or changed | What it does |
|---|---|---|
| `common/lighttime.py` | changed | Adds `C_KM_S`, `AU_KM`, `path_km` |
| `common/modes.py` | changed | `describe` adds `path_km`, `round_trip_s`, `plays_as_s` |
| `common/dsn.py` | new | Reads NASA's DSN Now feed |
| `common/sources.py` | new | The list of every outside source |
| `common/models.py` | changed | `Alert.cleared_note` |
| `base_station/reports.py` | changed | `why(alert)` |
| `base_station/routes.py` | changed | `earliest_reply_at`, `why`, `cleared_note`, `/sources` |
| `command_center/routes.py` | changed | `/outbox`, `/network` |
| `tests/conftest.py` | changed | Tests never call DSN |
| `tests/test_tonight.py`, `tests/test_contract.py` | new | 16 tests |
| `scripts/verify_data.py`, `scripts/crossval_lookahead.py` | new | Data check, held-out check |
| `docs/frontend/lighttime-api.ts`, `use-poll.ts`, `README.md` | new | The typed client for the frontend repo |

---

### Task 0: Starting point

- [ ] **Step 1:** Run `git status --short` and `python -m pytest -q`. Expected: clean tree apart from this plan, `91 passed`. If not, stop and tell the backend owner.
- [ ] **Step 2:** In `CLAUDE.md`, under "Read first", add the line `- Tonight's plan: docs/plans/2026-11-14-tonight-integration.md` and change "45 tests" to "91 tests".

---

### Task 1: Show the light-time working

**Files:** Modify `common/lighttime.py`, `common/modes.py`. Test: `tests/test_tonight.py`.

- [ ] **Step 1: Write the failing tests.** Create `tests/test_tonight.py`:

```python
from common import dsn, lighttime, modes

LOW = {"crew_id": 1, "spo2": 86}


def sos(client):
    for _ in range(5):
        raised = client.post("/api/base/readings", json=LOW).get_json()["alerts"]
    return raised[0]


def stop(state, name):
    return next(s for s in state["stops"] if s["stop"] == name)


def test_one_astronomical_unit_is_499_seconds_of_light():
    assert abs(lighttime.AU_KM / lighttime.C_KM_S - 499.0048) < 0.0001


def test_the_moon_figure_matches_the_moons_distance():
    assert abs(384_400 / lighttime.C_KM_S - modes.FIXED_DELAY_S["moon"]) < 0.05


def test_mars_light_time_is_inside_what_the_orbits_allow(app):
    assert 0.372 * 499 <= lighttime.mars_seconds() <= 2.68 * 499


def test_the_state_shows_its_working(client):
    state = client.get("/api/base/state").get_json()
    mars, moon = stop(state, "mars"), stop(state, "moon")
    assert mars["round_trip_s"] == 2 * mars["delay_s"]
    assert mars["plays_as_s"] == mars["delay_s"] / state["speedup"]
    assert abs(mars["path_km"] - mars["delay_s"] * 299_792.458) < 1
    assert moon["plays_as_s"] == moon["delay_s"]          # under a minute plays in real time
```

- [ ] **Step 2:** Run `python -m pytest tests/test_tonight.py -q`. Expected: an import error, `cannot import name 'dsn'`. Create an empty `common/dsn.py` for now so the other tests can fail for the right reason, and run again. Expected: 4 failed (`AU_KM`, `path_km` missing).

- [ ] **Step 3:** In `common/lighttime.py`, below the `_cache = {}` line, add:

```python
C_KM_S = 299_792.458        # speed of light in km/s, exact by definition
AU_KM = 149_597_870.7       # one astronomical unit in km (IAU 2012)


def path_km(delay_s):
    """How far a signal travels in delay_s seconds."""
    return delay_s * C_KM_S
```

- [ ] **Step 4:** In `common/modes.py`, change the import to `from common import lighttime, link` and replace `describe` with:

```python
def describe(stop):
    """One dial stop with its working: the delay, the path it stands for, the round trip,
    and how long one leg takes on the demo clock."""
    fixed = stop in FIXED_DELAY_S
    delay_s = FIXED_DELAY_S[stop] if fixed else lighttime.mars_seconds()
    link_up = STOPS[stop]["link_up"]
    mode = mode_for(delay_s, link_up)
    return {
        "stop": stop, "label": STOPS[stop]["label"], "link_up": link_up, "delay_s": delay_s,
        "mode": mode, "who_decides": WHO_DECIDES[mode],
        "light_time_source": "fixed" if fixed else lighttime.source(),
        "path_km": round(lighttime.path_km(delay_s)), "round_trip_s": 2 * delay_s,
        "plays_as_s": link.real_delay_s(delay_s),
    }
```

- [ ] **Step 5:** Run `python -m pytest -q`. Expected: `95 passed`. If an older test compares a whole `describe` result, add the three new keys to its expected value.
- [ ] **Step 6:** Add the three fields to the `/state` row of the API table in `docs/specs/2026-11-14-backend-design.md`, then `git add -A && git commit -m "feat: light-time working in the state (path, round trip, demo seconds)"`.

---

### Task 2: ETA for the doctor

**Files:** Modify `base_station/routes.py`, `command_center/routes.py`. Test: `tests/test_tonight.py`.

- [ ] **Step 1:** Add to the end of `tests/test_tonight.py`:

```python
def test_the_alert_says_when_the_earliest_reply_could_land(client):
    client.post("/api/base/dial", json={"stop": "mars"})
    sos(client)
    line = client.get("/api/base/alerts").get_json()[0]["timeline"]
    assert line["earliest_reply_at"] > line["sent_at"]


def test_a_queued_report_has_no_reply_time_yet(client):
    client.post("/api/base/dial", json={"stop": "sun"})
    sos(client)
    assert client.get("/api/base/alerts").get_json()[0]["timeline"]["earliest_reply_at"] is None


def test_earth_can_watch_its_reply_in_flight(client):
    client.post("/api/base/dial", json={"stop": "mars"})
    sent = client.post("/api/earth/reply", json={"text": "Give oxygen."}).get_json()
    out = client.get("/api/earth/outbox").get_json()
    assert [m["id"] for m in out] == [sent["id"]] and out[0]["status"] == "in_flight"
    assert 0 < out[0]["eta_s"] <= out[0]["delay_s"]
    assert client.get("/api/base/inbox").get_json() == []       # the ship has not heard yet
```

- [ ] **Step 2:** Run `python -m pytest tests/test_tonight.py -q`. Expected: 3 failed.
- [ ] **Step 3:** In `base_station/routes.py` replace `timeline` with:

```python
def timeline(alert):
    """The round trip of one alert, for the stepper on the alert screen. The earliest reply
    is the report's landing time plus the same leg back, as if the doctor answered at once."""
    report = db.session.get(LinkMessage, alert.report_id) if alert.report_id else None
    sent = link.to_dict(report) if report else {}
    reply = next((m for m in reversed(link.delivered("to_ship"))
                  if m.payload.get("alert_id") == alert.id), None)
    earliest = (report.deliver_at + (report.deliver_at - report.sent_at)
                if report is not None and report.sent_at is not None else None)
    return {
        "raised_at": iso(alert.at), "acknowledged_at": iso(alert.acknowledged_at),
        "sent_at": sent.get("sent_at"), "earth_eta_s": sent.get("eta_s"),
        "earth_at": sent.get("deliver_at") if sent.get("status") == "delivered" else None,
        "earliest_reply_at": iso(earliest),
        "reply_at": iso(reply.deliver_at) if reply else None,
        "resolved_at": iso(alert.cleared_at),
    }
```

- [ ] **Step 4:** In `command_center/routes.py`, add after the `inbox` route:

```python
@bp.get("/outbox")
def outbox():
    """What Earth has sent, with the mission time left until each lands on the ship."""
    now = link.utcnow()
    sent = (LinkMessage.query.filter_by(direction="to_ship")
            .order_by(LinkMessage.created_at.desc(), LinkMessage.id.desc()))
    return jsonify([link.to_dict(m, now) for m in sent])
```

- [ ] **Step 5:** Run `python -m pytest -q`. Expected: `98 passed`.
- [ ] **Step 6:** Add `earliest_reply_at` and `GET /api/earth/outbox` to the spec's API table. Commit: `feat: earliest reply time on the alert, Earth outbox`.

---

### Task 3: Every alert explains itself, and a person's override is kept

From the CSA advisor: the crew must be able to trace a recommendation, and an override must be owned by a person in their own words.

**Files:** Modify `common/models.py`, `base_station/reports.py`, `base_station/routes.py`. Test: `tests/test_tonight.py`.

- [ ] **Step 1:** Add to the end of `tests/test_tonight.py`:

```python
def test_every_alert_says_how_it_was_reached(client):
    sos(client)
    why = client.get("/api/base/alerts").get_json()[0]["why"]
    assert why[1] == "Last readings: 86, 86, 86, 86, 86%."
    assert any("NEWS2" in line for line in why) and why[-1].endswith("decides.")


def test_a_manual_sos_says_no_rule_was_involved(client):
    alert = client.post("/api/base/sos", json={"crew_id": 2}).get_json()
    assert alert["why"] == ["A crew member pressed SOS. No rule was involved."]


def test_resolving_keeps_the_crews_own_words_and_tells_earth(client):
    alert = sos(client)
    note = "Mask on. Back to 97 in two minutes."
    done = client.post(f"/api/base/alerts/{alert['id']}/clear", json={"by": "Lindqvist", "note": note}).get_json()
    assert done["cleared_note"] == note
    resolved = [m for m in client.get("/api/base/outbox").get_json() if m["payload"].get("event") == "resolved"]
    assert resolved[0]["payload"]["note"] == note
```

- [ ] **Step 2:** Run them. Expected: 3 failed.
- [ ] **Step 3:** In `common/models.py`, in the `Alert` class after `cleared_by = db.Column(db.String(40))`, add:

```python
    cleared_note = db.Column(db.String(280))     # the person's reason, in their own words
```

- [ ] **Step 4:** In `base_station/reports.py`, change the model import line to also import the rules, and add `why`:

```python
from base_station import lookahead, rules
```

```python
def why(alert):
    """How the ship reached this alert, in plain lines a medical officer can check."""
    if alert.vital == "manual":
        return ["A crew member pressed SOS. No rule was involved."]
    cfg = rules.LIMITS["vitals"].get(alert.vital)
    if cfg is None:
        return ["The sensor signal was not clean, so no reading was judged."]
    recent = (Reading.query.filter(Reading.crew_id == alert.crew_id, getattr(Reading, alert.vital).isnot(None))
              .order_by(Reading.at.desc(), Reading.id.desc()).limit(5).all())
    values = ", ".join(f"{getattr(r, alert.vital):g}" for r in reversed(recent))
    if alert.reason.endswith(lookahead.FALLING):
        rule = "Rule: the reading is still in the normal band but falling steadily toward the red line."
    else:
        rule = ("Rule: the reading sat in an out-of-range band. A sensor needs five readings in a row "
                "with a clean signal. A typed number counts once and stops at a warning.")
    return [f"What was seen: {alert.reason}.", f"Last readings: {values}{cfg['unit']}.", rule,
            f"Band table: {rules.LIMITS['source']}",
            "This is a fixed rule, not a diagnosis. The crew medical officer decides."]
```

- [ ] **Step 5:** In `base_station/routes.py`, in `alert_dict`, add two entries to the returned dict after `"cleared_by"`:

```python
        "cleared_note": alert.cleared_note, "why": reports.why(alert),
```

and replace the body of `clear_alert` with:

```python
    alert = db.get_or_404(Alert, alert_id)
    if alert.cleared_at is None:        # a second press changes nothing
        body = request.get_json(silent=True) or {}
        alert.cleared_at = utcnow()
        alert.cleared_by = body.get("by") or "crew"
        alert.cleared_note = (body.get("note") or "")[:280] or None
        db.session.commit()
        tell_earth(alert, {"event": "resolved", "by": alert.cleared_by, "note": alert.cleared_note})
    return jsonify(alert_dict(alert))
```

- [ ] **Step 6: The databases need the new column.** Local SQLite: `rm -f instance/lighttime.db`. The reviewer's Postgres, once:

`python -c "from app import create_app; from common.models import db; a = create_app(); a.app_context().push(); db.session.execute(db.text('ALTER TABLE alert ADD COLUMN IF NOT EXISTS cleared_note VARCHAR(280)')); db.session.commit()"`

- [ ] **Step 7:** Run `python -m pytest -q`. Expected: `101 passed`. If Python reports a circular import between `reports` and `rules`, move the `from base_station import lookahead, rules` line inside `why` and run again.
- [ ] **Step 8:** Add `why`, `cleared_note` and the `note` body field to the spec's API table. Commit: `feat: alerts explain themselves, resolve keeps the crew's note`.

---

### Task 4: One list of every source

**Files:** Create `common/sources.py`. Modify `base_station/routes.py`. Test: `tests/test_tonight.py`.

- [ ] **Step 1:** Add to `tests/test_tonight.py`:

```python
def test_the_sources_route_lists_the_nasa_data_we_use(client):
    listed = client.get("/api/base/sources").get_json()
    assert sum(s["agency"].startswith("NASA") for s in listed) >= 4
    assert all(set(s) == {"id", "agency", "name", "kind", "url", "used_for", "as_of"} for s in listed)
    assert listed[0]["id"] == "horizons" and "JPL Horizons" in listed[0]["as_of"]
```

- [ ] **Step 2:** Create `common/sources.py`:

```python
"""Every outside source the app uses, in one list: for the Data panel and for the judges."""
from common import lighttime

SOURCES = [
    {"id": "horizons", "agency": "NASA JPL", "name": "Horizons ephemeris system", "kind": "live",
     "url": "https://ssd.jpl.nasa.gov/api/horizons.api",
     "used_for": "Mars light time. It sets the delay on every message and who decides."},
    {"id": "dsn", "agency": "NASA", "name": "Deep Space Network Now", "kind": "live",
     "url": "https://eyes.nasa.gov/dsn/data/dsn.xml",
     "used_for": "Round-trip light time NASA measures to its Mars spacecraft. A second check on the delay."},
    {"id": "eda", "agency": "NASA", "name": "Open Science Data Repository, environmental data, mission RR-1 on the ISS",
     "kind": "file", "url": "https://visualization.osdr.nasa.gov/eda/",
     "used_for": "Cabin temperature, humidity, carbon dioxide and radiation dose."},
    {"id": "hrp", "agency": "NASA", "name": "Human Research Program risk list", "kind": "hand",
     "url": "https://www.nasa.gov/hrp/risks/", "used_for": "The risk name on every alert."},
    {"id": "ppg_dalia", "agency": "UCI Machine Learning Repository", "name": "PPG-DaLiA", "kind": "file",
     "url": "https://archive.ics.uci.edu/dataset/495/ppg+dalia",
     "used_for": "Heart rate and skin temperature replayed as the suit stream."},
    {"id": "spo2_uw", "agency": "University of Washington", "name": "Induced hypoxemia oximeter recordings",
     "kind": "file", "url": "https://github.com/ubicomplab/oximetry-phone-cam-data",
     "used_for": "The recorded fall in blood oxygen, and the test of the time-left rule."},
    {"id": "apnea_ecg", "agency": "PhysioNet", "name": "Apnea-ECG Database", "kind": "file",
     "url": "https://physionet.org/content/apnea-ecg/1.0.0/",
     "used_for": "False-alarm test of the blood-oxygen rules."},
]
AS_OF = {"file": "In the repo, see data/", "hand": "Copied by hand, see docs/data-sources.md",
         "live": "Asked when a screen needs it"}


def listing():
    """The list, each with a line saying how fresh it is."""
    return [{**s, "as_of": lighttime.source() if s["id"] == "horizons" else AS_OF[s["kind"]]} for s in SOURCES]
```

- [ ] **Step 3:** In `base_station/routes.py`, change `from common import link, modes` to `from common import link, modes, sources`, and add at the end of the file:

```python
@bp.get("/sources")
def data_sources():
    return jsonify(sources.listing())
```

- [ ] **Step 4:** Run `python -m pytest -q`. Expected: `102 passed`. Add the route to the spec's API table. Commit: `feat: sources route`.

---

### Task 5: A second NASA check on the Mars delay

**Files:** Create `common/dsn.py` (replace the empty file). Modify `command_center/routes.py`, `tests/conftest.py`. Test: `tests/test_tonight.py`.

- [ ] **Step 1: Save one real copy of the feed and look at it.**

Run: `curl -s https://eyes.nasa.gov/dsn/data/dsn.xml -o data/reference/dsn_sample.xml` then open the file.
Expected: `<dish name="...">` elements, each holding `<target name="..." ... rtlt="...">` elements. If the tags or the `rtlt` attribute are named differently, stop and tell the backend owner, because the parser below assumes them.

- [ ] **Step 2:** Add to `tests/test_tonight.py`:

```python
import pathlib

FEED = ('<dsn><dish name="DSS26"><target name="MRO" id="74" rtlt="1330.0"/></dish>'
        '<dish name="DSS43"><target name="VGR2" id="32" rtlt="140000"/><target name="MVN" id="202" rtlt="1330.4"/>'
        '</dish><timestamp>1</timestamp></dsn>')


def test_only_mars_spacecraft_are_read_from_the_feed():
    assert dsn.parse(FEED) == [{"dish": "DSS26", "craft": "MRO", "round_trip_s": 1330.0},
                               {"dish": "DSS43", "craft": "MVN", "round_trip_s": 1330.4}]


def test_the_saved_copy_of_the_real_feed_can_be_read():
    sample = pathlib.Path("data/reference/dsn_sample.xml")
    for seen in dsn.parse(sample.read_text(encoding="utf-8")) if sample.exists() else []:
        assert 360 < seen["round_trip_s"] < 2700            # Mars is 3 to 22 minutes away, each way


def test_earth_sees_two_nasa_figures_side_by_side(client, monkeypatch):
    monkeypatch.setattr(dsn, "fetch", lambda: FEED)
    dsn._cache.clear()
    seen = client.get("/api/earth/network").get_json()
    assert seen["dsn_one_way_s"] == 665.1 and len(seen["passes"]) == 2
    assert seen["differ_s"] == round(abs(665.1 - seen["horizons_one_way_s"]), 1)


def test_no_dsn_is_not_an_error(client):
    seen = client.get("/api/earth/network").get_json()
    assert seen["passes"] == [] and seen["dsn_one_way_s"] is None and seen["differ_s"] is None
```

- [ ] **Step 3:** Replace `tests/conftest.py` with:

```python
import pytest
import requests

from app import create_app
from base_station import usual
from common import dsn, lighttime


@pytest.fixture
def app(monkeypatch):
    def offline(*args):
        raise requests.ConnectionError("tests do not use the network")

    monkeypatch.setattr(lighttime, "fetch", offline)
    monkeypatch.setattr(dsn, "fetch", offline)
    lighttime._cache.clear()
    dsn._cache.clear()
    usual.clear()
    app = create_app("sqlite:///:memory:")
    app.config["TESTING"] = True
    return app


@pytest.fixture
def client(app):
    return app.test_client()
```

- [ ] **Step 4:** Write `common/dsn.py`:

```python
"""NASA's Deep Space Network Now feed: which antennas are on Mars right now, and the
round-trip light time NASA measures to its spacecraft there. A second check on Horizons."""
import time
import xml.etree.ElementTree as ET

import requests

DSN_URL = "https://eyes.nasa.gov/dsn/data/dsn.xml"
MARS_CRAFT = {"MRO", "M01O", "MVN", "MSL", "M20", "TGO", "MEX"}   # orbiters and rovers at Mars
KEEP_S = 60
_cache = {}


def fetch():
    return requests.get(DSN_URL, timeout=5).text


def parse(text):
    """[{"dish", "craft", "round_trip_s"}] for the Mars spacecraft in one copy of the feed."""
    passes = []
    for dish in ET.fromstring(text).iter("dish"):
        for target in dish.iter("target"):
            try:
                round_trip_s = float(target.get("rtlt", ""))
            except ValueError:
                continue
            if target.get("name", "").upper() in MARS_CRAFT and round_trip_s > 0:
                passes.append({"dish": dish.get("name"), "craft": target.get("name"), "round_trip_s": round_trip_s})
    return passes


def mars_passes():
    """(passes, a line saying where they came from). Asked at most once a minute."""
    if "at" not in _cache or time.monotonic() - _cache["at"] > KEEP_S:
        try:
            _cache.update(passes=parse(fetch()), note="NASA DSN Now, live")
        except (requests.RequestException, ET.ParseError):
            _cache.update(passes=[], note="NASA DSN Now could not be reached")
        _cache["at"] = time.monotonic()
    return _cache["passes"], _cache["note"]
```

- [ ] **Step 5:** In `command_center/routes.py`, change the imports to:

```python
import statistics

from flask import Blueprint, jsonify, request

from common import dsn, lighttime, link, modes
from common.models import LinkMessage, MissionState, db
```

and add at the end:

```python
@bp.get("/network")
def network():
    """Two NASA figures for the same thing: Horizons works the Mars delay out from the orbits,
    the Deep Space Network measures it to spacecraft that are there."""
    passes, note = dsn.mars_passes()
    measured = round(statistics.median(p["round_trip_s"] for p in passes) / 2, 1) if passes else None
    worked_out = lighttime.mars_seconds()
    return jsonify(passes=passes, source=note, url=dsn.DSN_URL, dsn_one_way_s=measured,
                   horizons_one_way_s=worked_out,
                   differ_s=None if measured is None else round(abs(measured - worked_out), 1))
```

- [ ] **Step 6:** Run `python -m pytest -q`. Expected: `106 passed`.
- [ ] **Step 7:** Start the server, then `curl -s localhost:5000/api/earth/network`. Expected: `"source": "NASA DSN Now, live"`. If `passes` is not empty, `differ_s` should be under 10. If it is larger, do not hide it: tell the backend owner. An empty list only means no antenna is on Mars this minute.
- [ ] **Step 8:** Add the route to the spec's API table. Commit: `feat: DSN Now cross-check of the Mars delay`.

---

### Task 6: The contract, with a test behind it, and a typed client for the frontend

**Files:** Create `tests/test_contract.py`, `docs/frontend/lighttime-api.ts`, `docs/frontend/use-poll.ts`, `docs/frontend/README.md`.

- [ ] **Step 1:** Create `tests/test_contract.py`. If this test ever fails, the TypeScript file below must change in the same commit.

```python
"""The exact fields each screen gets. docs/frontend/lighttime-api.ts mirrors these sets."""
STOP = {"stop", "label", "link_up", "delay_s", "mode", "who_decides", "light_time_source",
        "path_km", "round_trip_s", "plays_as_s"}
READING = {"id", "crew_id", "at", "source", "signal_ok", "context", "heart_rate", "spo2", "skin_temp",
           "bp_sys", "bp_dia", "glucose", "sleep_hours", "mood"}
TIMELINE = {"raised_at", "acknowledged_at", "sent_at", "earth_eta_s", "earth_at", "earliest_reply_at",
            "reply_at", "resolved_at"}
ALERT = {"id", "crew_id", "crew", "at", "level", "vital", "value", "unit", "reason", "source", "auto",
         "nasa_risk", "steps", "steps_done", "acknowledged_by", "cleared_at", "cleared_by", "cleared_note",
         "why", "timeline", "lookahead", "speak"}
MESSAGE = {"id", "direction", "kind", "priority", "payload", "status", "in_reply_to", "created_at",
           "sent_at", "deliver_at", "delay_s", "eta_s", "arrives_after_s", "earliest_reply_after_s"}


def test_every_screen_gets_the_fields_the_typed_client_expects(client):
    state = client.get("/api/base/state").get_json()
    assert set(state) == STOP | {"speedup", "stops"} and set(state["stops"][0]) == STOP
    for _ in range(5):
        posted = client.post("/api/base/readings", json={"crew_id": 1, "spo2": 86, "heart_rate": 88}).get_json()
    assert set(posted) == {"reading", "alerts"} and set(posted["reading"]) == READING
    alert = client.get("/api/base/alerts?open=1").get_json()[0]
    assert set(alert) == ALERT and set(alert["timeline"]) == TIMELINE
    member = client.get("/api/base/crew").get_json()[0]
    assert set(member) == {"id", "name", "role", "level", "latest", "typed", "usual"}
    assert set(member["latest"]) == READING and set(member["usual"]) == {"heart_rate"}
    assert set(client.get("/api/base/outbox").get_json()[0]) == MESSAGE
    assert set(client.get("/api/earth/inbox").get_json()) == {"link_up", "delay_s", "mode", "who_decides", "messages"}
    assert set(client.get("/api/base/habitat").get_json()) == {"cabin", "radiation", "source", "url", "kind"}
    assert set(client.post("/api/base/dial", json={"stop": "moon"}).get_json()) == {"state", "flushed"}
```

- [ ] **Step 2:** Run `python -m pytest -q`. Expected: `107 passed`. If a set differs, the code is the truth: correct the set here and the matching type below, and tell the backend owner which field.

- [ ] **Step 3:** Create `docs/frontend/lighttime-api.ts`:

```ts
// Typed client for the LightTime backend. Copy to src/lib/lighttime-api.ts in the frontend repo.
// The backend test tests/test_contract.py checks these field names. Do not rename them here.

export type Stop = "station" | "moon" | "mars" | "sun";
export type Mode = "doctor_live" | "crew_first" | "ship_alone";
export type Level = "nominal" | "advisory" | "caution" | "warning" | "emergency";
export type Story = "stage" | "full" | "real";

/** The four colours on screen. Add an SOS token next to ok, watch and alert. */
export const LEVEL_LABEL: Record<Level, "OK" | "WATCH" | "ALERT" | "SOS"> = {
  nominal: "OK", advisory: "WATCH", caution: "WATCH", warning: "ALERT", emergency: "SOS",
};

export interface StopState {
  stop: Stop; label: string; link_up: boolean;
  delay_s: number;        // one way, mission seconds. For "sun" show "No link" and ignore this
  mode: Mode; who_decides: string; light_time_source: string;
  path_km: number;        // delay x speed of light
  round_trip_s: number;   // 2 x delay: the earliest a reply can come back
  plays_as_s: number;     // real seconds one leg takes in the demo
}
export interface MissionState extends StopState { speedup: number; stops: StopState[] }

export interface Reading {
  id: number; crew_id: number; at: string; source: string; signal_ok: boolean; context: string | null;
  heart_rate: number | null; spo2: number | null; skin_temp: number | null; bp_sys: number | null;
  bp_dia: number | null; glucose: number | null; sleep_hours: number | null; mood: number | null;
}
export interface UsualRange { low: number; high: number; n: number }
export interface CrewMember {
  id: number; name: string; role: string; level: Level;
  latest: Reading | null; typed: Reading | null; usual: { heart_rate: UsualRange | null };
}

export interface Lookahead {
  now: number; per_min: number; eta_s: number; red_line: number;
  at: string; red_line_at: string;      // count down to red_line_at
  reply_s: number | null; earth_in_time: boolean;
}
export interface Timeline {
  raised_at: string; acknowledged_at: string | null; sent_at: string | null;
  earth_eta_s: number | null; earth_at: string | null;
  earliest_reply_at: string | null;     // count down to this for "earliest reply"
  reply_at: string | null; resolved_at: string | null;
}
export interface Alert {
  id: number; crew_id: number; crew: string; at: string; level: Level; vital: string;
  value: number | null; unit: string | null; reason: string; source: string | null; auto: boolean;
  nasa_risk: string; steps: string[]; steps_done: number[]; acknowledged_by: string | null;
  cleared_at: string | null; cleared_by: string | null; cleared_note: string | null;
  why: string[];                        // how the ship reached this alert. Show it
  timeline: Timeline; lookahead: Lookahead | null; speak: string | null;
}

export interface LinkMessage {
  id: number; direction: "to_earth" | "to_ship";
  kind: "report" | "update" | "message" | "reply" | "summary";
  priority: number; payload: Record<string, unknown>; status: "queued" | "in_flight" | "delivered";
  in_reply_to: number | null; created_at: string; sent_at: string | null; deliver_at: string | null;
  delay_s: number | null; eta_s: number | null;       // eta_s: mission seconds left
  arrives_after_s: number | null; earliest_reply_after_s: number | null;
}
export interface EarthInbox { link_up: boolean; delay_s: number; mode: Mode; who_decides: string; messages: LinkMessage[] }
export interface Habitat {
  cabin: { temp_c: number; humidity_pct: number; co2_ppm: number; as_of: string };
  radiation: { total_mgy_day: number; gcr_mgy_day: number; saa_mgy_day: number; as_of: string } | null;
  source: string; url: string; kind: string;
}
export interface Source { id: string; agency: string; name: string; kind: "live" | "file" | "hand"; url: string; used_for: string; as_of: string }
export interface Network {
  passes: { dish: string; craft: string; round_trip_s: number }[]; source: string; url: string;
  dsn_one_way_s: number | null; horizons_one_way_s: number; differ_s: number | null;
}
export type CheckIn = Partial<Pick<Reading, "bp_sys" | "bp_dia" | "glucose" | "sleep_hours" | "mood" | "spo2" | "heart_rate">>;

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:5000";

async function call<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(BASE + path, {
    method: body === undefined ? "GET" : "POST",
    cache: "no-store",
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) throw new Error(`${path}: ${response.status}`);
  return (await response.json()) as T;
}

export const api = {
  // ship
  state: () => call<MissionState>("/api/base/state"),
  dial: (stop: Stop) => call<{ state: StopState; flushed: number }>("/api/base/dial", { stop }),
  crew: () => call<CrewMember[]>("/api/base/crew"),
  readings: (crewId: number, limit = 120) => call<Reading[]>(`/api/base/crew/${crewId}/readings?limit=${limit}`),
  alerts: () => call<Alert[]>("/api/base/alerts?open=1"),
  allAlerts: () => call<Alert[]>("/api/base/alerts"),
  acknowledge: (id: number, by: string) => call<Alert>(`/api/base/alerts/${id}/ack`, { by }),
  tickStep: (id: number, index: number) => call<Alert>(`/api/base/alerts/${id}/steps`, { index }),
  sendToEarth: (id: number) => call<Alert>(`/api/base/alerts/${id}/send`, {}),
  resolve: (id: number, by: string, note: string) => call<Alert>(`/api/base/alerts/${id}/clear`, { by, note }),
  message: (text: string, from: string, alertId?: number) =>
    call<LinkMessage>("/api/base/messages", { text, from, alert_id: alertId ?? null }),
  sos: (crewId: number) => call<Alert>("/api/base/sos", { crew_id: crewId }),
  checkIn: (crewId: number, values: CheckIn) =>
    call<{ reading: Reading; alerts: Alert[] }>("/api/base/readings", { ...values, crew_id: crewId, source: "typed" }),
  outbox: () => call<LinkMessage[]>("/api/base/outbox"),    // everything that has left the ship: "What Earth has seen"
  inbox: () => call<LinkMessage[]>("/api/base/inbox"),
  habitat: () => call<Habitat>("/api/base/habitat"),
  sources: () => call<Source[]>("/api/base/sources"),
  sendSummaries: () => call<{ sent: number; pruned: number }>("/api/base/summary/send", {}),
  // demo controls
  reset: () => call<{ ok: boolean }>("/api/base/reset", {}),
  startStory: (name: Story, replay = true) => call<{ ok: boolean }>("/api/base/scenario/start", { name, replay }),
  stopStory: () => call<{ ok: boolean }>("/api/base/scenario/stop", {}),
  // Earth
  earthInbox: () => call<EarthInbox>("/api/earth/inbox"),
  earthOutbox: () => call<LinkMessage[]>("/api/earth/outbox"),
  earthReply: (text: string, messageId?: number, from = "Flight surgeon") =>
    call<LinkMessage>("/api/earth/reply", { text, message_id: messageId ?? null, from }),
  network: () => call<Network>("/api/earth/network"),
};

const spoken = new Set<string>();
/** Say an alert's line once per alert and level. Call it from a client component. */
export function speakOnce(alert: Alert): void {
  if (!alert.speak || typeof window === "undefined") return;
  const key = `${alert.id}:${alert.level}:${alert.at}`;
  if (spoken.has(key)) return;
  spoken.add(key);
  window.speechSynthesis.speak(new SpeechSynthesisUtterance(alert.speak));
}
```

- [ ] **Step 4:** Create `docs/frontend/use-poll.ts`:

```ts
"use client";
// Copy to src/lib/use-poll.ts. Pass a stable function such as api.crew, or wrap it in useCallback.
import { useEffect, useState } from "react";

export function usePoll<T>(load: () => Promise<T>, everyMs = 1000): { data: T | null; error: string | null } {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let live = true;
    const tick = async () => {
      try {
        const next = await load();
        if (live) { setData(next); setError(null); }
      } catch (problem) {
        if (live) setError(String(problem));
      }
    };
    void tick();
    const timer = setInterval(tick, everyMs);
    return () => { live = false; clearInterval(timer); };
  }, [load, everyMs]);
  return { data, error };
}
```

- [ ] **Step 5:** Create `docs/frontend/README.md`:

```markdown
# Wiring the frontend to the backend

1. Copy `lighttime-api.ts` and `use-poll.ts` into `src/lib/` in the frontend repo.
2. Put `NEXT_PUBLIC_API_URL=http://<backend laptop IP>:5000` in `.env.local`. The backend allows any origin.
3. In a client component: `const { data: crew } = usePoll(api.crew)`.

| Screen | Poll (once a second) | Buttons |
|---|---|---|
| Crew board and dial | `api.state`, `api.crew`, `api.alerts` | `api.dial`, `api.startStory`, `api.reset`, `api.sos` |
| Alert | `api.alerts` | `api.acknowledge`, `api.tickStep`, `api.sendToEarth`, `api.resolve`, `api.message` |
| What Earth has seen | `api.outbox`, `api.inbox` | `api.sendSummaries` |
| Earth console | `api.earthInbox`, `api.earthOutbox`; `api.network` every 30 s | `api.earthReply` |
| Data | `api.sources`, `api.habitat` (every 5 s) | none |

Rules that save you a bug each:

- Never work out a delay or a countdown from your own maths. Show `delay_s`, `round_trip_s`, `eta_s` as given, and count down to the times `red_line_at` and `earliest_reply_at`.
- Mission seconds and demo seconds differ. A Mars leg is 661 mission seconds and plays in 11 real seconds. Label it "playing 60x faster" using `speedup`.
- For the stop `sun`, show "No link". Ignore its `delay_s`.
- Call `speakOnce(alert)` for every open alert on every poll. It only speaks once.
- Show `why` on the alert screen and ask for a note when the crew resolves. The CSA advisor asked for both.
- Alert ids restart after a reset. Never store one.
- An empty form box can be sent as "". The backend treats it as no reading.
- Readings for one crew member include typed check-ins. Filter on `source` for a chart.
```

- [ ] **Step 6:** Commit: `docs: typed client and contract for the frontend`. Tell the frontend owner the three files are in `docs/frontend/`.

---

### Task 7: Verify the data

**Files:** Create `scripts/verify_data.py`, `data/CHECKSUMS.sha256` (written by the script).

- [ ] **Step 1:** Create `scripts/verify_data.py`:

```python
"""Check the data and the light-time numbers. Run from the repo root:

    python scripts/verify_data.py            every check, including the two NASA services
    python scripts/verify_data.py --offline  skip the checks that need the network
    python scripts/verify_data.py --write    record the checksums of the raw files (do this once)
"""
import csv
import hashlib
import pathlib
import statistics
import sys
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from base_station.rules import LIMITS           # noqa: E402
from common import dsn, lighttime, modes        # noqa: E402

DATA, SUMS = ROOT / "data", ROOT / "data" / "CHECKSUMS.sha256"
RAW = ("ppg_dalia", "eda", "spo2_uw", "spo2_apnea_ecg")
NEWS2 = {   # typed from the NEWS2 chart (Royal College of Physicians, 2017)
    "spo2": [[91, 3], [93, 2], [95, 1], [None, 0]],
    "heart_rate": [[40, 3], [50, 1], [90, 0], [110, 1], [130, 2], [None, 3]],
    "bp_sys": [[90, 3], [100, 2], [110, 1], [219, 0], [None, 3]],
}
failed = []


def check(name, ok, detail=""):
    if not ok:
        failed.append(name)
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  ({detail})" if detail else ""))


def rows(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def digest(path):
    """sha256 with Windows line endings folded, so the same file gives the same sum on every laptop."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def raw_files():
    return sorted(p for folder in RAW for p in (DATA / folder).rglob("*") if p.is_file())


if __name__ == "__main__":
    if "--write" in sys.argv:
        SUMS.write_text("".join(f"{digest(p)}  {p.relative_to(DATA).as_posix()}\n" for p in raw_files()))
        print(f"wrote {len(raw_files())} checksums to {SUMS.relative_to(ROOT)}")
        sys.exit(0)

    print("Light time")
    check("1 AU is 499.005 s of light", abs(lighttime.AU_KM / lighttime.C_KM_S - 499.0048) < 0.0001)
    check("Moon figure matches 384,400 km", abs(384_400 / lighttime.C_KM_S - modes.FIXED_DELAY_S["moon"]) < 0.05)
    check("Station figure matches a relay path of 2 x 35,786 km",
          abs(2 * 35_786 / lighttime.C_KM_S - modes.FIXED_DELAY_S["station"]) < 0.05)
    check("Crew-first line is five minutes", modes.CREW_FIRST_AT_S == 300)
    if "--offline" not in sys.argv:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        live = lighttime.fetch(today)
        check("Horizons answers, and Mars is inside its orbit limits", 0.372 * 499 <= live <= 2.68 * 499,
              f"{live:.2f} s one way, {live / 60:.2f} min, {live * lighttime.C_KM_S / 1e6:.1f} million km")
        if today in lighttime.FALLBACK_S:
            check("Saved fallback matches live Horizons", abs(live - lighttime.FALLBACK_S[today]) < 1,
                  f"saved {lighttime.FALLBACK_S[today]}")
        passes = dsn.parse(dsn.fetch())
        if passes:
            measured = statistics.median(p["round_trip_s"] for p in passes) / 2
            check("DSN Now agrees with Horizons within 10 s", abs(measured - live) < 10,
                  f"DSN {measured:.1f} s from {', '.join(p['craft'] for p in passes)}")
        else:
            print("SKIP  DSN Now: no antenna is on Mars this minute. Run again later.")

    print("Rules")
    for vital, bands in NEWS2.items():
        check(f"{vital} bands are the NEWS2 chart", LIMITS["vitals"][vital]["bands"] == bands)
    check("Heart rate cannot raise an alarm", LIMITS["vitals"]["heart_rate"].get("alert") is False)

    print("Clean tables")
    wrist = sorted((DATA / "clean" / "wrist").glob("S*.csv"))
    check("15 wrist files", len(wrist) == 15)
    for path in wrist:
        table = rows(path)
        rates, temps = [float(r["heart_rate"]) for r in table], [float(r["skin_temp"]) for r in table]
        flagged = sum(r["signal_ok"] == "0" for r in table)
        check(f"{path.stem}: heart rate and skin temperature are possible, few flags",
              30 <= min(rates) and max(rates) <= 230 and 20 <= min(temps) and max(temps) <= 42 and flagged <= 5,
              f"{len(table)} s, {min(rates):.0f} to {max(rates):.0f} bpm, {flagged} flagged")
    cabin = rows(DATA / "clean" / "cabin_rr1.csv")
    check("Cabin: 12,087 rows, all values possible",
          len(cabin) == 12087 and all(15 <= float(r["temp_c"]) <= 35 and 10 <= float(r["humidity_pct"]) <= 80
                                      and 300 <= float(r["co2_ppm"]) <= 8000 for r in cabin))
    doses = rows(DATA / "clean" / "radiation_rr1.csv")
    check("Radiation: 39 days, each under 2 mGy", len(doses) == 39 and all(0 < float(r["total_mgy_day"]) < 2 for r in doses))
    event = [float(r["spo2"]) for r in rows(DATA / "clean" / "spo2_event.csv")]
    check("Oxygen event: 769 s, 98 down to 67 and back to 96",
          len(event) == 769 and event[0] == 98 and min(event) == 67 and event[-1] == 96)

    print("Raw files")
    if SUMS.exists():
        known = dict(line.split("  ", 1)[::-1] for line in SUMS.read_text().splitlines())
        now = {p.relative_to(DATA).as_posix(): digest(p) for p in raw_files()}
        changed = [name for name in known if now.get(name) != known[name]]
        check(f"{len(known)} raw files unchanged since the checksums were written", not changed, ", ".join(changed[:3]))
    else:
        check("Checksums exist (run with --write once)", False)
    top = (DATA / "README.md").read_text(encoding="utf-8") if (DATA / "README.md").exists() else ""
    for folder in RAW:
        check(f"{folder} says where it came from", (DATA / folder / "README.md").exists() or folder in top)

    print(f"\n{'ALL CHECKS PASSED' if not failed else str(len(failed)) + ' FAILED: ' + '; '.join(failed)}")
    sys.exit(1 if failed else 0)
```

- [ ] **Step 2:** Run `python scripts/verify_data.py --write`, then `python scripts/verify_data.py`.
Expected: every line `PASS` (one `SKIP` is fine) and `ALL CHECKS PASSED`. A `FAIL` is a finding, not a typo to patch: use systematic-debugging to learn whether the data or the check is wrong, and tell the backend owner either way. Likely first suspects, since this script has never run: a column name in a clean table, or a top-level README that does not name a folder.

- [ ] **Step 3:** Commit: `data: verification script and checksums`.

- [ ] **Step 4: The checks a script cannot do.** Copy this table into `docs/data-verification.md` and have a person (the documentation owner) tick each line on Sunday morning. About 20 minutes.

| # | Open this | Confirm |
|---|---|---|
| 1 | NEWS2 chart, Royal College of Physicians 2017 (link in `limits.json` source) | The three band lists in `scripts/verify_data.py` match the chart |
| 2 | https://www.nasa.gov/hrp/risks/ | Each `nasa_risk` name in `limits.json` is spelled as NASA spells it |
| 3 | https://ssd.jpl.nasa.gov/horizons/ (web app: Mars, observer Earth centre, quantity 21) | Same light time as `/api/base/state` shows for Mars |
| 4 | https://eyes.nasa.gov/apps/dsn-now/ | A Mars spacecraft shown there appears in `/api/earth/network` |
| 5 | Each data folder's README | Licence and citation are present and the link opens |
| 6 | NASA-STD-3001 Volume 1, requirement V1 3004 | It says what the spec says it says |
| 7 | NEEMO 16 reference in `common/modes.py` | The five-minute line is in the source |
| 8 | A NASA page on ISS communications through TDRS | The 0.25 s station figure is fair. If none is found, label it "assumed" on the dial |
| 9 | The cue list in the CSA advisor record (CMO-DA, STD-3001 section 7.3) | Verified before anyone says it in the pitch, or left out |

---

### Task 8: A held-out check of the time-left settings

- [ ] **Step 1:** Create `scripts/crossval_lookahead.py`:

```python
"""Are the time-left settings luck? Choose them on five volunteers, test on the sixth, six times.

    python scripts/crossval_lookahead.py        about three minutes
"""
import itertools
import pathlib
import statistics
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from base_station import lookahead                      # noqa: E402
from scripts.build_clean_data import read_uw            # noqa: E402
from scripts.check_spo2_rules import one_hz, play       # noqa: E402

GRID = list(itertools.product((45, 60), (1.5, 2.0, 2.5), (0.4, 0.5, 0.6)))   # window, drop, agreement
MAX_FALSE = 3       # trend warnings allowed on the 7.8 hour control recording


def lead(values):
    """Seconds between the last trend warning and the SOS, or None if there was no warning first."""
    sos, warnings = play(values)
    before = [t for t, _ in warnings if t < sos[0]]
    return sos[0] - before[-1] if before else None


def score(leads):
    """More volunteers warned first, then a longer median warning."""
    got = [x for x in leads if x is not None]
    return len(got), statistics.median(got) if got else 0


if __name__ == "__main__":
    volunteers = {s: [row[0] for row in read_uw((ROOT / "data" / "spo2_uw" / f"{s}.csv").read_text(encoding="utf-8"))]
                  for s in range(100001, 100007)}
    control, table = one_hz("c01r"), {}
    for setting in GRID:
        lookahead.WINDOW, lookahead.MIN_DROP, lookahead.MIN_AGREEMENT = setting
        false = len(play(control)[1])
        table[setting] = (false, {s: lead(v) for s, v in volunteers.items()})
        print(f"window {setting[0]}, drop {setting[1]}, agreement {setting[2]}: "
              f"{false} control warnings, leads {list(table[setting][1].values())}")
    allowed = {k: v[1] for k, v in table.items() if v[0] <= MAX_FALSE}
    held = []
    for out in volunteers:
        best = max(allowed, key=lambda k: score([allowed[k][s] for s in volunteers if s != out]))
        held.append(allowed[best][out])
        print(f"held out {out}: settings chosen without it {best}, warning ahead by {held[-1]} s")
    got = [x for x in held if x is not None]
    print(f"\nHeld-out result: warned before the SOS for {len(got)} of 6, median {statistics.median(got) if got else 0:g} s ahead")
    print(f"Settings in the ship today: window 60, drop 2.0, agreement 0.5 -> {table[(60, 2.0, 0.5)]}")
```

- [ ] **Step 2:** Run it. Whatever it prints, write the held-out line into section 6 of `docs/specs/2026-11-14-ship-ai-and-data-design.md` in place of "this is a fit and not a validation", with the number as printed. If the held-out result is worse than 6 of 6, write that. Do not change the ship's settings tonight.
- [ ] **Step 3:** Commit: `evidence: leave-one-volunteer-out check of the time-left settings`.

---

### Task 9: Wrap up

- [ ] **Step 1:** `AI_USE.md`: add today's line (the backend owner, Claude, this plan: contract, light-time working, DSN check, verification).
- [ ] **Step 2:** `README.md`: add the three new routes and the two scripts.
- [ ] **Step 3:** `python -m pytest -q` (expected `107 passed`), then `git push`, then open the pull request to `main` for the reviewer.
- [ ] **Step 4: Tonight's run-through, with the frontend.** Each line must work on a second laptop pointed at this one.

| # | Do | See |
|---|---|---|
| 1 | Dial Mars | Delay 11 min, path 198 million km, "Crew medical officer", source JPL Horizons |
| 2 | Start `stage` with replay | Three crew tiles moving on real wrist data, SOS for Okafor in about 9 s, the line spoken once |
| 3 | Open the alert | `why` lines, checklist, timeline with a countdown to the earliest reply |
| 4 | Earth console | Nothing for 11 real seconds, then the report with its asked-ahead answers |
| 5 | Earth replies | Earth outbox counts down, the ship's inbox gets it 11 s later |
| 6 | Tick "mask", then Resolve with a note | Recovery, and Earth receives the note |
| 7 | Dial Behind the Sun, press SOS | "No link", report queued. Dial Mars: it flushes, SOS first |
| 8 | Data screen | Four NASA sources listed, cabin tiles, DSN figure beside Horizons |
| 9 | Reset, start again | Dial still on Mars, clean board |

---

## Not in this plan

A login on the API, a per-person sharing switch, doctor thinking time in the ETA, a learned model, DONKI space weather, and any frontend screen. A fallback console served by Flask is a question for the backend owner, not a task here.
