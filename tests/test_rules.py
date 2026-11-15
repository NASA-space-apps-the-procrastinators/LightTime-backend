from base_station import rules
from base_station.routes import ingest
from common.models import Alert, db, utcnow

N = rules.LIMITS["sustain_n"]


def feed(crew_id, times, **reading):
    raised = []
    for _ in range(times):
        raised += ingest({"crew_id": crew_id, **reading})[1]
    return raised


def test_bands_follow_the_news2_chart():
    assert [rules.band("spo2", v) for v in (96, 95, 93, 91)] == [0, 1, 2, 3]
    assert [rules.band("heart_rate", v) for v in (40, 50, 90, 110, 130, 131)] == [3, 1, 0, 1, 2, 3]
    assert [rules.band("bp_sys", v) for v in (90, 100, 110, 219, 220)] == [3, 2, 1, 0, 3]


def test_a_few_bad_readings_are_not_an_alarm(app):
    with app.app_context():
        assert feed(1, N - 1, spo2=86, heart_rate=72) == []


def test_sustained_low_oxygen_raises_one_emergency_with_its_reason(app):
    with app.app_context():
        raised = feed(1, N, spo2=86, heart_rate=72)
        assert [a.level for a in raised] == ["emergency"]
        assert raised[0].reason == f"Blood oxygen 86%, out of range for {N} s"
        assert raised[0].nasa_risk == "Risk of Hypoxia"
        assert feed(1, 5, spo2=86, heart_rate=72) == []


def test_a_caution_escalates_instead_of_duplicating(app):
    with app.app_context():
        assert [a.level for a in feed(1, N, spo2=95, heart_rate=72)] == ["caution"]
        assert [a.level for a in feed(1, N, spo2=86, heart_rate=72)] == ["emergency"]
        assert Alert.query.filter_by(crew_id=1, vital="spo2").count() == 1


def test_a_loose_sensor_never_sends_an_sos(app):
    with app.app_context():
        raised = feed(1, 20, spo2=70, heart_rate=20, signal_ok=False)
        assert [a.level for a in raised] == ["advisory"]
        assert raised[0].reason == "Check your sensor: no clean signal"
        assert Alert.query.filter_by(level="emergency").count() == 0


def test_the_sensor_advisory_clears_itself_when_the_signal_returns(app):
    with app.app_context():
        feed(1, 1, spo2=70, signal_ok=False)
        feed(1, 1, spo2=98, heart_rate=72)
        assert Alert.query.filter_by(vital="signal", cleared_at=None).count() == 0


def test_a_typed_reading_alerts_at_once_but_never_above_warning(app):
    with app.app_context():
        raised = ingest({"crew_id": 2, "source": "typed", "bp_sys": 88})[1]
        assert [a.level for a in raised] == ["warning"]
        assert raised[0].reason == "Systolic blood pressure 88 mmHg, out of range"


def test_a_cleared_alert_stays_quiet_unless_it_gets_worse(app):
    with app.app_context():
        caution = feed(1, N, spo2=95, heart_rate=72)[0]
        caution.cleared_at, caution.cleared_by = utcnow(), "Lindqvist"
        db.session.commit()
        assert feed(1, N, spo2=95, heart_rate=72) == []
        assert [a.level for a in feed(1, N, spo2=86, heart_rate=72)] == ["emergency"]


def test_heart_rate_alone_never_raises_an_alert(app):
    with app.app_context():
        assert feed(1, 4 * N, heart_rate=140, spo2=98) == []
        assert rules.band("heart_rate", 140) == 3


def test_an_estimated_blood_pressure_from_the_suit_never_alarms(client):
    raised = [alert for _ in range(6)
              for alert in client.post("/api/base/readings", json={"crew_id": 1, "bp_sys": 95}).get_json()["alerts"]]
    assert raised == [] and client.get("/api/base/alerts").get_json() == []
    typed = client.post("/api/base/readings",
                        json={"crew_id": 1, "source": "typed", "bp_sys": 88}).get_json()["alerts"]
    assert [alert["level"] for alert in typed] == ["warning"]         # a cuff reading typed by the crew still counts
