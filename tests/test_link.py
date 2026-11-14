from datetime import timedelta

from common import link
from common.models import utcnow


def test_short_delays_are_real_and_long_ones_are_sped_up():
    assert link.real_delay_s(1.3) == 1.3
    assert link.real_delay_s(660) == 11


def test_a_message_is_invisible_until_it_arrives(app):
    with app.app_context():
        t0 = utcnow()
        link.send("to_earth", "report", {"x": 1}, delay_s=660, link_up=True, now=t0)
        assert link.delivered("to_earth", now=t0 + timedelta(seconds=10)) == []
        assert len(link.delivered("to_earth", now=t0 + timedelta(seconds=11))) == 1
        assert link.delivered("to_ship", now=t0 + timedelta(seconds=11)) == []


def test_three_times_on_a_message(app):
    with app.app_context():
        message = link.send("to_earth", "report", {}, delay_s=660, link_up=True)
        shown = link.to_dict(message)
        assert shown["status"] == "in_flight"
        assert shown["arrives_after_s"] == 660 and shown["earliest_reply_after_s"] == 1320
        assert 0 < shown["eta_s"] <= 660


def test_blackout_queues_then_flushes_the_sos_first(app):
    with app.app_context():
        t0 = utcnow()
        link.send("to_earth", "update", {"n": "late"}, 660, link_up=False, priority=1, now=t0)
        link.send("to_earth", "report", {"n": "sos"}, 660, link_up=False, priority=0,
                  now=t0 + timedelta(seconds=1))
        assert link.delivered("to_earth", now=t0 + timedelta(hours=1)) == []
        assert link.flush_queue(660, now=t0 + timedelta(seconds=5)) == 2
        landed = link.delivered("to_earth", now=t0 + timedelta(seconds=30))
        assert [m.payload["n"] for m in sorted(landed, key=lambda m: m.deliver_at)] == ["sos", "late"]
