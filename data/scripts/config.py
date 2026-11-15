"""Every fixed choice behind the generated data, in one place.

Nothing here is random. The seeded scripts read these constants, so changing a
number here and rerunning build_all.py is the only way to change the data.
"""
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

UTC = timezone.utc
REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "data"
RAW_PPG = DATA / "ppg_dalia"
RAW_EDA = DATA / "eda"
REFERENCE_IN = DATA / "reference"
OUT = DATA / "processed"
OUT_REF = OUT / "reference"
OUT_CLEAN = OUT / "clean"
OUT_ANOM = OUT / "anomalous"
OUT_TRUTH = OUT / "ground_truth"
OUT_REPORTS = OUT / "reports"

DEFAULT_SEED = 2026

# ---- mission calendar -------------------------------------------------------
MISSION_ID = "LT-2026"
PLATFORM = "ISS"
LAUNCH = date(2026, 6, 10)                      # mission day 1, so 2026-11-14 is day 158
START = datetime(2026, 10, 16, tzinfo=UTC)      # mission day 129, start of minute data
DEMO_NOW = datetime(2026, 11, 14, 6, 30, tzinfo=UTC)
PACKETS_FROM = datetime(2026, 11, 13, tzinfo=UTC)  # mission days 157-158


def mission_day(d):
    if isinstance(d, datetime):
        d = d.date()
    return (d - LAUNCH).days + 1


def md_date(md):
    return LAUNCH + timedelta(days=md - 1)


def at(md, hh, mm=0, ss=0):
    """UTC datetime on a mission day."""
    d = md_date(md)
    return datetime(d.year, d.month, d.day, hh, mm, ss, tzinfo=UTC)


def iso(dt):
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ") if dt else ""


def iso_ms(dt):
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}Z"


def parse_ts(text):
    if not text:
        return None
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


# ---- crew -------------------------------------------------------------------
# C1's numbers are copied from the frontend contract (backend-api-contract.md).
# C2-C4 are a draft until crew-seed.json from the frontend repo is in hand.
CREW = [
    {"crew_id": "C1", "backend_id": 1, "name": "Okafor", "role": "Commander", "suit_id": "LT-01",
     "home_habitat_id": "H1", "is_cmo": False, "source": "backend-api-contract.md"},
    {"crew_id": "C2", "backend_id": 2, "name": "Linda Rodenburg", "role": "Flight Engineer", "suit_id": "LT-02",
     "home_habitat_id": "H1", "is_cmo": True, "source": "draft"},
    {"crew_id": "C3", "backend_id": 3, "name": "Sato", "role": "Flight Engineer", "suit_id": "LT-03",
     "home_habitat_id": "H2", "is_cmo": False, "source": "draft"},
    {"crew_id": "C4", "backend_id": 4, "name": "Rebecca Qi", "role": "Mission Specialist", "suit_id": "LT-04",
     "home_habitat_id": "H2", "is_cmo": False, "source": "draft"},
]
CREW_IDS = [c["crew_id"] for c in CREW]
CREW_BY_ID = {c["crew_id"]: c for c in CREW}

BASELINES = {
    "C1": {"hr_rest": (52, 64), "bp_sys": (108, 122), "bp_dia": (66, 78), "spo2": (96, 99),
           "temp_c": (36.3, 36.9), "resp": (12, 16), "sleep_h": (6.8, 7.6), "pvt_ms": 265,
           "vo2max_ml_min_kg": 44.0},
    "C2": {"hr_rest": (58, 70), "bp_sys": (112, 128), "bp_dia": (70, 82), "spo2": (96, 99),
           "temp_c": (36.4, 37.0), "resp": (13, 17), "sleep_h": (6.5, 7.3), "pvt_ms": 280,
           "vo2max_ml_min_kg": 40.0},
    "C3": {"hr_rest": (60, 72), "bp_sys": (104, 118), "bp_dia": (64, 76), "spo2": (96, 99),
           "temp_c": (36.2, 36.8), "resp": (12, 16), "sleep_h": (7.0, 7.8), "pvt_ms": 250,
           "vo2max_ml_min_kg": 42.0},
    "C4": {"hr_rest": (46, 56), "bp_sys": (110, 124), "bp_dia": (68, 80), "spo2": (96, 99),
           "temp_c": (36.4, 37.0), "resp": (10, 14), "sleep_h": (6.6, 7.4), "pvt_ms": 270,
           "vo2max_ml_min_kg": 52.0},
}
BASELINE_SET_ON = date(2026, 5, 27)  # pre-flight baseline data collection, L-14 days

