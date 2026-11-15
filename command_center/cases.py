"""What the ground knows, rebuilt from the link alone.

The command center never reads the ship's tables. Everything here comes from
link_message rows: the ship's messages once they have arrived on Earth, and the
ground's own replies (Earth always knows what it sent).

Ages are in mission time, like eta_s: the trip is counted at its real light time
(delay_s), not the 60x faster stage time, so an 11-minute trip reads 660 s.
"""
from datetime import datetime

from common import link
from common.models import LinkMessage, iso

# Decision 2 in backend-api-contract.md: backend level -> state shown on screen.
STATE = {"nominal": "OK", "advisory": "WATCH", "caution": "WATCH", "warning": "ALERT", "emergency": "SOS"}
RANK = {"OK": 0, "WATCH": 1, "ALERT": 2, "SOS": 3}


def parse_id(value):
    """Accept 7, "7" or "A7"/"M7" (the contract's string ids). None if it isn't one."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        digits = value.strip().lstrip("AaMmRr")
        if digits.isdigit():
            return int(digits)
    return None


def code(prefix, number):
    """The id the screens use, as the ship's API gives it: "A1", "C1", "M5". None stays None."""
    return None if number is None else f"{prefix}{number}"


def _seconds(a, b):
    return (a - b).total_seconds()


def mission_age(message, now):
    """Mission seconds since the ship created this message: time queued on board,
    plus the light time, plus the time since it landed."""
    queued = _seconds(message.sent_at, message.created_at)
    return queued + message.delay_s + max(0.0, _seconds(now, message.deliver_at))


def _parse_iso(text):
    return datetime.fromisoformat(text.rstrip("Z")) if text else None


def arrived(now):
    """Ship messages that have reached Earth, oldest arrival first."""
    return list(reversed(link.delivered("to_earth", now)))


def ground_sent():
    return (LinkMessage.query.filter_by(direction="to_ship")
            .order_by(LinkMessage.created_at, LinkMessage.id).all())


def _alert_of(message):
    return message.payload.get("alert_id")


def thread_entry(message, now):
    """One message in the contract's ThreadMessage shape."""
    status = link.to_dict(message, now)["status"]
    p = message.payload
    if message.kind == "report":
        author, text = "Ship", p.get("sbar", {}).get("situation", p.get("reason", ""))
    elif message.kind == "update":
        author = p.get("by", "crew")
        text = {"acknowledged": f"Acknowledged by {author}", "resolved": f"Resolved by {author}",
                "step": f"Step done: {p.get('step', p.get('step_index'))}"}.get(p.get("event"), p.get("event", ""))
    else:
        author, text = p.get("from", "crew" if message.direction == "to_earth" else "Flight surgeon"), p.get("text", "")
    return {
        "id": code("M", message.id), "alert_id": code("A", _alert_of(message)),
        "from": "crew" if message.direction == "to_earth" else "ground", "author": author, "kind": message.kind,
        "text": text, "created_at": iso(message.created_at), "sent_at": iso(message.sent_at),
        "arrived_at": iso(message.deliver_at) if status == "delivered" else None, "status": status,
        "in_reply_to": code("M", message.in_reply_to),
    }


