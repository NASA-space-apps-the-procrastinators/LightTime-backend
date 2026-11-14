"""The handoff report for Earth and the line the ship speaks."""
import json
import os

from common.models import Reading

with open(os.path.join(os.path.dirname(__file__), "procedures.json")) as f:
    PROCEDURES = json.load(f)

REQUEST = {
    "doctor_live": "Flight surgeon to direct care now.",
    "crew_first": "The crew is following the on-board checklist. "
                  "Earth to review and advise on what comes next.",
    "ship_alone": "Sent after a blackout. Earth to review what the crew did.",
}


def steps_for(vital):
    return PROCEDURES.get(vital, PROCEDURES["default"])


def _show(value, unit):
    return "not measured" if value is None else f"{value:g}{unit}"


def build(alert, crew, state):
    recent = (Reading.query.filter(Reading.crew_id == crew.id, Reading.source != "typed")
              .order_by(Reading.at.desc(), Reading.id.desc()).limit(30).all())
    if recent:
        last = recent[0]
        vitals = (f"heart rate {_show(last.heart_rate, ' bpm')}, "
                  f"blood oxygen {_show(last.spo2, '%')}, "
                  f"skin temperature {_show(last.skin_temp, ' C')}")
    else:
        vitals = "no sensor readings yet"
    if alert.auto:
        assessment = "Raised by a fixed rule on the readings. This is not a diagnosis."
    else:
        assessment = "Raised by a crew member pressing SOS. This is not a diagnosis."
    return {
        "alert_id": alert.id, "crew_id": crew.id, "crew": crew.name, "level": alert.level,
        "vital": alert.vital, "value": alert.value, "reason": alert.reason,
        "nasa_risk": alert.nasa_risk, "mode": state["mode"], "who_decides": state["who_decides"],
        "sbar": {
            "situation": f"{crew.name}: {alert.reason}. Raised at {alert.at:%H:%M:%S} UTC.",
            "background": (f"Mission stop: {state['label']}. "
                           f"One-way delay {state['delay_s']:.0f} s. Latest: {vitals}."),
            "assessment": assessment,
            "request": REQUEST[state["mode"]],
        },
        "steps": steps_for(alert.vital),
        "recent": [reading.to_dict() for reading in reversed(recent)],
    }


def speak(alert, crew, state):
    line = f"{crew.name}. {alert.reason}. SOS sent to the crew."
    if state["mode"] == "doctor_live":
        return line + " Flight surgeon notified, live."
    if state["mode"] == "crew_first":
        minutes = round(state["delay_s"] / 60)
        return line + (f" Earth will hear this in {minutes} minutes. "
                       f"Earliest reply in {2 * minutes} minutes. "
                       "Crew medical officer, start the checklist.")
    return line + " No signal to Earth. Report queued. Crew medical officer, start the checklist."
