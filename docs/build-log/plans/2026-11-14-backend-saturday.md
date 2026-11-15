# LIGHT-TIME Backend (Saturday) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A Flask and Postgres backend that takes suit readings, raises alerts with reasons, and carries reports and replies between ship and Earth with the real light-time delay.

**Architecture:** One Flask app with two blueprints: `base_station/` is the ship (`/api/base`), `command_center/` is the ground (`/api/earth`). The folder names follow the repo README, with underscores so Python can import them. They share one database, and the only thing Earth may read is the `link_message` table, where each row becomes visible when its `deliver_at` time passes. A dial sets the distance; one rule on the delay sets who decides.

**Tech Stack:** Python 3.10+, Flask 3, Flask-SQLAlchemy, Postgres through psycopg 3 (SQLite fallback for tests and one-laptop mode), requests, pytest.

**Design:** `docs/specs/2026-11-14-backend-design.md`

**Updated 14 Nov, 11:40, after the frontend owner's screens and the CSA workshop:** Tasks 6 and 7 gained acknowledge, send to Earth, a crew message and the round-trip timeline, so his alert screen runs on real data. The two packages are now `base_station` and `command_center`, to match the repo README. Apart from those names, Tasks 1 to 5 did not change, and Task 8 changed only in its test count.

**Run every command from the repo root.** On Windows, activate the virtual environment first with `.venv\Scripts\activate`.

---

## File map

| File | Responsibility |
| --- | --- |
| `app.py` | Builds the Flask app, connects the database, registers both blueprints |
| `common/models.py` | The five tables, `utcnow`, `iso`, `seed` |
| `common/lighttime.py` | Mars one-way light time from JPL Horizons, with a dated fallback |
| `common/modes.py` | The four dial stops and the who-decides rule |
| `common/link.py` | The delayed link: send, queue, flush, what has arrived |
| `base_station/routes.py` | Ship API |
| `base_station/rules.py`, `base_station/limits.json` | Bands, the sustained check, alerts |
| `base_station/reports.py`, `base_station/procedures.json` | Earth report and the spoken line |
| `base_station/scenario.py` | The scripted story |
| `command_center/routes.py` | Ground API |
| `tests/` | One test file per module |

---

### Task 1: Scaffold, tables and app factory

**Files:**
- Create: `requirements.txt`, `pytest.ini`, `.gitignore`, `.env.example`, `AI_USE.md`
- Create: `common/__init__.py`, `base_station/__init__.py`, `command_center/__init__.py` (all empty)
- Create: `common/models.py`, `app.py`, `base_station/routes.py`, `command_center/routes.py`
- Test: `tests/conftest.py`, `tests/test_app.py`

- [ ] **Step 1: Write the project files**

`requirements.txt`
```
Flask>=3.0
Flask-SQLAlchemy>=3.1
Flask-Cors>=4.0
psycopg[binary]>=3.2
python-dotenv>=1.0
requests>=2.31
pytest>=8.0
```

`pytest.ini`
```ini
[pytest]
pythonpath = .
testpaths = tests
```

`.gitignore`
```
.venv/
__pycache__/
.pytest_cache/
instance/
.env
```

`.env.example`
```
# Copy to .env. Leave DATABASE_URL out to use a local SQLite file.
DATABASE_URL=postgresql+psycopg://lighttime:lighttime@localhost:5432/lighttime
```

`AI_USE.md`
```markdown
# AI use log

One line per use: date, who, tool, what for.

- 2026-11-14, the backend owner, Claude: backend design, build plan and first version of the Flask backend code and tests.
```

- [ ] **Step 2: Install**

Run: `python -m venv .venv` then `.venv\Scripts\activate` then `pip install -r requirements.txt`
Expected: ends with `Successfully installed ...`

- [ ] **Step 3: Write the failing test**

`tests/conftest.py`
```python
import pytest

from app import create_app


@pytest.fixture
def app():
    app = create_app("sqlite:///:memory:")
    app.config["TESTING"] = True
    return app


@pytest.fixture
def client(app):
    return app.test_client()
```

`tests/test_app.py`
```python
from common.models import Crew, MissionState, db


def test_app_starts_with_three_crew_and_the_dial_at_station(app):
    with app.app_context():
        assert [c.name for c in Crew.query.order_by(Crew.id)] == ["Okafor", "Lindqvist", "Sato"]
        assert db.session.get(MissionState, 1).stop == "station"


def test_health(client):
    assert client.get("/api/base/health").get_json() == {"ok": True}
```

- [ ] **Step 4: Run it to see it fail**

Run: `python -m pytest tests/test_app.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app'`

- [ ] **Step 5: Write the code**

`common/models.py`
```python
"""Tables for the ship, the ground and the link between them."""
from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

VITALS = ["heart_rate", "spo2", "skin_temp", "bp_sys", "bp_dia", "glucose", "sleep_hours", "mood"]


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def iso(dt):
    return dt.isoformat() + "Z" if dt else None


class Crew(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(40), nullable=False)
    role = db.Column(db.String(40), nullable=False, default="crew")


class Reading(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    crew_id = db.Column(db.Integer, db.ForeignKey("crew.id"), nullable=False, index=True)
    at = db.Column(db.DateTime, nullable=False, default=utcnow, index=True)
    source = db.Column(db.String(12), nullable=False, default="suit")
    signal_ok = db.Column(db.Boolean, nullable=False, default=True)
    heart_rate = db.Column(db.Float)
    spo2 = db.Column(db.Float)
    skin_temp = db.Column(db.Float)
    bp_sys = db.Column(db.Float)
    bp_dia = db.Column(db.Float)
    glucose = db.Column(db.Float)
    sleep_hours = db.Column(db.Float)
    mood = db.Column(db.Float)

    def to_dict(self):
        out = {"id": self.id, "crew_id": self.crew_id, "at": iso(self.at),
               "source": self.source, "signal_ok": self.signal_ok}
        out.update({v: getattr(self, v) for v in VITALS})
        return out


class Alert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    crew_id = db.Column(db.Integer, db.ForeignKey("crew.id"), nullable=False, index=True)
    at = db.Column(db.DateTime, nullable=False, default=utcnow)
    level = db.Column(db.String(12), nullable=False)
    vital = db.Column(db.String(16), nullable=False)
    value = db.Column(db.Float)
    reason = db.Column(db.String(200), nullable=False)
    auto = db.Column(db.Boolean, nullable=False, default=True)
    nasa_risk = db.Column(db.String(80), nullable=False, default="")
    steps_done = db.Column(db.JSON, nullable=False, default=list)
    cleared_at = db.Column(db.DateTime)
    cleared_by = db.Column(db.String(40))


class MissionState(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    stop = db.Column(db.String(12), nullable=False, default="station")


class LinkMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    direction = db.Column(db.String(8), nullable=False)
    kind = db.Column(db.String(8), nullable=False)
    priority = db.Column(db.Integer, nullable=False, default=5)
    payload = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    sent_at = db.Column(db.DateTime)
    delay_s = db.Column(db.Float)
    deliver_at = db.Column(db.DateTime, index=True)
    in_reply_to = db.Column(db.Integer)


def seed():
    if Crew.query.count() == 0:
        db.session.add_all([Crew(name="Okafor"), Crew(name="Lindqvist", role="cmo"), Crew(name="Sato")])
    if db.session.get(MissionState, 1) is None:
        db.session.add(MissionState(id=1, stop="station"))
    db.session.commit()
```

`base_station/routes.py`
```python
from flask import Blueprint, jsonify

bp = Blueprint("base", __name__)


@bp.get("/health")
def health():
    return jsonify(ok=True)
```

`command_center/routes.py`
```python
from flask import Blueprint

bp = Blueprint("earth", __name__)
```

`app.py`
```python
import os

from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS

from common.models import db, seed


def create_app(database_url=None):
    load_dotenv()
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = (
        database_url or os.getenv("DATABASE_URL", "sqlite:///lighttime.db"))
    CORS(app)
    db.init_app(app)

    from base_station.routes import bp as base_bp
    from command_center.routes import bp as earth_bp
    app.register_blueprint(base_bp, url_prefix="/api/base")
    app.register_blueprint(earth_bp, url_prefix="/api/earth")

    with app.app_context():
        db.create_all()
        seed()
    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=5000)
```

- [ ] **Step 6: Run the tests**

