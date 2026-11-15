"""The console's side of the ship: each person's day against their own band, the trend chart
and the printed rules. Shapes follow the frontend owner's API contract of 14 November."""
import collections
import functools
from datetime import date, timedelta

from flask import jsonify, request

from base_station import scoring, usual
from base_station.morning import when
from base_station.routes import (_latest, _level, alert_code, alert_dict, alert_or_404, bad, body, bp,
                                 crew_or_404, person, row_number, stage, tell_earth, timeline)
from common import dataset, link
from common.models import Alert, Checkin, Crew, LinkMessage, Reminder, db, iso, utcnow

COLUMN = {"hr_rest": "hr_rest_bpm", "bp_sys": "bp_sys_mmhg", "bp_dia": "bp_dia_mmhg", "spo2": "spo2_pct",
          "temp_c": "core_temp_c", "resp": "resp_rpm", "sleep_h": "sleep_h", "mood": "mood", "pvt_ms": "pvt_ms",
          "dose_mSv_day": "dose_msv_day"}                 # console metric -> column in daily_summary.csv
LABEL = {"hr_rest": "resting heart rate", "bp_sys": "systolic blood pressure", "bp_dia": "diastolic blood pressure",
         "spo2": "blood oxygen", "temp_c": "temperature", "resp": "breathing rate", "sleep_h": "sleep",
         "mood": "mood", "pvt_ms": "reaction time", "dose_mSv_day": "radiation dose"}
TYPED = ("mood", "pvt_ms", "bp_sys", "bp_dia")            # what a check-in gives; the rest comes from the suit


@functools.lru_cache(maxsize=None)
def _last_day():
    return max(row["date"] for row in dataset.table("anomalous/daily_summary"))


def today():
    """The mission date as text. The dataset stops on its last day, so a later clock shows that day."""
    return min(utcnow().date().isoformat(), _last_day())


def daily(code, day):
    """One person's daily rows up to and including `day`, oldest first."""
    return [row for row in dataset.table("anomalous/daily_summary")
            if row["crew_id"] == code and row["date"] <= day]


def bands(code):
    """{metric: [low, high]} from the pre-flight baselines, or one number where there is no band."""
    out = {}
    for row in dataset.table("reference/baselines"):
        if row["crew_id"] == code:
            out[row["metric"]] = [float(row["low"]), float(row["high"])] if row["low"] else float(row["point"])
    return out


def baseline(code):
    own = bands(code)
    out = {metric: own[metric] for metric in ("hr_rest", "spo2", "temp_c", "resp", "sleep_h")}
    out.update(bp=[own["bp_sys"], own["bp_dia"]], pvt_ms=own["pvt_ms"], vo2max_ml_min_kg=own["vo2max_ml_min_kg"])
    return out


def day_of(crew, day):
    """One person's day: the values, the symptoms, the date of the check-in they come from, the week's rows.
    Until today's check-in exists, what the person typed at the last one stands (spec D9)."""
    rows = daily(crew.code, day)[-7:]
    row = rows[-1] if rows and rows[-1]["date"] == day else None
    values = {metric: dataset.num(row[column]) if row else None for metric, column in COLUMN.items()}
    checkin = (Checkin.query.filter(Checkin.crew_id == crew.id, Checkin.day <= day)
               .order_by(Checkin.day.desc()).first())
    if checkin is None:
        return values, [], None, rows
    for metric in TYPED:
        if getattr(checkin, metric) is not None:
            values[metric] = getattr(checkin, metric)
    if checkin.day == day and checkin.sleep_h is not None:
        values["sleep_h"] = checkin.sleep_h
    return values, checkin.symptoms or [], checkin.day, rows


def states_of(crew, values, symptoms, rows):
    """OK, WATCH or ALERT for each of the ten daily measurements."""
    own, out = bands(crew.code), {}
    for metric in scoring.METRICS:
        band = own[metric] if metric in scoring.BANDED else None
        week = [dataset.num(row[COLUMN[metric]]) for row in rows[:-1]] + [values[metric]]
        days_out = scoring.days_out_of_band(week, band) if band else 0
        out[metric] = scoring.score(metric, values[metric], band, days_out, bool(symptoms), own["pvt_ms"])
    return out


