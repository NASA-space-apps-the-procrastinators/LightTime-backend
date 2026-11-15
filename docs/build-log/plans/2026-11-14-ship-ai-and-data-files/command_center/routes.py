"""The ground's side. It reads only what the link has delivered."""
from flask import Blueprint, jsonify, request

from common import link, modes
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