Run: `python -m pytest tests/test_app.py -v`
Expected: 2 passed

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "feat: app factory, tables and seed crew"
```

---

### Task 2: Real light time and the who-decides rule

**Files:**
- Create: `common/lighttime.py`, `common/modes.py`
- Modify: `tests/conftest.py` (keep tests off the network)
- Test: `tests/test_lighttime.py`, `tests/test_modes.py`

- [ ] **Step 1: Write the failing tests**

Replace `tests/conftest.py` with:
```python
import pytest
import requests

from app import create_app
from common import lighttime


@pytest.fixture
def app(monkeypatch):
    def offline(day):
        raise requests.ConnectionError("tests do not use the network")

    monkeypatch.setattr(lighttime, "fetch", offline)
    lighttime._cache.clear()
    app = create_app("sqlite:///:memory:")
    app.config["TESTING"] = True
    return app


@pytest.fixture
def client(app):
    return app.test_client()
```

`tests/test_lighttime.py`
```python
from common import lighttime

SAMPLE = """
 Date__(UT)__HR:MN, , ,  1-way_down_LT,
$$SOE
 2026-Nov-15 00:00, , ,  10.94362708,
 2026-Nov-16 00:00, , ,  10.87269269,
$$EOE
"""


def test_parse_reads_minutes_and_returns_seconds():
    assert abs(lighttime.parse(SAMPLE) - 656.62) < 0.01


def test_offline_falls_back_to_the_dated_table(app):
    assert lighttime.mars_seconds("2026-11-15") == 656.62
    assert "2026-11-13" in lighttime.source("2026-11-15")
```

`tests/test_modes.py`
```python
from common import modes


def test_doctor_decides_below_five_minutes():
    assert modes.mode_for(0.25, True) == "doctor_live"
    assert modes.mode_for(299, True) == "doctor_live"


def test_crew_decides_from_five_minutes():
    assert modes.mode_for(300, True) == "crew_first"


def test_no_link_means_the_ship_is_alone():
    assert modes.mode_for(656, False) == "ship_alone"


def test_mars_stop_uses_real_light_time(app):
    mars = modes.describe("mars")
    assert mars["mode"] == "crew_first"
    assert 180 <= mars["delay_s"] <= 1350
    assert mars["who_decides"] == "Crew medical officer"


def test_station_and_moon_are_short_and_live(app):
    assert modes.describe("station")["mode"] == "doctor_live"
    assert modes.describe("moon")["delay_s"] == 1.3
```

- [ ] **Step 2: Run them to see them fail**

Run: `python -m pytest tests/test_lighttime.py tests/test_modes.py -v`
Expected: FAIL with `ImportError: cannot import name 'lighttime' from 'common'`

- [ ] **Step 3: Write the code**

`common/lighttime.py`
```python
"""One-way light time from command_center to Mars, from NASA JPL Horizons (quantity 21)."""
from datetime import datetime, timedelta, timezone

import requests

HORIZONS_URL = "https://ssd.jpl.nasa.gov/api/horizons.api"
# Read from Horizons on 2026-11-13: Mars seen from command_center's centre, in seconds.
FALLBACK_S = {"2026-11-14": 660.86, "2026-11-15": 656.62, "2026-11-16": 652.36}
FALLBACK_NOTE = "JPL Horizons, read on 2026-11-13"
_cache = {}


def parse(text):
    """Return seconds from a Horizons CSV ephemeris that holds quantity 21."""
    first_row = text.split("$$SOE")[1].split("$$EOE")[0].strip().splitlines()[0]
    numbers = []
    for field in first_row.split(","):
        try:
            numbers.append(float(field))
        except ValueError:
            pass
    return numbers[-1] * 60.0


