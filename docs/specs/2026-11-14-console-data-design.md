# The console's data: what the ship serves from the generated month

Date: 14 November 2026, evening. Plan: `docs/build-log/plans/2026-11-14-console-contract.md`. Inputs: the frontend owner's API contract (38 endpoints, 14 November), the generated dataset (commit `a25791f`, reviewed in `docs/build-log/reviews/2026-11-14-dataset-review.md`), the console's code on its `feat/alert-loop-and-log` branch, and the backend on `main` at `75d6c5f`.

This spec replaces sections 4 and 5 of `docs/specs/2026-11-14-console-link-design.md` and Tasks 0, 2, 3 and 4 of `docs/build-log/plans/2026-11-14-connect-everything.md`. The ship AI is unchanged except where `docs/specs/2026-11-14-lighttime-ai-design.md` says so.

## 1. Problem

The console is a finished set of screens running on a seed file and rules in the browser. It makes no API call. The backend is a finished ship computer with three invented crew, a distance dial, a delayed link and the ship AI, and no screen. A 30-day dataset now exists that holds everything the console shows. Until the backend serves that data in the shapes the console already uses, the two halves demonstrate different stories on different crews, and nothing a judge sees on the console has passed through the link that the project is named after.

## 2. Goals

1. The console's first four screens (crew overview, astronaut page, check-in, alert loop) can switch from the seed to the API one at a time, with no change to what they show for crew `C1`. Measured: the contract's `C1` example values come back from the API (plan Task 11, the run-through).
2. One crew, one calendar, one set of ids across console, ship and dataset: four crew `C1` to `C4`, mission day 158, alert `A1`.
3. "Restart demo" returns the same morning every time: 14 November 2026, 06:30 UTC, alert `A1` just raised.
4. Every value on a screen says whether it is real NASA data or simulated, and every rule prints its source.
5. Nothing already working breaks: the ship AI, the dial, the link and the Earth routes keep their behaviour and their tests.

## 3. Not doing tonight

- The health data log (`POST /packets`, `GET /packets`, `GET /stream-health`). It is step 5 in the contract's own order, and `packets.csv` is not in git. See section 8, P1.
- Phone push (step 6).
- Loading the minute or second vitals (35 MB) into the database. No screen in steps 1 to 4 reads them.
- Scoring minute data with the ship AI. Its rules assume one reading a second (review finding F3).
- A database table for anything that never changes during the demo. Baselines, daily history, cabin air and thresholds are read from their files.
- Renaming `heart_rate` or `skin_temp`. The console's `hr_rest` and `temp_c` are different measurements (a daily resting value, core temperature) and get their own fields.

## 4. Who uses this

- As the frontend owner, I want each endpoint to return the object my components already take, so that switching a screen is a fetch and an adapter and not a redesign.
- As a crew member at the console, I want my card to show today's values against my own band, so that I can see what is unusual for me.
- As the presenter, I want "Restart demo" to put everything back to 06:30, so that a rehearsal and the pitch show the same thing.
- As a judge, I want to see which numbers are NASA's and which are simulated, so that I can trust the ones that are real.
- As the backend owner, I want the old tests to keep passing, so that tonight's work cannot quietly break the ship AI.

## 5. Decisions

Each one is final for tonight unless the frontend owner objects. D1 to D6 answer the contract's six questions.

