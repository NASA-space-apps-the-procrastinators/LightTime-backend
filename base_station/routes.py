"""The ship's side: readings in, alerts and reports out."""
from flask import Blueprint, current_app, jsonify, request

from base_station import reports, rules, scenario
from common import link, modes
from common.models import (VITALS, Alert, Crew, LinkMessage, MissionState, Reading, db, iso,
                           utcnow)

bp = Blueprint("base", __name__)


def current_state():
    return modes.describe(db.session.get(MissionState, 1).stop)


def timeline(alert):
    """The round trip of one alert, for the stepper on the alert screen."""
    report = db.session.get(LinkMessage, alert.report_id) if alert.report_id else None
    sent = link.to_dict(report) if report else {}
    reply = next((m for m in reversed(link.delivered("to_ship"))
                  if m.payload.get("alert_id") == alert.id), None)
    return {
        "raised_at": iso(alert.at), "acknowledged_at": iso(alert.acknowledged_at),
        "sent_at": sent.get("sent_at"), "earth_eta_s": sent.get("eta_s"),
        "earth_at": sent.get("deliver_at") if sent.get("status") == "delivered" else None,
        "reply_at": iso(reply.deliver_at) if reply else None,
        "resolved_at": iso(alert.cleared_at),
    }


def alert_dict(alert):
    crew = db.session.get(Crew, alert.crew_id)
    cfg = rules.LIMITS["vitals"].get(alert.vital)
    return {
        "id": alert.id, "crew_id": alert.crew_id, "crew": crew.name, "at": iso(alert.at),
        "level": alert.level, "vital": alert.vital, "value": alert.value,
        "unit": cfg["unit"].strip() if cfg else None, "reason": alert.reason,
        "source": rules.LIMITS["source"] if cfg else None,
        "auto": alert.auto, "nasa_risk": alert.nasa_risk,
        "steps": reports.steps_for(alert.vital), "steps_done": alert.steps_done,
        "acknowledged_by": alert.acknowledged_by,
        "cleared_at": iso(alert.cleared_at), "cleared_by": alert.cleared_by,
        "timeline": timeline(alert),
        "speak": (reports.speak(alert, crew, current_state())
                  if alert.level == "emergency" else None),
    }


def send_report(alert):
    state = current_state()
    crew = db.session.get(Crew, alert.crew_id)
    message = link.send("to_earth", "report", reports.build(alert, crew, state),
                        state["delay_s"], state["link_up"], priority=0)
    alert.report_id = message.id
    db.session.commit()


def tell_earth(alert, event):
    """Send Earth an update about an alert it already has a report for."""
    if alert.report_id is None:
        return
    state = current_state()
    link.send("to_earth", "update", {"alert_id": alert.id, **event},
              state["delay_s"], state["link_up"], priority=1)


def ingest(data):
    """Store one reading, run the rules, and send an SOS report for any new emergency."""
    reading = Reading(crew_id=data["crew_id"], source=data.get("source", "suit"),
                      signal_ok=data.get("signal_ok", True),
                      **{vital: data.get(vital) for vital in VITALS})
    db.session.add(reading)
    db.session.commit()
    raised = rules.evaluate(reading)
    for alert in raised:
        if alert.level == "emergency":
            send_report(alert)
    return reading, raised


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
    reading, raised = ingest(request.get_json())
    return jsonify(reading=reading.to_dict(), alerts=[alert_dict(a) for a in raised]), 201


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


@bp.get("/alerts")
def alerts():
    query = Alert.query
    if request.args.get("open") == "1":
        query = query.filter_by(cleared_at=None)
    return jsonify([alert_dict(a) for a in query.order_by(Alert.at.desc(), Alert.id.desc())])


@bp.post("/alerts/<int:alert_id>/ack")
def acknowledge(alert_id):
    alert = db.get_or_404(Alert, alert_id)
    if alert.acknowledged_at is None:
        alert.acknowledged_at = utcnow()
        alert.acknowledged_by = (request.get_json(silent=True) or {}).get("by", "crew")
        db.session.commit()
        tell_earth(alert, {"event": "acknowledged", "by": alert.acknowledged_by})
    return jsonify(alert_dict(alert))


@bp.post("/alerts/<int:alert_id>/steps")
def tick_step(alert_id):
    alert = db.get_or_404(Alert, alert_id)
    index = int(request.get_json()["index"])
    if index not in alert.steps_done:
        alert.steps_done = alert.steps_done + [index]
        db.session.commit()
        tell_earth(alert, {"event": "step", "step_index": index,
                           "step": reports.steps_for(alert.vital)[index]})
    return jsonify(alert_dict(alert))


@bp.post("/alerts/<int:alert_id>/send")
def send_alert(alert_id):
    """The crew sends an alert to the flight surgeon. An SOS has already gone."""
    alert = db.get_or_404(Alert, alert_id)
    if alert.report_id is None:
        send_report(alert)
    return jsonify(alert_dict(alert))


@bp.post("/alerts/<int:alert_id>/clear")
def clear_alert(alert_id):
    alert = db.get_or_404(Alert, alert_id)
    alert.cleared_at = utcnow()
    alert.cleared_by = (request.get_json(silent=True) or {}).get("by", "crew")
    db.session.commit()
    tell_earth(alert, {"event": "resolved", "by": alert.cleared_by})
    return jsonify(alert_dict(alert))


@bp.post("/messages")
def crew_message():
    data = request.get_json()
    state = current_state()
    message = link.send("to_earth", "message",
                        {"text": data["text"], "from": data.get("from", "Crew"),
                         "alert_id": data.get("alert_id")},
                        state["delay_s"], state["link_up"], priority=2)
    return jsonify(link.to_dict(message)), 201


@bp.post("/sos")
def manual_sos():
    alert = Alert(crew_id=request.get_json()["crew_id"], vital="manual", level="emergency",
                  reason="Manual SOS pressed", auto=False, steps_done=[])
    db.session.add(alert)
    db.session.commit()
    send_report(alert)
    return jsonify(alert_dict(alert)), 201


@bp.get("/outbox")
def outbox():
    messages = (LinkMessage.query.filter_by(direction="to_earth")
                .order_by(LinkMessage.created_at.desc(), LinkMessage.id.desc()))
    return jsonify([link.to_dict(m) for m in messages])


@bp.get("/inbox")
def inbox():
    return jsonify([link.to_dict(m) for m in link.delivered("to_ship")])


@bp.post("/reset")
def reset():
    scenario.stop()
    for model in (LinkMessage, Alert, Reading):
        model.query.delete()
    db.session.get(MissionState, 1).stop = "station"
    db.session.commit()
    return jsonify(ok=True)


@bp.post("/scenario/start")
def scenario_start():
    name = (request.get_json(silent=True) or {}).get("name", "stage")
    if name not in scenario.SCENARIOS:
        return jsonify(error="unknown scenario"), 400
    scenario.start(current_app._get_current_object(), name)
    return jsonify(ok=True, name=name)


@bp.post("/scenario/stop")
def scenario_stop():
    scenario.stop()
    return jsonify(ok=True)
