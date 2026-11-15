"""The guided tour: one bubble of text for where the story is now. Four bubbles in 30 seconds.

The ship works the step out from what it has actually done (the alert, the report landing on Earth),
never from a timer, so a bubble cannot get ahead of the screen. The console draws the bubble
beside the part of the screen `anchor` names. The words are fixed templates; the numbers are the ship's.
"""
from flask import jsonify

from base_station import access, reports, scenario
from base_station.routes import alert_dict, bp, current_state
from common.models import Alert, Crew, LinkMessage, db, utcnow

STEPS = ("calm", "time_left", "sos", "earth_hears")
TITLE = {"calm": "The suits are talking", "time_left": "Time left", "sos": "SOS", "earth_hears": "Earth hears"}
ANCHOR = {"calm": "crew:C1", "time_left": "alerts", "sos": "alerts", "earth_hears": "earth"}


def _medical_officer():
    code = sorted(access.medical_officers())[0]
    return Crew.query.filter_by(code=code).first().name


def _alert():
    """The patient's blood-oxygen alert from the running story, or None."""
    query = Alert.query.filter_by(crew_id=scenario.PATIENT, vital="spo2", auto=True)
    since = scenario.since("scenario")
    if since is not None:
        query = query.filter(Alert.at >= since)
    return query.order_by(Alert.id.desc()).first()


def _earth_has_heard(alert):
    """True once anything the ship sent about this alert has landed on Earth."""
    now = utcnow()
    return any(m.payload.get("alert_id") == alert.id and m.deliver_at is not None and m.deliver_at <= now
               for m in LinkMessage.query.filter_by(direction="to_earth"))


def _where(alert):
    if alert is None:
        return "calm"
    if _earth_has_heard(alert):
        return "earth_hears"
    return "sos" if alert.level == "emergency" else "time_left"


def _text(step, shown, state):
    patient = db.session.get(Crew, scenario.PATIENT).name
    one_way = reports.span(state["delay_s"]) if state["link_up"] else None
    answer = reports.span(state["round_trip_s"]) if state["link_up"] else None
    if step == "calm":
        far = f"Earth is {one_way} away." if one_way else "There is no link to Earth."
        return f"One reading a second from every suit. {far} Watch {patient}'s blood oxygen."
    if step == "time_left":
        look = shown["lookahead"]
        left = f"about {reports.span(look['eta_s'])}" if look else "very little time"
        reply = f"Earth's answer takes {answer}." if answer else "Earth cannot answer."
        return f"Still in range, but falling. LIGHTTIME gives it {left}. {reply}"
    if step == "sos":
        hears = f"Earth will not hear this for {one_way}" if one_way else "Earth cannot hear this"
        return f"SOS. {hears}, so {_medical_officer()}, the crew medical officer, decides."
    return (f"Earth is only now hearing the first warning. Its answer is {one_way} more away. "
            f"The crew had to act alone.")


def bubble():
    if scenario.playing() is None:
        return {"running": False, "step": 0, "of": len(STEPS), "id": None, "title": None, "text": None,
                "anchor": None, "simulated": True}
    alert = _alert()
    step = _where(alert)
    return {"running": True, "step": STEPS.index(step) + 1, "of": len(STEPS), "id": step, "title": TITLE[step],
            "text": _text(step, alert_dict(alert) if alert else None, current_state()), "anchor": ANCHOR[step],
            "simulated": True}        # the story's readings are scripted


@bp.get("/tour")
def tour():
    return jsonify(bubble())
