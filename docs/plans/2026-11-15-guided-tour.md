# Guided Tour Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Also load: test-driven-development, verification-before-completion, karpathy-guidelines.

**Goal:** One press starts a 30 second tour for the pitch: a short story, and the ship tells the console which of four speech bubbles to show. Nobody has to press anything else.

**Architecture:** A fourth story ("tour") with a short calm, and one new module, `base_station/tour.py`, that reads what the ship has done and returns one bubble on `GET /api/base/tour`. The console polls it and draws the bubble. Spec: `docs/specs/2026-11-15-guided-tour-design.md`.

**Tech Stack:** Python, Flask, pytest. Console: React, TypeScript.

**Start state:** `Tj-Backend` at `890fb21` (the final fix merged with `main`, which brought the Earth feed and its tests), 234 tests. Run `python -m pytest -q` first; if it does not say `234 passed`, stop and tell the backend owner. Tasks 1 and 2 were run on a copy of `890fb21`: 238 tests pass, and the tour was timed against a running ship: bubbles at 0, 14.5, 20.6 and 25.6 seconds. Task 4 (console) was not run.

---

### Task 1: The failing tests

**Files:** Create `tests/test_tour.py`

- [ ] **Step 1: Write the tests**

```python
"""The guided tour: a short story, and one bubble of text for where the story is now."""
from datetime import timedelta

from base_station import scenario
from base_station.routes import ingest
from common import models
from common.models import Alert, utcnow

KEYS = {"running", "step", "of", "id", "title", "text", "anchor", "simulated"}


class Story:
    """The tour story, fed to the ship a second at a time, as the story's own thread would."""

    def __init__(self, app, monkeypatch, name="tour"):
        self.app, self.t = app, 0
        with app.app_context():
            monkeypatch.setattr(scenario, "_name", name)
            monkeypatch.setattr(scenario, "_since", utcnow())
        self.frames = scenario.frames(**scenario.SCENARIOS[name], treated=scenario.treated)

    def play_to(self, second):
        with self.app.app_context():
            while self.t < second:
                for reading in next(self.frames):
                    ingest(reading)
                self.t += 1


def tour(client):
    return client.get("/api/base/tour").get_json()


def test_the_tour_story_warns_by_16_seconds_and_calls_sos_by_22(app):
    cfg, seen = scenario.SCENARIOS["tour"], {}
    with app.app_context():
        for t, second in enumerate(scenario.frames(**cfg)):
            for reading in second:
                ingest(reading)
            for alert in Alert.query.filter_by(crew_id=1, vital="spo2"):
                seen.setdefault(alert.level, t)
            if "emergency" in seen:
                break
    assert seen["caution"] <= 16 and seen["caution"] + 5 <= seen["emergency"] <= 22


def test_with_no_story_there_is_no_bubble(client):
    out = tour(client)
    assert set(out) == KEYS
    assert (out["running"], out["step"], out["id"], out["text"]) == (False, 0, None, None)


def test_the_bubbles_follow_what_the_ship_actually_did(client, app, monkeypatch):
    client.post("/api/base/dial", json={"stop": "mars"})
    story = Story(app, monkeypatch)

    story.play_to(5)
    out = tour(client)
    assert (out["step"], out["of"], out["id"], out["anchor"]) == (1, 4, "calm", "crew:C1")
    assert "One reading a second" in out["text"] and "11 minutes" in out["text"]

    story.play_to(16)
    out = tour(client)
    assert (out["step"], out["id"], out["anchor"]) == (2, "time_left", "alerts")
    assert "LIGHTTIME gives it about" in out["text"] and "22 minutes" in out["text"]

    story.play_to(23)
    out = tour(client)
    assert (out["step"], out["id"]) == (3, "sos")
    assert "11 minutes" in out["text"] and "Rebecca" in out["text"]

    models.set_clock(utcnow() + timedelta(minutes=30))    # the report has reached Earth
    out = tour(client)
    assert (out["step"], out["id"], out["anchor"]) == (4, "earth_hears", "earth")
    assert "only now" in out["text"]
    assert all(len(text.split()) <= 26 for text in (out["text"],))    # short enough to read in five seconds


def test_the_demo_call_can_start_the_tour(morning, monkeypatch):
    started = []
    monkeypatch.setattr(scenario, "start", lambda app, name="full", real=False: started.append(name))
    assert morning.post("/api/base/demo/start", json={"name": "tour"}).get_json()["name"] == "tour"
    assert morning.post("/api/base/demo/start").get_json()["name"] == "full"
    assert started == ["tour", "full"]
    assert morning.post("/api/base/demo/start", json={"name": "real"}).status_code == 400
```