def crew_dict(crew):
    day = today()
    values, symptoms, checkin_day, rows = day_of(crew, day)
    states = states_of(crew, values, symptoms, rows)
    flagged = [LABEL[metric] for metric in scoring.METRICS if states[metric] in ("WATCH", "ALERT")]
    note = "All in band"
    if flagged:
        note = "Out of band: " + ", ".join(flagged) + (". Symptoms: " + ", ".join(symptoms) if symptoms else "")
    dose = next((row for row in dataset.table("anomalous/radiation_daily") if row["date"] == day), None)
    latest = _latest(crew.id, typed=False)
    quiet = iso(when(dataset.mission()["demo_now"]) - timedelta(minutes=1))   # the dataset's last minute row
    return {
        "id": crew.code, "name": crew.name, "role": crew.role, "suit_id": crew.suit_id,
        "state": scoring.worst([state for state in states.values() if state]), "note": note,
        "baseline": baseline(crew.code),
        "today": {"hr_rest": values["hr_rest"], "bp": [values["bp_sys"], values["bp_dia"]],
                  "spo2": values["spo2"], "temp_c": values["temp_c"], "resp": values["resp"],
                  "sleep_h": values["sleep_h"], "mood": values["mood"], "pvt_ms": values["pvt_ms"],
                  "symptoms": symptoms, "dose_mSv_day": values["dose_mSv_day"],
                  "dose_mSv_mission": dataset.num(dose["dose_msv_mission"]) if dose else None},
        "metric_states": states, "checkin_from": checkin_day,
        "last_packet_at": latest["at"] if latest else quiet,
        # the ship AI's side of the same person
        "level": _level(crew.id), "latest": latest, "typed": _latest(crew.id, typed=True),
        "usual": {"heart_rate": usual.usual_range(crew.id)},
    }


def history(crew, metric, days):
    day = today()
    points = [{"date": row["date"], "value": dataset.num(row[COLUMN[metric]])}
              for row in daily(crew.code, day)[-days:]]
    if points and points[-1]["date"] == day:
        points[-1]["value"] = day_of(crew, day)[0][metric]
    band = bands(crew.code)[metric] if metric in scoring.BANDED else None
    return {"crew_id": crew.code, "metric": metric, "unit": scoring.rule_text()[metric]["unit"], "band": band,
            "days": points,
            "days_out_of_band": scoring.days_out_of_band([p["value"] for p in points], band) if band else 0,
            "simulated": True}


@bp.get("/crew")
def crew_board():
    return jsonify([crew_dict(crew) for crew in Crew.query.order_by(Crew.id)])


@bp.get("/crew/<ref>")
def one_crew(ref):
    return jsonify(crew_dict(crew_or_404(ref)))


@bp.get("/crew/<ref>/history")
def crew_history(ref):
    crew = crew_or_404(ref)
    metric = request.args.get("metric")
    if metric not in COLUMN:
        return bad("metric must be one of " + ", ".join(COLUMN), "metric")
    days = min(max(request.args.get("days", 7, type=int), 1), 30)
    return jsonify(history(crew, metric, days))


@bp.get("/thresholds")
def thresholds():
    return jsonify(scoring.rule_text())


CABIN_SOURCE = ("Cabin CO2, temperature and humidity: NASA OSDR Environmental Data App, Rodent Research 1 "
                "(2014), replayed. CO2 is NASA's ppm converted with the cabin pressure. Oxygen, pressure and "
                "the dose in mSv are simulated.")
WEATHER_SOURCE = "Simulated event, laid out like a NASA DONKI SEP record"


@functools.lru_cache(maxsize=None)
def _cabin():
    """Hab A's rows, oldest first. Its CO2, temperature and humidity are the NASA record."""
    return [row for row in dataset.table("anomalous/cabin_env") if row["habitat_id"] == "H1"]


@bp.get("/station")
def station():
    now = iso(utcnow().replace(microsecond=0))      # the rows are whole seconds: "06:29:00Z" sorts after "06:29:00.3Z"
    row = next((r for r in reversed(_cabin()) if r["ts"] <= now), _cabin()[0])
    real = dataset.listed(row["real_fields"])
    dose = next((r for r in dataset.table("anomalous/radiation_daily") if r["date"] == today()), None)
    co2, dose_day = dataset.num(row["co2_mmhg"]), dataset.num(dose["dose_msv_day"]) if dose else None

    def reading(column, field):
        return {"value": dataset.num(row[column]), "state": None, "simulated": field not in real}

    return jsonify({
        "co2_mmHg": {"value": co2, "state": "ALERT" if co2 >= 4.5 else "WATCH" if co2 >= 2.8 else "OK",
                     "note": "WATCH from 2.8, ALERT from 4.5", "simulated": "co2_ppm" not in real},
        "ppo2_mmHg": reading("ppo2_mmhg", "ppo2_mmhg"),
        "pressure_kPa": reading("pressure_kpa", "pressure_kpa"),
        "temp_c": reading("temp_c", "temp_c"),
        "rh_pct": reading("rh_pct", "rh_pct"),
        "dose_mSv_today": {"value": dose_day, "state": "ALERT" if dose_day is not None and dose_day > 2 else "OK",
                           "note": "ALERT over 2", "simulated": True},
        "updated_at": row["ts"], "habitat": row["habitat_id"], "simulated": True, "source": CABIN_SOURCE,
    })


