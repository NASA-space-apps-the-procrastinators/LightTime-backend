def post(client, **reading):
    return client.post("/api/base/readings", json={"crew_id": 1, **reading}).get_json()


def test_a_number_no_oximeter_can_give_counts_as_a_sensor_dropout(client):
    for _ in range(6):
        posted = post(client, spo2=0)
    assert posted["reading"]["signal_ok"] is False
    assert [(a["vital"], a["level"]) for a in client.get("/api/base/alerts").get_json()] == [("signal", "advisory")]


def test_a_sensor_just_put_back_on_cannot_raise_an_alarm(client):
    post(client, spo2=0)
    for _ in range(5):                       # the low numbers a finger probe gives while it settles
        assert post(client, spo2=70)["alerts"] == []
    for _ in range(10):
        assert post(client, spo2=98)["alerts"] == []
    assert client.get("/api/base/alerts?open=1").get_json() == []


def test_a_low_reading_that_outlasts_the_settle_time_is_an_emergency(client):
    post(client, spo2=0)
    raised = []
    for _ in range(11):
        raised += post(client, spo2=85)["alerts"]
    assert [a["level"] for a in raised] == ["emergency"]
