"""The demo morning: 14 November 2026, 06:30 UTC, mission day 158, alert A1 just raised.

Loaded at start and on every reset when the app is in morning mode, so a restarted demo
always begins at the same moment. Everything here comes from data/processed."""
from datetime import datetime

from common import dataset
from common.models import (Alert, Checkin, Crew, LinkMessage, MissionState, Reading, Reminder, db,
                           set_clock)

CHECKLIST = {"hr_rest": "heart_rate"}     # which checklist a console alert uses; others use their own name
SKIP = {"hr"}                             # alerts no rule on the ship or the console would raise (review F6d)


def when(text):
    """A dataset time such as "2026-11-14T06:12:00Z" as the naive UTC the tables use, or None."""
    return datetime.fromisoformat(text.replace("Z", "")) if text else None


def whole(text):
    return None if text in ("", None) else int(float(text))


def load():
    mission = dataset.mission()
    set_clock(when(mission["demo_now"]))
    for model in (Reminder, Checkin, LinkMessage, Alert, Reading):
        model.query.delete()
    crew = {member.code: member for member in Crew.query}

    for row in dataset.table("anomalous/checkins"):
        if row["live_demo"] == "true":
            continue                      # the presenter does this one on stage
        db.session.add(Checkin(
            crew_id=crew[row["crew_id"]].id, day=row["date"], completed_at=when(row["completed_at"]),
            mood=whole(row["mood"]), sleep_h=dataset.num(row["sleep_h"]), pvt_ms=whole(row["pvt_ms"]),
            bp_sys=dataset.num(row["cuff_bp_sys_mmhg"]), bp_dia=dataset.num(row["cuff_bp_dia_mmhg"]),
            symptoms=dataset.listed(row["symptoms"]), note=row["note"]))

    alerts = {}
    for row in dataset.table("anomalous/alerts_seed"):
        if row["metric"] in SKIP:
            continue
        done = bool(row["resolved_at"])
        alerts[row["alert_id"]] = alert = Alert(
            ref=row["alert_id"], crew_id=crew[row["crew_id"]].id, at=when(row["raised_at"]),
            level=row["level"], vital=CHECKLIST.get(row["metric"], row["metric"]), metric=row["metric"],
            value=dataset.num(row["value"]), reason=row["reason"], auto=row["metric"] != "manual",
            nasa_risk=row["nasa_risk"], steps_done=[int(i) for i in dataset.listed(row["steps_done"])],
            symptoms=dataset.listed(row["symptoms"]),
            acknowledged_at=when(row["acknowledged_at"]), acknowledged_by="crew" if row["acknowledged_at"] else None,
            cleared_at=when(row["resolved_at"]), cleared_by="crew" if done else None)
        db.session.add(alert)
    db.session.flush()

    numbers = {}                          # the dataset's "M12" to this table's row number
    for row in dataset.table("anomalous/messages"):
        if row["alert_id"] and row["alert_id"] not in alerts:
            continue                      # the thread of an alert that was not loaded
        about = alerts.get(row["alert_id"])
        message = LinkMessage(
            direction=row["direction"], kind=row["kind"], priority=int(row["priority"]),
            payload={"alert_id": about.id if about else None, "text": row["text"], "from": row["author"],
                     "simulated": True},
            created_at=when(row["created_at"]), sent_at=when(row["sent_at"]), delay_s=dataset.num(row["delay_s"]),
            deliver_at=when(row["deliver_at"]), in_reply_to=numbers.get(row["in_reply_to"]))
        db.session.add(message)
        db.session.flush()
        numbers[row["message_id"]] = message.id
        if about is not None and row["kind"] == "report":
            about.report_id = message.id

    for row in dataset.table("anomalous/reminders"):
        if row["alert_id"] in alerts:
            db.session.add(Reminder(crew_id=crew[row["crew_id"]].id, alert_id=alerts[row["alert_id"]].id,
                                    text=row["text"], due_at=when(row["due_at"]), done_at=when(row["done_at"])))

    stamp = mission["demo_now"]           # the dial starts where the dataset's link window puts it
    window = next((w for w in dataset.table("reference/link_windows") if w["start"] <= stamp <= w["end"]), None)
    if window:
        db.session.get(MissionState, 1).stop = window["stop"]
    db.session.commit()
