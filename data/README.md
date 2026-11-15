# data

Everything the backend reads that is not code. The rules and the reasons are in `docs/specs/2026-11-14-data-sources-design.md`. The full list of sources and links is in `docs/data-sources.md`.

| Folder | Holds |
| --- | --- |
| `reference/` | Small files of facts copied from NASA and CSA pages, each with its link and the date it was read |
| `eda/` | Tables from NASA's Environmental Data App (https://visualization.osdr.nasa.gov/eda), fetched through its API: ISS cabin temperature (degrees C), humidity (%), CO2 (ppm) and radiation (mGy a day) |
| `ppg_dalia/` | Wrist heart rate and skin temperature for 15 volunteers, cut from the PPG-DaLiA dataset (https://archive.ics.uci.edu/dataset/495/ppg+dalia, CC BY 4.0) |
| `cache/` | The last good answer from each live feed. The app writes it. It is not in git |
| `scripts/` | The seeded scripts that build `processed/` from the raw files above |
| `processed/` | Generated crew, cabin, link and event tables, in a clean and an anomalous version. Never edited by hand |
| `raw_manifest.csv` | SHA-256 of every raw file in `ppg_dalia/` and `eda/`. The build stops if one changes |

## Rules

- No health data that can identify a person goes in this folder. Open, de-identified research data is fine under its licence; we leave out its questionnaire files (age, weight and the like). On screen it is labelled as replayed research data, never as our crew's own readings.
- Every file has a source. Write the link and the download date in the table below when you add one.
- No scraped pages. A source comes in as a live API, a downloaded file, or a fact copied by hand with its link.
- `ppg_dalia/` and `eda/` are raw and stay exactly as downloaded. Everything in `processed/` comes from `scripts/build_all.py`.
- Every generated row carries `simulated` and `provenance`, which says where its values came from (`sim`, `eda_rr1_replay(...)`, `sim+ppg_dalia_texture:S7`, `injected:AN03`, `fault:SF02`).

## What is in here

| File | From (link) | Downloaded on | By |
| --- | --- | --- | --- |
| `eda/rr1_telemetry.json` | https://visualization.osdr.nasa.gov/eda/api/missions/RR-1/telemetry_data/ | 14 Nov 2026 | Claude, for TJ |
| `eda/rr1_radiation.json` | https://visualization.osdr.nasa.gov/eda/api/missions/RR-1/radiation_data/ | 14 Nov 2026 | Claude, for TJ |
| `eda/missions.json` | https://visualization.osdr.nasa.gov/eda/api/missions/ | 14 Nov 2026 | Claude, for TJ |
| `reference/horizons_mars_light_time.csv` | https://ssd.jpl.nasa.gov/api/horizons.api (Mars, observer at Earth's centre, quantity 21, daily 16 Oct to 15 Nov 2026) | 14 Nov 2026 | Claude Code, for Ore |
| `reference/console_thresholds.json` | The console repo's `src/data/thresholds.json` (branch `feat/alert-loop-and-log`) | 14 Nov 2026 | Claude Code, for the backend owner |

## Credit lines for the project page

- NASA OSDR: "Data and visualizations are courtesy of the Environmental Data Application (EDA) (https://visualization.osdr.nasa.gov/eda/), Version #."
- PPG-DaLiA: Reiss, A., Indlekofer, I. and Schmidt, P. (2019). PPG-DaLiA. UCI Machine Learning Repository. https://doi.org/10.24432/C53890. Licence CC BY 4.0.
- Canadian Space Agency files: name the CSA as the source and link the Open Government Licence - Canada (https://open.canada.ca/en/open-government-licence-canada).

---

# Generated data (`processed/`)

The plan behind this, the open questions and the frontend coverage map are in `DATA_PLAN.md` and `PROJECT_NOTES.md` at the repo root.

## Regenerate

One command, standard library only, about 1.5 minutes:

    python data/scripts/build_all.py                # seed 2026 (the default)
    python data/scripts/build_all.py --check-repro  # builds twice and proves the files are byte-identical
    python data/scripts/build_all.py --seed 7       # a different seeded variant

The steps, which can also be run one at a time:

1. `generate_clean.py`: reference tables and the clean build
2. `inject_anomalies.py`: the anomalous build and `ground_truth/anomalies.csv`
3. `summarise.py --build clean|anomalous`: `daily_summary.csv` and `packets.csv`
4. `validate.py`: schema, keys, ranges, raw hashes, the clean/anomalous difference, the contract's demo numbers. It writes `reports/validation.txt` and `reports/coverage.md`

The three large files in each build (`vitals_1min.csv`, `vitals_1hz_demo.csv` and `packets.csv`, about 85 MB across both builds) are gitignored. Run the build after cloning.

## Replay through the backend

The harness runs the real backend in-process (Flask test client, SQLite in memory, no network) and posts the data in base-station arrival order (`gateway_ts`). It sends readings to `POST /api/base/readings`, check-ins as `source: "typed"`, SOS events to `POST /api/base/sos`, and link windows to `POST /api/base/dial`. It does not change any backend code.

    .venv/Scripts/python data/scripts/replay.py --build anomalous   # about 20 min
    .venv/Scripts/python data/scripts/replay.py --build clean

It writes `reports/replay_<build>.md` (caught, missed and false alarms against the ground truth) and `reports/replay_alerts_<build>.csv` (every alert the backend raised). The summary for TJ is in `reports/REPLAY_SUMMARY.md`.

Two things the harness does to the scratch database only (never to backend code):

- It adds crew row 4 and names rows 1 to 4 after C1 to C4, because the backend seeds only 3 crew.
- It clears an alert after 10 data-minutes back in range, with `by: "auto: replay"`, so one alert can't hide the next. It also prunes all but the newest 4,000 readings every 10k events: the rules never look back more than 30, and without pruning every query slows down.

## The two builds

| Folder | What |
| --- | --- |
| `processed/reference/` | Shared by both builds: mission, crew, habitats, metrics, channels, baselines, thresholds, link windows |
| `processed/clean/` | The 30 days with normal physiology only: day and night, exercise, sleep and the slow microgravity drift |
| `processed/anomalous/` | The same data with every anomaly in `ground_truth/anomalies.csv` injected. **This is the demo build**: its morning of 14 Nov matches `backend-api-contract.md` |
| `processed/ground_truth/anomalies.csv` | What was injected, when, and what a correct system and the current backend should each raise |
| `processed/reports/` | `validation.txt`, `coverage.md`, replay reports |
| `processed/BUILD_INFO.json` | Seed, git commit, raw manifest hash and the SHA-256 of every output |

The two builds differ only inside the anomaly windows. `validate.py` checks this.

## Timeline

The mission launches on 10 Jun 2026, so 14 Nov 2026 is mission day 158 (the contract's day). Minute data runs from 16 Oct 00:00Z (day 129) to `demo_now`, 14 Nov 06:30Z. The daily history runs from day 1 to day 158. The platform is the ISS, with a Mars-distance link: each day's real one-way light time comes from JPL Horizons, and there is one blackout (12 Nov 18:00Z to 13 Nov 12:00Z), a solar conjunction compressed to 18 hours. All times are UTC with a `Z`.

## Files and future database tables

Each CSV is one table. Load them with `COPY` into PostgreSQL 16; for the time-series tables, use the TimescaleDB extension.

| File | Table | Primary key | Links to | Rows | Notes |
| --- | --- | --- | --- | --- | --- |
| `reference/mission.csv` | `mission` | `mission_id` | | 1 | Launch date, platform, `demo_now` |
| `reference/crew.csv` | `crew` | `crew_id` (`C1`…`C4`) | `habitats` | 4 | `backend_id` maps to the current backend's integer ids. C2 to C4 names and roles are drafts |
| `reference/habitats.csv` | `habitat` | `habitat_id` | | 2 | H1 (galley, exercise), H2 (labs, sleep) |
| `reference/metrics.csv` | `metric` | `metric` | | 16 | Unit, frontend `api_name`, backend column name, possible range |
| `reference/channels.csv` | `channel` | `source` | | 9 | Sensor vocabulary for packets and stream health, modelled on the CSA Bio-Monitor |
| `reference/baselines.csv` | `baseline` | (`crew_id`, `metric`) | `crew` | 36 | The frontend's `baseline` object, set before flight |
| `reference/thresholds.csv` | `threshold` | `metric` | | 12 | Rule text from the contract. `source_status` says which sources are still pending |
| `reference/link_windows.csv` | `link_window` | `window_id` | | 31 | One per day while the link is up (with that day's light time), one for the blackout |
| `*/vitals_1min.csv` | `vital_minute` (hypertable) | `sample_id` | `crew`, `habitat` | 168,600 | HR, resp, SpO2, skin and core temp, activity, estimated systolic BP, signal quality. `sensor_ts` is the suit's clock and `gateway_ts` is arrival at the base |
| `*/vitals_1hz_demo.csv` | `vital_second` (hypertable) | `sample_id` | `crew`, `habitat` | 57,900 | Same columns at 1 Hz: the demo morning and each acute anomaly. HR and skin temp carry PPG-DaLiA variation |
| `*/cabin_env.csv` | `cabin_reading` (hypertable) | (`habitat_id`, `ts`) | `habitat` | 16,843 | Every 5 min. H1 CO2, temperature and RH are real EDA RR-1, replayed (`orig_ts` keeps the 2014 time); pressure and ppO2 are simulated. `real_fields` lists the real columns |
| `*/radiation_daily.csv` | `radiation_day` | `date` | | 30 | Real EDA mGy columns. The mSv columns are simulated and scaled (no unit conversion) |
| `*/daily_summary.csv` | `crew_day` (continuous aggregate) | (`crew_id`, `date`) | `crew` | 632 | Days 1 to 158. Feeds `history` and `today`. `hr_rest_bpm` is the median HR over the first 20 min after waking |
| `*/packets.csv` | `packet` (hypertable) | `packet_id` | `crew`, `channel`, `vital_minute` | 51,233 | The frontend Packet, one per metric per 60 s, for days 157 and 158 |
| `*/checkins.csv` | `checkin` | `checkin_id`, unique (`crew_id`, `date`) | `crew` | 119 | Mood, sleep, PVT, symptoms and a morning cuff BP. C1's 06:38 check-in on day 158 has `live_demo=true` (after `demo_now`) |
| `*/sos_events.csv` | `sos_event` | `event_id` | `crew`, `anomaly` | 0 / 1 | Glove triple-tap |
| `*/space_weather_events.csv` | `space_weather_event` | `sep_id` | `anomaly` | 0 / 2 | DONKI SEP layout, marked simulated |
| `*/alerts_seed.csv` | `alert` | `alert_id` (`A1`…) | `crew` | 0 / 7 | A1 is the demo alert (raised at 06:12). The others are resolved history with full timelines |
| `*/messages.csv` | `link_message` | `message_id` (`M1`…) | `alert` | 58 / 82 | Ship and Earth thread: `created_at`, `sent_at`, `deliver_at` (arrived) and status at `demo_now`. Delays are real mission time, not the stage's 60× speed-up |
| `*/reminders.csv` | `reminder` | `reminder_id` | `crew`, `alert` | 0 / 4 | From the accepted fever plan |
| `ground_truth/anomalies.csv` | `anomaly` | `id` | | 17 | Ground truth for scoring |

Mapping to the current backend's tables: `vitals_*` → `reading` (`hr_bpm`→`heart_rate`, `spo2_pct`→`spo2`, `skin_temp_c`→`skin_temp`, `bp_sys_est_mmhg`→`bp_sys`; resp, core temp and activity have no column yet). `checkins` → `reading` with `source=typed`. `alerts_seed` → `alert` plus the new columns the contract asks for. `messages` → `link_message`.

## Anomalies

| id | Crew / hab | When (UTC) | What |
| --- | --- | --- | --- |
| AN01 | C1 | 12 to 14 Nov | Resting HR 80, 82, 84 (band 52 to 64), short sleep, headache, slow PVT: the demo's A1 |
| AN02 | C3 | 6 Nov 14:00 to 15:30 | Gradual hypoxia, SpO2 down to about 88 % |
| AN03 | C2 | 8 Nov 10:40 to 11:00 | Tachycardia of 128 to 138 at rest; the same morning's exercise is the control |
| AN04 | C4 | 10 Nov 02:00 to 02:40 | Bradycardia of 36 to 38 in sleep |
| AN05 | C2 | 2 Nov 08:00 to 23:00 | Fever, core temperature up to about 39 °C |
| AN06 | H2 (C3, C4) | 4 Nov 09:00 to 13:00 | CO2 rises to 5.2 mmHg (scrubber fault); breathing and HR rise in both crew members |
| AN07 | all | 27 Oct | Large SEP event, 2.4 mSv day |
| AN08 | all | 14 Nov from 05:58 | SEP in progress on the demo morning, shelter advisory |
| AN09 | C4 | 11 Nov 16:20 | Glove triple-tap SOS |
| AN10 | C3 | 13 Nov 03:00 to 04:30 | SpO2 drop during the blackout: the report queues and flushes first |
| SF01 to SF04 | C1, C2, C3 | various | Sensor faults: dropout, flatline, impossible spikes, motion artifact |
| NC01 to NC03 | all | all days | Negative controls: exercise HR, sleeping HR, microgravity drift |
