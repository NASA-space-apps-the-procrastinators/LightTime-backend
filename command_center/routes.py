"""The ground's side. It reads only what the link has delivered (and what the ground
itself sent). The logic is in command_center/cases.py."""
import statistics

from flask import Blueprint, current_app, jsonify, request

from command_center import cases, feed
from common import dsn, lighttime, link, modes
from common.models import LinkMessage, MissionState, db

bp = Blueprint("earth", __name__)

MAX_TEXT = 2000


def current_state():
    return modes.describe(db.session.get(MissionState, 1).stop)


def bad(error, field):
    return jsonify(error=error, field=field), 400


def not_found():
    return jsonify(error="not found"), 404


@bp.get("/state")
def state():
    now = link.utcnow()
    out = current_state()
    last_at, last_age, n = cases.last_contact(now)
    sent = [link.to_dict(m, now)["status"] for m in cases.ground_sent()]
    out.update(speedup=link.SPEEDUP, last_contact_at=last_at, last_contact_age_s=last_age, arrived=n,
               ground_outbox={s: sent.count(s) for s in ("queued", "in_flight", "delivered")})
    return jsonify(out)


@bp.get("/inbox")
def inbox():
    now = link.utcnow()
    state = current_state()
    return jsonify(link_up=state["link_up"], delay_s=state["delay_s"], mode=state["mode"],
                   who_decides=state["who_decides"],
                   messages=[link.to_dict(m, now) for m in link.delivered("to_earth", now)])


@bp.get("/cases")
def case_list():
    now = link.utcnow()
    return jsonify(cases=cases.build_cases(now))


@bp.get("/cases/<alert_id>")
def case_detail(alert_id):
    aid = cases.parse_id(alert_id)
    case = cases.find_case(aid, link.utcnow()) if aid is not None else None
    return jsonify(case) if case else not_found()


@bp.get("/cases/<alert_id>/thread")
def case_thread(alert_id):
    aid = cases.parse_id(alert_id)
    now = link.utcnow()
    if aid is None or cases.report_for(aid, now) is None:
        return not_found()
    return jsonify(alert_id=cases.code("A", aid), messages=cases.thread(aid, now))


@bp.post("/feed/start")
def feed_start():
    """Start the suits' vitals feed to Earth. {"interval_s": 120} is optional."""
    data = request.get_json(silent=True)
    data = data if isinstance(data, dict) else {}
    interval_s = data.get("interval_s", feed.DEFAULT_INTERVAL_S)
    if (isinstance(interval_s, bool) or not isinstance(interval_s, (int, float))
            or not feed.MIN_INTERVAL_S <= interval_s <= feed.MAX_INTERVAL_S):
        return bad(f"interval_s is a number of seconds from {feed.MIN_INTERVAL_S} to {feed.MAX_INTERVAL_S}",
                   "interval_s")
    feed.start(current_app._get_current_object(), interval_s)
    return jsonify(feed.status())


@bp.post("/feed/stop")
def feed_stop():
    feed.stop()
    return jsonify(feed.status())


@bp.get("/feed")
def feed_status():
    return jsonify(feed.status())


@bp.get("/vitals")
def vitals():
    """The suit readings Earth has received, newest first, and the latest per crew member.
    ?crew=C1 for one person, ?limit= up to 1000 (default 100)."""
    crew = request.args.get("crew")
    if crew is not None:
        number = cases.parse_id(crew.upper().lstrip("C")) if crew.strip() else None
        if number is None:
            return bad("crew is a crew id such as C1", "crew")
        crew = cases.code("C", number)
    limit = request.args.get("limit", 100)
    try:
        limit = int(limit)
    except (TypeError, ValueError):
        return bad("limit is a whole number", "limit")
    if not 1 <= limit <= 1000:
        return bad("limit is from 1 to 1000", "limit")
    readings, latest = cases.vitals(link.utcnow(), crew, limit)
    return jsonify(readings=readings, latest=latest, simulated=True)


@bp.get("/outbox")
def outbox():
    """What Earth has sent, with the mission time left until each lands on the ship."""
    now = link.utcnow()
    sent = (LinkMessage.query.filter_by(direction="to_ship")
            .order_by(LinkMessage.created_at.desc(), LinkMessage.id.desc()))
    return jsonify([link.to_dict(m, now) for m in sent])


@bp.post("/reply")
def reply():
    """Advice back to the ship, with the same delay. Reply to a message (message_id)
    or to a case (alert_id); with neither it is a general message to the crew."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return bad("body must be a JSON object", "body")
    text = data.get("text")
    if not isinstance(text, str) or not text.strip():
        return bad("text is required", "text")
    if len(text) > MAX_TEXT:
        return bad(f"text is longer than {MAX_TEXT} characters", "text")
    author = data.get("from", "Flight surgeon")
    if not isinstance(author, str) or not author.strip():
        return bad("from must be a name", "from")
    now = link.utcnow()
    parent = None
    if data.get("message_id") is not None:
        mid = cases.parse_id(data["message_id"])
        if mid is None:
            return bad("message_id is not an id", "message_id")
        parent = db.session.get(LinkMessage, mid)
        if parent is None:
            return not_found()
        if parent.direction != "to_earth":
            return bad("can only reply to a message from the ship", "message_id")
        if parent.deliver_at is None or parent.deliver_at > now:
            return not_found()  # it has not reached Earth, so the ground cannot know it
    elif data.get("alert_id") is not None:
        aid = cases.parse_id(data["alert_id"])
        if aid is None:
            return bad("alert_id is not an id", "alert_id")
        parent = cases.report_for(aid, now)
        if parent is None:
            return not_found()
    state = current_state()
    message = link.send("to_ship", "reply",
                        {"text": text.strip(), "from": author.strip(),
                         "alert_id": parent.payload.get("alert_id") if parent else None},
                        state["delay_s"], state["link_up"], priority=0,
                        in_reply_to=parent.id if parent else None, now=now)
    return jsonify(link.to_dict(message, now)), 201


@bp.get("/network")
def network():
    """Two NASA figures for the same thing: Horizons works the Mars delay out from the orbits,
    the Deep Space Network measures it to spacecraft that are there."""
    passes, note = dsn.mars_passes()
    measured = round(statistics.median(p["round_trip_s"] for p in passes) / 2, 1) if passes else None
    worked_out = lighttime.mars_seconds()
    return jsonify(passes=passes, source=note, url=dsn.DSN_URL, dsn_one_way_s=measured,
                   horizons_one_way_s=worked_out,
                   differ_s=None if measured is None else round(abs(measured - worked_out), 1))
