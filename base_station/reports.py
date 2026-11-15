"""The handoff report for Earth and the line the ship speaks."""
import json
import os
from datetime import timedelta

from base_station import lookahead, rules
from common.models import Reading, iso, utcnow

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


def why(alert):
    """How the ship reached this alert, in plain lines a medical officer can check."""
    if alert.vital == "manual":
        return ["A crew member pressed SOS. No rule was involved."]
    cfg = rules.LIMITS["vitals"].get(alert.vital)
    if cfg is None:
        return ["The sensor signal was not clean, so no reading was judged."]
    recent = (Reading.query.filter(Reading.crew_id == alert.crew_id, getattr(Reading, alert.vital).isnot(None))
              .order_by(Reading.at.desc(), Reading.id.desc()).limit(5).all())
    values = ", ".join(f"{getattr(r, alert.vital):g}" for r in reversed(recent))
    if alert.reason.endswith(lookahead.FALLING):
        rule = "Rule: the reading is still in the normal band but falling steadily toward the red line."
    else:
        rule = ("Rule: the reading sat in an out-of-range band. A sensor needs five readings in a row "
                "with a clean signal. A typed number counts once and stops at a warning.")
    return [f"What was seen: {alert.reason}.", f"Last readings: {values}{cfg['unit']}.", rule,
            f"Band table: {rules.LIMITS['source']}",
            "This is a fixed rule, not a diagnosis. A person, not the ship, decides."]


def _show(value, unit):
    return "not measured" if value is None else f"{value:g}{unit}"


def span(seconds):
    if seconds < 2:
        return "under two seconds"
    return f"{round(seconds)} seconds" if seconds < 90 else f"{round(seconds / 60)} minutes"


def deadline(look, state):
    """Ship AI: can Earth answer before the red line? The time left against the earliest reply."""
    now = utcnow()
    reply_s = 2 * state["delay_s"] if state["link_up"] else None
    return {**look, "at": iso(now), "red_line_at": iso(now + timedelta(seconds=look["eta_s"])),
            "reply_s": reply_s, "earth_in_time": reply_s is not None and reply_s < look["eta_s"]}


def asked_ahead(alert, crew, recent, look, usual):
    """Ship AI: the questions a flight surgeon asks first, answered before the report leaves."""
    answers = []
    values = [getattr(r, alert.vital, None) for r in reversed(recent)]
    values = [v for v in values if v is not None]
    if len(values) >= 2:
        answers.append({"q": "How has it moved over the last minute?",
                        "a": f"From {values[0]:g} to {values[-1]:g} across {len(values)} readings."})
    if look:
        answers.append({"q": "How long until it is critical?",
                        "a": f"Falling {abs(look['per_min']):g} a minute. "
                             f"Red line in about {span(look['eta_s'])}."})
    if recent and recent[0].heart_rate is not None:
        own = (f" Usual range over the last day: {usual['low']} to {usual['high']} bpm."
               if usual else " No usual range learned yet.")
        answers.append({"q": "Is the heart rate normal for this person?",
                        "a": f"Now {recent[0].heart_rate:g} bpm." + own})
    poor = sum(not r.signal_ok for r in recent)
    answers.append({"q": "Is the sensor reading cleanly?",
                    "a": f"No: {poor} of the last {len(recent)} readings had a poor signal." if poor
                    else "Yes, every reading in the strip had a clean signal."})
    done = [steps_for(alert.vital)[i] for i in alert.steps_done]
    answers.append({"q": "What has the crew done so far?", "a": "; ".join(done) if done else "Nothing yet."})
    checkin = (Reading.query.filter_by(crew_id=crew.id, source="typed")
               .order_by(Reading.at.desc(), Reading.id.desc()).first())
    answers.append({"q": "How did they sleep and feel?",
                    "a": f"Last check-in: slept {_show(checkin.sleep_hours, ' h')}, "
                         f"mood {_show(checkin.mood, ' of 5')}." if checkin else "No check-in on record."})
    return answers


def build(alert, crew, state, look=None, usual=None):
    recent = (Reading.query.filter(Reading.crew_id == crew.id, Reading.source != "typed")
              .order_by(Reading.at.desc(), Reading.id.desc()).limit(60).all())
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
        "why": why(alert),
        "asked_ahead": asked_ahead(alert, crew, recent, look, usual),
        "lookahead": deadline(look, state) if look else None,
        "usual": usual,
        "steps": steps_for(alert.vital),
        "recent": [reading.to_dict() for reading in reversed(recent)],
    }


def speak_falling(crew, label, verdict):
    """The line for a falling trend. `verdict` is the deadline() that left with the report."""
    line = (f"{crew.name}. {label} {verdict['now']:g} and falling. "
            f"At this rate it reaches the red line in about {span(verdict['eta_s'])}.")
    if verdict["reply_s"] is None:
        return line + f" No signal to Earth. Crew medical officer, check on {crew.name} now."
    if verdict["earth_in_time"]:
        return line + f" Earth can answer in {span(verdict['reply_s'])}. Report sent."
    return line + (f" Earth's earliest reply is {span(verdict['reply_s'])} away. That is too late. "
                   f"Crew medical officer, check on {crew.name} now.")


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
