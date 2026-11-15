"""Wrong input, a second press, a second sender. Found by the code review on 14 November."""
import threading
import time

from base_station import routes, scenario
from common.models import utcnow

LOW = {"crew_id": 1, "spo2": 86}


def sos(client):
    for _ in range(5):
        raised = client.post("/api/base/readings", json=LOW).get_json()["alerts"]
    return raised[0]


def test_an_unknown_crew_member_is_refused_and_breaks_nothing(client):
    assert client.post("/api/base/sos", json={"crew_id": 99}).status_code == 400
    assert client.post("/api/base/readings", json={"crew_id": "Okafor", "spo2": 98}).status_code == 400
    assert client.post("/api/base/readings", json={}).status_code == 400
    assert client.get("/api/base/alerts").get_json() == []


def test_an_empty_box_on_the_check_in_form_is_not_an_error(client):
    posted = client.post("/api/base/readings", json={"crew_id": 1, "source": "typed", "bp_sys": "", "mood": "4"})
    assert posted.status_code == 201
    assert posted.get_json()["reading"]["bp_sys"] is None and posted.get_json()["reading"]["mood"] == 4
    assert client.post("/api/base/readings", json={"crew_id": 1, "spo2": "high"}).status_code == 400


def test_a_step_that_is_not_on_the_checklist_is_refused(client):
    alert = sos(client)
    assert client.post(f"/api/base/alerts/{alert['id']}/steps", json={"index": 7}).status_code == 400
    assert client.post(f"/api/base/alerts/{alert['id']}/steps", json={}).status_code == 400
    assert client.get("/api/base/alerts").get_json()[0]["steps_done"] == []


def test_resolving_twice_tells_earth_once(client):
    alert = sos(client)
    first = client.post(f"/api/base/alerts/{alert['id']}/clear", json={"by": None}).get_json()
    second = client.post(f"/api/base/alerts/{alert['id']}/clear", json={"by": "Linda Rodenburg"}).get_json()
    assert first["cleared_by"] == second["cleared_by"] == "crew" and first["cleared_at"] == second["cleared_at"]
    events = [m["payload"].get("event") for m in client.get("/api/base/outbox").get_json()]
    assert events.count("resolved") == 1


def test_pressing_sos_twice_makes_one_alert(client):
    assert client.post("/api/base/sos", json={"crew_id": 2}).status_code == 201
    assert client.post("/api/base/sos", json={"crew_id": 2}).status_code == 200
    assert len(client.get("/api/base/alerts").get_json()) == 1
    assert [m["kind"] for m in client.get("/api/base/outbox").get_json()] == ["report"]


def test_a_message_or_reply_with_no_text_is_refused(client):
    assert client.post("/api/base/messages", json={}).status_code == 400
    assert client.post("/api/earth/reply", json={"text": ""}).status_code == 400


def test_a_second_sender_for_the_same_person_does_not_hide_an_emergency(client):
    """The story plays for Okafor while a real sensor on them reports normal numbers."""
    raised = []
    for _ in range(5):
        raised += client.post("/api/base/readings", json={**LOW, "source": "scenario"}).get_json()["alerts"]
        client.post("/api/base/readings", json={"crew_id": 1, "spo2": 98})
    assert [a["level"] for a in raised] == ["emergency"]


def test_resolving_the_alert_also_ends_the_collapse(client, app):
    alert = sos(client)
    with app.app_context():
        assert scenario.treated() is False
        client.post(f"/api/base/alerts/{alert['id']}/clear")
        assert scenario.treated() is True


def test_an_alert_from_an_earlier_run_does_not_count_as_treatment(client, app, monkeypatch):
    alert = sos(client)
    client.post(f"/api/base/alerts/{alert['id']}/steps", json={"index": scenario.TREATMENT_STEP})
    with app.app_context():
        assert scenario.treated() is True
        monkeypatch.setattr(scenario, "_since", utcnow())
        assert scenario.treated() is False


def stories():
    return [t for t in threading.enumerate() if t.name == "story" and t.is_alive()]


def test_two_starts_at_once_still_play_one_story(app):
    callers = [threading.Thread(target=scenario.start, args=(app,)) for _ in range(2)]
    for caller in callers:
        caller.start()
    for caller in callers:
        caller.join()
    try:
        assert len(stories()) == 1
    finally:
        scenario.stop()
    assert stories() == []


def test_one_bad_reading_does_not_end_the_story(app, monkeypatch):
    def broken(reading):
        raise RuntimeError("bad reading")

    monkeypatch.setattr(routes, "ingest", broken)
    scenario.start(app)
    try:
        time.sleep(0.3)
        assert len(stories()) == 1
    finally:
        scenario.stop()
