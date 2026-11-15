"""The ship's side: readings in, alerts and reports out."""
import math
import time
from datetime import datetime, timedelta

from flask import Blueprint, abort, current_app, jsonify, make_response, request

from base_station import access, habitat, lookahead, morning, recorder, reports, rules, scenario, usual
from common import dataset, link, modes, sources
from common.models import (VITALS, Alert, Checkin, Crew, LinkMessage, MissionState, Reading, Reminder, db,
                           iso, utcnow)

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
    earliest = None
    if report is not None and report.sent_at is not None:
        took = (report.deliver_at - report.sent_at).total_seconds()
        # one leg back on the clock the report used: a message loaded with the morning took real light time
        leg = min((report.delay_s, link.real_delay_s(report.delay_s)), key=lambda one: abs(took - one))
        earliest = report.deliver_at + timedelta(seconds=leg)
    return {
        "raised_at": iso(alert.at), "acknowledged_at": iso(alert.acknowledged_at),
        "sent_at": sent.get("sent_at"), "earth_eta_s": sent.get("eta_s"),
        "earth_at": sent.get("deliver_at") if sent.get("status") == "delivered" else None,
        "earliest_reply_at": iso(earliest),
        # the true length of each leg, in mission seconds: the stamps above are on the demo clock
        "earth_after_s": sent.get("arrives_after_s"),
        "earliest_reply_after_s": sent.get("earliest_reply_after_s"),
        "reply_at": iso(reply.deliver_at) if reply else None,
        "resolved_at": iso(alert.cleared_at),
    }


def look_ahead(alert, source=None):
    """Ship AI: the falling trend behind an open alert, if there is one."""
    cfg = rules.LIMITS["vitals"].get(alert.vital)
    if cfg and cfg.get("lookahead") and alert.cleared_at is None and alert.level != "emergency":
        return lookahead.check(alert.crew_id, alert.vital, cfg["bands"][0][0], source, scenario.since(source))


STATE = {"advisory": "WATCH", "caution": "WATCH", "warning": "ALERT", "emergency": "SOS"}


def row_number(text, prefix):
    """The row number in "A6" or "6", or None. Only plain digits, and few enough to fit a column."""
    text = str(text)
    text = text[len(prefix):] if text[:len(prefix)] == prefix else text
    return int(text) if text.isascii() and text.isdigit() and len(text) <= 9 else None


def alert_code(alert):
    """The id the screens use: "A" and the row number. An alert loaded with the morning has the row its code names."""
    return f"A{alert.id}"


def find_alert(ref):
    """An alert from "A1" or from the row number, or None."""
    number = row_number(ref, "A")
    return db.session.get(Alert, number) if number is not None else None


def alert_or_404(ref):
    alert = find_alert(ref)
    if alert is None:
        abort(404)
    return alert


def stage(alert, line):
    """Where the alert is on its round trip. Worked out from the times, never stored."""
    if alert.cleared_at is not None:
        return "resolved"
    if line["reply_at"]:
        return "replied"
    if line["sent_at"]:
        return "sent"
    return "acknowledged" if alert.acknowledged_at is not None else "raised"


def alert_dict(alert):
    crew = db.session.get(Crew, alert.crew_id)
    cfg = rules.LIMITS["vitals"].get(alert.vital)
    report = db.session.get(LinkMessage, alert.report_id) if alert.report_id else None
    look = report.payload.get("lookahead") if report else None     # as it stood when the report left
    line = timeline(alert)
    text = reports.console_rule(alert)
    why = reports.why(alert)
    if text:                                    # a console rule raised it: a daily value against the person's band
        unit, rule, source, speak = text["unit"], text["alert"], text["source"], None
    else:                                       # the ship AI raised it, or a person pressed SOS
        unit = cfg["unit"].strip() if cfg else None
        rule = next((item[6:] for item in why if item.startswith("Rule: ")), None)
        source = rules.LIMITS["source"] if cfg else None
        if alert.level == "emergency":
            speak = reports.speak(alert, crew, current_state())
        else:
            speak = reports.speak_falling(crew, cfg["label"], look) if look else None
    if alert.cleared_at is not None:            # nothing left to say about a resolved alert
        speak = None
    todo = [step for index, step in enumerate(reports.steps_for(alert.vital)) if index not in alert.steps_done]
    return {
        "id": alert_code(alert), "crew_id": crew.code, "crew": crew.name, "at": iso(alert.at),
        "level": alert.level, "state": "RECHECK" if alert.vital == "signal" else STATE[alert.level],
        "stage": stage(alert, line), "vital": alert.vital, "metric": alert.metric or alert.vital,
        "value": alert.value, "unit": unit, "reason": alert.reason, "rule": rule, "source": source,
        "auto": alert.auto,
        "raised_by": "console" if text else "crew" if alert.vital == "manual" else "lighttime",
        "nasa_risk": alert.nasa_risk, "symptoms": alert.symptoms or [],
        "steps": reports.steps_for(alert.vital), "steps_done": alert.steps_done,
        "next_step": todo[0] if todo else None,
        "acknowledged_by": alert.acknowledged_by,
        "cleared_at": iso(alert.cleared_at), "cleared_by": alert.cleared_by,
        "cleared_note": alert.cleared_note, "why": why,
        "timeline": line,
        "lookahead": look,
        "speak": speak,
    }


