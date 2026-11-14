"""The link between ship and Earth. A message exists for the other side only
once its deliver_at time has passed."""
from datetime import timedelta

from common.models import LinkMessage, db, iso, utcnow

SPEEDUP = 60  # in the demo, one minute of light time plays as one second


def real_delay_s(delay_s):
    return delay_s / SPEEDUP if delay_s >= 60 else delay_s


def _dispatch(message, delay_s, now, stagger_s=0.0):
    message.sent_at = now
    message.delay_s = delay_s
    message.deliver_at = now + timedelta(seconds=real_delay_s(delay_s) + stagger_s)


def send(direction, kind, payload, delay_s, link_up, priority=5, in_reply_to=None, now=None):
    """Send now if the link is up. Otherwise the message waits in the queue."""
    now = now or utcnow()
    message = LinkMessage(direction=direction, kind=kind, payload=payload, priority=priority,
                          in_reply_to=in_reply_to, created_at=now)
    if link_up:
        _dispatch(message, delay_s, now)
    db.session.add(message)
    db.session.commit()
    return message


def flush_queue(delay_s, now=None):
    """The link is back: send everything that waited, most urgent first."""
    now = now or utcnow()
    queued = (LinkMessage.query.filter(LinkMessage.sent_at.is_(None))
              .order_by(LinkMessage.priority, LinkMessage.created_at).all())
    for position, message in enumerate(queued):
        _dispatch(message, delay_s, now, stagger_s=0.4 * position)
    db.session.commit()
    return len(queued)


def delivered(direction, now=None):
    now = now or utcnow()
    return (LinkMessage.query
            .filter(LinkMessage.direction == direction, LinkMessage.deliver_at.isnot(None),
                    LinkMessage.deliver_at <= now)
            .order_by(LinkMessage.deliver_at.desc()).all())


def to_dict(message, now=None):
    """eta_s is the mission time left until the message lands. It is worked out
    here so the screens do not depend on their own clocks."""
    now = now or utcnow()
    if message.sent_at is None:
        status, eta_s = "queued", None
    elif message.deliver_at <= now:
        status, eta_s = "delivered", 0.0
    else:
        status = "in_flight"
        whole = (message.deliver_at - message.sent_at).total_seconds()
        eta_s = message.delay_s * (message.deliver_at - now).total_seconds() / whole
    return {
        "id": message.id, "direction": message.direction, "kind": message.kind,
        "priority": message.priority, "payload": message.payload, "status": status,
        "in_reply_to": message.in_reply_to, "created_at": iso(message.created_at),
        "sent_at": iso(message.sent_at), "deliver_at": iso(message.deliver_at),
        "delay_s": message.delay_s, "eta_s": eta_s, "arrives_after_s": message.delay_s,
        "earliest_reply_after_s": None if message.delay_s is None else 2 * message.delay_s,
    }