# Generator-only physiology (not baselines shown on screen).
HR_MAX = {"C1": 182, "C2": 178, "C3": 184, "C4": 188}
SKIN_OFFSET = {"C1": 0.0, "C2": -0.3, "C3": 0.2, "C4": -0.1}
SUIT_CLOCK_OFFSET_S = {"C1": 0.21, "C2": -0.34, "C3": 0.08, "C4": 0.47}
SUIT_CLOCK_DRIFT_PPM = {"C1": 6.0, "C2": -11.0, "C3": 14.0, "C4": -3.0}
PPG_TEXTURE_SUBJECT = {"C1": "S2", "C2": "S3", "C3": "S7", "C4": "S10"}  # safe calm segments (ppg_dalia README)

# Exercise slots (start hh:mm, kind). ISS crews exercise about 2.5 h a day on ARED and CEVIS/T2.
EXERCISE = {
    "C1": [((8, 0), "exercise_ared"), ((15, 0), "exercise_cevis")],
    "C2": [((9, 30), "exercise_ared"), ((16, 30), "exercise_cevis")],
    "C3": [((10, 30), "exercise_cevis"), ((17, 0), "exercise_ared")],
    "C4": [((7, 45), "exercise_cevis"), ((13, 30), "exercise_ared")],
}
# Per-day overrides: (crew, mission day) -> list of slots, or [] for no exercise.
EXERCISE_OVERRIDE = {
    ("C2", 146): [],                                                     # fever day: no exercise
    ("C2", 152): [((8, 30), "exercise_cevis"), ((16, 30), "exercise_ared")],  # NC01 just before AN03
    ("C3", 148): [((14, 0), "exercise_cevis"), ((17, 0), "exercise_ared")],   # stays in H2 for AN06
    ("C3", 151): [((11, 0), "exercise_cevis"), ((17, 0), "exercise_ared")],   # SF01 at 10:00 is at work
    ("C3", 152): [((10, 30), "exercise_cevis"), ((17, 0), "exercise_ared")],  # SF04 at 10:45 is mid-session
}
EXERCISE_MIN = 70  # length of an override session; default sessions are 60-75 min
# Crew kept in a habitat for a time range regardless of schedule: (crew, md) -> (start, end, habitat)
HABITAT_HOLD = {
    ("C3", 148): ((9, 0), (13, 0), "H2"),
    ("C4", 148): ((9, 0), (13, 0), "H2"),
}

HABITATS = [
    {"habitat_id": "H1", "name": "Hab A (galley, exercise)", "cabin_data_source": "eda_rr1_replay"},
    {"habitat_id": "H2", "name": "Hab B (labs, sleep stations)", "cabin_data_source": "sim"},
]
CABIN_H2_OFFSET_DAYS = 7

# Radiation: simulated mSv anchored to the contract (0.51 mSv today, 81.0 mSv by day 158).
DOSE_MEAN_MSV_DAY = 0.51
DOSE_MISSION_AT_DEMO = 81.0

ACTIVITY_LABELS = ["sleep", "awake_in_bed", "post_sleep", "meal", "work", "exercise_ared",
                   "exercise_cevis", "pre_sleep"]

# ---- link to Earth ----------------------------------------------------------
# ISS platform, with a Mars-distance link (the analogue the backend dial plays).
# One compressed solar-conjunction blackout; a real one lasts about two weeks.
LINK_WINDOWS = [
    ("W1", START, at(156, 18), "mars", True, "Mars-distance link, Horizons light time for the day"),
    ("W2", at(156, 18), at(157, 12), "sun", False,
     "Solar conjunction blackout, compressed to 18 h for the demo (a real one is about 2 weeks)"),
    ("W3", at(157, 12), DEMO_NOW, "mars", True, "Link back; queue flushes SOS first"),
]