- [ ] **Step 2: Run them**

Run: `python -m pytest -q tests/test_tour.py`
Expected: `4 failed` (no "tour" story, no `/api/base/tour` route).

---

### Task 2: The tour story and the bubble

**Files:** Modify `base_station/scenario.py`, `base_station/routes.py`, `app.py`. Create `base_station/tour.py`.

- [ ] **Step 1: `base_station/scenario.py`, the story**

In `SCENARIOS`, above the `"full"` line, add:

```python
    # the guided tour: the same story with no calm and a quicker drift, so it fits in 30 seconds
    "tour": {"calm_s": 0, "drift_s": 16, "collapse_s": 60, "recover_s": 8, "tail_s": 180},
```

- [ ] **Step 2: `base_station/scenario.py`, remember which story is playing**

Under `_since = None       # when the running story started` add:

```python
_name = None        # which story was started last; None once it is stopped
```

Replace `stop()` with:

```python
def stop():
    global _name
    with _lock:
        _halt()
        _name = None


def playing():
    """The name of the story started last, or None once it has been stopped or the demo reset."""
    return _name
```

In `start()`, change `global _thread, _stop, _since` to `global _thread, _stop, _since, _name`, and change `_since = utcnow()` to:

```python
        _since, _name = utcnow(), name
```

- [ ] **Step 3: Create `base_station/tour.py`**

```python
"""The guided tour: one bubble of text for where the story is now. Four bubbles in 30 seconds.

The ship works the step out from what it has actually done (the alert, the report landing on Earth),
never from a timer, so a bubble cannot get ahead of the screen. The console draws the bubble
beside the part of the screen `anchor` names. The words are fixed templates; the numbers are the ship's.
"""
from flask import jsonify

from base_station import access, reports, scenario
from base_station.routes import alert_dict, bp, current_state
from common.models import Alert, Crew, LinkMessage, db, utcnow

STEPS = ("calm", "time_left", "sos", "earth_hears")
TITLE = {"calm": "The suits are talking", "time_left": "Time left", "sos": "SOS", "earth_hears": "Earth hears"}
ANCHOR = {"calm": "crew:C1", "time_left": "alerts", "sos": "alerts", "earth_hears": "earth"}


def _medical_officer():
    code = sorted(access.medical_officers())[0]
    return Crew.query.filter_by(code=code).first().name


def _alert():
    """The patient's blood-oxygen alert from the running story, or None."""
    query = Alert.query.filter_by(crew_id=scenario.PATIENT, vital="spo2", auto=True)
    since = scenario.since("scenario")
    if since is not None:
        query = query.filter(Alert.at >= since)
    return query.order_by(Alert.id.desc()).first()


def _earth_has_heard(alert):
    """True once anything the ship sent about this alert has landed on Earth."""
    now = utcnow()
    return any(m.payload.get("alert_id") == alert.id and m.deliver_at is not None and m.deliver_at <= now
               for m in LinkMessage.query.filter_by(direction="to_earth"))


def _where(alert):
    if alert is None:
        return "calm"
    if _earth_has_heard(alert):
        return "earth_hears"
    return "sos" if alert.level == "emergency" else "time_left"


def _text(step, shown, state):
    patient = db.session.get(Crew, scenario.PATIENT).name
    one_way = reports.span(state["delay_s"]) if state["link_up"] else None
    answer = reports.span(state["round_trip_s"]) if state["link_up"] else None
    if step == "calm":
        far = f"Earth is {one_way} away." if one_way else "There is no link to Earth."
        return f"One reading a second from every suit. {far} Watch {patient}'s blood oxygen."
    if step == "time_left":
        look = shown["lookahead"]
        left = f"about {reports.span(look['eta_s'])}" if look else "very little time"
        reply = f"Earth's answer takes {answer}." if answer else "Earth cannot answer."
        return f"Still in range, but falling. LIGHTTIME gives it {left}. {reply}"
    if step == "sos":
        hears = f"Earth will not hear this for {one_way}" if one_way else "Earth cannot hear this"
        return f"SOS. {hears}, so {_medical_officer()}, the crew medical officer, decides."
    return (f"Earth is only now hearing the first warning. Its answer is {one_way} more away. "
            f"The crew had to act alone.")


def bubble():
    if scenario.playing() is None:
        return {"running": False, "step": 0, "of": len(STEPS), "id": None, "title": None, "text": None,
                "anchor": None, "simulated": True}
    alert = _alert()
    step = _where(alert)
    return {"running": True, "step": STEPS.index(step) + 1, "of": len(STEPS), "id": step, "title": TITLE[step],
            "text": _text(step, alert_dict(alert) if alert else None, current_state()), "anchor": ANCHOR[step],
            "simulated": True}        # the story's readings are scripted


@bp.get("/tour")
def tour():
    return jsonify(bubble())
```

