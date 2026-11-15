"""Telling visitors apart without cookies and without keeping an IP address.

A visitor is sha256(salt + ip + user agent), first 16 hex characters. The salt is random, made at
start and replaced when the UTC day changes, and never stored, so yesterday's hashes cannot be
matched to today's or turned back into an address."""
import hashlib
import secrets
import threading

from flask import current_app

from stats.counter import today

BOT_MARKERS = ("bot", "crawler", "spider", "googlehc", "uptimechecks")

_lock = threading.Lock()
_salt = (None, "")      # (day, salt)
_shape_logged = False


def client_ip(request):
    """The second from last X-Forwarded-For entry (the one the Google load balancer adds),
    else the address the request came from."""
    global _shape_logged
    hops = [hop.strip() for hop in request.headers.get("X-Forwarded-For", "").split(",") if hop.strip()]
    if hops and not _shape_logged:      # once a process, the count only, never an address
        _shape_logged = True
        current_app.logger.warning("X-Forwarded-For has %d entries; the visitor is taken from the second from last",
                                   len(hops))
    return hops[-2] if len(hops) >= 2 else request.remote_addr or ""


def _salt_for(day):
    global _salt
    with _lock:
        if _salt[0] != day:
            _salt = (day, secrets.token_hex(16))
        return _salt[1]


def visitor_id(request, day=None):
    """This browser's hash for `day` (today, UTC, by default)."""
    text = _salt_for(day or today()) + client_ip(request) + request.headers.get("User-Agent", "")
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def is_bot(user_agent):
    """Crawlers, Google's health checks and uptime checks are not counted."""
    agent = (user_agent or "").lower()
    return any(marker in agent for marker in BOT_MARKERS)
