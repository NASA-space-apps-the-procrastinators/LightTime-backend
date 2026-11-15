# LIGHT-TIME backend: project notes

Written 14 November 2026 (Phase 1 of the data task, read-only scan). Scope: what the repo contains today, how data moves through it, and what the dummy data can and cannot support. No code or data was changed.

## 0. Four things that differ from the task brief

The brief describes a system larger than the one in the repo. These four differences shape the data plan.

1. **No MQTT, no time-series store, no audit log, no personal baselines.** The base station is one Flask app. Data comes in through `POST /api/base/readings` as JSON, or from a scripted thread (`base_station/scenario.py`) that calls the same `ingest()` function. Personal baselines are listed as "Sunday work" in the spec.
2. **There is a database layer, but it isn't deployed.** `common/models.py` defines five SQLAlchemy tables. The app uses `DATABASE_URL` (Postgres 16 has been tested) and falls back to `sqlite:///lighttime.db`. Nothing is hosted.
3. **There is no CSV of crew dummy data.** The CSVs in the repo are real, de-identified research data from PPG-DaLiA: 15 volunteers on Earth, wrist heart rate and skin temperature. The cabin data is JSON from NASA OSDR EDA. The only "dummy crew" is three hard-coded tuples in `scenario.py`. No code reads any file in `data/`. The one exception is `data/ppg_dalia/rule_check.py`, which is a stand-alone analysis.
4. **Some of the frontend's files are not in this repo.** The contract points to `Light Time/data/thresholds.json`, `crew-seed.json` and `packet-schema.json` in the frontend repo, and none of them is on this machine. They set crew names and roles, baselines for C2 to C4, and the scoring rule text.

## 1. Folder structure and tech stack

| Path | What it is |
| --- | --- |
| `app.py` | Flask app factory. Registers two blueprints, runs `db.create_all()` and `seed()` on startup, port 5000 |
| `common/models.py` | Tables `crew`, `reading`, `alert`, `mission_state`, `link_message`. Seeds the crew David, Damola (cmo) and Youssef, with integer ids 1 to 3 |
| `common/link.py` | The delayed link: a message becomes visible once `deliver_at` has passed |
| `common/lighttime.py` | Earth to Mars one-way light time from JPL Horizons, with a dated fallback |
| `common/modes.py` | The four dial stops and the "who decides" rule |
| `base_station/rules.py` + `limits.json` | Rules engine (NEWS2 bands) |
| `base_station/reports.py` + `procedures.json` | SBAR handoff report, spoken line, checklists |
| `base_station/scenario.py` | Scripted collapse story with three crew, no randomness |
| `base_station/routes.py` | `/api/base/*` (ship) |
| `command_center/routes.py` | `/api/earth/*` (ground). Reads only `link_message` |
| `tests/` | 9 files of pytest tests, using in-memory SQLite and no network |
| `docs/specs/`, `docs/plans/`, `docs/data-sources.md` | Backend spec, data-sources spec (not yet signed off), build plan, list of sources |
| `data/ppg_dalia/` | PPG-DaLiA wrist CSVs, 15 subjects (see section 7) |
| `data/eda/` | NASA OSDR EDA JSON for Rodent Research 1: cabin telemetry, radiation, mission list |
| `data/reference/`, `data/cache/` | Empty (`.gitkeep`; cache is gitignored) |

Stack: Python, Flask 3, Flask-SQLAlchemy 3.1, Flask-Cors, psycopg 3, python-dotenv, requests and pytest. There's no numpy or pandas, and there's no frontend in this repo (it is Next.js in a separate repo and reads `NEXT_PUBLIC_API_URL`).

## 2. How data enters the base station

There are two ways in, and both go through `base_station/routes.py:ingest()`:

- `POST /api/base/readings` with a JSON body. It's one reading per call, and the suit, hardware and check-in screen all use it.
- `scenario.start()` runs a background thread that builds one reading for each crew member every second and calls `ingest()` directly.

`ingest()` reads only these keys. Anything else is dropped without an error:

```json
{ "crew_id": 1, "source": "suit|scenario|typed", "signal_ok": true,
  "heart_rate": 72, "spo2": 98.0, "skin_temp": 33.5, "bp_sys": 118, "bp_dia": 76,
  "glucose": null, "sleep_hours": null, "mood": null }
```

Important for the data work:

- **Sensor timestamps are thrown away.** `Reading.at` is always the server's `utcnow()` when the reading is stored. Nothing on the way in accepts an `at` or `ts` field.
- **No channel for breathing rate, activity or accelerometer, core temperature, CO2, radiation or PVT.** Those values would be dropped.
- `signal_ok` is a boolean. The frontend's `signal_quality` (0 to 1, with RECHECK under 0.6) has nowhere to go.
- Manual SOS is a separate call, `POST /api/base/sos {crew_id}`. Nothing represents a glove tap. A glove tap would have to be sent as this call.

## 3. Packet and message schema in the code

**`reading` table:** `id` int PK, `crew_id` int FK, `at` datetime (server time, naive UTC), `source` str(12), `signal_ok` bool, then the floats `heart_rate`, `spo2`, `skin_temp`, `bp_sys`, `bp_dia`, `glucose`, `sleep_hours` and `mood`.

**`alert` table:** `id`, `crew_id`, `at`, `level` (advisory, caution, warning or emergency), `vital` (a vital name, `signal` or `manual`), `value`, `reason`, `auto`, `nasa_risk`, `steps_done` (JSON list), `acknowledged_at/by`, `cleared_at/by`, `report_id`. There is no `stage`, `symptoms`, `metric` or `rule` column.

**`link_message` table:** `id`, `direction` (`to_earth` or `to_ship`), `kind` (`report`, `update`, `message` or `reply`), `priority` (0 is most urgent; report 0, update 1, message 2, reply 0), `payload` JSON, `created_at`, `sent_at`, `delay_s`, `deliver_at`, `in_reply_to`. Its `to_dict` adds `status` (`queued`, `in_flight` or `delivered`), `eta_s`, `arrives_after_s` and `earliest_reply_after_s`.

**Report payload** (`reports.build`): alert fields, `mode`, `who_decides`, an `sbar` block, `steps`, and `recent`, which holds the last 30 sensed readings with server-time `at` values.

The frontend's **Packet** object (one metric per packet, with `ts`, `suit_id`, `mission_day`, `location`, `source` sensor name, `signal_quality`, `window_s`, `sent_to_ground`, `ack`) does not exist anywhere in the backend.

## 4. Rules engine and baselines

- `limits.json`, labelled "NEWS2, not validated for spaceflight", has bands for only three vitals:
  - `spo2`: 91 or below is emergency, 93 or below warning, 95 or below caution
  - `heart_rate`: 40 or below emergency, 50 or below caution, 51 to 90 nominal, 110 or below caution, 130 or below warning, above 130 emergency
  - `bp_sys`: 90 or below emergency, 100 or below warning, 110 or below caution, 219 or below nominal, above that emergency
- **Sustained check:** a sensed reading must be at a band, or a worse one, for `sustain_n = 5` readings in a row, all with `signal_ok`. Otherwise the level is stepped down. A typed reading needs one reading but is capped at warning.
- **Sensor check:** `signal_ok = false` raises one `signal` advisory ("Check your sensor") and skips every vital rule for that reading. The next clean reading clears it automatically.
- **One open alert per crew member per vital.** A new breach escalates the open alert or does nothing, so no second alert is raised until a person clears the first one.
- **Quiet window:** after a person clears an alert, the same vital stays silent for 60 s (server clock) unless it gets worse. An alert whose `cleared_by` starts with `auto` skips the quiet window.
- Only emergencies send a report to Earth by themselves.
- **No personal baselines.** Every crew member gets the same fixed bands, and there are no rules for skin temperature, sleep, mood, breathing rate, CO2 or dose. `rule_check.py` shows that the NEWS2 heart-rate bands fire on 14 of 15 healthy volunteers during desk work.

## 5. Earth link simulator

- The delay depends on the dial stop: `station` 0.25 s and `moon` 1.3 s are fixed, `mars` comes from JPL Horizons (fallback 660.86 s on 14 Nov), and `sun` means the link is down.
- `real_delay_s`: a delay of 60 s or more plays 60 times faster (`SPEEDUP = 60`), so 11 minutes plays in 11 s.
- **Contact windows are manual, not scheduled.** The link is down only while someone has the dial on `sun`. There is no calendar of windows, no loss of signal while the link is up, and no bandwidth limit.
- During a blackout, a message is stored with `sent_at = NULL`. When the dial moves off `sun`, `flush_queue` sends everything, most urgent first and 0.4 s apart.
- **Who decides:** the crew alone if the link is down, the crew medical officer if the one-way delay is 300 s or more (NEEMO 16), and the flight surgeon otherwise.
- Data age on the Earth side: `created_at`, `sent_at`, `deliver_at` (which serves as received) and `eta_s` are available per message. Two things are missing: when a reply was read, and the sensor time of any reading in the report.