def send_report(alert, look=None):
    state = current_state()
    crew = db.session.get(Crew, alert.crew_id)
    payload = reports.build(alert, crew, state, look, usual.usual_range(crew.id))
    if reports.console_rule(alert):        # a console rule raised it: Earth gets seven days and the check-in
        from base_station import console   # imported here because console imports this module
        payload.update(bundle=console.bundle(crew), text=console.BUNDLE_TEXT)
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


def body():
    """The JSON object a button sent, or {} for anything else."""
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def bad(message, field):
    """A 400 that names the field at fault."""
    return jsonify(error=message, field=field), 400


def person(value):
    """Who pressed the button, cut to fit the 40-character column."""
    return (value.strip()[:40] if isinstance(value, str) else "") or "crew"


SUIT_NAMES = {"astronaut_id": "crew_id", "heart_rate_bpm": "heart_rate", "spo2_percent": "spo2",
              "skin_temp_c": "skin_temp"}              # the suit firmware's names for the ship's fields
READ = set(VITALS) | {"crew_id", "source", "signal_ok", "context"} | set(SUIT_NAMES)
# A heart rate outside this is refused as impossible input. A project choice for bad data,
# not an alert rule: the alert bands live in limits.json.
HEART_RATE_POSSIBLE = (20, 250)


def in_our_words(data):
    """The suit's firmware has its own field names. The ship's own name wins where both are sent."""
    return {**{ours: data[theirs] for theirs, ours in SUIT_NAMES.items() if theirs in data}, **data}


def find_crew(ref):
    """A crew member from "C1", from a suit id such as "LT-04", or from the row number. Or None."""
    text = str(ref)
    crew = Crew.query.filter((Crew.code == text) | (Crew.suit_id == text)).first()
    number = row_number(ref, "")
    if crew is None and number is not None:
        crew = db.session.get(Crew, number)
    return crew


def crew_or_404(ref):
    crew = find_crew(ref)
    if crew is None:
        abort(404)
    return crew