# ---- anomalies (ground truth) -----------------------------------------------
# Times are UTC. Mission days: 140=10-27, 146=11-02, 148=11-04, 149=11-05, 150=11-06,
# 151=11-07, 152=11-08, 153=11-09, 154=11-10, 155=11-11, 156=11-12, 157=11-13, 158=11-14.
ANOMALIES = [
    dict(id="AN01", crew_member="C1", habitat_id="", type="hr_rest_3day", kind="medical",
         start=at(155, 21, 30), end=DEMO_NOW, severity="moderate", expected_alert="ALERT",
         expected_backend_level="none", metrics="hr_rest|resp|temp_c|sleep_h|mood|pvt_ms",
         is_medical=True,
         notes="Resting HR 80/82/84 on days 156-158 (band 52-64), short sleep, headache, slow PVT. "
               "The frontend's A1 story. NEWS2 calls 84 bpm nominal."),
    dict(id="AN02", crew_member="C3", habitat_id="", type="spo2_drop", kind="medical",
         start=at(150, 14), end=at(150, 15, 30), severity="high", expected_alert="ALERT",
         expected_backend_level="emergency", metrics="spo2|hr|resp", is_medical=True,
         notes="Gradual hypoxia: SpO2 from about 97 to 88-89 over 60 min at rest, HR +15, resp +6, recovers by 15:30."),
    dict(id="AN03", crew_member="C2", habitat_id="", type="tachycardia_rest", kind="medical",
         start=at(152, 10, 40), end=at(152, 11), severity="high", expected_alert="ALERT",
         expected_backend_level="warning", metrics="hr", is_medical=True,
         notes="HR 128-138 with activity < 0.08 g at a desk, abrupt onset and offset. "
               "C2 exercised 08:30-09:40 the same morning (NC01)."),
    dict(id="AN04", crew_member="C4", habitat_id="", type="bradycardia_sleep", kind="medical",
         start=at(154, 2), end=at(154, 2, 40), severity="high", expected_alert="ALERT",
         expected_backend_level="emergency", metrics="hr", is_medical=True,
         notes="Sleeping HR 36-38 against C4's normal sleeping 44-48."),
    dict(id="AN05", crew_member="C2", habitat_id="", type="fever", kind="medical",
         start=at(146, 8), end=at(146, 23), severity="moderate", expected_alert="ALERT",
         expected_backend_level="not_ingested", metrics="temp_c|skin_temp|hr|resp", is_medical=True,
         notes="Core temp +1.8 C over 6 h (peaks about 39.0 C on the midday high), plateau to 18:00, back by 23:00. Skin +1.2 C, "
               "HR +10 per C, resp +3. Backend has no temperature rule."),
    dict(id="AN06", crew_member="", habitat_id="H2", type="co2_buildup", kind="environmental",
         start=at(148, 9), end=at(148, 13), severity="moderate", expected_alert="ALERT",
         expected_backend_level="not_ingested", metrics="co2_mmHg|resp|hr", is_medical=False,
         notes="Scrubber fault in H2: CO2 to 5.2 mmHg (ALERT over 4.5 from about 10:30). "
               "C3 and C4 are inside: resp +4, HR +5, headache at next check-in."),
    dict(id="AN07", crew_member="", habitat_id="", type="sep_event", kind="environmental",
         start=at(140, 13, 20), end=at(141, 10), severity="high", expected_alert="ALERT",
         expected_backend_level="not_ingested", metrics="dose_mSv_day|space_weather", is_medical=False,
         notes="Large solar particle event, DONKI-style record. Day dose 2.4 mSv (ALERT over 2)."),
    dict(id="AN08", crew_member="", habitat_id="", type="sep_event", kind="environmental",
         start=at(158, 5, 58), end=at(158, 23, 58), severity="low", expected_alert="WATCH",
         expected_backend_level="not_ingested", metrics="space_weather", is_medical=False,
         notes="SEP in progress on the demo morning; shelter advisory, dose stays 0.51 mSv."),
    dict(id="AN09", crew_member="C4", habitat_id="", type="sos_glove_tap", kind="medical",
         start=at(155, 16, 20), end=at(155, 16, 35), severity="critical", expected_alert="SOS",
         expected_backend_level="emergency", metrics="sos|hr|activity", is_medical=True,
         notes="Hand trapped during maintenance: triple glove tap at 16:20:07, HR +30, activity burst."),
    dict(id="AN10", crew_member="C3", habitat_id="", type="spo2_drop", kind="medical",
         start=at(157, 3), end=at(157, 4, 30), severity="critical", expected_alert="ALERT",
         expected_backend_level="emergency", metrics="spo2|hr", is_medical=True,
         notes="SpO2 97 to 88 in sleep during the conjunction blackout (link down). "
               "The SOS report must queue and flush first when the link returns at 12:00."),
    dict(id="SF01", crew_member="C3", habitat_id="", type="dropout", kind="sensor_fault",
         start=at(151, 10), end=at(151, 10, 25), severity="low", expected_alert="RECHECK",
         expected_backend_level="advisory", metrics="hr|resp", is_medical=False,
         notes="Chest band and ECG off the skin: HR and resp null, signal quality 0."),
    dict(id="SF02", crew_member="C2", habitat_id="", type="flatline", kind="sensor_fault",
         start=at(149, 13), end=at(149, 16), severity="low", expected_alert="RECHECK",
         expected_backend_level="none", metrics="spo2", is_medical=False,
         notes="Pulse oximeter stuck at exactly 97.0 for 3 h while reporting good quality."),
    dict(id="SF03", crew_member="C1", habitat_id="", type="spike", kind="sensor_fault",
         start=at(153, 3), end=at(153, 21), severity="low", expected_alert="none",
         expected_backend_level="none", metrics="hr|skin_temp|spo2|temp_c", is_medical=False,
         notes="Six single-sample impossible values (HR 250, HR 0, skin 45 C, SpO2 40, HR 251, core 43 C)."),
    dict(id="SF04", crew_member="C3", habitat_id="", type="motion_artifact", kind="sensor_fault",
         start=at(152, 10, 45), end=at(152, 10, 48), severity="low", expected_alert="RECHECK",
         expected_backend_level="advisory", metrics="hr", is_medical=False,
         notes="Signal quality 0.45 for 3 min during exercise, HR jumps of up to +40."),
    dict(id="NC01", crew_member="", habitat_id="", type="exercise_control", kind="negative_control",
         start=START, end=DEMO_NOW, severity="low", expected_alert="none",
         expected_backend_level="warning", metrics="hr|bp_sys", is_medical=False,
         notes="Every exercise session, all crew. Normal physiology; a correct system stays quiet."),
    dict(id="NC02", crew_member="", habitat_id="", type="sleep_low_hr_control", kind="negative_control",
         start=START, end=DEMO_NOW, severity="low", expected_alert="none",
         expected_backend_level="caution", metrics="hr", is_medical=False,
         notes="Normal sleeping HR, all crew. C4 (athletic) sleeps at 44-48, under NEWS2's 50."),
    dict(id="NC03", crew_member="", habitat_id="", type="microgravity_drift", kind="negative_control",
         start=START, end=DEMO_NOW, severity="low", expected_alert="none",
         expected_backend_level="none", metrics="hr_rest|bp_sys|temp_c|sleep_h", is_medical=False,
         notes="Slow adaptation drift (HR -3, BP -4, core +0.3 C, sleep -0.3 h), settled by day 60."),
]