@bp.get("/space-weather")
def space_weather():
    now = iso(utcnow().replace(microsecond=0))
    event = next((e for e in dataset.table("anomalous/space_weather_events")
                  if e["event_time"] <= now <= e["end_time"]), None)
    if event is None:
        return jsonify(state="OK", headline="No solar particle event", advisory=None, event_at=None,
                       source=WEATHER_SOURCE, simulated=True)
    return jsonify(state=event["state"], headline=event["headline"], advisory=event["advisory"],
                   event_at=event["event_time"], source=WEATHER_SOURCE, simulated=True)


SYMPTOMS = {"headache", "short sleep", "congestion", "nausea", "blurred vision", "back pain"}


def _number(value, low, high, whole=False):
    """True for a real number in range. JSON true and false are not numbers here."""
    kind = int if whole else (int, float)
    return isinstance(value, kind) and not isinstance(value, bool) and low <= value <= high


def streak(day):
    """Days in a row, ending today or yesterday, on which every crew member checked in."""
    everyone = Crew.query.count()
    done = collections.Counter(found for (found,) in db.session.query(Checkin.day))
    days, at = (1 if done[day] == everyone else 0), date.fromisoformat(day) - timedelta(days=1)
    while done[at.isoformat()] == everyone:
        days, at = days + 1, at - timedelta(days=1)
    return days


