import json
import threading
from datetime import date, timedelta

from flask import request

from app import create_app
from common.models import db
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


def _send(client, events, agent=CHROME):
    return client.post("/api/stats/events", json={"events": events}, headers={"User-Agent": agent})


def test_page_views_and_clicks_from_the_console_are_counted(app, client):
    answer = _send(client, [{"kind": "pageview", "name": "/crew/[id]"}, {"kind": "click", "name": "Dial: Mars"}])
    assert answer.status_code == 204
    assert _counts(app) == {("pageview", "/crew/[id]"): 1, ("click", "Dial: Mars"): 1}


def test_a_beacon_sent_as_plain_text_is_read_as_json(app, client):
    answer = client.post("/api/stats/events", data='{"events": [{"kind": "click", "name": "SOS"}]}',
                         content_type="text/plain;charset=UTF-8", headers=BROWSER)
    assert answer.status_code == 204
    assert _counts(app) == {("click", "SOS"): 1}


def test_bad_events_are_refused_and_nothing_is_counted(app, client):
    too_many = _send(client, [{"kind": "click", "name": "a"}] * 21)
    assert too_many.status_code == 400 and too_many.get_json()["field"] == "events"
    assert _send(client, [{"kind": "x", "name": "a"}]).get_json() == {"error": "unknown kind", "field": "kind"}
    assert _send(client, [{"kind": "click", "name": "a"}, {"kind": "click", "name": " "}]).status_code == 400
    assert client.post("/api/stats/events", data="not json", headers=BROWSER).status_code == 400
    assert _counts(app) == {}


def test_a_long_name_is_cut_to_80_characters(app, client):
    _send(client, [{"kind": "click", "name": "x" * 200}])
    assert _counts(app) == {("click", "x" * 80): 1}


def test_a_body_over_16_kb_is_refused(client):
    assert _send(client, [{"kind": "click", "name": "x" * 17000}]).status_code == 413


def test_a_bot_is_answered_and_not_counted(app, client):
    assert _send(client, [{"kind": "pageview", "name": "/"}], agent="Googlebot/2.1").status_code == 204
    assert _counts(app) == {}


def _seed(app, rows, visitors=()):
    with app.app_context():
        db.session.add_all(StatCount(day=day, kind=kind, name=name, n=n) for day, kind, name, n in rows)
        db.session.add_all(StatVisitor(day=day, visitor=v) for day, v in visitors)
        db.session.commit()


def test_totals_come_back_by_day_in_date_order(app, client):
    today = counter.today()
    days = [today - timedelta(days=2), today - timedelta(days=1), today]
    _seed(app, [(days[2], "pageview", "/", 5), (days[0], "pageview", "/", 1), (days[0], "click", "SOS", 2),
                (days[1], "poll", "GET /api/base/state", 60), (days[1], "request", "POST /api/base/dial", 3),
                (days[2], "pageview", "/crew/[id]", 4)],
          [(days[0], "a"), (days[1], "a"), (days[1], "b"), (days[2], "c")])
    stats = client.get("/api/stats?days=7").get_json()
    assert stats["days"] == [
        {"day": days[0].isoformat(), "visitors": 1, "pageviews": 1, "clicks": 2, "requests": 0, "polls": 0},
        {"day": days[1].isoformat(), "visitors": 2, "pageviews": 0, "clicks": 0, "requests": 3, "polls": 60},
        {"day": days[2].isoformat(), "visitors": 1, "pageviews": 9, "clicks": 0, "requests": 0, "polls": 0}]
    assert stats["top_pages"] == [{"name": "/", "n": 6}, {"name": "/crew/[id]", "n": 4}]
    assert stats["top_routes"] == [{"name": "GET /api/base/state", "n": 60}, {"name": "POST /api/base/dial", "n": 3}]


def test_days_outside_the_window_are_left_out(app, client):
    _seed(app, [(counter.today() - timedelta(days=7), "click", "old", 1)])
    assert client.get("/api/stats?days=7").get_json()["top_clicks"] == []
    assert client.get("/api/stats?days=8").get_json()["top_clicks"] == [{"name": "old", "n": 1}]


def test_top_clicks_are_the_ten_most_pressed(app, client):
    _seed(app, [(counter.today(), "click", f"button {i}", i) for i in range(1, 13)])
    top = client.get("/api/stats").get_json()["top_clicks"]
    assert [t["n"] for t in top] == [12, 11, 10, 9, 8, 7, 6, 5, 4, 3]


def test_counts_in_memory_are_flushed_before_the_totals(client):
    _send(client, [{"kind": "click", "name": "Dial: Mars"}])
    assert client.get("/api/stats").get_json()["top_clicks"] == [{"name": "Dial: Mars", "n": 1}]


