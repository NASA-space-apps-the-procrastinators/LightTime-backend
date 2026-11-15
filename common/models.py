"""Tables for the ship, the ground and the link between them."""
from datetime import datetime, timedelta, timezone

from flask_sqlalchemy import SQLAlchemy

from common import dataset

db = SQLAlchemy()

VITALS = ["heart_rate", "spo2", "skin_temp", "bp_sys", "bp_dia", "glucose", "sleep_hours", "mood"]

_clock_offset = timedelta(0)


def utcnow():
    """The ship's clock: real time, or the mission clock once set_clock has started one."""
    return datetime.now(timezone.utc).replace(tzinfo=None) + _clock_offset


def set_clock(now=None):
    """Start the mission clock at `now` (naive UTC). None goes back to the real clock."""
    global _clock_offset
    real = datetime.now(timezone.utc).replace(tzinfo=None)
    _clock_offset = now - real if now else timedelta(0)


def iso(dt):
    return dt.isoformat() + "Z" if dt else None


class Crew(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(40), nullable=False)
    role = db.Column(db.String(40), nullable=False, default="crew")
    code = db.Column(db.String(4), unique=True)          # "C1": the id every screen uses
    suit_id = db.Column(db.String(8))


class Reading(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    crew_id = db.Column(db.Integer, db.ForeignKey("crew.id"), nullable=False, index=True)
    at = db.Column(db.DateTime, nullable=False, default=utcnow, index=True)
    source = db.Column(db.String(12), nullable=False, default="suit")
    signal_ok = db.Column(db.Boolean, nullable=False, default=True)
    context = db.Column(db.String(12))
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
               "source": self.source, "signal_ok": self.signal_ok, "context": self.context}
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
    cleared_note = db.Column(db.String(280))     # the person's reason, in their own words
    acknowledged_at = db.Column(db.DateTime)
    acknowledged_by = db.Column(db.String(40))
    report_id = db.Column(db.Integer)
    ref = db.Column(db.String(8), unique=True)           # "A1" for an alert loaded with the demo morning
    metric = db.Column(db.String(16))                    # set when a console rule raised it, e.g. "hr_rest"
    symptoms = db.Column(db.JSON, nullable=False, default=list)


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


class Checkin(db.Model):
    """One morning check-in. One row per person per mission date."""
    id = db.Column(db.Integer, primary_key=True)
    crew_id = db.Column(db.Integer, db.ForeignKey("crew.id"), nullable=False, index=True)
    day = db.Column(db.String(10), nullable=False, index=True)      # "2026-11-14"
    completed_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    mood = db.Column(db.Integer)
    sleep_h = db.Column(db.Float)
    pvt_ms = db.Column(db.Integer)
    bp_sys = db.Column(db.Float)                                    # the morning cuff reading
    bp_dia = db.Column(db.Float)
    symptoms = db.Column(db.JSON, nullable=False, default=list)
    note = db.Column(db.String(500), nullable=False, default="")


class Reminder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    crew_id = db.Column(db.Integer, db.ForeignKey("crew.id"), nullable=False, index=True)
    alert_id = db.Column(db.Integer)
    text = db.Column(db.String(120), nullable=False)
    due_at = db.Column(db.DateTime, nullable=False)
    done_at = db.Column(db.DateTime)


def seed():
    if Crew.query.count() == 0:
        db.session.add_all([Crew(code=row["crew_id"], name=row["name"], role=row["role"], suit_id=row["suit_id"])
                            for row in dataset.table("reference/crew")])
    if db.session.get(MissionState, 1) is None:
        db.session.add(MissionState(id=1, stop="station"))
    db.session.commit()