## 6. Missing, broken or inconsistent

**Against the frontend contract** (these are the backend's to fix, not the data task's):

| Issue | Where |
| --- | --- |
| Crew are David, Damola and Youssef with int ids 1 to 3. The frontend expects C1 to C4 (TJ, Rebecca, Kyler, David) as strings | `models.seed`, `<int:crew_id>` routes |
| Field names differ: `heart_rate`, `skin_temp`, `sleep_hours` versus `hr_rest`, `temp_c`, `sleep_h` | `models.VITALS` |
| `level` (NEWS2) versus `state` (OK, WATCH, ALERT, RECHECK, SOS). Alerts have no `stage`, `metric`, `rule` or `symptoms` | `alert_dict` |
| Platform: the frontend says ISS, mission day 158. The backend story is a Mars dial | `modes.py` vs contract |
| Temperature: the backend sends skin temperature (about 33.5 °C). The frontend's `temp_c` band of 36.3 to 36.9 °C and its fever rule (over 38.0 °C) are core temperature | `scenario.NORMAL` vs Crew object |
| Units: EDA CO2 is in ppm and the frontend wants mmHg. EDA radiation is in mGy a day and the frontend wants mSv a day. The data-sources spec says to convert only with a cited factor | `data/eda` vs `/station` |

**Bugs and risks found while reading** (suggested fixes for TJ; I did not change anything):