def crew_id_or_400(data):
    crew = find_crew(data.get("crew_id"))
    if crew is None:
        abort(make_response(*bad("unknown crew_id", "crew_id")))
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
    reading = Reading(crew_id=data["crew_id"], source=data.get("source") or "suit",
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
    out["ship_ai"] = modes.SHIP_AI
    out["mission_day"] = dataset.mission_day(datetime.fromisoformat(dataset.mission_date(utcnow())))
    out["platform"] = dataset.mission()["platform"]
    out["now"] = iso(utcnow())           # the ship's clock, so a screen never counts down on its own
    out["stops"] = [modes.describe(stop) for stop in modes.STOPS]
    return jsonify(out)


@bp.post("/dial")
def dial():
    stop = body().get("stop")
    if not isinstance(stop, str) or stop not in modes.STOPS:
        return bad("unknown stop", "stop")
    db.session.get(MissionState, 1).stop = stop
    db.session.commit()
    new_state = current_state()
    flushed = link.flush_queue(new_state["delay_s"]) if new_state["link_up"] else 0
    return jsonify(state=new_state, flushed=flushed)


@bp.post("/readings")
def post_reading():
    data = in_our_words(body())
    crew_id = crew_id_or_400(data)
    given = {}
    for vital in VITALS:
        try:
            value = number(data.get(vital))
        except (TypeError, ValueError, OverflowError):
            value = math.nan
        if value is not None and not math.isfinite(value):       # "inf" would break Earth's JSON
            return bad("a reading must be a number", vital)
        if value is not None:
            given[vital] = value
    if not given:
        return bad("a reading needs at least one vital sign, such as heart_rate or spo2", "heart_rate")
    low, high = HEART_RATE_POSSIBLE
    if not low <= given.get("heart_rate", low) <= high:
        return bad(f"heart_rate must be between {low} and {high} beats a minute", "heart_rate")
    for field in ("source", "context"):
        if data.get(field) is not None and not (isinstance(data[field], str) and len(data[field]) <= 12):
            return bad(f"{field} is text of at most 12 characters", field)
    reading, raised = ingest({**data, "crew_id": crew_id})
    ignored = sorted(key for key in data if key not in READ)      # for example the suit's radiation fields
    return jsonify(reading=reading.to_dict(), alerts=[alert_dict(a) for a in raised], ignored=ignored), 201


def _latest(crew_id, typed):
    query = Reading.query.filter_by(crew_id=crew_id)
    query = query.filter(Reading.source == "typed") if typed else query.filter(Reading.source != "typed")
    row = query.order_by(Reading.at.desc(), Reading.id.desc()).first()
    return row.to_dict() if row else None


def _level(crew_id):
    levels = [alert.level for alert in Alert.query.filter_by(crew_id=crew_id, cleared_at=None)]
    return max(levels, key=rules.RANK.get, default="nominal")


@bp.get("/crew/<ref>/readings")
def crew_readings(ref):
    crew = crew_or_404(ref)
    if not access.may_read(crew.code):
        return access.refuse()
    limit = min(request.args.get("limit", 120, type=int), 600)
    rows = (Reading.query.filter_by(crew_id=crew.id)
            .order_by(Reading.at.desc(), Reading.id.desc()).limit(limit).all())
    return jsonify([row.to_dict() for row in reversed(rows)])


@bp.get("/alerts")
def alerts():
    query = Alert.query
    if request.args.get("open") == "1":
        query = query.filter_by(cleared_at=None)
    views = [access.alert_view(alert_dict(a)) for a in query.order_by(Alert.at.desc(), Alert.id.desc())]
    return jsonify([view for view in views if view is not None])


@bp.get("/alerts/<alert_id>")
def one_alert(alert_id):
    view = access.alert_view(alert_dict(alert_or_404(alert_id)))
    return access.refuse() if view is None else jsonify(view)


@bp.post("/alerts/<alert_id>/ack")
def acknowledge(alert_id):
    alert = alert_or_404(alert_id)
    sent = body()
    if isinstance(sent.get("symptoms"), list):
        alert.symptoms = [item for item in sent["symptoms"] if isinstance(item, str)][:6]
        db.session.commit()
    if alert.acknowledged_at is None:
        alert.acknowledged_at = utcnow()
        alert.acknowledged_by = person(sent.get("by"))
        db.session.commit()
        tell_earth(alert, {"event": "acknowledged", "by": alert.acknowledged_by})
    return jsonify(alert_dict(alert))


@bp.post("/alerts/<alert_id>/steps")
def tick_step(alert_id):
    alert = alert_or_404(alert_id)
    try:
        index = int(body()["index"])
    except (KeyError, TypeError, ValueError, OverflowError):
        index = -1
    if not 0 <= index < len(reports.steps_for(alert.vital)):
        return bad("unknown step", "index")
    if index not in alert.steps_done:
        alert.steps_done = alert.steps_done + [index]
        db.session.commit()
        tell_earth(alert, {"event": "step", "step_index": index,
                           "step": reports.steps_for(alert.vital)[index]})
    return jsonify(alert_dict(alert))


@bp.post("/alerts/<alert_id>/send")
def send_alert(alert_id):
    """The crew sends an alert to the flight surgeon. An SOS has already gone."""
    alert = alert_or_404(alert_id)
    if alert.report_id is None:
        send_report(alert, look_ahead(alert))
    return jsonify(alert_dict(alert))


@bp.post("/alerts/<alert_id>/clear")
def clear_alert(alert_id):
    alert = alert_or_404(alert_id)
    if alert.cleared_at is None:        # a second press changes nothing
        sent = body()
        note = sent.get("note")
        if note is not None and not isinstance(note, str):
            return bad("a note must be text", "note")
        alert.cleared_at = utcnow()
        alert.cleared_by = person(sent.get("by"))
        alert.cleared_note = (note or "").strip()[:280] or None
        db.session.commit()
        tell_earth(alert, {"event": "resolved", "by": alert.cleared_by, "note": alert.cleared_note})
    return jsonify(alert_dict(alert))


@bp.post("/messages")
def crew_message():
    data = body()
    if not data.get("text"):
        return bad("a message needs text", "text")
    named = data.get("alert_id") not in (None, "")    # an empty box on a form names no alert
    about = find_alert(data["alert_id"]) if named else None
    if named and about is None:
        return bad("unknown alert_id", "alert_id")
    state = current_state()
    message = link.send("to_earth", "message",
                        {"text": data["text"], "from": data.get("from", "Crew"),
                         "alert_id": about.id if about else None},
                        state["delay_s"], state["link_up"], priority=2)
    return jsonify(link.to_dict(message)), 201


@bp.post("/sos")
def manual_sos():
    crew_id = crew_id_or_400(body())
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
    for model in (Reminder, Checkin, LinkMessage, Alert, Reading):
        model.query.delete()
    db.session.commit()      # the dial stays where it is, so a restarted demo keeps its distance
    usual.clear()
    if current_app.config.get("MORNING"):
        morning.load()       # the demo morning starts again, at 06:30, with its own dial stop
    return jsonify(ok=True)


@bp.post("/demo/start")
def demo_start():
    """One button for the stage: the demo starts again, the dial goes to Mars, the full story plays."""
    reset()
    db.session.get(MissionState, 1).stop = "mars"
    db.session.commit()
    scenario.start(current_app._get_current_object(), "full")
    return jsonify(ok=True, name="full", state=current_state())


@bp.post("/scenario/start")
def scenario_start():
    sent = body()
    name, real = sent.get("name", "full"), bool(sent.get("replay"))
    if not isinstance(name, str) or name not in scenario.SCENARIOS:
        return bad("unknown scenario", "name")
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


@bp.errorhandler(404)
def not_found(error):
    return jsonify(error="not found"), 404


@bp.errorhandler(400)
def bad_request(error):
    return jsonify(error=error.description, field=None), 400
