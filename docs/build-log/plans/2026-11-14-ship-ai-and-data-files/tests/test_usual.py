from base_station import scenario, usual
from base_station.routes import ingest


def test_no_usual_range_until_there_is_enough_history(app):
    with app.app_context():
        ingest({"crew_id": 1, "heart_rate": 70})
        assert usual.usual_range(1) is None


def test_the_usual_range_comes_from_the_persons_own_resting_history(app):
    with app.app_context():
        scenario.backfill(seconds=1800)
        own = usual.usual_range(1)
        assert own["n"] >= 600 and 40 <= own["low"] < own["high"] <= 130


def test_exercise_does_not_stretch_the_usual_range(app):
    with app.app_context():
        for i in range(700):
            ingest({"crew_id": 2, "heart_rate": 60 + i % 10})
        for _ in range(100):
            ingest({"crew_id": 2, "heart_rate": 165, "context": "exercise"})
        assert usual.usual_range(2)["high"] <= 70


def test_the_crew_board_shows_each_persons_usual_range(client, app):
    with app.app_context():
        scenario.backfill(seconds=1800)
    board = client.get("/api/base/crew").get_json()
    assert board[0]["usual"]["heart_rate"]["low"] < board[0]["usual"]["heart_rate"]["high"]
    assert board[0]["latest"]["source"] == "replay"
