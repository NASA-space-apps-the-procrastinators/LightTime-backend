from stats import counter
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
