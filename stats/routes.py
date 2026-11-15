"""The stats routes, served at /api/stats. Public, with no key."""
import json

from flask import Blueprint, jsonify, request

from stats import counter
from stats.visitor import is_bot

bp = Blueprint("stats", __name__)

EVENT_KINDS = ("pageview", "click")
MAX_EVENTS = 20
MAX_BODY = 16 * 1024


def bad(message, field, status=400):
    """An error that names the field at fault, as every other route's errors do."""
    return jsonify(error=message, field=field), status


@bp.post("/events")
def events():
    """Page views and clicks from the console: {"events": [{"kind", "name"}]}, at most 20.
    The body is read as JSON whatever its content type, because a beacon is sent as plain text."""
    data = request.stream.read(MAX_BODY + 1)    # never more, whatever the headers say
    if len(data) > MAX_BODY:
        return bad("body over 16 KB", "events", 413)
    if is_bot(request.headers.get("User-Agent")):
        return "", 204
    try:
        sent = json.loads(data)
    except ValueError:
        sent = None
    events = sent.get("events") if isinstance(sent, dict) else None
    if not isinstance(events, list) or len(events) > MAX_EVENTS:
        return bad(f"events must be a list of at most {MAX_EVENTS}", "events")
    for event in events:
        if not isinstance(event, dict) or event.get("kind") not in EVENT_KINDS:
            return bad("unknown kind", "kind")
        if not isinstance(event.get("name"), str) or not event["name"].strip():
            return bad("an event needs a name", "name")
    for event in events:
        counter.add(event["kind"], event["name"].strip()[:80])
    return "", 204
