LOW = {"crew_id": 1, "spo2": 86}


def sos(client):
    for _ in range(5):
        raised = client.post("/api/base/readings", json=LOW).get_json()["alerts"]
    return raised[0]


def test_a_live_alert_speaks_the_consoles_language(client):
    alert = sos(client)
    assert alert["id"].startswith("A") and alert["crew_id"] == "C1" and alert["crew"] == "Okafor"
    assert (alert["state"], alert["level"], alert["metric"]) == ("SOS", "emergency", "spo2")
    assert alert["stage"] == "sent" and alert["symptoms"] == [] and alert["rule"]     # an SOS sends itself


def test_a_sensor_check_is_a_recheck_and_never_an_alert(client):
    raised = client.post("/api/base/readings",
                         json={"crew_id": 1, "spo2": 98, "signal_ok": False}).get_json()["alerts"]
    assert (raised[0]["state"], raised[0]["metric"], raised[0]["stage"]) == ("RECHECK", "signal", "raised")


def test_one_alert_can_be_fetched_by_its_code_or_its_number(client):
    alert = sos(client)
    assert client.get(f"/api/base/alerts/{alert['id']}").get_json()["id"] == alert["id"]
    assert client.get(f"/api/base/alerts/{alert['id'][1:]}").get_json()["id"] == alert["id"]
    missing = client.get("/api/base/alerts/A999")
    assert missing.status_code == 404 and missing.get_json() == {"error": "not found"}


def test_symptoms_given_at_acknowledge_stay_on_the_alert(client):
    alert = sos(client)
    acked = client.post(f"/api/base/alerts/{alert['id']}/ack",
                        json={"by": "Okafor", "symptoms": ["headache"]}).get_json()
    assert acked["symptoms"] == ["headache"] and acked["timeline"]["acknowledged_at"] is not None
