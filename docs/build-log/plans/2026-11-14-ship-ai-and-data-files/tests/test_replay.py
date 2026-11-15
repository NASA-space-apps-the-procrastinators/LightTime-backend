import itertools

from base_station import replay, scenario
from base_station.routes import ingest
from common.models import Alert, LinkMessage, Reading, utcnow


def test_history_ends_where_the_live_part_starts():
    past = replay.history(1, 120)
    assert [age for age, _ in past][:2] == [120, 119] and past[-1][0] == 1
    assert past[-1][1] == replay.rows(1)[replay.HISTORY_S - 1]
    assert replay.live(1, 0) == replay.rows(1)[replay.HISTORY_S]


def test_the_live_part_loops():
    length = len(replay.rows(1)) - replay.HISTORY_S
    assert replay.live(1, length) == replay.live(1, 0)


def test_backfill_gives_the_recorder_a_past_without_raising_alerts(app):
    with app.app_context():
        assert scenario.backfill(seconds=120) == 360
        oldest = Reading.query.order_by(Reading.at).first()
        assert oldest.source == "replay" and 115 <= (utcnow() - oldest.at).total_seconds() <= 125
        assert oldest.context in ("rest", "exercise") and oldest.spo2 is not None
        assert Alert.query.count() == 0


def test_a_story_on_real_wrist_data_still_raises_exactly_one_sos(app):
    with app.app_context():
        story = scenario.frames(**scenario.SCENARIOS["stage"], real=replay.live)
        first = next(story)
        assert first[0]["source"] == "replay"
        assert first[0]["heart_rate"] == replay.live(1, 0)["heart_rate"]
        for second in [first] + list(story):
            for reading in second:
                ingest(reading)
        assert [(a.crew_id, a.vital, a.level) for a in Alert.query.all()] == [(1, "spo2", "emergency")]


def test_start_can_ask_for_real_wrist_data(client):
    started = client.post("/api/base/scenario/start", json={"name": "stage", "replay": True}).get_json()
    client.post("/api/base/scenario/stop")
    assert started == {"ok": True, "name": "stage", "replay": True}
    assert len(client.get("/api/base/crew/1/readings?limit=600").get_json()) == 600


def test_the_real_story_warns_earth_before_the_red_line(app):
    """A real recorded fall in blood oxygen, played through the same rules as the stage story."""
    with app.app_context():
        story = scenario.frames(**scenario.SCENARIOS["real"], real=replay.live)
        report_s = sos_s = None
        for second, readings in enumerate(itertools.islice(story, 240)):
            for reading in readings:
                _, raised = ingest(reading)
                if any(a.level == "emergency" for a in raised):
                    sos_s = sos_s or second
            if report_s is None and LinkMessage.query.filter_by(kind="report").count():
                report_s = second
        report = LinkMessage.query.filter_by(kind="report").one()
        assert report.payload["level"] == "caution" and report.payload["lookahead"]["eta_s"] > 0
        assert sos_s - report_s >= 120                    # two minutes of warning on this recording
        assert [(a.crew_id, a.vital, a.level) for a in Alert.query.all()] == [(1, "spo2", "emergency")]