- [ ] **Step 4: `app.py`, load the new routes**

Change `from base_station import console, log  # noqa: F401` to `from base_station import console, log, tour  # noqa: F401` (keep the rest of the line).

- [ ] **Step 5: `base_station/routes.py`, let the demo call start the tour**

Replace the body of `demo_start` with:

```python
    """One button for the stage: the demo starts again, the dial goes to Mars, the story plays.
    {"name": "tour"} plays the short story the guided tour uses; the default is "full"."""
    name = body().get("name", "full")
    if name not in ("full", "tour"):
        return bad("name is full or tour", "name")
    reset()
    db.session.get(MissionState, 1).stop = "mars"
    db.session.commit()
    scenario.start(current_app._get_current_object(), name)
    return jsonify(ok=True, name=name, state=current_state())
```

- [ ] **Step 6: Run everything**

Run: `python -m pytest -q`
Expected: `238 passed`

- [ ] **Step 7: The API table and the types, in the same commit**

In `docs/specs/2026-11-14-backend-design.md`: change the `demo/start` row to say it takes an optional `{name}` of "full" (default) or "tour"; add "tour" to the story names in the `scenario/start` row; add:

```markdown
| `GET /api/base/tour` | console | new: the guided tour's bubble for where the story is now. `running`, `step` (0 with no story, else 1 to 4), `of` (4), `id` (`calm`, `time_left`, `sos`, `earth_hears`), `title`, `text`, `anchor` (`crew:C1`, `alerts` or `earth`: the part of the screen to point at), `simulated`. The step comes from what the ship has done, never from a timer |
```

In `docs/frontend/lighttime-api.ts`: add `"tour"` to `Story`; change the existing `startDemo` line to

```ts
  startDemo: (name: "full" | "tour" = "full") => call<{ ok: boolean; name: string; state: StopState }>("/api/base/demo/start", { name }),
```

and add

```ts
export interface TourBubble {
  running: boolean; step: number; of: number;
  id: "calm" | "time_left" | "sos" | "earth_hears" | null;
  title: string | null; text: string | null; anchor: string | null; simulated: boolean;
}
```

In `CLAUDE.md`, add to the count line: `With the guided tour it is at 238`. Add one line to `AI_USE.md` in its own format.

- [ ] **Step 8: Commit**

```bash
git add base_station app.py tests/test_tour.py docs/specs/2026-11-14-backend-design.md docs/frontend/lighttime-api.ts CLAUDE.md AI_USE.md
git commit -m "feat: a guided tour: a short story and GET /api/base/tour, one bubble for where the story is"
```

---

### Task 3: Play it, then ship it

- [ ] **Step 1: Start a clean ship** (`python app.py`, one process), then:

```powershell
curl.exe -s -X POST http://localhost:5000/api/base/demo/start -H "content-type: application/json" -d '{\"name\":\"tour\"}'
```

- [ ] **Step 2: Read the bubble at about 5, 17, 22 and 28 seconds**

Run each time: `curl.exe -s http://localhost:5000/api/base/tour`
Expected, in order:
1. "One reading a second from every suit. Earth is 11 minutes away. Watch TJ's blood oxygen."
2. "Still in range, but falling. LIGHTTIME gives it about 13 seconds. Earth's answer takes 22 minutes." (the seconds vary by one or two)
3. "SOS. Earth will not hear this for 11 minutes, so Rebecca, the crew medical officer, decides."
4. "Earth is only now hearing the first warning. Its answer is 11 minutes more away. The crew had to act alone."