# Single-sample spikes for SF03 (minute data, crew C1).
SF03_SPIKES = [
    (at(153, 3, 14), "hr_bpm", 250.0), (at(153, 8, 41), "hr_bpm", 0.0),
    (at(153, 11, 2), "skin_temp_c", 45.0), (at(153, 14, 27), "spo2_pct", 40.0),
    (at(153, 17, 55), "hr_bpm", 251.0), (at(153, 20, 13), "core_temp_c", 43.0),
]

# AN01 targets on the morning-rest window, matching the contract's demo crew card.
AN01_TARGETS = {
    156: {"hr_bpm": 80, "resp_rpm": 16},
    157: {"hr_bpm": 82, "resp_rpm": 16},
    158: {"hr_bpm": 84, "resp_rpm": 17, "core_temp_c": 37.2, "spo2_pct": 97},
}
AN01_SLEEP_H = {156: 5.6, 157: 5.4, 158: 5.1}

# ---- 1 Hz windows (same in both builds) ---------------------------------------
HZ_WINDOWS = [
    ("C1", at(158, 4, 30), DEMO_NOW), ("C2", at(158, 4, 30), DEMO_NOW),
    ("C3", at(158, 4, 30), DEMO_NOW), ("C4", at(158, 4, 30), DEMO_NOW),
    ("C3", at(150, 13, 40), at(150, 15, 50)),   # AN02
    ("C2", at(152, 10, 20), at(152, 11, 20)),   # AN03
    ("C4", at(154, 1, 40), at(154, 3, 0)),      # AN04
    ("C4", at(155, 16, 0), at(155, 16, 50)),    # AN09
    ("C3", at(157, 2, 40), at(157, 4, 40)),     # AN10
    ("C3", at(151, 9, 50), at(151, 10, 35)),    # SF01
]

SYMPTOMS = ["headache", "short sleep", "congestion", "nausea", "blurred vision", "back pain"]

FLIGHT_SURGEON = "Dr. Adeyemi"


def near_spike(t, minutes=2):
    """SF03 is six single samples, not a window: match only events close to one of them."""
    return any(abs((t - st).total_seconds()) <= minutes * 60 for st, _, _ in SF03_SPIKES)
