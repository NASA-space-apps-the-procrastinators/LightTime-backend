"""The ship's side: readings in, alerts and reports out."""
import time

from flask import Blueprint, abort, current_app, jsonify, request

from base_station import habitat, lookahead, recorder, reports, rules, scenario, usual
from common import link, modes, sources
from common.models import (VITALS, Alert, Crew, LinkMessage, MissionState, Reading, db, iso,
                           utcnow)

bp = Blueprint("base", __name__)


def current_state():
    return modes.describe(db.session.get(MissionState, 1).stop)


def timeline(alert):
    """The round trip of one alert, for the stepper on the alert screen. The earliest reply
    is the report's landing time plus the same leg back, as if the doctor answered at once."""
    report = db.session.get(LinkMessage, alert.report_id) if alert.report_id else None
    sent = link.to_dict(report) if report else {}
    reply = next((m for m in reversed(link.delivered("to_ship"))
                  if m.payload.get("alert_id") == alert.id), None)
    earliest = (report.deliver_at + (report.deliver_at - report.sent_at)
                if report is not None and report.sent_at is not None else None)
    return {
        "raised_at": iso(alert.at), "acknowledged_at": iso(alert.acknowledged_at),
        "sent_at": sent.get("sent_at"), "earth_eta_s": sent.get("eta_s"),
        "earth_at": sent.get("deliver_at") if sent.get("status") == "delivered" else None,
        "earliest_reply_at": iso(earliest),
        "reply_at": iso(reply.deliver_at) if reply else None,
        "resolved_at": iso(alert.cleared_at),
    }


def look_ahead(alert, source=None):
    """Ship AI: the falling trend behind an open alert, if there is one."""
    cfg = rules.LIMITS["vitals"].get(alert.vital)
    if cfg and cfg.get("lookahead") and alert.cleared_at is None and alert.level != "emergency":
        return lookahead.check(alert.crew_id, alert.vital, cfg["bands"][0][0], source)


def alert_dict(alert):
    crew = db.session.get(Crew, alert.crew_id)
    cfg = rules.LIMITS["vitals"].get(alert.vital)
    report = db.session.get(LinkMessage, alert.report_id) if alert.report_id else None
    look = report.payload.get("lookahead") if report else None     # as it stood when the report left
    if alert.level == "emergency":
        speak = reports.speak(alert, crew, current_state())
    else:
        speak = reports.speak_falling(crew, cfg["label"], look) if look else None
    return {
        "id": alert.id, "crew_id": alert.crew_id, "crew": crew.name, "at": iso(alert.at),
        "level": alert.level, "vital": alert.vital, "value": alert.value,
        "unit": cfg["unit"].strip() if cfg else None, "reason": alert.reason,
        "source": rules.LIMITS["source"] if cfg else None,
        "auto": alert.auto, "nasa_risk": alert.nasa_risk,
        "steps": reports.steps_for(alert.vital), "steps_done": alert.steps_done,
        "acknowledged_by": alert.acknowledged_by,
        "cleared_at": iso(alert.cleared_at), "cleared_by": alert.cleared_by,
        "cleared_note": alert.cleared_note, "why": reports.why(alert),
        "timeline": timeline(alert),
        "lookahead": look,
        "speak": speak,
    }


def send_report(alert, look=None):
    state = current_state()
    crew = db.session.get(Crew, alert.crew_id)
    payload = reports.build(alert, crew, state, look, usual.usual_range(crew.id))
    message = link.send("to_earth", "report", payload, state["delay_s"], state["link_up"], priority=0)
    alert.report_id = message.id
    db.session.commit()


def tell_earth(alert, event, priority=1):
    """Send Earth an update about an alert it already has a report for."""
    if alert.report_id is None:
        return
    state = current_state()
    link.send("to_earth", "update", {"alert_id": alert.id, **event},
              state["delay_s"], state["link_up"], priority=priority)


def crew_id_or_400(data):
    try:
        crew = db.session.get(Crew, int(data["crew_id"]))
    except (KeyError, TypeError, ValueError):
        crew = None
    if crew is None:
        abort(400, "unknown crew_id")
    return crew.id


def number(value):
    """A form sends an empty box as "". That is no reading, not a bad one."""
    return None if value in (None, "") else float(value)


