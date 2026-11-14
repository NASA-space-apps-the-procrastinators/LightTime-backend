"""The ship's side: readings in, alerts and reports out."""
from flask import Blueprint, jsonify, request

from base_station import rules
from common import link, modes
from common.models import VITALS, Alert, Crew, MissionState, Reading, db

bp = Blueprint("base", __name__)


def current_state():
    return modes.describe(db.session.get(MissionState, 1).stop)


def ingest(data):
    """Store one reading. Returns the reading and the alerts it raised."""
    reading = Reading(crew_id=data["crew_id"], source=data.get("source", "suit"),
                      signal_ok=data.get("signal_ok", True),
                      **{vital: data.get(vital) for vital in VITALS})
    db.session.add(reading)
    db.session.commit()
    return reading, rules.evaluate(reading)


@bp.get("/health")
def health():
    return jsonify(ok=True)


@bp.get("/state")
def state():
    out = current_state()
    out["speedup"] = link.SPEEDUP
    out["stops"] = [modes.describe(stop) for stop in modes.STOPS]
    return jsonify(out)


@bp.post("/dial")
def dial():
    stop = request.get_json().get("stop")
    if stop not in modes.STOPS:
        return jsonify(error="unknown stop"), 400
    db.session.get(MissionState, 1).stop = stop
    db.session.commit()
    new_state = current_state()
    flushed = link.flush_queue(new_state["delay_s"]) if new_state["link_up"] else 0
    return jsonify(state=new_state, flushed=flushed)


@bp.post("/readings")
def post_reading():
    reading, _ = ingest(request.get_json())
    return jsonify(reading=reading.to_dict()), 201


def _latest(crew_id, typed):
    query = Reading.query.filter_by(crew_id=crew_id)
    query = query.filter(Reading.source == "typed") if typed else query.filter(Reading.source != "typed")
    row = query.order_by(Reading.at.desc(), Reading.id.desc()).first()
    return row.to_dict() if row else None


def _level(crew_id):
    levels = [alert.level for alert in Alert.query.filter_by(crew_id=crew_id, cleared_at=None)]
    return max(levels, key=rules.RANK.get, default="nominal")


@bp.get("/crew")
def crew_board():
    return jsonify([{"id": c.id, "name": c.name, "role": c.role, "level": _level(c.id),
                     "latest": _latest(c.id, typed=False), "typed": _latest(c.id, typed=True)}
                    for c in Crew.query.order_by(Crew.id)])


@bp.get("/crew/<int:crew_id>/readings")
def crew_readings(crew_id):
    limit = min(int(request.args.get("limit", 120)), 600)
    rows = (Reading.query.filter_by(crew_id=crew_id)
            .order_by(Reading.at.desc(), Reading.id.desc()).limit(limit).all())
    return jsonify([row.to_dict() for row in reversed(rows)])
