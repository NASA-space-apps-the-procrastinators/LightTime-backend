"""The two stats tables. Daily totals only, never one row per event. They use the "stats" bind,
which is STATS_DATABASE_URL when it is set and the main database when it is not."""
from common.models import db


class StatCount(db.Model):
    """How many of one kind of thing happened on one UTC day: kind is pageview, click, request or poll."""
    __bind_key__ = "stats"
    __tablename__ = "stat_count"
    day = db.Column(db.Date, primary_key=True)
    kind = db.Column(db.String(8), primary_key=True)
    name = db.Column(db.String(80), primary_key=True)
    n = db.Column(db.Integer, nullable=False)


class StatVisitor(db.Model):
    """One visitor on one UTC day, known only by a hash that changes daily."""
    __bind_key__ = "stats"
    __tablename__ = "stat_visitor"
    day = db.Column(db.Date, primary_key=True)
    visitor = db.Column(db.String(16), primary_key=True)