@bp.get("/checkins/today")
def checkins_today():
    day, crew = today(), Crew.query.order_by(Crew.id).all()
    done = {crew_id for (crew_id,) in db.session.query(Checkin.crew_id).filter_by(day=day)}
    days = streak(day)
    return jsonify(date=day, done=[c.code for c in crew if c.id in done],
                   due=[c.code for c in crew if c.id not in done], streak=days,
                   next_badge_at=(days // 7 + 1) * 7)       # assumed: a badge every seventh day (spec Q3)


@bp.post("/crew/<ref>/checkins")
def post_checkin(ref):
    crew, sent = crew_or_404(ref), body()
    symptoms, note = sent.get("symptoms", []), sent.get("note") or ""
    if not _number(sent.get("mood"), 1, 5, whole=True):
        return bad("mood is a whole number from 1 to 5", "mood")
    if not _number(sent.get("sleep_h"), 0, 24):
        return bad("sleep_h is from 0 to 24", "sleep_h")
    if not (isinstance(symptoms, list) and all(isinstance(item, str) and item in SYMPTOMS for item in symptoms)):
        return bad("symptoms come from: " + ", ".join(sorted(SYMPTOMS)), "symptoms")
    if not isinstance(note, str) or len(note) > 500:
        return bad("note is at most 500 characters", "note")
    if sent.get("pvt_ms") is not None and not _number(sent["pvt_ms"], 100, 3000, whole=True):
        return bad("pvt_ms is a whole number from 100 to 3000", "pvt_ms")
    for field in ("bp_sys", "bp_dia"):
        if sent.get(field) is not None and not _number(sent[field], 30, 260):
            return bad(f"{field} is a cuff reading in mmHg", field)

    day = today()
    row = Checkin.query.filter_by(crew_id=crew.id, day=day).first()
    first = row is None
    if first:
        row = Checkin(crew_id=crew.id, day=day)
        db.session.add(row)
    earlier = (Checkin.query.filter(Checkin.crew_id == crew.id, Checkin.day < day)
               .order_by(Checkin.day.desc()).first())
    for field in ("bp_sys", "bp_dia", "pvt_ms"):     # the last typed value stands until a new one is sent (D9)
        if sent.get(field) is not None:
            setattr(row, field, sent[field] if field == "pvt_ms" else float(sent[field]))
        elif getattr(row, field) is None and earlier is not None:
            setattr(row, field, getattr(earlier, field))
    row.completed_at, row.mood, row.sleep_h = utcnow(), sent["mood"], float(sent["sleep_h"])
    row.symptoms, row.note = symptoms, note
    for alert in Alert.query.filter_by(crew_id=crew.id, cleared_at=None):
        alert.symptoms = symptoms
    db.session.commit()

    values, _, _, rows = day_of(crew, day)
    states = states_of(crew, values, symptoms, rows)
    open_alert = (Alert.query.filter_by(crew_id=crew.id, cleared_at=None)
                  .order_by(Alert.at.desc(), Alert.id.desc()).first())
    return jsonify(crew_id=crew.code, completed_at=iso(row.completed_at), first_today=first, streak=streak(day),
                   metric_states={metric: states[metric] for metric in ("sleep_h", "mood", "pvt_ms")},
                   open_alert_id=alert_code(open_alert) if open_alert else None), 201


BUNDLE = ("hr_rest", "bp_sys", "bp_dia", "temp_c", "sleep_h")
BUNDLE_TEXT = "Alert bundle: 7 days of heart rate, blood pressure, temperature and sleep, plus today's check-in."


def bundle(crew):
    """What goes to the flight surgeon with a console alert."""
    day = today()
    values, symptoms, checkin_day, _ = day_of(crew, day)
    return {"days": {metric: history(crew, metric, 7)["days"] for metric in BUNDLE},
            "today": {**values, "symptoms": symptoms, "checkin_from": checkin_day}, "simulated": True}


def _line(message):
    """One line of text for a message that carries none of its own."""
    payload = message.payload
    if payload.get("text"):
        return payload["text"]
    if message.kind == "report":
        return f"{payload.get('crew', 'Crew')}: {payload.get('reason', 'alert')}. Handoff report attached."
    event = payload.get("event")
    if event == "acknowledged":
        return f"Acknowledged by {payload.get('by', 'crew')}."
    if event == "step":
        return f"Step done: {payload.get('step')}."
    if event == "escalated":
        return f"Now {payload.get('level')}: {payload.get('reason')}."
    if event == "resolved":
        return f"Resolved by {payload.get('by', 'crew')}." + (f" {payload['note']}" if payload.get("note") else "")
    return message.kind


def thread_message(message, alert, now):
    sent, ours = link.to_dict(message, now), message.direction == "to_earth"
    payload = message.payload
    sos = message.kind == "report" and payload.get("level") == "emergency"    # the ship sends an SOS by itself
    return {"id": f"M{message.id}", "alert_id": alert_code(alert), "from": "crew" if ours else "ground",
            "author": payload.get("from") or ("Ship (auto SOS)" if sos else None) or payload.get("crew")
                      or payload.get("by") or ("Ship" if ours else "Flight surgeon"),
            "text": _line(message), "kind": message.kind, "sent_at": sent["sent_at"],
            "arrived_at": sent["deliver_at"] if sent["status"] == "delivered" else None, "status": sent["status"]}


@bp.get("/alerts/<alert_id>/thread")
def alert_thread(alert_id):
    """Everything the ship sent about one alert, and everything from Earth that has arrived. Oldest first."""
    alert, now = alert_or_404(alert_id), utcnow()
    rows = [m for m in LinkMessage.query.order_by(LinkMessage.created_at, LinkMessage.id)
            if m.payload.get("alert_id") == alert.id
            and (m.direction == "to_earth" or (m.deliver_at is not None and m.deliver_at <= now))]
    return jsonify(alert_id=alert_code(alert), messages=[thread_message(m, alert, now) for m in rows])


def reminder_dict(reminder):
    return {"id": f"R{reminder.id}", "crew_id": db.session.get(Crew, reminder.crew_id).code,
            "text": reminder.text, "due_at": iso(reminder.due_at), "done_at": iso(reminder.done_at)}


@bp.post("/alerts/<alert_id>/accept-plan")
def accept_plan(alert_id):
    """The crew accepts the flight surgeon's reply. For the demo the plan is always the same four checks."""
    alert = alert_or_404(alert_id)
    if stage(alert, timeline(alert)) != "replied":
        return jsonify(alert=alert_dict(alert), reminders=[])      # a double click changes nothing
    now = utcnow()
    alert.cleared_at, alert.cleared_by = now, person(body().get("by"))
    alert.cleared_note = "Accepted the flight surgeon's plan"
    made = [Reminder(crew_id=alert.crew_id, alert_id=alert.id, text="Take temperature",
                     due_at=now + timedelta(hours=4 * n)) for n in (1, 2, 3, 4)]
    db.session.add_all(made)
    db.session.commit()
    tell_earth(alert, {"event": "resolved", "by": alert.cleared_by, "note": alert.cleared_note})
    return jsonify(alert=alert_dict(alert), reminders=[reminder_dict(r) for r in made])


@bp.get("/reminders")
def reminders():
    query = Reminder.query
    if request.args.get("crew"):
        query = query.filter_by(crew_id=crew_or_404(request.args["crew"]).id)
    if request.args.get("open") == "1":
        query = query.filter(Reminder.done_at.is_(None))
    return jsonify([reminder_dict(r) for r in query.order_by(Reminder.due_at, Reminder.id)])


@bp.post("/reminders/<ref>/done")
def reminder_done(ref):
    number = row_number(ref, "R")
    reminder = db.session.get(Reminder, number) if number is not None else None
    if reminder is None:
        return jsonify(error="not found"), 404
    if reminder.done_at is None:
        reminder.done_at = utcnow()
        db.session.commit()
    return jsonify(reminder_dict(reminder))