def test_days_must_be_1_to_90(client):
    for days in ("0", "91", "seven"):
        answer = client.get(f"/api/stats?days={days}")
        assert answer.status_code == 400 and answer.get_json()["field"] == "days"
    assert client.get("/api/stats?days=90").status_code == 200


def test_no_stats_yet_is_empty_lists(client):
    assert client.get("/api/stats").get_json() == {"days": [], "top_pages": [], "top_clicks": [], "top_routes": []}


def test_the_page_is_one_html_file_that_reads_the_totals(client):
    answer = client.get("/api/stats/page")
    page = answer.get_data(as_text=True)
    assert answer.status_code == 200 and answer.mimetype == "text/html"
    assert "/api/stats" in page and "Real traffic, not simulated" in page
    assert "<script src" not in page        # no outside scripts
    assert "innerHTML" not in page          # names are public input: written as text, never as markup


def test_a_failed_flush_keeps_the_counts_for_the_next(app, client, monkeypatch):
    write = counter._write

    def down(counts, visitors):
        raise OSError("stats database unreachable")

    client.get("/api/base/state", headers=BROWSER)
    with app.app_context():
        monkeypatch.setattr(counter, "_write", down)
        assert counter.flush() is False
        assert StatCount.query.count() == 0
        monkeypatch.setattr(counter, "_write", write)
        assert counter.flush() is True
        assert [(r.name, r.n) for r in StatCount.query] == [("GET /api/base/state", 1)]
        assert StatVisitor.query.count() == 1


def test_no_flush_thread_is_started_under_test(client):
    client.get("/api/base/state", headers=BROWSER)
    assert counter._thread is None


def test_outside_tests_the_first_request_starts_one_flush_thread(app, client, monkeypatch):
    ran, at_exit = [], []
    monkeypatch.setattr(counter, "_thread", None)
    monkeypatch.setattr(counter, "_run", ran.append)
    monkeypatch.setattr(counter.atexit, "register", lambda flush, *args: at_exit.append(args))
    app.config["TESTING"] = False
    client.get("/api/base/state", headers=BROWSER)
    client.get("/api/base/state", headers=BROWSER)
    counter._thread.join(1)
    assert ran == [app] and at_exit == [(app,)]


def test_a_name_the_database_cannot_hold_is_refused_and_others_still_flush(app, client):
    for bad_name in ("a\u0000b", "\ud800", "\u0007"):
        answer = client.post("/api/stats/events", data=json.dumps({"events": [{"kind": "click", "name": bad_name}]}),
                             content_type="text/plain", headers=BROWSER)
        assert answer.status_code == 400 and answer.get_json()["field"] == "name"
    _send(client, [{"kind": "click", "name": "Send to\n   flight surgeon"}])
    assert _counts(app) == {("click", "Send to flight surgeon"): 1}


def test_deep_nesting_is_a_400_not_a_500(client):
    answer = client.post("/api/stats/events", data="[" * 16000, content_type="text/plain", headers=BROWSER)
    assert answer.status_code == 400


def test_the_totals_do_not_wait_for_a_flush_already_writing(client):
    answers = []
    with counter._writing:
        reader = threading.Thread(target=lambda: answers.append(client.get("/api/stats").status_code))
        reader.start()
        reader.join(5)
        assert not reader.is_alive()
    assert answers == [200]


def test_the_ship_starts_when_the_stats_database_cannot_be_reached(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("STATS_DATABASE_URL", f"sqlite:///{tmp_path / 'no-such-dir' / 'stats.db'}")
    app = create_app(morning=False)
    app.config["TESTING"] = True
    client = app.test_client()
    assert client.get("/api/base/state", headers=BROWSER).status_code == 200
    with app.app_context():
        assert counter.flush() is False         # kept in memory for the next try
    (tmp_path / "no-such-dir").mkdir()
    with app.app_context():
        assert counter.flush() is True          # the tables are made once the database is there
        assert StatCount.query.count() == 1


def test_the_forwarded_shape_is_logged_once_without_addresses(app, caplog, monkeypatch):
    monkeypatch.setattr(visitor, "_shape_logged", False)
    with caplog.at_level("WARNING"):
        for _ in range(2):
            with _request(app, forwarded="192.0.2.44, 35.191.0.1"):
                visitor.client_ip(request)
    lines = [r.getMessage() for r in caplog.records if "X-Forwarded-For" in r.getMessage()]
    assert lines == ["X-Forwarded-For has 2 entries; the visitor is taken from the second from last"]
