"""Tables for the ship, the ground and the link between them."""
from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

VITALS = ["heart_rate", "spo2", "skin_temp", "bp_sys", "bp_dia", "glucose", "sleep_hours", "mood"]


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def iso(dt):
    return dt.isoformat() + "Z" if dt else None


class Crew(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(40), nullable=False)
    role = db.Column(db.String(40), nullable=False, default="crew")


class Reading(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    crew_id = db.Column(db.Integer, db.ForeignKey("crew.id"), nullable=False, index=True)
    at = db.Column(db.DateTime, nullable=False, default=utcnow, index=True)
    source = db.Column(db.String(12), nullable=False, default="suit")
    signal_ok = db.Column(db.Boolean, nullable=False, default=True)
    heart_rate = db.Column(db.Float)
    spo2 = db.Column(db.Float)
    skin_temp = db.Column(db.Float)
    bp_sys = db.Column(db.Float)
    bp_dia = db.Column(db.Float)
    glucose = db.Column(db.Float)
    sleep_hours = db.Column(db.Float)
    mood = db.Column(db.Float)

    def to_dict(self):
        out = {"id": self.id, "crew_id": self.crew_id, "at": iso(self.at),
               "source": self.source, "signal_ok": self.signal_ok}
        out.update({v: getattr(self, v) for v in VITALS})
        return out


class Alert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    crew_id = db.Column(db.Integer, db.ForeignKey("crew.id"), nullable=False, index=True)
    at = db.Column(db.DateTime, nullable=False, default=utcnow)
    level = db.Column(db.String(12), nullable=False)
    vital = db.Column(db.String(16), nullable=False)
    value = db.Column(db.Float)
    reason = db.Column(db.String(200), nullable=False)
    auto = db.Column(db.Boolean, nullable=False, default=True)
    nasa_risk = db.Column(db.String(80), nullable=False, default="")
    steps_done = db.Column(db.JSON, nullable=False, default=list)
    cleared_at = db.Column(db.DateTime)
    cleared_by = db.Column(db.String(40))
    acknowledged_at = db.Column(db.DateTime)
    acknowledged_by = db.Column(db.String(40))
    report_id = db.Column(db.Integer)


class MissionState(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    stop = db.Column(db.String(12), nullable=False, default="station")


class LinkMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    direction = db.Column(db.String(8), nullable=False)
    kind = db.Column(db.String(8), nullable=False)
    priority = db.Column(db.Integer, nullable=False, default=5)
    payload = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    sent_at = db.Column(db.DateTime)
    delay_s = db.Column(db.Float)
    deliver_at = db.Column(db.DateTime, index=True)
    in_reply_to = db.Column(db.Integer)


def seed():
    if Crew.query.count() == 0:
        db.session.add_all([Crew(name="David"), Crew(name="Damola", role="cmo"), Crew(name="Youssef")])
    if db.session.get(MissionState, 1) is None:
        db.session.add(MissionState(id=1, stop="station"))
    db.session.commit()