- [ ] **Step 3: Time it once with a stopwatch.** Bubble 4 must be up by 27 seconds. If it is later than 30, stop and tell the backend owner; do not shorten the rules.

- [ ] **Step 4: Push, open the pull request into `main`, and after the merge deploys:**

```bash
curl -s https://lighttime.health/api/base/tour
```

Expected: `"running": false, "step": 0` (and not a 404).

---

### Task 4: The console (for the frontend owner; not run)

- [ ] **Step 1: Mark the three anchors.** Add `data-tour="crew:C1"` to the commander's crew card (in the card, `data-tour={`crew:${crew.id}`}`), `data-tour="alerts"` to the alerts panel, `data-tour="earth"` to the "Earth" link in the header.

- [ ] **Step 2: Create `src/components/base-station/tour-bubble.tsx`**

```tsx
"use client";

import { useEffect, useState } from "react";
import { API_URL, LIVE } from "@/lib/ship-api";

type Bubble = {
  running: boolean; step: number; of: number; id: string | null;
  title: string | null; text: string | null; anchor: string | null;
};

/** The guided tour: asks the ship once a second which bubble to show, and draws it beside its anchor. */
export function TourBubble() {
  const [bubble, setBubble] = useState<Bubble | null>(null);
  const [box, setBox] = useState<DOMRect | null>(null);

  useEffect(() => {
    if (!LIVE) return;
    const ask = () =>
      fetch(`${API_URL}/api/base/tour`)
        .then((r) => (r.ok ? r.json() : null))
        .then(setBubble, () => setBubble(null));
    ask();
    const timer = setInterval(ask, 1000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    const el = bubble?.anchor
      ? document.querySelector(`[data-tour="${bubble.anchor}"]`)
      : null;
    if (el) el.scrollIntoView({ block: "nearest", behavior: "smooth" });
    setBox(el ? el.getBoundingClientRect() : null);
  }, [bubble?.id, bubble?.anchor]);

  if (!bubble?.running || !bubble.text) return null;
  const top = box ? Math.min(box.top + 16, window.innerHeight - 260) : 96;
  const left = box ? Math.max(16, Math.min(box.left - 344, window.innerWidth - 344)) : 16;

  return (
    <div
      role="status"
      aria-live="polite"
      className="fixed z-50 w-80 rounded-2xl border-2 border-foreground bg-background p-4 shadow-[6px_6px_0_0_currentColor]"
      style={{ top, left }}
    >
      <p className="text-[11px] uppercase tracking-wide text-muted-foreground">
        Tour {bubble.step} of {bubble.of} · simulated story
      </p>
      <p className="mt-1 text-base font-semibold">{bubble.title}</p>
      <p className="mt-1 text-sm leading-snug">{bubble.text}</p>
    </div>
  );
}
```

- [ ] **Step 3: Mount it and add the button.** Render `<TourBubble />` once in the base station layout. In `app-header.tsx`, beside "Start story":

```tsx
<Button
  size="sm"
  className="min-h-11 shrink-0 md:min-h-9"
  title="A 30 second guided tour: a short emergency with a bubble explaining each step"
  onClick={() =>
    shipApi.post("/api/base/demo/start", { name: "tour" }).then(refresh, refresh)
  }
>
  Take the tour
</Button>
```

- [ ] **Step 4: Check by eye.** Press "Take the tour": a bubble at once beside TJ's card; it moves to the alerts panel at about 14 seconds; SOS text at about 20; at about 26 it points at the Earth link. The bubble stays until the story is stopped or the demo is reset. If the bubble covers the thing it points at on a phone, pin it to the bottom of the screen at widths under 768 px.

---

## Presenter's cue card (30 seconds)

Press "Take the tour" and talk over the bubbles.

| Second | Bubble | Say |
|---|---|---|
| 0 | The suits are talking | "We are at Mars. Every suit reports once a second. Earth is 11 minutes away." |
| 14 | Time left | "Nothing is out of range yet, but the ship sees the trend and says how long is left: seconds. Earth's answer takes 22 minutes." |
| 20 | SOS | "Now it is an emergency. Earth has not even heard. So the crew medical officer decides." |
| 26 | Earth hears | "And only now does the first warning reach Earth. That gap is LIGHT-TIME." |