def _case(report, updates, replies, now):
    p = report.payload
    recent = [r for r in p.get("recent", []) if r.get("at")]
    newest = max((_parse_iso(r["at"]) for r in recent), default=None)
    report_age = mission_age(report, now)
    last = max([report] + updates, key=lambda m: m.deliver_at)
    case = {
        "alert_id": code("A", p["alert_id"]), "crew_id": code("C", p.get("crew_id")), "crew": p.get("crew"),
        "vital": p.get("vital"), "level": p.get("level"), "state": STATE.get(p.get("level"), "WATCH"),
        "value": p.get("value"), "reason": p.get("reason"), "nasa_risk": p.get("nasa_risk"),
        "mode_at_send": p.get("mode"), "who_decides_at_send": p.get("who_decides"),
        "raised_at": p.get("raised_at") or iso(report.created_at),
        "status": "reported", "acknowledged_by": None, "acknowledged_at": None,
        "resolved_by": None, "resolved_at": None, "steps_done": [],
        "timeline": {"reported_at": iso(report.created_at), "sent_at": iso(report.sent_at),
                     "arrived_at": iso(report.deliver_at)},
        "last_heard_at": iso(last.deliver_at),
        "replies": len(replies), "awaiting_reply": not replies,
        "reply_status": link.to_dict(replies[-1], now)["status"] if replies else None,
        "data_age": {
            "report_age_s": round(report_age, 1),
            "queued_s": round(_seconds(report.sent_at, report.created_at), 1),
            "transit_s": report.delay_s,
            "newest_reading_at": iso(newest),
            "newest_reading_age_s": round(report_age + _seconds(report.created_at, newest), 1) if newest else None,
            "last_heard_age_s": round(mission_age(last, now), 1),
        },
    }
    for u in updates:
        if u.kind != "update":
            continue
        event = u.payload.get("event")
        if event == "acknowledged":
            case["acknowledged_by"], case["acknowledged_at"] = u.payload.get("by"), iso(u.created_at)
            if case["status"] == "reported":
                case["status"] = "acknowledged"
        elif event == "step":
            index = u.payload.get("step_index")
            if index not in case["steps_done"]:
                case["steps_done"].append(index)
            if case["status"] in ("reported", "acknowledged"):
                case["status"] = "in_progress"
        elif event == "resolved":
            case["resolved_by"], case["resolved_at"] = u.payload.get("by"), iso(u.created_at)
            case["status"] = "resolved"
    return case


def build_cases(now, detail=False):
    """One case per alert whose report has reached Earth. Open cases first, then the
    most serious, then the newest."""
    ship = arrived(now)
    reports, follow = {}, {}
    for m in ship:
        aid = _alert_of(m)
        if aid is None:
            continue
        if m.kind == "report" and aid not in reports:
            reports[aid] = m
        else:
            follow.setdefault(aid, []).append(m)
    replies = {}
    for m in ground_sent():
        if _alert_of(m) is not None:
            replies.setdefault(_alert_of(m), []).append(m)
    out = []
    for aid, report in reports.items():
        case = _case(report, follow.get(aid, []), replies.get(aid, []), now)
        if detail:
            p = report.payload
            case["report"] = {"sbar": p.get("sbar"), "steps": p.get("steps", []), "recent": p.get("recent", [])}
            case["report_message_id"] = code("M", report.id)
        out.append(case)
    out.sort(key=lambda c: c["raised_at"], reverse=True)
    out.sort(key=lambda c: RANK.get(c["state"], 0), reverse=True)
    out.sort(key=lambda c: c["status"] == "resolved")
    return out


def find_case(alert_id, now):
    for case in build_cases(now, detail=True):
        if case["alert_id"] == code("A", alert_id):
            return case
    return None


def thread(alert_id, now):
    """Every message about one alert that Earth can see, oldest first."""
    seen = [m for m in arrived(now) if _alert_of(m) == alert_id]
    sent = [m for m in ground_sent() if _alert_of(m) == alert_id]
    messages = sorted(seen + sent, key=lambda m: (m.created_at, m.id))
    return [thread_entry(m, now) for m in messages]


def report_for(alert_id, now):
    """The arrived report message for an alert, or None."""
    return next((m for m in arrived(now) if m.kind == "report" and _alert_of(m) == alert_id), None)


def outbox(now):
    out = []
    for m in reversed(ground_sent()):
        entry = thread_entry(m, now)
        d = link.to_dict(m, now)
        entry.update({"eta_s": d["eta_s"], "delay_s": m.delay_s, "deliver_at": iso(m.deliver_at)})
        out.append(entry)
    return out


def last_contact(now):
    ship = arrived(now)
    if not ship:
        return None, None, 0
    last = ship[-1]
    return iso(last.deliver_at), round(mission_age(last, now), 1), len(ship)
