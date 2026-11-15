"""The console's side of the ship: each person's day against their own band, the trend chart
and the printed rules. Shapes follow the frontend owner's API contract of 14 November."""
import functools
from datetime import timedelta

from flask import jsonify, request

from base_station import scoring, usual
from base_station.morning import when
from base_station.routes import _latest, _level, bp, crew_or_404
from common import dataset
from common.models import Checkin, Crew, iso, utcnow

COLUMN = {"hr_rest": "hr_rest_bpm", "bp_sys": "bp_sys_mmhg", "bp_dia": "bp_dia_mmhg", "spo2": "spo2_pct",
          "temp_c": "core_temp_c", "resp": "resp_rpm", "sleep_h": "sleep_h", "mood": "mood", "pvt_ms": "pvt_ms",
          "dose_mSv_day": "dose_msv_day"}                 # console metric -> column in daily_summary.csv
LABEL = {"hr_rest": "resting heart rate", "bp_sys": "systolic blood pressure", "bp_dia": "diastolic blood pressure",
         "spo2": "blood oxygen", "temp_c": "temperature", "resp": "breathing rate", "sleep_h": "sleep",
         "mood": "mood", "pvt_ms": "reaction time", "dose_mSv_day": "radiation dose"}
TYPED = ("mood", "pvt_ms", "bp_sys", "bp_dia")            # what a check-in gives; the rest comes from the suit


def bad(message, field):
    return jsonify(error=message, field=field), 400


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
