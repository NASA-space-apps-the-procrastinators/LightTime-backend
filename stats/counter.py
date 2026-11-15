"""Counts held in memory and written to the stats tables as daily totals.

The console polls once a second, so writing on every request would lock SQLite. Requests only
touch memory here; flush() writes. The counts are swapped out under the lock and written outside
it, so a slow or unreachable stats database never holds up a ship request."""
import atexit
import threading
import time
from collections import Counter
from datetime import datetime, timezone

from flask import current_app

from common.models import db
from stats.models import StatCount, StatVisitor

FLUSH_EVERY_S = 30

_lock = threading.Lock()        # guards the counts in memory and the thread
_writing = threading.Lock()     # one flush writes at a time
_counts = Counter()             # (day, kind, name) -> n
_visitors = set()               # (day, visitor)
_thread = None


def today():
    """The real UTC date. Stats use real time, never the mission clock."""
    return datetime.now(timezone.utc).date()


def add(kind, name):
    """Count one pageview, click, request or poll under a name, cut to fit the 80-character column."""
    with _lock:
        _counts[(today(), kind, name[:80])] += 1


def see(visitor):
    """Note one visitor hash for today."""
    with _lock:
        _visitors.add((today(), visitor))


def clear():
    """Forget the counts not yet written."""
    with _lock:
        _counts.clear()
        _visitors.clear()


def _take():
    global _counts, _visitors
    with _lock:
        counts, visitors = _counts, _visitors
        _counts, _visitors = Counter(), set()
    return counts, visitors


def _keep(counts, visitors):
    with _lock:
        _counts.update(counts)
        _visitors.update(visitors)


def _write(counts, visitors):
    for (day, kind, name), n in counts.items():
        same = StatCount.query.filter_by(day=day, kind=kind, name=name)
        if not same.update({StatCount.n: StatCount.n + n}):
            db.session.add(StatCount(day=day, kind=kind, name=name, n=n))
    for day, visitor in visitors:
        if db.session.get(StatVisitor, (day, visitor)) is None:
            db.session.add(StatVisitor(day=day, visitor=visitor))
    db.session.commit()


def flush():
    """Write the counts held in memory. If the write fails, log a warning and keep them for the
    next try: traffic stats must never break a ship request. Returns True when they were written."""
    with _writing:
        counts, visitors = _take()
        if not counts and not visitors:
            return True
        try:
            _write(counts, visitors)
        except Exception:
            db.session.rollback()
            _keep(counts, visitors)
            current_app.logger.warning("traffic stats were not written; kept for the next try", exc_info=True)
            return False
    return True


def _flush_in(app):
    with app.app_context():
        flush()


def _run(app):
    while True:
        time.sleep(FLUSH_EVERY_S)
        _flush_in(app)


def start(app):
    """Start the one thread that flushes every 30 seconds, and flush once more at shutdown.
    A second call does nothing."""
    global _thread
    with _lock:
        if _thread is not None:
            return
        _thread = threading.Thread(target=_run, args=(app,), daemon=True, name="stats-flush")
    _thread.start()
    atexit.register(_flush_in, app)
