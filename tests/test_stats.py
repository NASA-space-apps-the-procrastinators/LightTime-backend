from datetime import date

from flask import request

from stats import counter, visitor
from stats.models import StatCount, StatVisitor


def test_two_adds_flush_as_one_row(app):
    with app.app_context():
        counter.add("click", "Dial: Mars")
        counter.add("click", "Dial: Mars")
        counter.flush()
        rows = StatCount.query.all()
        assert [(r.kind, r.name, r.n) for r in rows] == [("click", "Dial: Mars", 2)]


def test_a_second_flush_updates_the_row(app):
    with app.app_context():
        counter.add("pageview", "/")
        counter.add("pageview", "/")
        counter.flush()
        counter.add("pageview", "/")
        counter.flush()
        rows = StatCount.query.all()
        assert [(r.name, r.n) for r in rows] == [("/", 3)]


def test_the_same_visitor_is_one_row(app):
    with app.app_context():
        counter.see("abc123")
        counter.see("abc123")
        counter.flush()
        counter.see("abc123")
        counter.flush()
        assert [v.visitor for v in StatVisitor.query.all()] == ["abc123"]


def test_reset_leaves_the_stats(app, client):
    with app.app_context():
        counter.add("click", "Start story")
        counter.see("abc123")
        counter.flush()
    assert client.post("/api/base/reset").status_code == 200
    with app.app_context():
        assert StatCount.query.filter_by(kind="click").count() == 1
        assert StatVisitor.query.count() == 1


CHROME = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
          "Chrome/130.0.0.0 Safari/537.36")


def _request(app, ip="203.0.113.7", agent=CHROME, forwarded=None):
    headers = {"User-Agent": agent}
    if forwarded:
        headers["X-Forwarded-For"] = forwarded
    return app.test_request_context(headers=headers, environ_base={"REMOTE_ADDR": ip})


def test_the_same_browser_is_the_same_visitor(app):
    day = date(2026, 11, 15)
    with _request(app):
        first = visitor.visitor_id(request, day)
    with _request(app):
        assert visitor.visitor_id(request, day) == first
        assert len(first) == 16
    with _request(app, ip="198.51.100.9"):
        assert visitor.visitor_id(request, day) != first


def test_the_visitor_id_changes_with_the_day(app):
    with _request(app):
        assert visitor.visitor_id(request, date(2026, 11, 15)) != visitor.visitor_id(request, date(2026, 11, 16))


def test_the_ip_is_the_second_from_last_forwarded_entry(app):
    with _request(app, forwarded="1.1.1.1, 2.2.2.2, 3.3.3.3"):
        assert visitor.client_ip(request) == "2.2.2.2"
    with _request(app, ip="203.0.113.7"):
        assert visitor.client_ip(request) == "203.0.113.7"


def test_the_raw_ip_is_stored_nowhere(app):
    with _request(app, forwarded="192.0.2.44, 35.191.0.1"):
        counter.see(visitor.visitor_id(request))
        counter.add("poll", "GET /api/base/state")
        counter.flush()
        rows = [(r.day, r.kind, r.name, r.n) for r in StatCount.query] + [(v.day, v.visitor) for v in StatVisitor.query]
    assert rows and "192.0.2.44" not in repr(rows)


def test_bots_are_known_by_their_user_agent():
    assert visitor.is_bot("GoogleHC/1.0")
    assert visitor.is_bot("Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)")
    assert not visitor.is_bot(CHROME)


BROWSER = {"User-Agent": CHROME}


def _counts(app):
    with app.app_context():
        counter.flush()
        return {(r.kind, r.name): r.n for r in StatCount.query}


def test_polls_are_counted_by_route(app, client):
    client.get("/api/base/state", headers=BROWSER)
    client.get("/api/base/state", headers=BROWSER)
    assert _counts(app) == {("poll", "GET /api/base/state"): 2}
    with app.app_context():
        assert StatVisitor.query.count() == 1


def test_a_route_with_an_id_is_counted_once_by_its_rule(app, client):
    client.get("/api/base/crew/C1", headers=BROWSER)
    client.get("/api/base/crew/C2", headers=BROWSER)
    assert _counts(app) == {("poll", "GET /api/base/crew/<ref>"): 2}


def test_a_dial_press_is_a_request(app, client):
    client.post("/api/base/dial", json={"stop": "mars"}, headers=BROWSER)
    assert _counts(app) == {("request", "POST /api/base/dial"): 1}


def test_a_path_no_route_has_is_unmatched(app, client):
    assert client.get("/api/base/nowhere", headers=BROWSER).status_code == 404
    assert _counts(app) == {("poll", "unmatched"): 1}


def test_bots_preflights_and_the_ships_own_calls_are_not_counted(app, client):
    client.get("/api/base/state", headers={"User-Agent": "GoogleHC/1.0"})
    client.options("/api/base/state", headers=BROWSER)
    client.get("/api/base/state")       # the test client's own user agent, as the vitals feed sends
    assert _counts(app) == {}
    with app.app_context():
        assert StatVisitor.query.count() == 0