1. Readings carry no sensor time (`Reading.at` is the server's clock). Replayed or buffered data loses its real time, and Earth cannot tell how old a reading really is.
2. If a 4th crew member posts a reading, the `crew` table has no row for them. On SQLite the reading is stored, but `alert_dict` then crashes on `crew.name` (`None`), and `POST /sos` with an unknown `crew_id` does the same. On Postgres the foreign key rejects the reading.
3. `GET /crew/<id>/readings?limit=abc` gives a 500 error, because the `int()` call is not checked.
4. `POST /dial` with no JSON body gives a 500 error (`None.get`).
5. An open alert hides every later breach of the same vital until a person clears it. In a replay, the first false alarm on a vital would mask every real event after it unless the harness clears alerts.
6. The quiet window and `utcnow()` depend on wall-clock time, so a replay faster than real time doesn't behave like real time.
7. A reading with `signal_ok = false` skips every rule for that reading, even for vitals from a sensor that is still good.
8. For a date it doesn't have, `lighttime` silently uses the 15 November fallback.

**Documentation:**

- `data/README.md` and the data-sources spec say PPG-DaLiA holds "three volunteers", but the folder holds all 15 (S1 to S15). Fixed in `data/README.md` in Phase 2; the spec is TJ's and is unchanged.
- `CLAUDE.md` says to work on `Tj-Backend`, but this work is on `Ore-backend`.
- `CLAUDE.md` also says to log AI use in `AI_USE.md`. Phase 1 was limited to these two files, so that entry is still owed.

## 7. Audit of the existing data

None of these files is crew dummy data. Two are real research or NASA data and one is a reference list. All are kept untouched.

### 7.1 `data/ppg_dalia/S{1..15}_HR.csv`

| Item | Value |
| --- | --- |
| What | Heart rate from an Empatica E4 wrist device (an estimate made from the PPG signal), 15 healthy volunteers on Earth |
| Format | Not a normal CSV. Line 1 is the start time (Unix seconds, UTC), line 2 is the rate (1.0 Hz), then one value per line. There is no header and no ID column |
| Type and unit | float, bpm |
| Rows | 7,956 (S12) to 10,809 (S10) values. That's 2.2 to 3.0 h each, 135,568 in total |
| Time range | 2018-06-29 (S1) to 2018-07-23 (S15). Each session starts at about 08:45 UTC on a different day |
| Range | 43.7 to 179.7 bpm. Medians are 74 to 111 bpm (S5 and S6 run high) |
| Missing | None (no blanks or NaN) |
| Subject | From the file name only (`S1`) |

### 7.2 `data/ppg_dalia/S{1..15}_TEMP.csv`

Same layout as the HR files, at 4 Hz, in °C, **wrist skin temperature**. Each file has 31,856 to 43,272 values. It starts **10 s before** the matching HR file. Range 26.3 to 36.5 °C. S8 runs cold, with a median of 29.7 °C. No missing values.

### 7.3 `data/ppg_dalia/S{1..15}_activity.csv`

17 `# LABEL, second` lines with no header row. Each line gives the second, counted from the TEMP start, at which an activity begins. The labels are `NO_ACTIVITY`, `BASELINE`, `STAIRS`, `SOCCER`, `CYCLING`, `DRIVING`, `LUNCH`, `WALKING`, `WORKING` and `CLEAN_BASELINE`. Line 1 is `# SUBJECT_ID, Sk`.

### 7.4 `data/eda/rr1_telemetry.json` (JSON, not CSV)

| Item | Value |
| --- | --- |
| What | ISS cabin environment during Rodent Research 1, plus the matched ground-control chamber |
| Columns | `time` (ISO Z), `temperature_iss` / `temperature_ground` (°C), `humidity_iss` / `humidity_ground` (% RH), `co2_iss` / `co2_ground` (ppm), `milestones` (text or null) |
| Rows | 12,087. The time range is 2014-09-20 03:59Z to 2014-11-01 03:54Z |
| Sampling | Every 5 min (12,071 of the gaps). Two outages, of 20 min and 33 min |
| Ranges | ISS temperature 18.5 to 26.8 °C, RH 31 to 76 %, CO2 1,862 to 4,667 ppm, which is about 1.4 to 3.5 mmHg at 760 mmHg |
| Notes | `co2_ground` sits above 1,500 ppm in 9,953 rows. That's because the ground chamber copies the ISS CO2 level by design, so it is not room air. 7 milestone rows. No nulls in any value column |

### 7.5 `data/eda/rr1_radiation.json`

39 daily rows, from 2014-09-21 to 2014-10-29. Columns: `time`, `gcr`, `saa` and `total`, all in **mGy a day** (`total` is about 0.19 to 0.21), plus `milestones`. All 34 nulls are in `milestones`.

### 7.6 `data/eda/missions.json`

24 mission records (`name`, `title`, `description`, `link`), used for reference only. The last record holds placeholder text ("Description", "Link").

### 7.7 How the files relate

- PPG HR, TEMP and activity files for one subject share the subject number in the file name, and their clocks are linked: HR = TEMP + 10 s, and activity seconds count from the TEMP start. Those are the only keys.
- EDA telemetry and radiation share the mission (RR-1) and the calendar date.
- **No file shares a key with the backend.** There is no crew id, no suit id, and no time on the mission calendar.

### 7.8 Columns no code uses, and fields the code expects that no file has

- No backend code reads any data file. Everything in `data/` is unused by the app.
- The backend has `glucose` and `sleep_hours`, which no file supplies and the frontend never shows. The frontend wants `glucose` nowhere.
- The backend expects `heart_rate`, `spo2`, `skin_temp`, `bp_sys`, `bp_dia`, `sleep_hours` and `mood` per crew member. The files supply only heart rate and skin temperature, for strangers on Earth. There is no SpO2, blood pressure, breathing rate, sleep or mood in any file.

## 8. Frontend coverage map

Source: `backend-api-contract.md` (Damola, 14 Nov). "Today" is what the repo's data holds now. "Plan" names the file and column in `DATA_PLAN.md` that will supply it.

Status key: **C** covered, **NC** needs a new column, **NF** needs a new CSV, **FU** needs a format or unit change, **Q** unclear (a question for the user or Damola), **API** derived by the backend at request time (the data only has to hold the inputs).

### Header and mission

| Field | Today | Status | Plan |
| --- | --- | --- | --- |
| stop, delay_s, link_up, mode, who_decides | Backend runtime | C | `link_windows.csv` drives `/dial` during replay |
| `mission_day` | None | NF | `mission.csv` (launch date) plus `mission_day` on every time-based row |
| `platform` "ISS" | None | NF, Q | `mission.csv.platform`. ISS or Mars transit? |

### Crew object (overview and astronaut pages)

| Field | Today | Status | Plan |
| --- | --- | --- | --- |
| `id` "C1"…"C4" | Backend ints 1 to 3 | FU | `crew.csv.crew_id` as a string. The replay maps it to an int |
| `name`, `role` | Backend seed (other people) | NF, Q | `crew.csv`. Needs `crew-seed.json` |
| `suit_id` | None | NF | `crew.csv.suit_id` |
| `baseline.hr_rest`, `bp`, `spo2`, `temp_c`, `resp`, `sleep_h`, `pvt_ms`, `vo2max` | None (C1 only in the contract) | NF, Q | `baselines.csv`. C2 to C4 need `crew-seed.json` |
| `today.hr_rest` | None | NF, Q | `daily_summary.csv.hr_rest_bpm`. What does "resting" mean here? |
| `today.bp` [sys, dia] | None | NF, Q | `daily_summary.csv`. Systolic is estimated by the shirt; where does diastolic come from? |
| `today.spo2`, `today.resp` | None | NF | `daily_summary.csv` from `vitals_1min.csv` |
| `today.temp_c` | Skin temp only | FU, Q | Core versus skin. Plan: both, `core_temp_c` and `skin_temp_c` |
| `today.sleep_h`, `mood`, `pvt_ms`, `symptoms` | None | NF | `checkins.csv` |
| `today.dose_mSv_day`, `dose_mSv_mission` | EDA mGy a day | FU, Q | `radiation_daily.csv`. The mGy to mSv factor needs a source |
| `metric_states`, `state`, `note` | None | API, Q | Inputs are present. Who writes `note`? |
| `last_packet_at` | None | NC | `vitals_*.csv.sensor_ts` |

### History, thresholds and check-in

| Field | Today | Status | Plan |
| --- | --- | --- | --- |
| `history.days[]` (up to 30), `band`, `unit`, `simulated` | None | NF | `daily_summary.csv` for mission days 1 to 158, plus `baselines.csv` |
| `days_out_of_band` | None | API | Derived |
| `thresholds` (unit, watch, alert, source) | `limits.json` (NEWS2 only) | NF, Q | `thresholds.csv`, copied from `thresholds.json`. Needs the file |
| Check-in body (mood, sleep_h, symptoms, note, pvt_ms) | None | NF | `checkins.csv` |
| `streak`, `next_badge_at`, `done` / `due` | None | API, Q | Derived from `checkins.csv`. The badge rule is unclear |

### Station environment and space weather

| Field | Today | Status | Plan |
| --- | --- | --- | --- |
| `co2_mmHg` | EDA ppm | FU | `cabin_env.csv`: `co2_ppm` from EDA plus `co2_mmHg` (Dalton's law, see `DATA_PLAN.md` §4.3) |
| `ppo2_mmHg`, `pressure_kPa` | None (not in EDA) | NC | `cabin_env.csv`, simulated and flagged |
| `temp_c`, `rh_pct` | EDA | C, FU | `cabin_env.csv`, with 2014 times shifted onto the mission calendar and the original time kept |
| `dose_mSv_today` | EDA mGy | FU, Q | `radiation_daily.csv` |
| `updated_at`, `simulated`, `source` | None | NC | A provenance column on every row |
| Space weather (state, headline, advisory, event_at, source) | None | NF, Q | `space_weather_events.csv` (DONKI SEP layout). The contract wants `simulated: false`, but an injected event is simulated |

### Alerts, thread and reminders

| Field | Today | Status | Plan |
| --- | --- | --- | --- |
| Alert A1 with `metric`, `state`, `stage`, `rule`, `symptoms`, `timeline.*` | Backend creates alerts live; no seed | NF | `alerts_seed.csv`: A1 at `raised`, plus past resolved alerts |
| `steps` | `procedures.json` | C | Kept as is. It's base station data, so I won't touch it |
| ThreadMessage (from, author, text, sent_at, arrived_at, status) | None | NF | `messages.csv`, one row per `link_message` row |
| Reminders | None | NF | `reminders.csv` |

### Health data log

| Field | Today | Status | Plan |
| --- | --- | --- | --- |
| Packet fields (`crew_id`, `suit_id`, `ts`, `mission_day`, `location`, `source`, `metric`, `value`, `unit`, `signal_quality`, `window_s`, `sent_to_ground`, `ack`) | None | NF | `packets.csv` |
| `transmitted_to_ground_today` | None | API | From `packets.sent_to_ground` |
| `stream-health` (lowest signal quality per sensor) | None | API | From `packets.signal_quality` and `channels.csv` |
| Push | n/a | out of scope | Not data |

### Earth side

| Need | Today | Status | Plan |
| --- | --- | --- | --- |
| Message data age: `created_at`, `sent_at`, received (`deliver_at`) | `link_message` | C | `messages.csv` keeps all three |
| Reading data age (sensor time to Earth) | Missing (server time only) | NC | `sensor_ts` and `gateway_ts` in the vitals files. The backend has to keep them (fix 1 for TJ) |
| History of messages between the flight surgeon and the crew | Live only | NF | `messages.csv` (past threads plus A1) |
| Alert status as Earth sees it | `update` messages | C | `messages.csv` `kind=update` rows |
| Sync status (queued, in flight, delivered) | `link.to_dict` | C | `messages.csv.status`, stored as of the data's "now" |
| Link status and windows over time | Manual dial only | NF | `link_windows.csv` |
