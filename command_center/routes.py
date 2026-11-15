"""The ground's side. It reads only what the link has delivered."""
import statistics

from flask import Blueprint, jsonify, request

from common import dsn, lighttime, link, modes
from common.models import LinkMessage, MissionState, db

bp = Blueprint("earth", __name__)


def current_state():
    return modes.describe(db.session.get(MissionState, 1).stop)


@bp.get("/inbox")
def inbox():
    now = link.utcnow()
    state = current_state()
    return jsonify(link_up=state["link_up"], delay_s=state["delay_s"], mode=state["mode"],
                   who_decides=state["who_decides"],
                   messages=[link.to_dict(m, now) for m in link.delivered("to_earth", now)])


@bp.get("/outbox")
def outbox():
    """What Earth has sent, with the mission time left until each lands on the ship."""
    now = link.utcnow()
    sent = (LinkMessage.query.filter_by(direction="to_ship")
            .order_by(LinkMessage.created_at.desc(), LinkMessage.id.desc()))
    return jsonify([link.to_dict(m, now) for m in sent])


@bp.post("/reply")
def reply():
    data = request.get_json(silent=True) or {}
    if not data.get("text"):
        return jsonify(error="a reply needs text"), 400
    state = current_state()
    parent = db.session.get(LinkMessage, data["message_id"]) if data.get("message_id") else None
    message = link.send("to_ship", "reply",
                        {"text": data["text"], "from": data.get("from", "Flight surgeon"),
                         "alert_id": parent.payload.get("alert_id") if parent else None},
                        state["delay_s"], state["link_up"], priority=0,
                        in_reply_to=data.get("message_id"))
    return jsonify(link.to_dict(message)), 201


@bp.get("/network")
def network():
    """Two NASA figures for the same thing: Horizons works the Mars delay out from the orbits,
    the Deep Space Network reports it for spacecraft that are there."""
    passes, note = dsn.mars_passes()
    measured = round(statistics.median(p["round_trip_s"] for p in passes) / 2, 1) if passes else None
    worked_out = lighttime.mars_seconds()
    return jsonify(passes=passes, source=note, url=dsn.DSN_URL, dsn_one_way_s=measured,
                   horizons_one_way_s=worked_out,
                   differ_s=None if measured is None else round(abs(measured - worked_out), 1))
