"""The exact fields each screen gets. docs/frontend/lighttime-api.ts mirrors these sets."""
STOP = {"stop", "label", "link_up", "delay_s", "mode", "who_decides", "light_time_source",
        "path_km", "round_trip_s", "plays_as_s"}
READING = {"id", "crew_id", "at", "source", "signal_ok", "context", "heart_rate", "spo2", "skin_temp",
           "bp_sys", "bp_dia", "glucose", "sleep_hours", "mood"}
TIMELINE = {"raised_at", "acknowledged_at", "sent_at", "earth_eta_s", "earth_at", "earliest_reply_at",
            "reply_at", "resolved_at"}
ALERT = {"id", "crew_id", "crew", "at", "level", "vital", "value", "unit", "reason", "source", "auto",
         "nasa_risk", "steps", "steps_done", "acknowledged_by", "cleared_at", "cleared_by", "cleared_note",
         "why", "timeline", "lookahead", "speak", "state", "stage", "metric", "rule", "symptoms"}
MESSAGE = {"id", "direction", "kind", "priority", "payload", "status", "in_reply_to", "created_at",
           "sent_at", "deliver_at", "delay_s", "eta_s", "arrives_after_s", "earliest_reply_after_s"}


def test_every_screen_gets_the_fields_the_typed_client_expects(client):
    state = client.get("/api/base/state").get_json()
    assert set(state) == STOP | {"speedup", "stops", "mission_day", "platform"} and set(state["stops"][0]) == STOP
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
