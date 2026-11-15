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
