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
    assert client.get("/api/base/state").get_json()["stop"] == "mars"     # the dial stays put


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
