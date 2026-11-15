"""The stats routes, served at /api/stats. Public, with no key."""
import json
from collections import Counter, defaultdict
from datetime import timedelta

from flask import Blueprint, jsonify, request
from sqlalchemy import func

from common.models import db
from stats import counter
from stats.models import StatCount, StatVisitor
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


def _top(totals):
    """The ten largest {name: n}, largest first."""
    return [{"name": name, "n": n} for name, n in sorted(totals.items(), key=lambda t: (-t[1], t[0]))[:10]]


@bp.get("")
def totals():
    """Daily totals for the last ?days= days (1 to 90, default 7), oldest first, and the top ten
    pages, clicks and routes over them. Flushes first, so the page is never 30 seconds behind."""
    try:
        days = int(request.args.get("days", "7"))
    except ValueError:
        days = 0
    if not 1 <= days <= 90:
        return bad("days must be a whole number from 1 to 90", "days")
    counter.flush()
    since = counter.today() - timedelta(days=days - 1)
    by_day = defaultdict(lambda: dict.fromkeys(("visitors", "pageviews", "clicks", "requests", "polls"), 0))
    tops = {"pageview": Counter(), "click": Counter(), "route": Counter()}
    for row in StatCount.query.filter(StatCount.day >= since):
        by_day[row.day][row.kind + "s"] += row.n
        tops["route" if row.kind in ("request", "poll") else row.kind][row.name] += row.n
    visitors = (db.session.query(StatVisitor.day, func.count()).filter(StatVisitor.day >= since)
                .group_by(StatVisitor.day))
    for day, n in visitors:
        by_day[day]["visitors"] = n
    return jsonify(days=[{"day": day.isoformat(), **by_day[day]} for day in sorted(by_day)],
                   top_pages=_top(tops["pageview"]), top_clicks=_top(tops["click"]),
                   top_routes=_top(tops["route"]))
