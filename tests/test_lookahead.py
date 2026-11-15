from base_station import lookahead


def fall(client, start=98.0, step=0.1, n=30, crew_id=1):
    """Post a steady fall, one reading a second. Returns every alert it raised."""
    raised = []
    for i in range(n):
        posted = client.post("/api/base/readings", json={"crew_id": crew_id, "spo2": round(start - step * i, 1)})
        raised += posted.get_json()["alerts"]
    return raised


def open_alert(client):
    return client.get("/api/base/alerts?open=1").get_json()[0]


def test_one_wild_reading_does_not_move_the_trend():
    steady = [98 - 0.1 * i for i in range(30)]
    assert lookahead.falling(steady[:15] + [70] + steady[16:], 91)["per_min"] == -6.0


def test_whole_number_readings_still_show_a_fall():
    # Real oximeters report whole numbers, so many pairs of readings are equal.
    look = lookahead.falling([98] * 20 + [97] * 20 + [96] * 20, 91)
    assert look["per_min"] < 0 and look["now"] == 96


def test_steady_or_jumpy_readings_are_not_a_trend():
    assert lookahead.falling([97, 98, 97, 99] * 15, 91) is None
    assert lookahead.falling([98] * 40 + [97] * 20, 91) is None        # one point down is not enough


def test_a_steady_fall_raises_a_caution_while_the_reading_is_still_normal(client):
    raised = fall(client)
    assert [a["level"] for a in raised] == ["caution"] and raised[0]["reason"].endswith("and falling")
    look = open_alert(client)["lookahead"]
    assert look["per_min"] == -6.0 and 40 <= look["eta_s"] <= 60 and look["red_line"] == 91
    assert look["red_line_at"] > look["at"]


def test_at_mars_the_ship_says_earth_cannot_answer_in_time(client):
    client.post("/api/base/dial", json={"stop": "mars"})
    fall(client)
    alert = open_alert(client)
    assert alert["lookahead"]["earth_in_time"] is False and alert["lookahead"]["reply_s"] > 1200
    assert "That is too late. Crew medical officer, check on TJ now." in alert["speak"]


def test_near_earth_the_ship_says_the_surgeon_can_answer(client):
    fall(client)
    alert = open_alert(client)
    assert alert["lookahead"]["earth_in_time"] is True
    assert "Earth can answer in under two seconds. Report sent." in alert["speak"]


def test_behind_the_sun_the_ship_says_there_is_no_signal(client):
    client.post("/api/base/dial", json={"stop": "sun"})
    fall(client)
    assert "No signal to Earth." in open_alert(client)["speak"]


def test_the_falling_trend_goes_to_earth_early_with_the_answers_attached(client):
    fall(client)
    sent = client.get("/api/base/outbox").get_json()
    assert [m["kind"] for m in sent] == ["report"] and sent[0]["payload"]["level"] == "caution"
    questions = [item["q"] for item in sent[0]["payload"]["asked_ahead"]]
    assert "How long until it is critical?" in questions and "What has the crew done so far?" in questions


def test_a_collapse_after_the_warning_updates_earth_instead_of_sending_a_second_report(client):
    fall(client)
    for _ in range(5):
        client.post("/api/base/readings", json={"crew_id": 1, "spo2": 86})
    alerts = client.get("/api/base/alerts").get_json()
    assert [a["level"] for a in alerts] == ["emergency"] and "SOS sent" in alerts[0]["speak"]
    assert alerts[0]["lookahead"]["eta_s"] > 0                    # the early prediction stays on the record
    sent = client.get("/api/base/outbox").get_json()
    assert sorted(m["kind"] for m in sent) == ["report", "update"]
    assert [m["payload"]["event"] for m in sent if m["kind"] == "update"] == ["escalated"]


def test_an_alert_the_bands_raised_first_still_gets_its_early_report(client):
    # Whole numbers falling a point every 12 seconds, starting just above the first band.
    values = [96] * 30 + [95] * 12 + [94] * 12 + [93] * 12 + [92] * 6
    raised = []
    for value in values:
        raised += client.post("/api/base/readings", json={"crew_id": 1, "spo2": value}).get_json()["alerts"]
    assert raised[0]["reason"] == "Blood oxygen 95%, out of range for 5 s"
    sent = client.get("/api/base/outbox").get_json()
    report = [m for m in sent if m["kind"] == "report"]
    assert len(report) == 1 and report[0]["payload"]["lookahead"]["eta_s"] > 0
    assert report[0]["payload"]["level"] in ("caution", "warning")