def fetch(day):
    next_day = (datetime.strptime(day, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
    params = {
        "format": "text", "COMMAND": "'499'", "OBJ_DATA": "'NO'", "MAKE_EPHEM": "'YES'",
        "EPHEM_TYPE": "'OBSERVER'", "CENTER": "'500@399'", "START_TIME": f"'{day}'",
        "STOP_TIME": f"'{next_day}'", "STEP_SIZE": "'1d'", "QUANTITIES": "'21'",
        "CSV_FORMAT": "'YES'",
    }
    response = requests.get(HORIZONS_URL, params=params, timeout=5)
    response.raise_for_status()
    return parse(response.text)


def _lookup(day):
    day = day or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if day not in _cache:
        try:
            _cache[day] = (fetch(day), "JPL Horizons, live")
        except (requests.RequestException, IndexError, ValueError):
            _cache[day] = (FALLBACK_S.get(day, FALLBACK_S["2026-11-15"]), FALLBACK_NOTE)
    return _cache[day]


def mars_seconds(day=None):
    return _lookup(day)[0]


def source(day=None):
    return _lookup(day)[1]
```

`common/modes.py`
```python
"""The four dial stops and the rule for who decides."""
from common import lighttime

# NASA's NEEMO 16 test (Rader et al. 2013): at about five minutes one way,
# critical medical advice cannot always get through.
CREW_FIRST_AT_S = 300

STOPS = {
    "station": {"label": "Space station", "link_up": True},
    "moon": {"label": "Moon", "link_up": True},
    "mars": {"label": "Mars", "link_up": True},
    "sun": {"label": "Behind the Sun", "link_up": False},
}
FIXED_DELAY_S = {"station": 0.25, "moon": 1.3}
WHO_DECIDES = {
    "doctor_live": "Flight surgeon on Earth",
    "crew_first": "Crew medical officer",
    "ship_alone": "The crew, alone",
}


def mode_for(delay_s, link_up):
    if not link_up:
        return "ship_alone"
    if delay_s >= CREW_FIRST_AT_S:
        return "crew_first"
    return "doctor_live"


def describe(stop):
    fixed = stop in FIXED_DELAY_S
    delay_s = FIXED_DELAY_S[stop] if fixed else lighttime.mars_seconds()
    link_up = STOPS[stop]["link_up"]
    mode = mode_for(delay_s, link_up)
    return {
        "stop": stop, "label": STOPS[stop]["label"], "link_up": link_up, "delay_s": delay_s,
        "mode": mode, "who_decides": WHO_DECIDES[mode],
        "light_time_source": "fixed" if fixed else lighttime.source(),
    }
```

- [ ] **Step 4: Run the tests**

Run: `python -m pytest -v`
Expected: 9 passed

- [ ] **Step 5: Check the live number once, by hand**

Run: `python -c "from common import lighttime; print(lighttime.mars_seconds(), lighttime.source())"`
Expected on the venue network: a number near `660` and `JPL Horizons, live`. If it prints the fallback note, the network blocked the call; the demo still runs on the dated values.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat: Mars light time from JPL Horizons and the who-decides rule"
```

---

### Task 3: The delayed link

**Files:**
- Create: `common/link.py`
- Test: `tests/test_link.py`

- [ ] **Step 1: Write the failing test**

`tests/test_link.py`
```python
from datetime import timedelta

from common import link
from common.models import utcnow


def test_short_delays_are_real_and_long_ones_are_sped_up():
    assert link.real_delay_s(1.3) == 1.3
    assert link.real_delay_s(660) == 11


def test_a_message_is_invisible_until_it_arrives(app):
    with app.app_context():
        t0 = utcnow()
        link.send("to_earth", "report", {"x": 1}, delay_s=660, link_up=True, now=t0)
        assert link.delivered("to_earth", now=t0 + timedelta(seconds=10)) == []
        assert len(link.delivered("to_earth", now=t0 + timedelta(seconds=11))) == 1
        assert link.delivered("to_ship", now=t0 + timedelta(seconds=11)) == []


def test_three_times_on_a_message(app):
    with app.app_context():
        message = link.send("to_earth", "report", {}, delay_s=660, link_up=True)
        shown = link.to_dict(message)
        assert shown["status"] == "in_flight"
        assert shown["arrives_after_s"] == 660 and shown["earliest_reply_after_s"] == 1320
        assert 0 < shown["eta_s"] <= 660


def test_blackout_queues_then_flushes_the_sos_first(app):
    with app.app_context():
        t0 = utcnow()
        link.send("to_earth", "update", {"n": "late"}, 660, link_up=False, priority=1, now=t0)
        link.send("to_earth", "report", {"n": "sos"}, 660, link_up=False, priority=0,
                  now=t0 + timedelta(seconds=1))
        assert link.delivered("to_earth", now=t0 + timedelta(hours=1)) == []
        assert link.flush_queue(660, now=t0 + timedelta(seconds=5)) == 2
        landed = link.delivered("to_earth", now=t0 + timedelta(seconds=30))
        assert [m.payload["n"] for m in sorted(landed, key=lambda m: m.deliver_at)] == ["sos", "late"]
```

- [ ] **Step 2: Run it to see it fail**

Run: `python -m pytest tests/test_link.py -v`
Expected: FAIL with `ImportError: cannot import name 'link' from 'common'`

- [ ] **Step 3: Write the code**

`common/link.py`
```python
"""The link between ship and Earth. A message exists for the other side only
once its deliver_at time has passed."""
from datetime import timedelta

from common.models import LinkMessage, db, iso, utcnow

SPEEDUP = 60  # in the demo, one minute of light time plays as one second


def real_delay_s(delay_s):
    return delay_s / SPEEDUP if delay_s >= 60 else delay_s


def _dispatch(message, delay_s, now, stagger_s=0.0):
    message.sent_at = now
    message.delay_s = delay_s
    message.deliver_at = now + timedelta(seconds=real_delay_s(delay_s) + stagger_s)


def send(direction, kind, payload, delay_s, link_up, priority=5, in_reply_to=None, now=None):
    """Send now if the link is up. Otherwise the message waits in the queue."""
    now = now or utcnow()
    message = LinkMessage(direction=direction, kind=kind, payload=payload, priority=priority,
                          in_reply_to=in_reply_to, created_at=now)
    if link_up:
        _dispatch(message, delay_s, now)
    db.session.add(message)
    db.session.commit()
    return message


def flush_queue(delay_s, now=None):
    """The link is back: send everything that waited, most urgent first."""
    now = now or utcnow()
    queued = (LinkMessage.query.filter(LinkMessage.sent_at.is_(None))
              .order_by(LinkMessage.priority, LinkMessage.created_at).all())
    for position, message in enumerate(queued):
        _dispatch(message, delay_s, now, stagger_s=0.4 * position)
    db.session.commit()
    return len(queued)


def delivered(direction, now=None):
    now = now or utcnow()
    return (LinkMessage.query
            .filter(LinkMessage.direction == direction, LinkMessage.deliver_at.isnot(None),
                    LinkMessage.deliver_at <= now)
            .order_by(LinkMessage.deliver_at.desc()).all())


def to_dict(message, now=None):
    """eta_s is the mission time left until the message lands. It is worked out
    here so the screens do not depend on their own clocks."""
    now = now or utcnow()
    if message.sent_at is None:
        status, eta_s = "queued", None
    elif message.deliver_at <= now:
        status, eta_s = "delivered", 0.0
    else:
        status = "in_flight"
        whole = (message.deliver_at - message.sent_at).total_seconds()
        eta_s = message.delay_s * (message.deliver_at - now).total_seconds() / whole
    return {
        "id": message.id, "direction": message.direction, "kind": message.kind,
        "priority": message.priority, "payload": message.payload, "status": status,
        "in_reply_to": message.in_reply_to, "created_at": iso(message.created_at),
        "sent_at": iso(message.sent_at), "deliver_at": iso(message.deliver_at),
        "delay_s": message.delay_s, "eta_s": eta_s, "arrives_after_s": message.delay_s,
        "earliest_reply_after_s": None if message.delay_s is None else 2 * message.delay_s,
    }
```

- [ ] **Step 4: Run the tests**

Run: `python -m pytest -v`
Expected: 13 passed

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: delayed link with queue and flush"
```

---

### Task 4: Readings in, crew board out, and the dial

**Files:**
- Modify: `base_station/routes.py` (replace the whole file)
- Test: `tests/test_base_api.py`

- [ ] **Step 1: Write the failing test**

`tests/test_base_api.py`
```python
def test_a_reading_reaches_the_crew_board(client):
    posted = client.post("/api/base/readings",
                         json={"crew_id": 1, "heart_rate": 72, "spo2": 98, "skin_temp": 33.5})
    assert posted.status_code == 201
    board = client.get("/api/base/crew").get_json()
    assert board[0]["name"] == "Okafor"
    assert board[0]["latest"]["heart_rate"] == 72
    assert board[0]["level"] == "nominal"
    assert board[1]["latest"] is None


def test_typed_readings_sit_beside_sensed_ones(client):
    client.post("/api/base/readings", json={"crew_id": 1, "heart_rate": 72, "spo2": 98})
    client.post("/api/base/readings", json={"crew_id": 1, "source": "typed", "sleep_hours": 6.5, "mood": 4})
    david = client.get("/api/base/crew").get_json()[0]
    assert david["latest"]["heart_rate"] == 72
    assert david["typed"]["sleep_hours"] == 6.5


def test_readings_come_back_oldest_first_for_the_chart(client):
    for rate in (70, 71, 72):
        client.post("/api/base/readings", json={"crew_id": 1, "heart_rate": rate})
    rows = client.get("/api/base/crew/1/readings?limit=2").get_json()
    assert [r["heart_rate"] for r in rows] == [71, 72]


def test_the_dial_changes_who_decides(client):
    assert client.get("/api/base/state").get_json()["mode"] == "doctor_live"
    mars = client.post("/api/base/dial", json={"stop": "mars"}).get_json()["state"]
    assert mars["mode"] == "crew_first" and mars["who_decides"] == "Crew medical officer"
    sun = client.post("/api/base/dial", json={"stop": "sun"}).get_json()["state"]
    assert sun["mode"] == "ship_alone" and sun["link_up"] is False
    assert client.post("/api/base/dial", json={"stop": "pluto"}).status_code == 400
    assert len(client.get("/api/base/state").get_json()["stops"]) == 4
```

- [ ] **Step 2: Run it to see it fail**

Run: `python -m pytest tests/test_base_api.py -v`
Expected: 4 failed, because `/api/base/readings` and the other new routes return `404`

- [ ] **Step 3: Write the code**

Replace `base_station/routes.py` with:
```python
"""The ship's side: readings in, alerts and reports out."""
from flask import Blueprint, jsonify, request

from common import link, modes
from common.models import VITALS, Crew, MissionState, Reading, db

bp = Blueprint("base", __name__)


def current_state():
    return modes.describe(db.session.get(MissionState, 1).stop)


def ingest(data):
    """Store one reading. Returns the reading and the alerts it raised."""
    reading = Reading(crew_id=data["crew_id"], source=data.get("source", "suit"),
                      signal_ok=data.get("signal_ok", True),
                      **{vital: data.get(vital) for vital in VITALS})
    db.session.add(reading)
    db.session.commit()
    return reading, []


@bp.get("/health")
def health():
    return jsonify(ok=True)


@bp.get("/state")
def state():
    out = current_state()
    out["speedup"] = link.SPEEDUP
    out["stops"] = [modes.describe(stop) for stop in modes.STOPS]
    return jsonify(out)


@bp.post("/dial")
def dial():
    stop = request.get_json().get("stop")
    if stop not in modes.STOPS:
        return jsonify(error="unknown stop"), 400
    db.session.get(MissionState, 1).stop = stop
    db.session.commit()
    new_state = current_state()
    flushed = link.flush_queue(new_state["delay_s"]) if new_state["link_up"] else 0
    return jsonify(state=new_state, flushed=flushed)


@bp.post("/readings")
def post_reading():
    reading, _ = ingest(request.get_json())
    return jsonify(reading=reading.to_dict()), 201


def _latest(crew_id, typed):
    query = Reading.query.filter_by(crew_id=crew_id)
    query = query.filter(Reading.source == "typed") if typed else query.filter(Reading.source != "typed")
    row = query.order_by(Reading.at.desc(), Reading.id.desc()).first()
    return row.to_dict() if row else None


def _level(crew_id):
    return "nominal"


@bp.get("/crew")
def crew_board():
    return jsonify([{"id": c.id, "name": c.name, "role": c.role, "level": _level(c.id),
                     "latest": _latest(c.id, typed=False), "typed": _latest(c.id, typed=True)}
                    for c in Crew.query.order_by(Crew.id)])


@bp.get("/crew/<int:crew_id>/readings")
def crew_readings(crew_id):
    limit = min(int(request.args.get("limit", 120)), 600)
    rows = (Reading.query.filter_by(crew_id=crew_id)
            .order_by(Reading.at.desc(), Reading.id.desc()).limit(limit).all())
    return jsonify([row.to_dict() for row in reversed(rows)])
```

- [ ] **Step 4: Run the tests**

Run: `python -m pytest -v`
Expected: 17 passed

- [ ] **Step 5: See it in a browser, then from a second laptop**

Run: `python app.py`, then open `http://localhost:5000/api/base/state`
Expected: JSON with `"stop": "station"` and four entries under `"stops"`.

Find this laptop's address with `ipconfig` (the IPv4 line) and ask the frontend owner to open `http://<that address>:5000/api/base/health` on his laptop.
Expected: `{"ok": true}`. If it does not load, allow Python in the Windows firewall prompt. If it still does not load, the venue Wi-Fi is keeping laptops apart: put both laptops on one phone hotspot and try again. Do this check now, not at 16:00. Stop the server with Ctrl+C.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat: readings, crew board and the distance dial"
```

**Block 1 goal met here:** a posted heartbeat shows on `/api/base/crew`. Give the frontend owner and Okafor the URL.

---

### Task 5: Rules that do not cry wolf

**Files:**
- Create: `base_station/limits.json`, `base_station/rules.py`
- Modify: `base_station/routes.py` (`ingest` and `_level`)
- Test: `tests/test_rules.py`

- [ ] **Step 1: Write the failing test**

`tests/test_rules.py`
```python
from base_station import rules
from base_station.routes import ingest
from common.models import Alert, db, utcnow

N = rules.LIMITS["sustain_n"]


def feed(crew_id, times, **reading):
    raised = []
    for _ in range(times):
        raised += ingest({"crew_id": crew_id, **reading})[1]
    return raised


def test_bands_follow_the_news2_chart():
    assert [rules.band("spo2", v) for v in (96, 95, 93, 91)] == [0, 1, 2, 3]
    assert [rules.band("heart_rate", v) for v in (40, 50, 90, 110, 130, 131)] == [3, 1, 0, 1, 2, 3]
    assert [rules.band("bp_sys", v) for v in (90, 100, 110, 219, 220)] == [3, 2, 1, 0, 3]


def test_a_few_bad_readings_are_not_an_alarm(app):
    with app.app_context():
        assert feed(1, N - 1, spo2=86, heart_rate=72) == []


def test_sustained_low_oxygen_raises_one_emergency_with_its_reason(app):
    with app.app_context():
        raised = feed(1, N, spo2=86, heart_rate=72)
        assert [a.level for a in raised] == ["emergency"]
        assert raised[0].reason == f"Blood oxygen 86%, out of range for {N} s"
        assert raised[0].nasa_risk == "Risk of Hypoxia"
        assert feed(1, 5, spo2=86, heart_rate=72) == []


def test_a_caution_escalates_instead_of_duplicating(app):
    with app.app_context():
        assert [a.level for a in feed(1, N, spo2=95, heart_rate=72)] == ["caution"]
        assert [a.level for a in feed(1, N, spo2=86, heart_rate=72)] == ["emergency"]
        assert Alert.query.filter_by(crew_id=1, vital="spo2").count() == 1


def test_a_loose_sensor_never_sends_an_sos(app):
    with app.app_context():
        raised = feed(1, 20, spo2=70, heart_rate=20, signal_ok=False)
        assert [a.level for a in raised] == ["advisory"]
        assert raised[0].reason == "Check your sensor: no clean signal"
        assert Alert.query.filter_by(level="emergency").count() == 0


def test_the_sensor_advisory_clears_itself_when_the_signal_returns(app):
    with app.app_context():
        feed(1, 1, spo2=70, signal_ok=False)
        feed(1, 1, spo2=98, heart_rate=72)
        assert Alert.query.filter_by(vital="signal", cleared_at=None).count() == 0


def test_a_typed_reading_alerts_at_once_but_never_above_warning(app):
    with app.app_context():
        raised = ingest({"crew_id": 2, "source": "typed", "bp_sys": 88})[1]
        assert [a.level for a in raised] == ["warning"]
        assert raised[0].reason == "Systolic blood pressure 88 mmHg, out of range"


def test_a_cleared_alert_stays_quiet_unless_it_gets_worse(app):
    with app.app_context():
        caution = feed(1, N, spo2=95, heart_rate=72)[0]
        caution.cleared_at, caution.cleared_by = utcnow(), "Lindqvist"
        db.session.commit()
        assert feed(1, N, spo2=95, heart_rate=72) == []
        assert [a.level for a in feed(1, N, spo2=86, heart_rate=72)] == ["emergency"]
```

- [ ] **Step 2: Run it to see it fail**

Run: `python -m pytest tests/test_rules.py -v`
Expected: FAIL with `ImportError: cannot import name 'rules' from 'base_station'`

- [ ] **Step 3: Write the limits**

`base_station/limits.json`
```json
{
  "source": "Bands follow the NEWS2 chart (Royal College of Physicians, 2017). NEWS2 is a hospital score and is not validated for spaceflight. These are demo tiers.",
  "sustain_n": 5,
  "quiet_s": 60,
  "vitals": {
    "spo2": {
      "label": "Blood oxygen", "unit": "%", "nasa_risk": "Risk of Hypoxia",
      "bands": [[91, 3], [93, 2], [95, 1], [null, 0]]
    },
    "heart_rate": {
      "label": "Heart rate", "unit": " bpm", "nasa_risk": "Risk of Cardiovascular Adaptations",
      "bands": [[40, 3], [50, 1], [90, 0], [110, 1], [130, 2], [null, 3]]
    },
    "bp_sys": {
      "label": "Systolic blood pressure", "unit": " mmHg", "nasa_risk": "Risk of Cardiovascular Adaptations",
      "bands": [[90, 3], [100, 2], [110, 1], [219, 0], [null, 3]]
    }
  }
}
```

Each band is `[upper limit, score]`: a value at or below the upper limit gets that score, and `null` means no upper limit. `sustain_n` is how many suit readings in a row must be out of range (5 seconds at one reading a second). `quiet_s` is how long a vital stays quiet after a person clears its alert, unless it gets worse. Skin temperature has no band on purpose, because the NEWS2 temperature bands are for core temperature.

- [ ] **Step 4: Write the rules**

`base_station/rules.py`
```python
"""Fixed rules that turn readings into alerts. Bands follow the NEWS2 chart."""
import json
import os

from common.models import Alert, Reading, db, utcnow

with open(os.path.join(os.path.dirname(__file__), "limits.json")) as f:
    LIMITS = json.load(f)

LEVELS = {1: "caution", 2: "warning", 3: "emergency"}
RANK = {"nominal": -1, "advisory": 0, "caution": 1, "warning": 2, "emergency": 3}


def band(vital, value):
    for upper, score in LIMITS["vitals"][vital]["bands"]:
        if upper is None or value <= upper:
            return score


def sustained(crew_id, vital, score, n):
    """True when the last n readings of this vital are all at this band or worse,
    each with a clean signal."""
    column = getattr(Reading, vital)
    recent = (Reading.query.filter(Reading.crew_id == crew_id, column.isnot(None))
              .order_by(Reading.at.desc(), Reading.id.desc()).limit(n).all())
    return len(recent) == n and all(
        r.signal_ok and band(vital, getattr(r, vital)) >= score for r in recent)


def _open_alert(crew_id, vital):
    return Alert.query.filter_by(crew_id=crew_id, vital=vital, cleared_at=None).first()


def _quiet(crew_id, vital, level):
    """True when a person cleared this alert in the last quiet_s seconds and it is
    no worse now. This is the alarm pause on a bedside monitor."""
    last = (Alert.query.filter(Alert.crew_id == crew_id, Alert.vital == vital,
                               Alert.cleared_at.isnot(None))
            .order_by(Alert.cleared_at.desc()).first())
    return (last is not None and not last.cleared_by.startswith("auto")
            and (utcnow() - last.cleared_at).total_seconds() < LIMITS["quiet_s"]
            and RANK[level] <= RANK[last.level])


def _raise(crew_id, vital, level, value, reason, nasa_risk=""):
    """Open an alert, or escalate the open one. Returns None when nothing changed."""
    alert = _open_alert(crew_id, vital)
    if alert is None:
        if _quiet(crew_id, vital, level):
            return None
        alert = Alert(crew_id=crew_id, vital=vital, level=level, value=value, reason=reason,
                      nasa_risk=nasa_risk, steps_done=[])
        db.session.add(alert)
    elif RANK[level] > RANK[alert.level]:
        alert.level, alert.value, alert.reason = level, value, reason
    else:
        return None
    db.session.commit()
    return alert


def evaluate(reading):
    """Return the alerts this reading raised or escalated."""
    typed = reading.source == "typed"
    if not typed:
        if not reading.signal_ok:
            alert = _raise(reading.crew_id, "signal", "advisory", None,
                           "Check your sensor: no clean signal")
            return [alert] if alert else []
        stale = _open_alert(reading.crew_id, "signal")
        if stale:
            stale.cleared_at, stale.cleared_by = utcnow(), "auto: signal is back"
            db.session.commit()

    n = 1 if typed else LIMITS["sustain_n"]
    raised = []
    for vital, cfg in LIMITS["vitals"].items():
        value = getattr(reading, vital)
        if value is None:
            continue
        # A typed number can be a typo, so it stops at a warning. SOS needs a sensor.
        score = min(band(vital, value), 2) if typed else band(vital, value)
        while score and not sustained(reading.crew_id, vital, score, n):
            score -= 1
        if not score:
            continue
        held = f", out of range for {n} s" if n > 1 else ", out of range"
        alert = _raise(reading.crew_id, vital, LEVELS[score], value,
                       f"{cfg['label']} {value:g}{cfg['unit']}{held}", cfg["nasa_risk"])
        if alert:
            raised.append(alert)
    return raised
```

- [ ] **Step 5: Wire the rules into the routes**

In `base_station/routes.py`, change the imports to:
```python
from base_station import rules
from common import link, modes
from common.models import VITALS, Alert, Crew, MissionState, Reading, db
```

Replace the last line of `ingest` (`return reading, []`) with:
```python
    return reading, rules.evaluate(reading)
```

Replace `_level` with:
```python
def _level(crew_id):
    levels = [alert.level for alert in Alert.query.filter_by(crew_id=crew_id, cleared_at=None)]
    return max(levels, key=rules.RANK.get, default="nominal")
```

- [ ] **Step 6: Run the tests**

Run: `python -m pytest -v`
Expected: 25 passed

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "feat: alert rules with a sustained check and a sensor check"
```

---

### Task 6: SOS, the Earth report and the spoken line

**Files:**
- Create: `base_station/procedures.json`, `base_station/reports.py`
- Modify: `base_station/routes.py`, `common/models.py` (three new columns on `Alert`)
- Test: `tests/test_base_api.py` (add tests)

- [ ] **Step 1: Write the failing tests**

Add to the end of `tests/test_base_api.py`:
```python
from base_station import rules

N = rules.LIMITS["sustain_n"]


def collapse(client, crew_id=1):
    for _ in range(N):
        response = client.post("/api/base/readings",
                               json={"crew_id": crew_id, "spo2": 86, "heart_rate": 72})
    return response.get_json()["alerts"][0]


def test_an_emergency_sends_a_report_with_three_times_and_a_spoken_line(client):
    client.post("/api/base/dial", json={"stop": "mars"})
    alert = collapse(client)
    assert alert["level"] == "emergency" and alert["nasa_risk"] == "Risk of Hypoxia"
    assert "Earth will hear this in 11 minutes. Earliest reply in 22 minutes." in alert["speak"]
    assert len(alert["steps"]) == 3 and alert["steps_done"] == []
    report = client.get("/api/base/outbox").get_json()[0]
    assert report["kind"] == "report" and report["status"] == "in_flight"
    assert report["earliest_reply_after_s"] == 2 * report["arrives_after_s"]
    assert report["payload"]["sbar"]["situation"].startswith("Okafor: Blood oxygen 86%")
    assert report["payload"]["who_decides"] == "Crew medical officer"


def test_near_earth_the_ship_says_the_doctor_is_live(client):
    assert "Flight surgeon notified, live." in collapse(client)["speak"]


def test_ticking_a_step_tells_earth(client):
    alert = collapse(client)
    done = client.post(f"/api/base/alerts/{alert['id']}/steps", json={"index": 0}).get_json()
    assert done["steps_done"] == [0]
    kinds = sorted(m["kind"] for m in client.get("/api/base/outbox").get_json())
    assert kinds == ["report", "update"]


def test_a_person_clears_the_alert_and_the_tile_goes_back(client):
    alert = collapse(client)
    assert client.get("/api/base/crew").get_json()[0]["level"] == "emergency"
    cleared = client.post(f"/api/base/alerts/{alert['id']}/clear", json={"by": "Lindqvist"}).get_json()
    assert cleared["cleared_by"] == "Lindqvist"
    assert client.get("/api/base/alerts?open=1").get_json() == []
    assert client.get("/api/base/crew").get_json()[0]["level"] == "nominal"


def test_manual_sos_sends_a_report(client):
    alert = client.post("/api/base/sos", json={"crew_id": 2}).get_json()
    assert alert["level"] == "emergency" and alert["auto"] is False
    assert client.get("/api/base/outbox").get_json()[0]["payload"]["crew"] == "Lindqvist"


def test_reset_gives_a_clean_run(client):
    client.post("/api/base/dial", json={"stop": "mars"})
    collapse(client)
    client.post("/api/base/reset")
    assert client.get("/api/base/outbox").get_json() == []
    assert client.get("/api/base/alerts").get_json() == []
    assert client.get("/api/base/state").get_json()["stop"] == "station"


def test_acknowledging_tells_earth_and_shows_on_the_round_trip(client):
    alert = collapse(client)
    assert alert["timeline"]["sent_at"] is not None and alert["timeline"]["acknowledged_at"] is None
    acked = client.post(f"/api/base/alerts/{alert['id']}/ack", json={"by": "Lindqvist"}).get_json()
    assert acked["acknowledged_by"] == "Lindqvist" and acked["timeline"]["acknowledged_at"] is not None
    events = [m["payload"].get("event") for m in client.get("/api/base/outbox").get_json()]
    assert "acknowledged" in events


def test_a_warning_goes_to_earth_only_when_the_crew_sends_it(client):
    posted = client.post("/api/base/readings", json={"crew_id": 2, "source": "typed", "bp_sys": 88})
    alert = posted.get_json()["alerts"][0]
    assert alert["level"] == "warning" and alert["unit"] == "mmHg" and "NEWS2" in alert["source"]
    client.post(f"/api/base/alerts/{alert['id']}/ack", json={"by": "Lindqvist"})
    assert client.get("/api/base/outbox").get_json() == []
    client.post(f"/api/base/alerts/{alert['id']}/send")
    client.post(f"/api/base/alerts/{alert['id']}/send")
    assert [m["kind"] for m in client.get("/api/base/outbox").get_json()] == ["report"]


def test_the_crew_can_message_the_flight_surgeon(client):
    sent = client.post("/api/base/messages", json={"text": "He is awake and talking.", "alert_id": 7})
    assert sent.status_code == 201
    message = client.get("/api/base/outbox").get_json()[0]
    assert message["kind"] == "message" and message["payload"]["alert_id"] == 7
    assert message["payload"]["text"] == "He is awake and talking."
```

- [ ] **Step 2: Run them to see them fail**

Run: `python -m pytest tests/test_base_api.py -v`
Expected: 9 failed, 4 passed (`KeyError: 'alerts'`, and the new routes return `404`)

- [ ] **Step 3: Write the checklist wording and the report builder**

`base_station/procedures.json`
```json
{
  "note": "Demo checklist wording, not medical advice. The documentation owner replaces each list with sourced text. Keep the treatment as the second step of the spo2 list: the scripted story waits for it.",
  "spo2": [
    "Go to the crew member and check that they respond",
    "Fit the oxygen mask from the medical kit",
    "Recheck blood oxygen after two minutes"
  ],
  "heart_rate": [
    "Go to the crew member and check that they respond",
    "Have them stop work and rest",
    "Recheck heart rate after two minutes"
  ],
  "default": [
    "Go to the crew member and check that they respond",
    "Call the crew medical officer",
    "Recheck the reading after two minutes"
  ]
}
```

`base_station/reports.py`
```python
"""The handoff report for Earth and the line the ship speaks."""
import json
import os

from common.models import Reading

with open(os.path.join(os.path.dirname(__file__), "procedures.json")) as f:
    PROCEDURES = json.load(f)

REQUEST = {
    "doctor_live": "Flight surgeon to direct care now.",
    "crew_first": "The crew is following the on-board checklist. "
                  "Earth to review and advise on what comes next.",
    "ship_alone": "Sent after a blackout. Earth to review what the crew did.",
}


def steps_for(vital):
    return PROCEDURES.get(vital, PROCEDURES["default"])


def _show(value, unit):
    return "not measured" if value is None else f"{value:g}{unit}"


def build(alert, crew, state):
    recent = (Reading.query.filter(Reading.crew_id == crew.id, Reading.source != "typed")
              .order_by(Reading.at.desc(), Reading.id.desc()).limit(30).all())
    if recent:
        last = recent[0]
        vitals = (f"heart rate {_show(last.heart_rate, ' bpm')}, "
                  f"blood oxygen {_show(last.spo2, '%')}, "
                  f"skin temperature {_show(last.skin_temp, ' C')}")
    else:
        vitals = "no sensor readings yet"
    if alert.auto:
        assessment = "Raised by a fixed rule on the readings. This is not a diagnosis."
    else:
        assessment = "Raised by a crew member pressing SOS. This is not a diagnosis."
    return {
        "alert_id": alert.id, "crew_id": crew.id, "crew": crew.name, "level": alert.level,
        "vital": alert.vital, "value": alert.value, "reason": alert.reason,
        "nasa_risk": alert.nasa_risk, "mode": state["mode"], "who_decides": state["who_decides"],
        "sbar": {
            "situation": f"{crew.name}: {alert.reason}. Raised at {alert.at:%H:%M:%S} UTC.",
            "background": (f"Mission stop: {state['label']}. "
                           f"One-way delay {state['delay_s']:.0f} s. Latest: {vitals}."),
            "assessment": assessment,
            "request": REQUEST[state["mode"]],
        },
        "steps": steps_for(alert.vital),
        "recent": [reading.to_dict() for reading in reversed(recent)],
    }


def speak(alert, crew, state):
    line = f"{crew.name}. {alert.reason}. SOS sent to the crew."
    if state["mode"] == "doctor_live":
        return line + " Flight surgeon notified, live."
    if state["mode"] == "crew_first":
        minutes = round(state["delay_s"] / 60)
        return line + (f" Earth will hear this in {minutes} minutes. "
                       f"Earliest reply in {2 * minutes} minutes. "
                       "Crew medical officer, start the checklist.")
    return line + " No signal to Earth. Report queued. Crew medical officer, start the checklist."
```

- [ ] **Step 4: Add three columns to the alert table**

In `common/models.py`, add these lines to the `Alert` class, after `cleared_by`:
```python
    acknowledged_at = db.Column(db.DateTime)
    acknowledged_by = db.Column(db.String(40))
    report_id = db.Column(db.Integer)
```

If you have already run the server, delete `instance/lighttime.db` so the table is made again with the new columns.

- [ ] **Step 5: Add the routes**

In `base_station/routes.py`, change the imports to:
```python
from base_station import reports, rules
from common import link, modes
from common.models import (VITALS, Alert, Crew, LinkMessage, MissionState, Reading, db, iso,
                           utcnow)
```

Replace `ingest` with:
```python
def timeline(alert):
    """The round trip of one alert, for the stepper on the alert screen."""
    report = db.session.get(LinkMessage, alert.report_id) if alert.report_id else None
    sent = link.to_dict(report) if report else {}
    reply = next((m for m in reversed(link.delivered("to_ship"))
                  if m.payload.get("alert_id") == alert.id), None)
    return {
        "raised_at": iso(alert.at), "acknowledged_at": iso(alert.acknowledged_at),
        "sent_at": sent.get("sent_at"), "earth_eta_s": sent.get("eta_s"),
        "earth_at": sent.get("deliver_at") if sent.get("status") == "delivered" else None,
        "reply_at": iso(reply.deliver_at) if reply else None,
        "resolved_at": iso(alert.cleared_at),
    }


def alert_dict(alert):
    crew = db.session.get(Crew, alert.crew_id)
    cfg = rules.LIMITS["vitals"].get(alert.vital)
    return {
        "id": alert.id, "crew_id": alert.crew_id, "crew": crew.name, "at": iso(alert.at),
        "level": alert.level, "vital": alert.vital, "value": alert.value,
        "unit": cfg["unit"].strip() if cfg else None, "reason": alert.reason,
        "source": rules.LIMITS["source"] if cfg else None,
        "auto": alert.auto, "nasa_risk": alert.nasa_risk,
        "steps": reports.steps_for(alert.vital), "steps_done": alert.steps_done,
        "acknowledged_by": alert.acknowledged_by,
        "cleared_at": iso(alert.cleared_at), "cleared_by": alert.cleared_by,
        "timeline": timeline(alert),
        "speak": (reports.speak(alert, crew, current_state())
                  if alert.level == "emergency" else None),
    }


def send_report(alert):
    state = current_state()
    crew = db.session.get(Crew, alert.crew_id)
    message = link.send("to_earth", "report", reports.build(alert, crew, state),
                        state["delay_s"], state["link_up"], priority=0)
    alert.report_id = message.id
    db.session.commit()


def tell_earth(alert, event):
    """Send Earth an update about an alert it already has a report for."""
    if alert.report_id is None:
        return
    state = current_state()
    link.send("to_earth", "update", {"alert_id": alert.id, **event},
              state["delay_s"], state["link_up"], priority=1)


def ingest(data):
    """Store one reading, run the rules, and send an SOS report for any new emergency."""
    reading = Reading(crew_id=data["crew_id"], source=data.get("source", "suit"),
                      signal_ok=data.get("signal_ok", True),
                      **{vital: data.get(vital) for vital in VITALS})
    db.session.add(reading)
    db.session.commit()
    raised = rules.evaluate(reading)
    for alert in raised:
        if alert.level == "emergency":
            send_report(alert)
    return reading, raised
```

Replace `post_reading` with:
```python
@bp.post("/readings")
def post_reading():
    reading, raised = ingest(request.get_json())
    return jsonify(reading=reading.to_dict(), alerts=[alert_dict(a) for a in raised]), 201
```

Add at the end of the file:
```python
@bp.get("/alerts")
def alerts():
    query = Alert.query
    if request.args.get("open") == "1":
        query = query.filter_by(cleared_at=None)
    return jsonify([alert_dict(a) for a in query.order_by(Alert.at.desc(), Alert.id.desc())])


@bp.post("/alerts/<int:alert_id>/ack")
def acknowledge(alert_id):
    alert = db.get_or_404(Alert, alert_id)
    if alert.acknowledged_at is None:
        alert.acknowledged_at = utcnow()
        alert.acknowledged_by = (request.get_json(silent=True) or {}).get("by", "crew")
        db.session.commit()
        tell_earth(alert, {"event": "acknowledged", "by": alert.acknowledged_by})
    return jsonify(alert_dict(alert))


@bp.post("/alerts/<int:alert_id>/steps")
def tick_step(alert_id):
    alert = db.get_or_404(Alert, alert_id)
    index = int(request.get_json()["index"])
    if index not in alert.steps_done:
        alert.steps_done = alert.steps_done + [index]
        db.session.commit()
        tell_earth(alert, {"event": "step", "step_index": index,
                           "step": reports.steps_for(alert.vital)[index]})
    return jsonify(alert_dict(alert))


@bp.post("/alerts/<int:alert_id>/send")
def send_alert(alert_id):
    """The crew sends an alert to the flight surgeon. An SOS has already gone."""
    alert = db.get_or_404(Alert, alert_id)
    if alert.report_id is None:
        send_report(alert)
    return jsonify(alert_dict(alert))


@bp.post("/alerts/<int:alert_id>/clear")
def clear_alert(alert_id):
    alert = db.get_or_404(Alert, alert_id)
    alert.cleared_at = utcnow()
    alert.cleared_by = (request.get_json(silent=True) or {}).get("by", "crew")
    db.session.commit()
    tell_earth(alert, {"event": "resolved", "by": alert.cleared_by})
    return jsonify(alert_dict(alert))


@bp.post("/messages")
def crew_message():
    data = request.get_json()
    state = current_state()
    message = link.send("to_earth", "message",
                        {"text": data["text"], "from": data.get("from", "Crew"),
                         "alert_id": data.get("alert_id")},
                        state["delay_s"], state["link_up"], priority=2)
    return jsonify(link.to_dict(message)), 201


@bp.post("/sos")
def manual_sos():
    alert = Alert(crew_id=request.get_json()["crew_id"], vital="manual", level="emergency",
                  reason="Manual SOS pressed", auto=False, steps_done=[])
    db.session.add(alert)
    db.session.commit()
    send_report(alert)
    return jsonify(alert_dict(alert)), 201


@bp.get("/outbox")
def outbox():
    messages = (LinkMessage.query.filter_by(direction="to_earth")
                .order_by(LinkMessage.created_at.desc(), LinkMessage.id.desc()))
    return jsonify([link.to_dict(m) for m in messages])


@bp.get("/inbox")
def inbox():
    return jsonify([link.to_dict(m) for m in link.delivered("to_ship")])


@bp.post("/reset")
def reset():
    for model in (LinkMessage, Alert, Reading):
        model.query.delete()
    db.session.get(MissionState, 1).stop = "station"
    db.session.commit()
    return jsonify(ok=True)
```

- [ ] **Step 6: Run the tests**

Run: `python -m pytest -v`
Expected: 34 passed

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "feat: SOS with reason, Earth report, spoken line, acknowledge, steps and the round trip"
```

**Block 2 goal met here:** an out-of-range reading raises an SOS with its reason, and `/api/base/alerts?open=1` gives every screen the same alert and the line to speak.

---

### Task 7: The Earth console API

**Files:**
- Modify: `command_center/routes.py` (replace the whole file)
- Test: `tests/test_earth_api.py`

- [ ] **Step 1: Write the failing test**

`tests/test_earth_api.py`
```python
from datetime import timedelta

from base_station import rules
from common import link


def emergency_at(client, stop):
    client.post("/api/base/dial", json={"stop": stop})
    for _ in range(rules.LIMITS["sustain_n"]):
        client.post("/api/base/readings", json={"crew_id": 1, "spo2": 86, "heart_rate": 72})


def later(monkeypatch, seconds):
    clock = link.utcnow
    monkeypatch.setattr(link, "utcnow", lambda: clock() + timedelta(seconds=seconds))


def earth_messages(client):
    return client.get("/api/earth/inbox").get_json()["messages"]


def test_earth_sees_nothing_until_the_light_arrives(client, monkeypatch):
    emergency_at(client, "mars")
    assert earth_messages(client) == []
    later(monkeypatch, 12)
    messages = earth_messages(client)
    assert len(messages) == 1
    assert messages[0]["payload"]["sbar"]["situation"].startswith("Okafor")
    assert messages[0]["status"] == "delivered"


def test_near_earth_the_report_lands_at_once(client, monkeypatch):
    emergency_at(client, "station")
    later(monkeypatch, 1)
    assert len(earth_messages(client)) == 1


def test_a_reply_takes_the_same_time_to_come_back(client, monkeypatch):
    emergency_at(client, "mars")
    later(monkeypatch, 12)
    report = earth_messages(client)[0]
    sent = client.post("/api/earth/reply",
                       json={"message_id": report["id"], "text": "Keep the mask on."})
    assert sent.status_code == 201
    assert client.get("/api/base/inbox").get_json() == []
    later(monkeypatch, 12)
    reply = client.get("/api/base/inbox").get_json()[0]
    assert reply["payload"]["text"] == "Keep the mask on." and reply["in_reply_to"] == report["id"]


def test_a_blackout_queues_the_report_and_flushes_when_the_link_returns(client, monkeypatch):
    emergency_at(client, "sun")
    assert client.get("/api/base/outbox").get_json()[0]["status"] == "queued"
    assert client.get("/api/earth/inbox").get_json()["link_up"] is False
    later(monkeypatch, 3600)
    assert earth_messages(client) == []
    assert client.post("/api/base/dial", json={"stop": "mars"}).get_json()["flushed"] == 1
    later(monkeypatch, 12)
    assert len(earth_messages(client)) == 1


def test_the_round_trip_shows_on_the_alert_timeline(client, monkeypatch):
    def timeline():
        return client.get("/api/base/alerts?open=1").get_json()[0]["timeline"]

    emergency_at(client, "mars")
    assert timeline()["earth_at"] is None and timeline()["earth_eta_s"] > 0
    later(monkeypatch, 12)
    report = earth_messages(client)[0]
    client.post("/api/earth/reply", json={"message_id": report["id"], "text": "Keep the mask on."})
    assert timeline()["earth_at"] is not None and timeline()["reply_at"] is None
    later(monkeypatch, 12)
    assert timeline()["reply_at"] is not None
```

- [ ] **Step 2: Run it to see it fail**

Run: `python -m pytest tests/test_earth_api.py -v`
Expected: 5 failed, because `/api/earth/inbox` returns `404`

- [ ] **Step 3: Write the code**

Replace `command_center/routes.py` with:
```python
"""The ground's side. It reads only what the link has delivered."""
from flask import Blueprint, jsonify, request

from common import link, modes
from common.models import LinkMessage, MissionState, db

bp = Blueprint("earth", __name__)


def current_state():
    return modes.describe(db.session.get(MissionState, 1).stop)


@bp.get("/inbox")
def inbox():
    now = link.utcnow()
    state = current_state()
    return jsonify(link_up=state["link_up"], delay_s=state["delay_s"], mode=state["mode"],
                   who_decides=state["who_decides"],
                   messages=[link.to_dict(m, now) for m in link.delivered("to_earth", now)])


@bp.post("/reply")
def reply():
    data = request.get_json()
    state = current_state()
    parent = db.session.get(LinkMessage, data["message_id"]) if data.get("message_id") else None
    message = link.send("to_ship", "reply",
                        {"text": data["text"], "from": data.get("from", "Flight surgeon"),
                         "alert_id": parent.payload.get("alert_id") if parent else None},
                        state["delay_s"], state["link_up"], priority=0,
                        in_reply_to=data.get("message_id"))
    return jsonify(link.to_dict(message)), 201
```

- [ ] **Step 4: Run the tests**

Run: `python -m pytest -v`
Expected: 39 passed

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: Earth inbox and delayed replies"
```

**Block 3 goal met here:** a report leaves, lands after the delay, and the reply comes back the same way.

---

### Task 8: The scripted story

**Files:**
- Create: `base_station/scenario.py`
- Modify: `base_station/routes.py`
- Test: `tests/test_scenario.py`

The story: calm readings for three people, then Okafor's blood oxygen falls. It stays low until the crew ticks the treatment step (the second step of the checklist), then it recovers and the readings carry on, so the tiles stay live for the rest of the demo.

- [ ] **Step 1: Write the failing test**

`tests/test_scenario.py`
```python
from base_station import rules, scenario
from base_station.routes import ingest
from common.models import Alert, LinkMessage


def test_the_story_is_the_same_every_run():
    stage = scenario.SCENARIOS["stage"]
    assert list(scenario.frames(**stage)) == list(scenario.frames(**stage))


def test_every_second_has_one_reading_per_crew_member():
    first = next(scenario.frames(**scenario.SCENARIOS["stage"]))
    assert [r["crew_id"] for r in first] == [1, 2, 3]
    assert all(r["source"] == "scenario" for r in first)


def test_the_full_story_raises_one_sos_and_ends_with_normal_readings(app):
    with app.app_context():
        for second in scenario.frames(**scenario.SCENARIOS["full"]):
            for reading in second:
                ingest(reading)
        alerts = [(a.crew_id, a.vital, a.level) for a in Alert.query.all()]
        assert alerts == [(1, "spo2", "emergency")]
        assert LinkMessage.query.filter_by(kind="report").count() == 1
        assert second[0]["spo2"] >= 96


def test_treated_turns_true_when_the_crew_ticks_the_treatment_step(client, app):
    for _ in range(rules.LIMITS["sustain_n"]):
        response = client.post("/api/base/readings", json={"crew_id": 1, "spo2": 86})
    alert_id = response.get_json()["alerts"][0]["id"]
    with app.app_context():
        assert scenario.treated() is False
    client.post(f"/api/base/alerts/{alert_id}/steps", json={"index": scenario.TREATMENT_STEP})
    with app.app_context():
        assert scenario.treated() is True


def test_treatment_ends_the_collapse():
    story = scenario.frames(**scenario.SCENARIOS["stage"], treated=lambda: True)
    assert min(second[0]["spo2"] for second in story) > scenario.LOW_SPO2


def test_start_rejects_an_unknown_story(client):
    assert client.post("/api/base/scenario/start", json={"name": "nope"}).status_code == 400
```

- [ ] **Step 2: Run it to see it fail**

Run: `python -m pytest tests/test_scenario.py -v`
Expected: FAIL with `ImportError: cannot import name 'scenario' from 'base_station'`

- [ ] **Step 3: Write the code**

`base_station/scenario.py`
```python
"""The scripted day and collapse. No randomness: every run plays the same."""
import math
import threading
import time

from common.models import Alert

# crew_id: resting heart rate, blood oxygen, skin temperature. SIMULATED values.
NORMAL = {1: (72, 98.0, 33.5), 2: (64, 99.0, 33.2), 3: (80, 97.5, 33.8)}
PATIENT = 1
LOW_SPO2, RAISED_RATE = 86.0, 88
TREATMENT_STEP = 1  # the second step of the spo2 checklist in procedures.json

SCENARIOS = {
    "stage": {"calm_s": 4, "drift_s": 0, "collapse_s": 60, "recover_s": 8, "tail_s": 180},
    "full": {"calm_s": 20, "drift_s": 20, "collapse_s": 60, "recover_s": 8, "tail_s": 180},
}

_thread = None
_stop = threading.Event()


def treated():
    """True once the crew has ticked the treatment step on the patient's open oxygen alert."""
    alert = Alert.query.filter_by(crew_id=PATIENT, vital="spo2", cleared_at=None).first()
    return alert is not None and TREATMENT_STEP in alert.steps_done


def _patient_script(calm_s, drift_s, collapse_s, recover_s, tail_s, treated):
    """Yield (blood oxygen, heart rate) for the patient each second. None means normal."""
    rate, oxygen, _ = NORMAL[PATIENT]
    for _ in range(calm_s):
        yield None, None
    for i in range(drift_s):
        yield oxygen - 4.5 * i / drift_s, rate + 14 * i / drift_s
    for _ in range(collapse_s):
        if treated():
            break
        yield LOW_SPO2, RAISED_RATE
    for i in range(1, recover_s + 1):
        share = i / recover_s
        yield LOW_SPO2 + (oxygen - LOW_SPO2) * share, RAISED_RATE + (rate - RAISED_RATE) * share
    for _ in range(tail_s):
        yield None, None


def _reading(crew_id, t, spo2=None, rate=None):
    base_rate, base_oxygen, temp = NORMAL[crew_id]
    wobble = math.sin(t / 3.0 + crew_id)
    return {"crew_id": crew_id, "source": "scenario", "signal_ok": True,
            "heart_rate": round(base_rate + 2 * wobble if rate is None else rate),
            "spo2": round(base_oxygen + 0.4 * wobble if spo2 is None else spo2, 1),
            "skin_temp": round(temp + 0.1 * wobble, 1)}


def frames(calm_s, drift_s, collapse_s, recover_s, tail_s, treated=lambda: False):
    """Yield one list of readings per second: calm, a slow drift, the collapse (until
    the crew treats it or collapse_s runs out), recovery, then calm again."""
    script = _patient_script(calm_s, drift_s, collapse_s, recover_s, tail_s, treated)
    for t, (spo2, rate) in enumerate(script):
        yield [_reading(c, t, spo2, rate) if c == PATIENT else _reading(c, t) for c in NORMAL]


def _run(app, name):
    from base_station.routes import ingest

    with app.app_context():
        for second in frames(**SCENARIOS[name], treated=treated):
            if _stop.is_set():
                return
            for reading in second:
                ingest(reading)
            time.sleep(1)


def stop():
    _stop.set()
    if _thread and _thread.is_alive():
        _thread.join(timeout=3)


def start(app, name="stage"):
    global _thread
    stop()
    _stop.clear()
    _thread = threading.Thread(target=_run, args=(app, name), daemon=True)
    _thread.start()
```

- [ ] **Step 4: Add the routes**

In `base_station/routes.py`, change the first two import lines to:
```python
from flask import Blueprint, current_app, jsonify, request

from base_station import reports, rules, scenario
```

Add at the end of the file:
```python
@bp.post("/scenario/start")
def scenario_start():
    name = (request.get_json(silent=True) or {}).get("name", "stage")
    if name not in scenario.SCENARIOS:
        return jsonify(error="unknown scenario"), 400
    scenario.start(current_app._get_current_object(), name)
    return jsonify(ok=True, name=name)


@bp.post("/scenario/stop")
def scenario_stop():
    scenario.stop()
    return jsonify(ok=True)
```

In `reset`, add this as the first line of the function body:
```python
    scenario.stop()
```

- [ ] **Step 5: Run the tests**

Run: `python -m pytest -v`
Expected: 45 passed

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat: scripted story with treatment, recovery, start and stop"
```

---

### Task 9: Run on Postgres and hand the API to the screens

**Files:**
- Create: `.env` (not committed), `README.md`

- [ ] **Step 1: Point the app at Postgres**

Ask the reviewer for the server's connection details, or create a local database:
```sql
CREATE USER lighttime WITH PASSWORD 'lighttime';
CREATE DATABASE lighttime OWNER lighttime;
```
Copy `.env.example` to `.env` and set `DATABASE_URL` to that database.

- [ ] **Step 2: Start the server**

Run: `python app.py`
Expected: `Running on http://0.0.0.0:5000`. The tables are created on first start.

- [ ] **Step 3: Play the Mars story by hand**

In a second terminal (cmd or Git Bash, not PowerShell):
```bash
curl -X POST localhost:5000/api/base/reset
curl -X POST localhost:5000/api/base/dial -H "Content-Type: application/json" -d "{\"stop\": \"mars\"}"
curl -X POST localhost:5000/api/base/scenario/start -H "Content-Type: application/json" -d "{\"name\": \"stage\"}"
```
About ten seconds after the start call:
```bash
curl "localhost:5000/api/base/alerts?open=1"
curl localhost:5000/api/base/outbox
```
Expected: one `emergency` alert for Okafor with a `speak` line, and one report with `"status": "in_flight"` (`"delivered"` if more than twenty seconds have passed). Note the alert's `id`.

Acknowledge it and tick the treatment step, with that id in place of `1`:
```bash
curl -X POST localhost:5000/api/base/alerts/1/ack -H "Content-Type: application/json" -d "{\"by\": \"the frontend owner\"}"
curl -X POST localhost:5000/api/base/alerts/1/steps -H "Content-Type: application/json" -d "{\"index\": 1}"
```
Wait fifteen seconds, then:
```bash
curl localhost:5000/api/base/crew
curl localhost:5000/api/earth/inbox
curl -X POST localhost:5000/api/base/scenario/stop
```
Expected: Okafor's `spo2` is back above 96, and Earth's `"messages"` hold the report and two updates (acknowledged, step).

- [ ] **Step 4: Extend the README**

The reviewer's README is already in the repo. Replace it with this, which keeps his two rules and uses the folder names as they are on disk.

`README.md`
```markdown
# LightTime Backend

The ship's computer and the link to Earth for LIGHT-TIME (NASA Space Apps 2026).

## Code Organization

- Code intended for base stations belongs in the `base_station` folder. It serves `/api/base`.
- Code intended for the command center belongs in the `command_center` folder. It serves `/api/earth`.
- Code both sides share belongs in the `common` folder: tables, the delayed link, Mars light time, the who-decides rule.

The folder names use underscores because Python cannot import a folder with a hyphen in its name.

## Run

    python -m venv .venv
    .venv\Scripts\activate
    pip install -r requirements.txt
    python app.py

The server listens on port 5000 and does not reload on its own: stop it with Ctrl+C
and start it again after a change. Without a `.env` file it uses a local SQLite file.
For Postgres, copy `.env.example` to `.env` and set `DATABASE_URL`.

## Test

    python -m pytest -v

## API

The API table, the field names and the design decisions are in `docs/specs/2026-11-14-backend-design.md`.

## Data and honesty notes

- Mars light time comes from NASA JPL Horizons. If the call fails, dated values read on 13 November are used and labelled.
- Crew readings in the scripted story are simulated.
- Alert bands follow the NEWS2 chart (Royal College of Physicians 2017), which is not validated for spaceflight.
- Checklist wording in `base_station/procedures.json` is demo text, not medical advice.
- AI use is logged in `AI_USE.md`.
```

- [ ] **Step 5: Commit and push**

```bash
git add -A
git commit -m "docs: README and run notes"
git push
```

Then open a pull request from `Tj-Backend` into `main` for the reviewer to review.

- [ ] **Step 6: Hand over**

Send the frontend owner and Okafor the server address and the API table from the design doc. Ask the frontend owner to check the reading field names against his list.

---

## What this plan leaves for Sunday

In this order, each as its own short plan, started only if the 16:15 full run works: a week of history with personal baselines (feeds the trend chart and the baseline numbers on the frontend owner's screens), live space weather from NASA DONKI for the habitat tiles, CSA's open heart-rate filter as a noise rule, the check-in schedule and reminders, and FHIR export.
