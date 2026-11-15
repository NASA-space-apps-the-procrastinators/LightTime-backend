"""The health log: the suits' minute stream as packets, newest first.

The rows are the generated month (anomalous/vitals_1min.csv), so every answer says simulated.
A packet is not a reading: LIGHTTIME never judges one. Only the two limits the console's rules
apply to a single value are checked here: blood oxygen under 94 % and core temperature over 38.0.
The band rules are for a morning's resting value, and a minute during exercise is not that."""
from datetime import timedelta

from flask import jsonify, request

from base_station import access, scoring
from base_station.console import bands
from base_station.morning import when
from base_station.routes import bad, bp, find_crew
from common import dataset
from common.models import LinkMessage, db, utcnow

RECHECK_BELOW = 0.6       # the console's packet-schema.json: under this a packet is shown as RECHECK
WINDOW_MINUTES = 60
STATES = ("OK", "WATCH", "ALERT", "RECHECK")
# column in vitals_1min.csv, the console's name for the sensor, the packet's metric, its unit,
# and the console rule whose hard limit holds for one value (None: logged, not judged)
STREAMS = [
    ("hr_bpm", "ecg", "hr", "bpm", None),
    ("resp_rpm", "chest_band", "resp", "/min", None),
    ("spo2_pct", "ppg", "spo2", "%", "spo2"),
    ("core_temp_c", "thermistor", "temp_c", "°C", "temp_c"),
    ("skin_temp_c", "thermistor", "skin_temp_c", "°C", None),
    ("activity_g", "imu", "activity_g", "g", None),
]


def _rows(now):
    """The minute rows at or before the ship's clock, oldest first."""
    stamp = now.isoformat()[:19]      # whole seconds: as text, "06:29:00Z" would sort after "06:29:00.3Z"
    return [row for row in dataset.last_minutes() if row["sensor_ts"][:19] <= stamp]


def packets_of(row, own, suit_id):
    """One minute row from a suit as packets: one for each sensor stream that has a value."""
    quality = dataset.num(row["signal_quality"]) or 0.0      # no figure at all is treated as unreadable
    for column, source, metric, unit, rule in STREAMS:
        value = dataset.num(row[column])
        if value is None:
            continue
        packet = {"crew_id": row["crew_id"], "suit_id": suit_id, "ts": row["sensor_ts"],
                  "mission_day": int(row["mission_day"]), "location": dataset.mission()["platform"],
                  "source": source, "metric": metric, "value": value, "unit": unit,
                  "signal_quality": quality, "window_s": 60,
                  "sent_to_ground": False,     # the ship sends reports and summaries, never a raw packet
                  "ack": None}
        if quality < RECHECK_BELOW:
            packet["state"] = "RECHECK"
        elif rule:
            packet.update(baseline=own[rule], rule=scoring.rule_text()[rule]["alert"],
                          state="ALERT" if scoring.hard_alert(rule, value) else "OK")
        yield packet


def sent_today():
    """How many messages the ship has sent toward Earth on the ship's date."""
    day = utcnow().date()
    sent = db.session.query(LinkMessage.sent_at).filter(LinkMessage.direction == "to_earth",
                                                        LinkMessage.sent_at.isnot(None))
    return sum(1 for (at,) in sent if at.date() == day)


@bp.get("/packets")
def packets():
    """The health log: the suits' minute stream as packets, newest first; ?crew=, ?state=, ?limit= up to 1000."""
    crew, state = request.args.get("crew"), request.args.get("state")
    member = find_crew(crew) if crew else None
    if crew and member is None:
        return bad("unknown crew", "crew")
    if state and state not in STATES:
        return bad("state is one of " + ", ".join(STATES), "state")
    limit = min(max(request.args.get("limit", 200, type=int), 1), 1000)
    suits = {row["crew_id"]: row["suit_id"] for row in dataset.table("reference/crew")}
    own, out = {}, []
    for row in reversed(_rows(utcnow())):
        code = row["crew_id"]
        if (member is not None and code != member.code) or not access.may_read(code):
            continue
        if code not in own:
            own[code] = bands(code)
        out += [packet for packet in packets_of(row, own[code], suits[code])
                if not state or packet.get("state") == state]
        if len(out) >= limit:
            break
    return jsonify(packets=out[:limit], transmitted_to_ground_today=sent_today(), simulated=True)


@bp.get("/stream-health")
def stream_health():
    """The lowest signal quality each sensor reported over the newest hour of packets."""
    rows, lowest = _rows(utcnow()), {}
    if rows:
        since = (when(rows[-1]["sensor_ts"]) - timedelta(minutes=WINDOW_MINUTES)).isoformat()[:19]
        for row in rows:
            if row["sensor_ts"][:19] <= since:
                continue
            quality = dataset.num(row["signal_quality"]) or 0.0
            for column, source, *_ in STREAMS:
                if row[column] != "":
                    lowest[source] = min(lowest.get(source, 1.0), quality)
    return jsonify(sensors=[{"source": source, "lowest_signal_quality": quality,
                             "state": "RECHECK" if quality < RECHECK_BELOW else "OK"}
                            for source, quality in sorted(lowest.items())],
                   window_minutes=WINDOW_MINUTES, simulated=True)
