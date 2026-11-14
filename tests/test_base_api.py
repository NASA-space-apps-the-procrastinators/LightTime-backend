def test_a_reading_reaches_the_crew_board(client):
    posted = client.post("/api/base/readings",
                         json={"crew_id": 1, "heart_rate": 72, "spo2": 98, "skin_temp": 33.5})
    assert posted.status_code == 201
    board = client.get("/api/base/crew").get_json()
    assert board[0]["name"] == "David"
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
