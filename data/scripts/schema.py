"""The data model as code. validate.py checks every output CSV against it, and
data/README.md documents the same tables. One entry per CSV = one future table.

Column spec: (name, type, required, unit, min, max)
types: text, int, float, bool, ts (ISO 8601 UTC with Z), date, list (| separated)
"""

T, I, F, B, TS, D, L = "text", "int", "float", "bool", "ts", "date", "list"


def col(name, typ, required=True, unit="", lo=None, hi=None):
    return {"name": name, "type": typ, "required": required, "unit": unit, "min": lo, "max": hi}


PROV = [col("simulated", B), col("provenance", T)]

TABLES = {
    # ---------------- reference (processed/reference) ----------------
    "mission": {"folder": "reference", "pk": ["mission_id"], "fk": {}, "cols": [
        col("mission_id", T), col("launch_date", D), col("platform", T), col("demo_now", TS),
        col("link_model", T), *PROV]},
    "crew": {"folder": "reference", "pk": ["crew_id"], "fk": {"home_habitat_id": ("habitats", "habitat_id")}, "cols": [
        col("crew_id", T), col("backend_id", I, lo=1), col("name", T), col("role", T), col("suit_id", T),
        col("home_habitat_id", T), col("is_cmo", B), col("source", T)]},
    "habitats": {"folder": "reference", "pk": ["habitat_id"], "fk": {}, "cols": [
        col("habitat_id", T), col("name", T), col("cabin_data_source", T)]},
    "metrics": {"folder": "reference", "pk": ["metric"], "fk": {}, "cols": [
        col("metric", T), col("unit", T), col("api_name", T), col("backend_name", T, False),
        col("min_possible", F), col("max_possible", F), col("description", T)]},
    "channels": {"folder": "reference", "pk": ["source"], "fk": {}, "cols": [
        col("source", T), col("device_model", T), col("metrics", L), col("native_rate", T), col("note", T, False)]},
    "baselines": {"folder": "reference", "pk": ["crew_id", "metric"], "fk": {"crew_id": ("crew", "crew_id")}, "cols": [
        col("crew_id", T), col("metric", T), col("low", F, False), col("high", F, False),
        col("point", F, False), col("unit", T), col("set_on", D), col("source", T)]},
    "thresholds": {"folder": "reference", "pk": ["metric"], "fk": {}, "cols": [
        col("metric", T), col("unit", T), col("watch_rule", T), col("alert_rule", T),
        col("watch_param", F, False), col("alert_param", F, False), col("needs_symptom", B),
        col("consecutive_days", I, False), col("source", T), col("source_status", T)]},
    "link_windows": {"folder": "reference", "pk": ["window_id"], "fk": {}, "cols": [
        col("window_id", T), col("start", TS), col("end", TS), col("stop", T), col("link_up", B),
        col("one_way_delay_s", F, False, "s", 0, 1500), col("delay_source", T), col("note", T)]},
    # ---------------- time series (clean/ and anomalous/) ----------------
    "vitals_1min": {"folder": "series", "pk": ["sample_id"], "fk": {"crew_id": ("crew", "crew_id"),
                                                                     "habitat_id": ("habitats", "habitat_id")}, "cols": [
        col("sample_id", T), col("crew_id", T), col("sensor_ts", TS), col("gateway_ts", TS),
        col("mission_day", I, lo=1), col("habitat_id", T), col("activity_label", T),
        col("hr_bpm", F, False, "bpm", 25, 230), col("resp_rpm", F, False, "/min", 4, 60),
        col("spo2_pct", F, False, "%", 50, 100), col("skin_temp_c", F, False, "C", 25, 42),
        col("core_temp_c", F, False, "C", 34, 42.5), col("activity_g", F, False, "g", 0, 4),
        col("bp_sys_est_mmhg", F, False, "mmHg", 60, 230), col("signal_quality", F, True, "", 0, 1),
        col("signal_ok", B), *PROV]},
    "vitals_1hz_demo": {"folder": "series", "pk": ["sample_id"], "fk": {"crew_id": ("crew", "crew_id"),
                                                                         "habitat_id": ("habitats", "habitat_id")},
                        "same_as": "vitals_1min"},
    "cabin_env": {"folder": "series", "pk": ["habitat_id", "ts"], "fk": {"habitat_id": ("habitats", "habitat_id")}, "cols": [
        col("habitat_id", T), col("ts", TS), col("mission_day", I), col("co2_ppm", F, True, "ppm", 200, 12000),
        col("co2_mmhg", F, True, "mmHg", 0.1, 10), col("ppo2_mmhg", F, True, "mmHg", 120, 200),
        col("pressure_kpa", F, True, "kPa", 95, 105), col("temp_c", F, True, "C", 15, 32),
        col("rh_pct", F, True, "%", 10, 90), col("orig_ts", TS, False), col("real_fields", L, False), *PROV]},
    "radiation_daily": {"folder": "series", "pk": ["date"], "fk": {}, "cols": [
        col("date", D), col("mission_day", I), col("gcr_mgy", F, True, "mGy/day", 0, 5),
        col("saa_mgy", F, True, "mGy/day", 0, 5), col("sep_mgy", F, True, "mGy/day", 0, 10),
        col("total_mgy", F, True, "mGy/day", 0, 10),
        col("dose_msv_day", F, True, "mSv/day", 0, 50), col("dose_msv_mission", F, True, "mSv", 0, 1000),
        col("orig_date", D, False), *PROV]},
    "daily_summary": {"folder": "series", "pk": ["crew_id", "date"], "fk": {"crew_id": ("crew", "crew_id")}, "cols": [
        col("crew_id", T), col("date", D), col("mission_day", I, lo=1),
        col("hr_rest_bpm", F, False, "bpm", 30, 150), col("bp_sys_mmhg", F, False, "mmHg", 70, 200),
        col("bp_dia_mmhg", F, False, "mmHg", 40, 130), col("spo2_pct", F, False, "%", 80, 100),
        col("core_temp_c", F, False, "C", 35, 41), col("skin_temp_c", F, False, "C", 28, 38),
        col("resp_rpm", F, False, "/min", 6, 40), col("sleep_h", F, False, "h", 0, 24),
        col("sleep_h_suit", F, False, "h", 0, 24), col("mood", I, False, "", 1, 5),
        col("pvt_ms", I, False, "ms", 100, 3000), col("dose_msv_day", F, False, "mSv/day", 0, 50),
        col("symptoms", L, False), col("resolution", T), *PROV]},
    "packets": {"folder": "series", "pk": ["packet_id"], "fk": {"crew_id": ("crew", "crew_id"),
                                                                 "source": ("channels", "source"),
                                                                 "sample_id": ("vitals_1min", "sample_id")}, "cols": [
        col("packet_id", T), col("crew_id", T), col("suit_id", T), col("ts", TS), col("mission_day", I),
        col("location", T), col("habitat_id", T), col("source", T), col("metric", T), col("value", F, False),
        col("unit", T), col("signal_quality", F, True, "", 0, 1), col("window_s", I),
        col("sent_to_ground", B), col("ack", T, False), col("sample_id", T), *PROV]},
    # ---------------- events (clean/ and anomalous/) ----------------
    "checkins": {"folder": "series", "pk": ["checkin_id"], "fk": {"crew_id": ("crew", "crew_id")}, "cols": [
        col("checkin_id", T), col("crew_id", T), col("date", D), col("completed_at", TS),
        col("mood", I, True, "", 1, 5), col("sleep_h", F, True, "h", 0, 24), col("pvt_ms", I, True, "ms", 100, 3000),
        col("symptoms", L, False), col("note", T, False), col("first_today", B),
        col("cuff_bp_sys_mmhg", F, False, "mmHg", 70, 200), col("cuff_bp_dia_mmhg", F, False, "mmHg", 40, 130),
        col("live_demo", B), *PROV]},
    "sos_events": {"folder": "series", "pk": ["event_id"], "fk": {"crew_id": ("crew", "crew_id")}, "cols": [
        col("event_id", T), col("crew_id", T), col("suit_id", T), col("sensor_ts", TS), col("gateway_ts", TS),
        col("trigger", T), col("anomaly_id", T, False), *PROV]},
    "space_weather_events": {"folder": "series", "pk": ["sep_id"], "fk": {}, "cols": [
        col("sep_id", T), col("event_time", TS), col("end_time", TS), col("instruments", L),
        col("linked_events", L, False), col("link", T), col("state", T), col("headline", T),
        col("advisory", T), col("anomaly_id", T, False), *PROV]},
    "alerts_seed": {"folder": "series", "pk": ["alert_id"], "fk": {"crew_id": ("crew", "crew_id")}, "cols": [
        col("alert_id", T), col("crew_id", T), col("metric", T), col("value", F, False), col("unit", T, False),
        col("state", T), col("level", T), col("stage", T), col("reason", T), col("rule", T), col("source", T),
        col("nasa_risk", T, False), col("symptoms", L, False), col("steps_done", L, False), col("raised_at", TS),
        col("acknowledged_at", TS, False), col("sent_at", TS, False), col("earth_at", TS, False),
        col("reply_at", TS, False), col("resolved_at", TS, False), col("anomaly_id", T, False), *PROV]},
    "messages": {"folder": "series", "pk": ["message_id"], "fk": {}, "cols": [
        col("message_id", T), col("alert_id", T, False), col("direction", T), col("kind", T), col("from_side", T),
        col("author", T), col("text", T), col("priority", I, True, "", 0, 9), col("created_at", TS),
        col("sent_at", TS, False), col("delay_s", F, False, "s", 0, 1500), col("deliver_at", TS, False),
        col("status_at_demo_now", T), col("in_reply_to", T, False), *PROV]},
    "reminders": {"folder": "series", "pk": ["reminder_id"], "fk": {"crew_id": ("crew", "crew_id")}, "cols": [
        col("reminder_id", T), col("crew_id", T), col("alert_id", T, False), col("text", T), col("due_at", TS),
        col("done_at", TS, False), *PROV]},
    # ---------------- ground truth ----------------
    "anomalies": {"folder": "ground_truth", "pk": ["id"], "fk": {}, "cols": [
        col("id", T), col("crew_member", T, False), col("habitat_id", T, False), col("type", T), col("kind", T),
        col("start", TS), col("end", TS), col("severity", T), col("expected_alert", T),
        col("expected_backend_level", T), col("metrics", L), col("is_medical", B),
        col("link_state_at_start", T), col("notes", T)]},
}

for spec in TABLES.values():
    if "same_as" in spec:
        spec["cols"] = TABLES[spec["same_as"]]["cols"]


def columns(table):
    return [c["name"] for c in TABLES[table]["cols"]]


SERIES_TABLES = [t for t, s in TABLES.items() if s["folder"] == "series"]
REFERENCE_TABLES = [t for t, s in TABLES.items() if s["folder"] == "reference"]
