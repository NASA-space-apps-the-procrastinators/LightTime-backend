"""Who may read whose health record on the ship.

The console says who is looking, in the X-LightTime-Viewer header (or ?viewer=). This shapes
what each screen shows. It is not a login: nothing here proves who the person is.

No viewer    the medical station. Every record, as before this file existed.
The CMO      every record. reference/crew.csv marks the crew medical officer with is_cmo.
Anyone else  their own record in full, a name card for the rest, and an SOS as a short notice.
"""
from flask import jsonify, request

from common import dataset

HEADER = "X-LightTime-Viewer"
REFUSAL = "this record is for the person it is about and the crew medical officer"
CARD = ("id", "name", "role", "suit_id", "is_cmo")
NOTICE = ("id", "crew_id", "crew", "at", "level", "state", "stage", "vital", "metric", "raised_by",
          "acknowledged_by", "cleared_at", "cleared_by", "timeline")


def medical_officers():
    return {row["crew_id"] for row in dataset.table("reference/crew") if row["is_cmo"] == "true"}


def viewer():
    """The crew code the console says is looking, or None for the medical station."""
    return (request.headers.get(HEADER) or request.args.get("viewer") or "").strip().upper() or None


def may_read(code):
    who = viewer()
    return who is None or who == code or who in medical_officers()


def refuse():
    return jsonify(error=REFUSAL, field="viewer"), 403


def crew_view(record):
    """A full crew record, or the name card a crewmate gets."""
    record["is_cmo"] = record["id"] in medical_officers()
    if may_read(record["id"]):
        return dict(record, restricted=False)
    return dict({key: record[key] for key in CARD}, restricted=True)


def alert_view(alert):
    """A full alert, the short notice of someone else's SOS, or None for their quieter alerts."""
    if may_read(alert["crew_id"]):
        return dict(alert, restricted=False)
    if alert["level"] != "emergency":
        return None
    return dict({key: alert[key] for key in NOTICE}, restricted=True)
