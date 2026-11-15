# LIGHT-TIME data plan

Status: **approved and built**, 14 November 2026, on `Ore-backend`. Read `PROJECT_NOTES.md` first: it explains why most of this is new files rather than edits to old ones. How to run it is in `data/README.md`.

## Decisions taken (Q1 to Q10)

| # | Decision |
| --- | --- |
| Q1 | ISS platform, mission day 158 = 14 Nov 2026 (matches the frontend), with a Mars-distance link: each day's real Horizons light time (`data/reference/horizons_mars_light_time.csv`) and one compressed conjunction blackout |
| Q2 | Crew ids are the strings `C1`…`C4` (TJ, Rebecca, Kyler, David). `crew.backend_id` maps them to the backend's integers. **The frontend keeps its id format; the backend should adopt `C1`…`C4`** (see `PROJECT_NOTES.md` §6) |
| Q3 | C2 to C4 baselines and roles are drafts (`source = draft`). Threshold rule text comes from the contract; sources not in the contract are marked `pending` |
| Q4 | No mGy to mSv conversion. The real EDA mGy is kept; mSv is simulated, using the EDA day-to-day shape scaled so day 158 is 0.51 and the mission total is 81.0 |
| Q5 | CO2 ppm to mmHg by Dalton's law, using each row's own cabin pressure |
| Q6 | Both `core_temp_c` (the frontend's `temp_c`) and `skin_temp_c` |
| Q7 | PPG-DaLiA calm-segment variation (mean removed) is added to the 1 Hz series, with `provenance = sim+ppg_dalia_texture:Sx` on every row |
| Q8 | `vitals_*` and `packets` are gitignored (rebuild in about 1.5 min); everything else is committed |
| Q9 | Done as a false-alarm breakdown in the replay report; the full frontend-rules scorer is listed as a follow-up |
| Q10 | Branch `Ore-backend`; `AI_USE.md` line added; nothing committed |

Changes from the draft below: there are two SEP events (AN07 large, AN08 demo morning), so the SOS is **AN09** and the blackout event is **AN10**. AN10 runs to 04:30 to cover the wake-up it causes. The sensor clock resyncs daily, which keeps the offset under 2 s. `gateway_ts ≥ sensor_ts` became "gateway − sensor between −2 s and 15 min", because the two clocks differ. `cabin_env` gained `real_fields` and `radiation_daily` gained `sep_mgy`.

Scope: data only. This plan adds files under `data/` and scripts that build them. It does not change backend, API or frontend code. Anything the backend would need to change is listed in §9 as a suggestion for TJ.

## 1. Principles

1. **The originals stay as they are.** `data/ppg_dalia/` and `data/eda/` are the raw inputs and stay byte for byte as they are, in the same place. Moving them to `data/raw/` would break `rule_check.py`'s documented run, the paths in `docs/`, and `data/README.md`. A `data/raw_manifest.csv` records the SHA-256 of every raw file, and the build fails if any of them changes.
2. **Everything else is built.** All outputs go to `data/processed/` and come from one seeded script. Nothing in `processed/` is edited by hand.
3. **Clean and anomalous versions are built as two separate steps,** so both always exist and differ only by the injected events.
4. **Every row says where it came from.** Each row carries `simulated` (true or false) and a `provenance` column. Possible values: `sim`, `eda_rr1_replay`, `ppg_dalia_texture:S7`, `injected:AN03`, `fault:SF02`. This follows the honesty rule in `CLAUDE.md` and `data/README.md`.
5. **One-to-one with future database tables.** One CSV per table, `snake_case` columns, the unit in the column name, ISO 8601 UTC times with `Z`, and string ids where the frontend wants strings.

## 2. Folder layout after Phase 2

```
data/
  ppg_dalia/            untouched (raw)
  eda/                  untouched (raw)
  raw_manifest.csv      sha256 of every raw file
  scripts/
    build_all.py        the one command: generate, inject, summarise, validate
    generate_clean.py   step 1: clean signals
    inject_anomalies.py step 2: anomalous copy and ground truth
    summarise.py        daily_summary, packets
    validate.py         schema, keys, ranges
    replay.py           pushes data through the real backend in-process and scores it
    schema.py           the data model below, as code (the single source for validate.py)
  processed/
    reference/          crew, baselines, thresholds, habitats, channels, mission  (shared by both versions)
    clean/              time-series and events without anomalies
    anomalous/          the same files with anomalies injected
    ground_truth/       anomalies.csv
    reports/            validation.txt, replay_score.md, replay_alerts.csv
  README.md             extended (the existing text is kept)
```

Scripts use the **standard library only** (`csv`, `random`, `math`, `hashlib`, `datetime`), so there is nothing new to install. `replay.py` also imports the app, which is already in `requirements.txt`.

**One command:** `python data/scripts/build_all.py --seed 2026` rebuilds everything. With the same seed and the same raw files, the output is byte-identical. The build writes the seed, the script git hash and the raw hashes into `processed/BUILD_INFO.json`, and `validate.py` checks that two builds produce the same files.

## 3. Data model

PK is the primary key and FK a foreign key. All times are `timestamptz` in UTC. The "DB type" column is for Postgres.

### 3.1 Reference tables (`processed/reference/`)

**`mission.csv`** (one row)

| Column | Type | Notes |
| --- | --- | --- |
| `mission_id` PK | text | `LT-2026` |
| `launch_date` | date | `2026-06-10`, so mission day 158 is 2026-11-14 |
| `platform` | text | `ISS` (see Q1) |
| `demo_now` | timestamptz | `2026-11-14T06:30:00Z`, the "now" the data ends at |
| `simulated` | bool | true |

**`crew.csv`**

| Column | Type | Notes |
| --- | --- | --- |
| `crew_id` PK | text | `C1`…`C4` |
| `backend_id` | int | 1…4. Used only by the replay, to map onto the backend's integer ids |
| `name`, `role` | text | From `crew-seed.json` once it's received. Until then: TJ (Commander), Rebecca, Kyler, David, with the other roles marked TBD |
| `suit_id` | text | `LT-01`…`LT-04` |
| `home_habitat_id` FK | text | → `habitats` |
| `is_cmo` | bool | Which crew member is the medical officer |

**`baselines.csv`** (long format, one row per crew member per metric; this is the frontend's `baseline` object)

| Column | Type | Notes |
| --- | --- | --- |
| `crew_id` FK, `metric` FK | text | PK is (`crew_id`, `metric`) |
| `low`, `high` | float, nullable | The band |
| `point` | float, nullable | Single-value baselines (`pvt_ms`, `vo2max_ml_min_kg`) |
| `unit` | text | |
| `set_on` | date | Pre-launch date |
| `source` | text | `crew-seed.json` or `simulated` |

Proposed values (C1 is copied from the contract; C2 to C4 are my draft until `crew-seed.json` arrives):

| | HR rest | BP sys / dia | SpO2 | Core temp °C | Resp | Sleep h | PVT ms | VO2max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C1 TJ | 52–64 | 108–122 / 66–78 | 96–99 | 36.3–36.9 | 12–16 | 6.8–7.6 | 265 | 44.0 |
| C2 Rebecca | 58–70 | 112–128 / 70–82 | 96–99 | 36.4–37.0 | 13–17 | 6.5–7.3 | 280 | 40.0 |
| C3 Kyler | 60–72 | 104–118 / 64–76 | 96–99 | 36.2–36.8 | 12–16 | 7.0–7.8 | 250 | 42.0 |
| C4 David | 46–56 | 110–124 / 68–80 | 96–99 | 36.4–37.0 | 10–14 | 6.6–7.4 | 270 | 52.0 |

C4's resting HR is deliberately athletic. Asleep, C4 sits under the backend's NEWS2 line of 50 bpm, so C4 is the false-alarm control for the fixed bands.

**`thresholds.csv`** (one row per metric; feeds `GET /thresholds`)

`metric` PK, `unit`, `watch_rule` (text), `alert_rule` (text), `watch_param`, `alert_param` (float, nullable), `needs_symptom` (bool), `consecutive_days` (int, nullable), `source` (text). The rows are copied word for word from the frontend's `thresholds.json` (blocked on Q3). Two more rows, `co2_mmHg` (WATCH 2.8, ALERT 4.5, OCHMO CO2 brief) and `signal_quality` (RECHECK under 0.6), come from the contract text.

**`habitats.csv`**: `habitat_id` PK (`H1`, `H2`), `name`, `cabin_data_source` (`eda_rr1_replay` or `sim`).

**`channels.csv`** (the sensor vocabulary; feeds `stream-health`)

| `source` | Device it's modelled on | Metrics | Native rate |
| --- | --- | --- | --- |
| `ecg` | Bio-Monitor (Astroskin) shirt, ECG | `hr_bpm` | 1 Hz (beat-derived) |
| `chest_band` | Shirt respiratory inductance bands | `resp_rpm` | 1 Hz |
| `pulse_ox` | Bio-Monitor headband | `spo2_pct` | 1 Hz |
| `skin_temp` | Headband skin sensor | `skin_temp_c` | 1 Hz |
| `core_temp` | Heat-flux core temperature sensor (see Q6) | `core_temp_c` | 1/min |
| `accel` | Shirt 3-axis accelerometer | `activity_g` | 1 Hz (1 s magnitude) |
| `bp_est` | Shirt estimated systolic blood pressure | `bp_sys_est_mmhg` | 1/min |
| `cabin_co2` etc. | Cabin sensors | Cabin metrics | 5 min |

**`metrics.csv`**: `metric` PK, `unit`, `api_name` (frontend name such as `hr_rest`), `backend_name` (`heart_rate`, `skin_temp`, ...), `min_possible`, `max_possible`. This table holds the name mapping, and `validate.py` uses it for range checks.

### 3.2 Time-series tables (`processed/clean/` and `processed/anomalous/`, same schema)

**`vitals_1min.csv`**: one row per crew member per minute, mission days 129 to 158 (2026-10-16 00:00Z to 2026-11-14 06:30Z), about 4 × 42,870 ≈ 171k rows.

| Column | Type | Unit | Notes |
| --- | --- | --- | --- |
| `sample_id` PK | text | | `C1-20261114T061200Z` |
| `crew_id` FK | text | | |
| `sensor_ts` | timestamptz | | Time stamped on the suit, with a per-suit clock offset of ±0.5 s and slow drift |
| `gateway_ts` | timestamptz | | Time the base station received it. Usually 50 to 400 ms after `sensor_ts`, with occasional store-and-forward bursts |
| `mission_day` | int | | |
| `habitat_id` FK | text | | Where the crew member is |
| `activity_label` | text | | `sleep`, `exercise_ared`, `exercise_cevis`, `work`, `meal`, `eva_prep`, `leisure` |
| `hr_bpm`, `resp_rpm`, `spo2_pct`, `skin_temp_c`, `core_temp_c`, `activity_g`, `bp_sys_est_mmhg` | float, nullable | as named | Null means no sample |
| `signal_quality` | float 0–1 | | Worst channel in the window |
| `signal_ok` | bool | | `signal_quality >= 0.6`, to match the backend |
| `simulated`, `provenance` | bool, text | | |

**`vitals_1hz_demo.csv`**: same schema, at 1 Hz, for mission day 158 from 04:30 to 06:30Z (4 × 7,200 = 28,800 rows), plus 1 Hz windows around each acute anomaly. This matches the backend's "5 readings = 5 s" design, so the replay behaves as it does on stage.

**`cabin_env.csv`**: one row per habitat every 5 min.

`habitat_id` FK, `ts`, `co2_ppm`, `co2_mmhg`, `ppo2_mmhg`, `pressure_kpa`, `temp_c`, `rh_pct`, `orig_ts` (the EDA 2014 time, null if simulated), `simulated`, `provenance`. PK is (`habitat_id`, `ts`).

**`radiation_daily.csv`**: `date` PK, `mission_day`, `gcr_mgy`, `saa_mgy`, `total_mgy` (from EDA), `dose_msv_day`, `dose_msv_mission` (see Q4), `orig_date`, `simulated`, `provenance`.

**`daily_summary.csv`**: one row per crew member per day, mission days 1 to 158. This feeds `history` and `today`.

`crew_id`, `date`, `mission_day` (PK `crew_id`+`date`), `hr_rest_bpm` (definition in Q-F1), `bp_sys_mmhg`, `bp_dia_mmhg`, `spo2_pct`, `core_temp_c`, `skin_temp_c`, `resp_rpm`, `sleep_h`, `mood`, `pvt_ms`, `dose_msv_day`, `symptoms` (`|`-separated), `simulated`, `provenance`. Days 1 to 128 are made at daily resolution only, so the slow drift has a history. Days 129 to 158 are added up from `vitals_1min` and `checkins`.

**`packets.csv`**: the frontend's Packet, long format, one row per metric per 60 s window, for mission days 157 to 158.

`packet_id` PK, `crew_id`, `suit_id`, `ts`, `mission_day`, `location`, `source` FK → channels, `metric`, `value`, `unit`, `signal_quality`, `window_s`, `sent_to_ground` (bool), `ack` (nullable), `sample_id` FK → vitals. The backend adds `baseline`, `rule` and `state` when it stores a packet, so they aren't here.

### 3.3 Event tables (same folders)

| File | Columns | PK / FKs |
| --- | --- | --- |
| `checkins.csv` | `checkin_id`, `crew_id`, `date`, `completed_at`, `mood` (1 to 5), `sleep_h`, `pvt_ms`, `symptoms`, `note`, `first_today` | PK `checkin_id`; unique (`crew_id`, `date`) |
| `sos_events.csv` | `event_id`, `crew_id`, `suit_id`, `sensor_ts`, `gateway_ts`, `trigger` (`glove_triple_tap` or `button`), `anomaly_id` | → crew, anomalies |
| `space_weather_events.csv` | DONKI SEP layout: `sep_id` (`2026-11-14T05:58:00-SEP-001`), `event_time`, `instruments`, `linked_events`, `link`, plus `end_time`, `state`, `headline`, `advisory`, `simulated`, `provenance` | PK `sep_id` |
| `link_windows.csv` | `window_id`, `start`, `end`, `stop` (`station`, `moon`, `mars` or `sun`), `link_up`, `one_way_delay_s`, `delay_source`, `note` | PK `window_id`; no overlaps allowed |
| `alerts_seed.csv` | `alert_id` (`A1`…), `crew_id`, `metric`, `value`, `unit`, `state`, `level`, `stage`, `reason`, `rule`, `source`, `nasa_risk`, `symptoms`, `steps_done`, `raised_at`, `acknowledged_at`, `sent_at`, `earth_at`, `reply_at`, `resolved_at`, `anomaly_id` | → crew, metrics |
| `messages.csv` | `message_id` (`M1`…), `alert_id`, `direction`, `kind`, `from_side` (`crew` or `ground`), `author`, `text`, `priority`, `created_at`, `sent_at`, `delay_s`, `deliver_at`, `status_at_demo_now`, `in_reply_to` | Maps 1:1 to `link_message`; `arrived_at` = `deliver_at` |
| `reminders.csv` | `reminder_id`, `crew_id`, `alert_id`, `text`, `due_at`, `done_at` | → crew, alerts |

`alerts_seed`, `messages` and `reminders` hold the past (resolved alerts and their threads, so the history and log screens have something in them) plus the demo morning: A1 at `raised`, no reply yet, no reminders. They are kept as at `demo_now`.

### 3.4 Ground truth (`processed/ground_truth/anomalies.csv`)

| Column | Type | Notes |
| --- | --- | --- |
| `id` PK | text | `AN01`…, sensor faults `SF01`…, negative controls `NC01`… |
| `crew_member` | text, nullable | `C1`…, or null for a habitat or space-weather event |
| `habitat_id` | text, nullable | For cabin events |
| `type` | text | `spo2_drop`, `tachycardia_rest`, `bradycardia_sleep`, `fever`, `co2_buildup`, `sep_event`, `sos_glove_tap`, `hr_rest_3day`, `dropout`, `flatline`, `spike`, `exercise_control`, ... |
| `kind` | text | `medical`, `environmental`, `sensor_fault` or `negative_control` |
| `start`, `end` | timestamptz | |
| `severity` | text | `low`, `moderate`, `high` or `critical` |
| `expected_alert` | text | What a correct system should show: `none`, `RECHECK`, `WATCH`, `ALERT` or `SOS` |
| `expected_backend_level` | text | What the current NEWS2 backend should raise if it works as written: `none`, `advisory`, `caution`, `warning`, `emergency` or `not_ingested` |
| `metrics` | text | `|`-separated metrics affected |
| `is_medical` | bool | False for sensor faults and negative controls |
| `link_state_at_start` | text | `up` or `down` |
| `notes` | text | |

### 3.5 Relationships

```
mission 1─* (every time row carries mission_day)
crew 1─* baselines, vitals_*, daily_summary, packets, checkins, sos_events, alerts_seed, reminders
habitats 1─* cabin_env;  crew.home_habitat_id, vitals.habitat_id → habitats
metrics 1─* baselines, thresholds, packets, alerts_seed
channels 1─* packets
alerts_seed 1─* messages, reminders;  anomalies 1─* sos_events, alerts_seed (optional)
vitals_1min.sample_id 1─* packets.sample_id
```

### 3.6 Which database later

**PostgreSQL 16 with the TimescaleDB extension.** Postgres is already what the backend targets (`DATABASE_URL`, tested on 16). The `vitals_*`, `cabin_env` and `packets` tables become hypertables keyed on time, with continuous aggregates for `daily_summary`. The reference and event tables stay ordinary tables. Nothing needs redesign: each CSV loads with `COPY`. Plain Postgres also works at this size (about 0.25 M rows). Timescale only matters once data arrives at 1 Hz for a whole mission. I won't set anything up.

## 4. How the files get built

### 4.1 Changes to the existing files

**None.** No existing file is edited, moved or deleted, so nothing that reads them today can break: `rule_check.py`, the docs and the backend (which reads none of them) are unaffected.

The only edit is to `data/README.md`: Phase 2 adds sections and keeps every existing line. It also corrects "three volunteers" to "15". That's a documentation change and breaks nothing.

### 4.2 How the raw data is used (extended, not thrown away)

| Raw | Used for | How |
| --- | --- | --- |
| `eda/rr1_telemetry.json` | `cabin_env` H1: `temp_c`, `rh_pct`, `co2_ppm` | 2014-09-20 onward is shifted so it starts on mission day 129. 30 days of the 42 available. The real time is kept in `orig_ts`. Its two real outages stay as gaps. `provenance = eda_rr1_replay`, `simulated = false` |
| Same file | `cabin_env` H2 | The same series with a 7-day offset and seeded jitter, `simulated = true` (it's derived) |
| `eda/rr1_radiation.json` | `radiation_daily.total_mgy` | The 39 daily values, shifted and looped where the 30-day window needs it |
| `ppg_dalia/S*_HR.csv` | Beat-to-beat **texture** in `vitals_1hz_demo` | Only the calm segments the README marks safe (BASELINE / WORKING for S2, S3, S7, S10). The values are high-pass filtered, so only the variation is kept and the subject's own level is dropped, then added to each crew member's simulated baseline. C1←S2, C2←S3, C3←S7, C4←S10. Provenance is recorded per row. See Q7 |
| `ppg_dalia/S*_TEMP.csv` | Skin temperature texture in the same way | Variation only |
| `ppg_dalia/rule_check.py` result | Validation target | The replay checks that the NEWS2 false-alarm pattern it found shows up in our data too |

### 4.3 Unit conversions (each one cited, none guessed)

- **CO2 from ppm to mmHg** by Dalton's law: `mmHg = ppm × P_cabin_mmHg / 10⁶`, using the row's own `pressure_kpa` × 7.50062. At 101.3 kPa, 1 mmHg ≈ 1,316 ppm. The contract's WATCH line of 2.8 mmHg is about 3,680 ppm. Real RR-1 data reaches 4,667 ppm (3.5 mmHg), so the **real** data already crosses WATCH. That's worth knowing (Q5).
- **Radiation from mGy to mSv**: no conversion until a source is agreed (Q4). Until then, `dose_msv_day` is simulated and flagged. It is anchored to the contract's 0.51 mSv a day and 81 mSv by day 158, and the measured mGy sits next to it.

## 5. Realism model (clean build)

**Day plan (ISS GMT schedule):** wake 06:00, post-sleep 06:00 to 07:30, work 07:30 to 19:30 with two exercise sessions of 60 to 75 min each (ARED resistance and CEVIS or treadmill; times differ per crew member and day), meals at 07:00, 12:30 and 19:00, pre-sleep 19:30 to 21:30, sleep window 21:30 to 06:00. Actual sleep is 5.8 to 7.8 h, drawn around each crew member's baseline, with sleep onset delay and wake bouts.

**Per channel** (each is baseline plus circadian term plus activity term plus AR(1) noise):

| Channel | Model |
| --- | --- |
| HR | Sleep minimum about 6 to 10 bpm under the resting band's low end. A circadian sine with its low point near 04:00. Exercise rises to 55 to 80 % of the crew member's HR reserve, worked out from VO2max, with an exponential on and off. Recovery takes 2 to 5 min. Meals add 3 to 6 bpm |
| Resp | Rest at baseline, sleep 1 to 2 lower, exercise 25 to 35 |
| SpO2 | Whole percent. 96 to 99 awake, about 1 % lower in sleep, rare one-sample dips of 1 % |
| Core temp | Circadian swing of ±0.3 °C, lowest about 04:00 and highest about 18:00. +0.3 to 0.5 °C during exercise |
| Skin temp | 32.5 to 35 °C. Higher at night (distal warming), dips at the start of exercise |
| Activity (g) | About 0.01 asleep, 0.05 to 0.15 at work, 0.3 to 0.8 during exercise. Lower than on Earth, because there are no steps in microgravity |
| BP sys est | Baseline with circadian swing, +20 to 40 during resistance exercise, −10 in sleep |
| Signal quality | 0.9 to 0.99 at rest, 0.6 to 0.85 during exercise (motion), rare short drops under 0.6 |
| Cabin CO2 | EDA replay for H1. Small rises when the crew gather (meals) |

**Slow microgravity drift** is modelled as an exponential approach over the first 30 to 60 days, so by mission day 129 it is almost flat:

- resting HR −3 bpm
- systolic BP −4 mmHg
- core temperature +0.3 °C (after Stahn et al. 2017, "space fever", which I'll check before citing)
- sleep −0.3 h

It is sized to stay inside each band, so it raises no alert. `validate.py` asserts that the clean build has no day where a frontend scoring rule fires on drift alone.

**Sensor timestamps:** each suit has a fixed clock offset and a drift of ≤ 20 ppm. `sensor_ts` is what the suit says and `gateway_ts` is when the base station got it. During a link blackout this changes nothing: the suit-to-base link is local, and only base-to-Earth is cut.

**Demo morning (mission day 158)** is made to match the contract exactly:

- C1's HR rest is 80, 82 and 84 on days 156, 157 and 158, with a headache and 5.1 h of sleep
- the SEP event starts at 05:58Z
- A1 is raised at 06:12Z
- C2, C3 and C4 have checked in and C1 is due, with a streak of 12
- C1's last packet is at 06:29Z

## 6. Anomaly injection plan (step 2, `inject_anomalies.py`)

The anomalous build reads `clean/`, applies each anomaly as a change on top of the clean signal, and writes `anomalous/` plus `anomalies.csv`. Shapes are smooth ramps (logistic on and off), not step changes. Dates are mission days (MD) and times UTC.

| id | Crew / hab | When | What is injected | expected_alert | Current backend should… |
| --- | --- | --- | --- | --- | --- |
| AN01 `hr_rest_3day` | C1 | MD156–158 | Resting HR +16 to +22 over the band, plus a headache, short sleep and a high PVT (the A1 story) | ALERT | not catch it (84 bpm is "nominal" in NEWS2) |
| AN02 `spo2_drop` (gradual hypoxia) | C3 | MD150 14:00–15:30 | SpO2 98 → 89 over 60 min, HR +15, resp +6, then recovery | ALERT, then SOS at ≤ 91 | caution → warning → emergency |
| AN03 `tachycardia_rest` | C2 | MD152 10:40–11:00 | HR 125–135 with activity_g < 0.08 (at rest). An exercise session the same day reaches 150 bpm with high activity (NC01) | ALERT | warning/emergency on AN03, and also fire on NC01 (a false alarm) |
| AN04 `bradycardia_sleep` | C4 | MD154 02:00–02:40 | Sleeping HR 36–38, against C4's normal sleeping HR of 44–48 | ALERT | emergency at ≤ 40. C4's normal nights trip "caution" at ≤ 50 (false alarms, NC02) |
| AN05 `fever` | C2 | MD146 08:00–20:00 | Core temp 36.8 → 38.6 °C over 6 h, skin temp +1.2, HR +10 per °C, resp +3, then malaise at the next check-in | ALERT (over 38.0) | not catch it (no temperature rule); HR may reach caution |
| AN06 `co2_buildup` | H2 (C3, C4 inside) | MD148 09:00–13:00 | Scrubber fault: CO2 2.6 → 5.2 mmHg, both crew show resp +3 to 5 and HR +5. Headache at the next day's check-in | Cabin ALERT over 4.5, crew WATCH | not catch it (CO2 not ingested) |
| AN07 `sep_event` | all | MD140 13:20 to MD141 10:00 | DONKI-style SEP record. Day dose 2.4 mSv (ALERT) | ALERT, space weather only | not catch it (not ingested) |
| AN08 `sep_event` | all | MD158 05:58 for 18 h | DONKI-style SEP record with a shelter advisory. Dose stays 0.51 (the contract's value) | WATCH | not catch it (not ingested) |
| AN09 `sos_glove_tap` | C4 | MD155 16:20 | Triple glove tap during maintenance, with HR +30 and a burst of activity | SOS | emergency through `POST /sos` |
| AN10 `spo2_drop` during **conjunction** | C3 (moved from C1 so it doesn't overlap AN01) | MD157 03:00–04:30, link down from MD156 18:00 to MD157 12:00 | SpO2 97 → 88 and HR +20 in sleep, then awake | SOS, report **queued**, then flushed SOS-first when the link returns | emergency; report `queued` until `/dial` leaves `sun` |
| SF01 `dropout` | C3 chest band | MD151 10:00–10:25 | `resp_rpm` and `hr_bpm` are null and quality is 0.0 | RECHECK, no medical alert | `signal` advisory only |
| SF02 `flatline` | C2 pulse ox | MD149 13:00–16:00 | SpO2 stuck at exactly 97.0, quality still reported 0.9 | RECHECK (flatline detection) | not catch it (it looks valid) |
| SF03 `spike` | C1 | MD153, 6 single samples | HR 250 / 0, skin temp 45 °C, SpO2 40, each lasting 1 sample | none (filtered) / RECHECK | none, because a single sample can't meet the 5-in-a-row rule |
| SF04 `motion_artifact` | C3 | MD152, during exercise | Quality 0.4–0.55 for 3 min with HR jumps | RECHECK | `signal` advisory |
| NC01–NC03 negative controls | various | daily | Exercise HR, athletic sleeping HR, microgravity drift | none | may fire. Counted as false alarms |

Spikes and impossible values appear **only** in the SF rows. `validate.py` allows a value outside `metrics.min_possible` / `max_possible` only when its `provenance` is `fault:SFxx`.

## 7. Verification: replay and scoring (`replay.py`)

1. Builds the backend **in-process** with `create_app("sqlite:///<scratch>.db")` and its test client, the same way `tests/conftest.py` does. No server is needed and no base station code changes. Network is off (Horizons is patched to its fallback, as the tests do).
2. **Setting up the replay database (not backend code):** the backend seeds only 3 crew members, so the harness adds `crew` rows 1 to 4 through the models before the replay. Crew ids map C1→1 … C4→4.
3. **Feeding the data:** rows go in `sensor_ts` order. The harness posts each row to `POST /api/base/readings`, renaming `hr_bpm` to `heart_rate`, `spo2_pct` to `spo2` and `skin_temp_c` to `skin_temp`, and setting `bp_sys` from `bp_sys_est_mmhg` and `signal_ok`. Check-ins go in with `source: "typed"`. SOS events go to `POST /sos`. Link windows go to `POST /dial` at their start times. Channels the backend can't take (resp, core temp, CO2, dose) are recorded as `not_ingested`.
4. **Time:** the backend stamps readings with server time. So the harness keeps its own map from each posted `sample_id` to the alerts that post returned, and scores in data time. The 60 s quiet window runs on wall-clock time, so the harness never clears with a person's name. It closes each alert with `POST /clear {"by": "auto: replay"}` after 10 data-minutes in range, which skips the quiet window by the backend's own rule. That way one false alarm can't mask a later real event (`PROJECT_NOTES.md` §6 item 5).
5. **Scoring** (`reports/replay_score.md` plus `replay_alerts.csv`):
   - **Caught:** an alert for the same crew member (or anyone in the habitat), on a matching metric, raised between `start` and `end + 15 min`. The report gives time-to-detect and whether the level reached `expected_backend_level`.
   - **Missed:** an anomaly with no matching alert. The reason is recorded as `not_ingested`, `below_band` or `masked`.
   - **False alarm:** an alert with no anomaly window. Counted per crew member per day and split into sensor (`signal`) and medical, with negative-control hits named. A medical alert during a sensor fault counts as a false alarm.
   - **Link check:** for AN09, the report must be `queued` during the blackout and `delivered` after it, before lower-priority messages.
6. Runs on **both** builds. The clean build should give zero caught and only false alarms, so its count is the false-alarm baseline. The anomalous build gives caught and missed. There are two modes: `--windows` (the 1 Hz windows plus ±2 h around each anomaly, a few minutes to run) and `--full` (all 171k rows, likely 15 to 30 min).
7. (Optional, see Q9) A second score against the frontend's Scoring table, applied by the harness alone, shows the gap between today's backend and the target. That's an evaluation tool, not backend code.

`validate.py` checks:

- every file against `schema.py`: columns, types, required fields, units from `metrics.csv`
- PK uniqueness and that every FK exists
- times in ISO Z and increasing for each crew member
- `gateway_ts ≥ sensor_ts`
- no overlap in `link_windows`
- ranges, with the SF exception above
- clean and anomalous builds differ only inside anomaly windows
- the raw hashes are unchanged
- the coverage map is fully covered or listed as outstanding

## 8. Size and git

The estimated output is about 25 to 35 MB of CSV. My proposal is to commit `reference/`, `ground_truth/`, `reports/` and the small event files, and gitignore `vitals_*.csv` and `packets.csv` (they rebuild in under a minute). See Q8.

## 9. Suggested backend fixes for TJ (I won't make any of these)

1. Accept and store a sensor `ts` on `/readings`, next to the server's `at`.
2. Seed C1 to C4 or read them from `crew.csv`. Guard `alert_dict` and `/sos` against unknown crew.
3. Channels for `resp`, core temperature and cabin CO2, so fever, CO2 and breathing anomalies can be scored at all.
4. Personal-baseline rules from `thresholds.csv`, to replace the fixed NEWS2 HR bands that misfire on exercise and athletic sleep.
5. Validate `limit` and the `/dial` body.
6. Flatline detection, because a stuck value with good quality passes today.

## 10. Open questions

### For you

| # | Question | My default if you don't say |
| --- | --- | --- |
| Q1 | Platform and timeline: is it ISS, mission day 158 (frontend), or a Mars transit (the backend dial)? | ISS calendar, with `link_windows` using the dial stops (mostly `mars` delay, one `sun` blackout) so the light-time story still plays |
| Q2 | Crew: C1–C4 for the data, even though the backend then seeded the team's names (David, Damola and Youssef)? | Yes, C1–C4. The replay maps them to ints. Since 15 November the four carry team names: TJ, Rebecca, Kyler and David; Dr. Youssef and Damola work the Earth side |
| Q3 | Can you get `thresholds.json`, `crew-seed.json` and `packet-schema.json` from the frontend repo? | Draft values marked `source=draft`, replaced when the files arrive |
| Q4 | mGy to mSv: which factor and source? | No conversion. Simulated mSv flagged, real mGy kept next to it |
| Q5 | CO2 ppm to mmHg by Dalton's law using the row's own pressure: is that "cited" enough? | Yes, with the formula written in the README |
| Q6 | Core temperature as well as skin temperature? | Yes, both columns. The frontend's `temp_c` maps to core |
| Q7 | Can PPG-DaLiA variation be blended into simulated crew vitals, given the "never as our crew's own readings" rule? | Yes, variation only, with row-level provenance. Otherwise pure synthetic |
| Q8 | Commit the large generated CSVs or gitignore them? | Gitignore `vitals_*` and `packets`, commit the rest |
| Q9 | Add the optional frontend-rules score in the replay? | Yes |
| Q10 | Phase 2 will add a line to `AI_USE.md` (a `CLAUDE.md` rule). Which branch should this go on: `Ore-backend` or `Tj-Backend`? | `Ore-backend`, add the line, no commit until you ask |

### For Damola (frontend)

| # | Question |
| --- | --- |
| F1 | How is `today.hr_rest` defined: lowest 5-min mean during sleep, a morning reading at rest, or the daily mean at rest? |
| F2 | Where does `bp_dia` come from? The shirt estimates only systolic, and the check-in body has no BP field |
| F3 | Is `temp_c` core or skin? The band and the fever rule only make sense for core |
| F4 | Packets: is one 60 s window per metric right, and which sensor `source` names do you use (`ecg`, `chest_band`, others)? |
| F5 | The streak and `next_badge_at` rule, and what counts as "done today" (before which hour)? |
| F6 | Who writes the crew `note`: a backend template or the frontend? |
| F7 | Space weather says `simulated: false`, but any SEP in our dataset is injected. Is `simulated: true` with a DONKI layout OK? |
| F8 | `resp`: WATCH over 20 /min ignores the personal band of 12–16. Is that intended? |
| F9 | Does the Earth console need the sensor time of each reading (true data age), or only message times? |
