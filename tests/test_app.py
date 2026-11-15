from common.models import Crew, MissionState, db


def test_app_starts_with_four_crew_and_the_dial_at_station(app):
    with app.app_context():
        assert [c.name for c in Crew.query.order_by(Crew.id)] == ["TJ", "Rebecca", "Kyler", "David"]
        assert db.session.get(MissionState, 1).stop == "station"


def test_health(client):
    assert client.get("/api/base/health").get_json() == {"ok": True}
