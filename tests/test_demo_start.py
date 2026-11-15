"""One button for the stage: the demo starts again, the dial goes to Mars, the full story plays."""
from base_station import scenario


def test_one_call_resets_dials_mars_and_starts_the_full_story(morning, monkeypatch):
    started = []
    monkeypatch.setattr(scenario, "start", lambda app, name="full", real=False: started.append(name))
    morning.post("/api/base/messages", json={"text": "Left over from the last run.", "from": "TJ"})
    out = morning.post("/api/base/demo/start")
    assert out.status_code == 200 and out.get_json()["name"] == "full"
    assert started == ["full"]
    state = morning.get("/api/base/state").get_json()
    assert state["stop"] == "mars" and state["mode"] == out.get_json()["state"]["mode"]
    assert state["now"].startswith("2026-11-14T06:30")
    assert not any(m["payload"].get("text") == "Left over from the last run."
                   for m in morning.get("/api/base/outbox").get_json())
