from base_station import rules, scenario
from base_station.routes import ingest
from common.models import Alert, LinkMessage, utcnow


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


def test_a_new_storys_trend_does_not_reach_back_into_the_last_story(app, monkeypatch):
    """Without a restart, the second story's calm start must not be read as a fall:
    the last 60 readings still hold the first story's drop to 86 %."""
    with app.app_context():
        for second in list(scenario.frames(**scenario.SCENARIOS["full"]))[:60]:    # calm, drift, the drop
            for reading in second:
                ingest(reading)
        assert scenario.close_last_run() == 1
        monkeypatch.setattr(scenario, "_since", utcnow())
        raised = []
        for second in list(scenario.frames(**scenario.SCENARIOS["full"]))[:10]:    # the new story's calm
            for reading in second:
                raised += ingest(reading)[1]
        assert [(a.vital, a.level) for a in raised] == []