def ingest(data):
    """Store one reading and run the rules. An emergency sends a report by itself. So does a
    reading that is falling toward its red line, because the answer takes time to come back.
    If Earth already has the report, it gets an update instead."""
    vitals = {vital: number(data.get(vital)) for vital in VITALS}
    plausible = all(low <= vitals[vital] <= high for vital, (low, high) in rules.LIMITS["plausible"].items()
                    if vitals[vital] is not None)
    reading = Reading(crew_id=data["crew_id"], source=data.get("source", "suit"),
                      signal_ok=bool(data.get("signal_ok", True)) and plausible, context=data.get("context"),
                      **vitals)
    db.session.add(reading)
    db.session.commit()
    raised = rules.evaluate(reading)
    for alert in raised:
        if alert.report_id is not None:
            tell_earth(alert, {"event": "escalated", "level": alert.level, "reason": alert.reason},
                       priority=0 if alert.level == "emergency" else 1)
    for alert in Alert.query.filter_by(crew_id=reading.crew_id, cleared_at=None, report_id=None).all():
        look = look_ahead(alert, reading.source)
        if alert.level == "emergency" or look:
            send_report(alert, look)
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
    data = request.get_json(silent=True) or {}
    try:
        reading, raised = ingest({**data, "crew_id": crew_id_or_400(data)})
    except (TypeError, ValueError):
        db.session.rollback()
        abort(400, "a reading must be a number")
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
                     "latest": _latest(c.id, typed=False), "typed": _latest(c.id, typed=True),
                     "usual": {"heart_rate": usual.usual_range(c.id)}}
                    for c in Crew.query.order_by(Crew.id)])


@bp.get("/crew/<int:crew_id>/readings")
def crew_readings(crew_id):
    limit = min(request.args.get("limit", 120, type=int), 600)
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
        alert.acknowledged_by = (request.get_json(silent=True) or {}).get("by") or "crew"
        db.session.commit()
        tell_earth(alert, {"event": "acknowledged", "by": alert.acknowledged_by})
    return jsonify(alert_dict(alert))


@bp.post("/alerts/<int:alert_id>/steps")
def tick_step(alert_id):
    alert = db.get_or_404(Alert, alert_id)
    try:
        index = int((request.get_json(silent=True) or {})["index"])
    except (KeyError, TypeError, ValueError):
        index = -1
    if not 0 <= index < len(reports.steps_for(alert.vital)):
        return jsonify(error="unknown step"), 400
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
        send_report(alert, look_ahead(alert))
    return jsonify(alert_dict(alert))


@bp.post("/alerts/<int:alert_id>/clear")
def clear_alert(alert_id):
    alert = db.get_or_404(Alert, alert_id)
    if alert.cleared_at is None:        # a second press changes nothing
        body = request.get_json(silent=True) or {}
        alert.cleared_at = utcnow()
        alert.cleared_by = body.get("by") or "crew"
        alert.cleared_note = (body.get("note") or "")[:280] or None
        db.session.commit()
        tell_earth(alert, {"event": "resolved", "by": alert.cleared_by, "note": alert.cleared_note})
    return jsonify(alert_dict(alert))


@bp.post("/messages")
def crew_message():
    data = request.get_json(silent=True) or {}
    if not data.get("text"):
        return jsonify(error="a message needs text"), 400
    state = current_state()
    message = link.send("to_earth", "message",
                        {"text": data["text"], "from": data.get("from", "Crew"),
                         "alert_id": data.get("alert_id")},
                        state["delay_s"], state["link_up"], priority=2)
    return jsonify(link.to_dict(message)), 201


@bp.post("/sos")
def manual_sos():
    crew_id = crew_id_or_400(request.get_json(silent=True) or {})
    alert = Alert.query.filter_by(crew_id=crew_id, vital="manual", cleared_at=None).first()
    if alert is not None:               # a second press changes nothing
        return jsonify(alert_dict(alert))
    alert = Alert(crew_id=crew_id, vital="manual", level="emergency",
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
    db.session.commit()      # the dial stays where it is, so a restarted demo keeps its distance
    usual.clear()
    return jsonify(ok=True)


@bp.post("/scenario/start")
def scenario_start():
    body = request.get_json(silent=True) or {}
    name, real = body.get("name", "stage"), bool(body.get("replay"))
    if name not in scenario.SCENARIOS:
        return jsonify(error="unknown scenario"), 400
    scenario.start(current_app._get_current_object(), name, real)
    return jsonify(ok=True, name=name, replay=real)


@bp.post("/scenario/stop")
def scenario_stop():
    scenario.stop()
    return jsonify(ok=True)


@bp.get("/habitat")
def habitat_now():
    return jsonify(habitat.at(time.monotonic() - habitat.STARTED))


@bp.post("/summary/send")
def send_summaries():
    """Send Earth each person's daily summary, then let readings older than 24 hours go."""
    state = current_state()
    for crew in Crew.query.order_by(Crew.id):
        link.send("to_earth", "summary", recorder.daily_summary(crew),
                  state["delay_s"], state["link_up"], priority=3)
    return jsonify(sent=Crew.query.count(), pruned=recorder.prune())


@bp.get("/sources")
def data_sources():
    return jsonify(sources.listing())