| # | Decision | Why |
| --- | --- | --- |
| D1 | Crew: the four in `data/processed/reference/crew.csv`, ids `C1` to `C4`. The team's own names leave the backend | The contract's proposal. One crew everywhere |
| D2 | State names: alerts carry `state` (`OK`, `WATCH`, `ALERT`, `RECHECK`, `SOS`) and keep `level`. `advisory` on a sensor check is `RECHECK`; other `advisory` and `caution` are `WATCH`; `warning` is `ALERT`; `emergency` is `SOS`. A Crew object's `state` is only ever `OK`, `WATCH` or `ALERT` | The console's Crew schema rejects `SOS` and would fail to load. A crew member under a live emergency also carries `level: "emergency"` |
| D3 | Field names: `sleep_h` is the only rename. `hr_rest` (daily resting heart rate) and `temp_c` (core temperature) are new daily values. Raw readings keep `heart_rate` and `skin_temp` | A per-second heart rate is not a resting heart rate, and skin temperature (about 33 °C) is not core temperature (about 36.6 °C). The dataset keeps them apart too |
| D4 | Rules: two sets, each for its own speed. The console rules (daily values against the person's own band) give `metric_states` and `state`. The ship AI's rules (one-a-second readings) give live alerts. Neither replaces the other | The contract's proposal |
| D5 | Ids are strings in every Crew object, Alert object and new endpoint: `C1`, `A1`, `M5`, `R2`. Routes accept the string or the bare number. Raw readings, reports and link messages keep the database number | The console links to `A1` and `C1` by name. Changing the old payloads would break tests and gain nothing: the console does not read them |
| D6 | The flight surgeon's reply is a real message through `POST /api/earth/reply` and takes the light time to arrive. The console's own scripted reply stays in the console as its fallback | The contract's proposal. See open question Q1 |
| D7 | Mission clock: when the demo morning is loaded, the ship's clock is set to 14 November 2026, 06:30:00 UTC and runs forward in real time. Every time the API returns is on that clock | Seeded times (raised 06:12) and new ones (acknowledged 06:31) must make one story. Without this the timeline would read "raised 06:12, acknowledged 19:03 the next day" |
| D8 | The morning is loaded when `LIGHTTIME_MORNING=1` is set in `.env`, at start and on every `POST /api/base/reset`. Without it the backend starts empty, as it does now | The 110 existing tests assume an empty ship. The demo needs the morning |
| D9 | "Today" for a value the crew types (mood, reaction time, cuff blood pressure, symptoms) is the most recent check-in, today's or an earlier one. The check-in accepts optional `bp_sys` and `bp_dia`; when they are missing, the last cuff reading stands | Review finding F5. A card must never show an empty value, and must never show one nobody entered |
| D10 | Static data stays in files. Only what the crew can change is a table: check-ins, reminders, alerts, link messages | Fewer things to migrate and reset |
| D11 | The backend mirrors the console's `scoring.ts`, not the contract's Scoring table and not the text in `thresholds.json` | The three disagree (review F6b). The code is what the screen does today, and "both sides agree" means agreeing with that |
| D12 | Seeded alerts `A4` and `A5` are not loaded | No rule in the console or the ship AI raises them (review F6d). Showing them as past alerts would claim a rule that does not exist |
| D13 | The dial starts on the stop that the dataset's link window gives for 06:30: Mars, 660.86 s one way | The dataset's own link model, and the project's point |
| D14 | Cabin states: the ship gives a state only where it has a sourced limit (CO2 and daily dose). Oxygen, pressure, temperature and humidity come back with `state: null` and the console keeps scoring them as it does now | The backend rule is that every threshold has a source. The console's bands for those four have none in `thresholds.json` |

## 6. Where each thing comes from

| What the console shows | File or table | Notes |
| --- | --- | --- |
| Mission day, platform | `reference/mission.csv` | Day = mission clock date minus `launch_date`, plus 1. Platform is `ISS` |
| Crew id, name, role, suit | `reference/crew.csv` | Loaded into the `crew` table at first start |
| Baseline bands | `reference/baselines.csv` | Read from the file |
| Today's suit values: `hr_rest`, `spo2`, `temp_c`, `resp`, `sleep_h`, `dose_mSv_day` | `anomalous/daily_summary.csv`, the row for the mission date | `hr_rest_bpm`, `spo2_pct`, `core_temp_c`, `resp_rpm`, `sleep_h`, `dose_msv_day` |
| Today's typed values: `mood`, `pvt_ms`, `bp`, `symptoms` | `checkin` table | Seeded from `anomalous/checkins.csv`, except rows flagged `live_demo` |
| `dose_mSv_mission` | `anomalous/radiation_daily.csv` | The same for all four crew |
| History | `anomalous/daily_summary.csv` | Up to 30 days. Today's point uses today's values |
| Station strip | `anomalous/cabin_env.csv`, Hab A (`H1`), latest row at or before the mission clock | CO2, temperature and humidity are NASA's Rodent Research 1 record, replayed |
| Space weather | `anomalous/space_weather_events.csv` | The event that covers the mission clock, if any. Always `simulated: true` |
| Rule text and sources | `data/reference/console_thresholds.json` | A copy of the console's `src/data/thresholds.json` |
| Alerts `A1`, `A2`, `A3`, `A6`, `A7` | `alert` table | Seeded from `anomalous/alerts_seed.csv` |
| Threads | `link_message` table | Seeded from `anomalous/messages.csv`, for loaded alerts and routine messages |
| Reminders | `reminder` table | Seeded from `anomalous/reminders.csv` (four, all done) |
| Dial position at 06:30 | `reference/link_windows.csv` | Mars |

Never read by the ship: `ground_truth/`, `reports/`, `clean/`, `sos_events.csv` (the glove tap is history already shown by alert `A6`), `vitals_1min.csv`, `vitals_1hz_demo.csv`, `channels.csv`, `metrics.csv`, `thresholds.csv` (its sources are pending; the console's file is the authority).

## 7. The objects

Fields the contract lists are returned exactly. Extra fields are marked "added" and are safe to ignore.

### Crew

`id`, `name`, `role`, `suit_id`, `state`, `note`, `baseline`, `today`, `metric_states`, `last_packet_at` as in the contract. Added: `level` (the ship AI's worst open level for this person), `latest`, `typed`, `usual` (the old crew board fields, unchanged), and `checkin_from` (the date of the check-in that `today`'s typed values come from, so a card can say "from yesterday").

- `baseline` has `hr_rest`, `spo2`, `temp_c`, `resp`, `sleep_h` as `[low, high]`, `bp` as `[[low, high], [low, high]]`, and `pvt_ms` and `vo2max_ml_min_kg` as numbers.
- `today` has `hr_rest`, `bp` as `[sys, dia]`, `spo2`, `temp_c`, `resp`, `sleep_h`, `mood`, `pvt_ms`, `symptoms`, `dose_mSv_day`, `dose_mSv_mission`.
- `note` is built from a template: "All in band", or "Out of band: " and the flagged measurements, then the symptoms.
- `last_packet_at` is the time of the person's latest live reading, or one minute before the dataset's `demo_now` when there is none (the dataset's last minute row is 06:29).

### Console rules (`metric_states`)

The same steps as the console's `scoring.ts`, in the same order:

1. `ALERT` if blood oxygen is under 94, core temperature is over 38.0, or the day's dose is over 2 mSv.
2. Otherwise `OK` unless the value is out of range for its measurement: resting heart rate and blood pressure outside the band; blood oxygen below the band; core temperature above the band; breathing over 20 a minute; sleep below the band or under 6.5 h; mood 2 or lower; reaction time over the baseline plus 15 %; dose never.
3. An out-of-range value is `ALERT` if the person has any symptom today, or if a banded measurement has been outside its band three days running counting back from today. Otherwise `WATCH`.

Checked with a script against the dataset: at 06:30 crew `C1` is `ALERT` on resting heart rate, temperature and sleep. After the live check-in (mood 2, 312 ms, headache, cuff 128/82) `C1` matches the contract's example on all ten measurements.

### Alert

Contract fields: `id`, `crew_id`, `crew`, `metric`, `value`, `unit`, `state`, `stage`, `reason`, `rule`, `source`, `nasa_risk`, `symptoms`, `steps`, `steps_done`, `timeline`, `speak`. Kept from before: `level`, `vital`, `at`, `auto`, `acknowledged_by`, `cleared_at`, `cleared_by`, `cleared_note`, `why`, `lookahead`, and `timeline.earliest_reply_at`.

- `stage` is worked out, not stored: `resolved` once cleared; else `replied` once a reply has arrived; else `sent` once the report has left; else `acknowledged`; else `raised`.
- For an alert raised by a console rule, `rule` and `source` come from `console_thresholds.json` and `unit` from the same file. For a live alert from the ship AI they come from `limits.json`, and `metric` is the vital's name (`spo2`, `bp_sys`), `signal` for a sensor check or `manual` for an SOS press.
- A live emergency reaches stage `sent` before anyone acknowledges it, because the ship sends its report by itself.

### ThreadMessage, Reminder

As in the contract. A thread holds every message for one alert that the ship has sent, and every message from Earth that has arrived. A report or update that has no text of its own gets one line built from its payload. Added: `kind` (`report`, `update`, `message`, `reply`).

### Errors

`400` with `{"error", "field"}` and `404` with `{"error": "not found"}`, on every `/api/base` route.

## 8. Requirements

### P0: tonight, in the contract's build order

**R1. Crew overview (contract step 1).** `GET /crew` returns four Crew objects. `GET /state` adds `mission_day` and `platform`. `GET /station`, `GET /space-weather` and `GET /checkins/today` exist. `GET /alerts?open=1` returns Alert objects.
- [ ] Given the morning is loaded, when the crew list is read, then the first item has `id` `C1`, `name` `Okafor`, `today.hr_rest` 84, `today.temp_c` 37.2, `today.sleep_h` 5.1 and `state` `ALERT`.
- [ ] Given the morning is loaded, then `GET /state` gives `mission_day` 158 and `platform` `ISS`, and the stop is Mars.
- [ ] Given the morning is loaded, then `GET /checkins/today` gives `done` `C2`, `C3`, `C4`, `due` `C1`, `streak` 12, `next_badge_at` 14.
- [ ] Given the morning is loaded, then `GET /space-weather` gives `state` `WATCH`, `event_at` 05:58 and `simulated` true.
- [ ] Given the morning is loaded, then `GET /station` gives a CO2 value in mmHg with a state, marks CO2, temperature and humidity as not simulated and oxygen, pressure and dose as simulated, and names NASA's Environmental Data App as the source.
- [ ] Given the morning is loaded, then the one open alert has `id` `A1`, `metric` `hr_rest`, `value` 84, `state` `ALERT`, `stage` `raised` and the heart rate checklist as `steps`.
- [ ] No response anywhere contains the word "pending".

**R2. Astronaut page (step 2).** `GET /crew/<id>`, `GET /crew/<id>/history?metric=&days=`, `GET /thresholds`.
- [ ] Given `C1` and `hr_rest`, then the last three of seven days are 80, 82, 84, `band` is `[52, 64]`, `days_out_of_band` is 3 and `simulated` is true.
- [ ] Given a metric with no band (`mood`), then `band` is null.
- [ ] Given an unknown metric, then 400 with `field` `metric`. Given an unknown crew, then 404.
- [ ] `GET /thresholds` has the ten console metrics and `co2_mmHg`, each with `unit`, `watch`, `alert` and `source`.

**R3. Check-in (step 3).** `POST /crew/<id>/checkins`.
- [ ] Given `C1` posts mood 2, sleep 5.1, headache, 312 ms, then 201 with `first_today` true, `streak` 13, `metric_states` `ALERT` for sleep, mood and reaction time, and `open_alert_id` `A1`.
- [ ] Given the same crew posts again that day, then `first_today` is false and the streak stays 13.
- [ ] Given mood 6, then 400 with `field` `mood`. The same for sleep outside 0 to 24, a note over 500 characters, reaction time outside 100 to 3000 and a symptom not on the list.
- [ ] The symptoms are copied onto that person's open alerts.

**R4. Alert loop (step 4).** `GET /alerts/<id>`, `ack` with symptoms, `send` with the 7-day bundle, `GET /alerts/<id>/thread`, `POST /alerts/<id>/accept-plan`, `GET /reminders`, `POST /reminders/<id>/done`, `POST /reset`.
- [ ] Given `A1` is acknowledged and sent, then its stage is `sent`, the report in the outbox carries seven days of resting heart rate, blood pressure, temperature and sleep and today's check-in, and the thread has one message from the crew.
- [ ] Given Earth replies to that report, when the light time has passed, then the stage is `replied` and the thread has two messages.
- [ ] Given the stage is `replied`, when the plan is accepted, then the stage is `resolved`, four "Take temperature" reminders exist four hours apart, and Earth is told.
- [ ] Given the stage is not `replied`, when the plan is accepted, then the alert comes back unchanged with no reminders and status 200.
- [ ] Given anything has been done, when the demo is reset, then `A1` is back at `raised`, `C1` is due for check-in, the streak is 12, no reminder is open and the clock reads 06:30.

**R5. Nothing old breaks.** The 110 existing tests pass, with expectations changed only for the crew's names and the string ids listed in the plan.

### P1: Sunday morning, only if the run-through passed

- **Health data log (step 5).** Needs `packets.csv` rebuilt (`python data/scripts/build_all.py`), a `packet` table, and the sensor names settled between the dataset (`pulse_ox`, `bp_est`) and the console's schema (`ppg`, `cuff`).
- **Cabin CO2 on a live clock.** After 06:30 the station strip holds its last row. Replaying the next rows of the NASA record would keep it moving.
- **Live values on the cards.** The ship AI's `latest` reading is already on each Crew object; the console could show it beside the daily value.

### P2: later

- Push notifications.
- A parsed treatment plan in place of the fixed "temperature every 4 hours".
- Contact windows from `link_windows.csv` driving the dial by themselves.

## 9. For the frontend owner

What the code on `feat/alert-loop-and-log` needs when a screen switches to the API. None of it is a backend change.

1. **Adapter names.** The store uses `crewId`, `raisedAt`, `acknowledgedAt`, `sentAt`, `replyAt`, `resolvedAt`, `dueAt`, `completedAt` and a single `at` on messages. The API returns `crew_id`, `timeline.raised_at` and so on, `due_at`, `completed_at`, and `sent_at` with `arrived_at`.
2. **`Alert.metric` is a strict list in the store.** Live alerts from the ship AI arrive with `signal` or `manual`, which that list rejects. Parse alerts one by one and keep the ones that pass, or widen the list.
3. **Times are UTC on the mission clock.** The console prints times in the browser's zone, so 06:12Z shows as 01:12 in Ontario. Format with `timeZone: "UTC"`.
4. **Cabin values differ from the seed, and that is the point.** At 06:29 Hab A's CO2 is 2.99 mmHg, over the 2.8 line, because it is NASA's real record. Oxygen is 156.5, pressure 101.39, temperature 22.9, humidity 50.
5. **`C2` to `C4` differ from the seed** until the dataset is rebuilt from `crew-seed.json` (review F4). `C4` scores `ALERT` on sleep.
6. **The history chart must take a null** (a day with no value) and up to 30 points.
7. **Rule text and rule code disagree** for blood pressure, breathing, sleep, mood and reaction time, and the heart rate text ("baseline + 20 for 3 days") is stricter than the rule that raises `A1`. The alert page prints the text. One of the two should change.
8. **The check-in sends no blood pressure.** If the cuff step in the check-in flow has the reading, add `bp_sys` and `bp_dia` to the body.
9. **A source to check before the pitch:** the console rewrites "NASA-STD-3001 V1 3004 vital-sign trending" to "V1 3004 In-Mission Medical Care". The backend repeats the console's wording and has not checked it against the standard.

## 10. Risks

| Risk | Sign | What to do |
| --- | --- | --- |
| The hosted Postgres has the old tables | `column crew.code does not exist` at start | Plan Task 2, step 6: drop the demo tables once and restart |
| The mission clock leaks between tests | An unrelated test fails on a time | `conftest.py` puts the clock back before every test (plan Task 1) |
| The dataset is rebuilt with other values | A test on `C2` to `C4` fails | The tests pin `C1` only. If one pins another crew, the test is wrong |
| The console polls four crew objects a second and each reads 632 rows | Slow responses on the venue laptop | The files are read once and kept in memory. If it is still slow, cache the crew list for one second |
| The demo runs past midnight on the mission clock (17.5 hours after a reset) | "Today" has no row | "Today" is the last day the dataset has. Reset before that |

## 11. Open questions

- **Q1 (team, blocking for the pitch, not for the build).** There is no Earth screen yet. Decision D6 needs someone to send the reply: an Earth page in the console (the old plan's Task 4, to be re-pointed at this API), or the console's scripted reply calling `POST /api/earth/reply` instead of the store.
- **Q2 (frontend owner).** Is carrying yesterday's check-in forward on the card acceptable (D9), with `checkin_from` to label it?
- **Q3 (frontend owner).** What is the badge rule? The backend assumes the next multiple of 7 above the streak, which gives the contract's 14.
- **Q4 (data owner).** Rebuild from `crew-seed.json` tonight or leave `C2` to `C4` as they are (review F4)?
- **Q5 (data owner, frontend owner).** Which sensor names does the log use (review F6k)? Needed before P1.
