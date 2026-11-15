# LIGHT-TIME backend spec

Date: 14 November 2026. Owner: The backend owner. Status: approved by the backend owner at 11:02, updated at 11:45 after the frontend owner's screens and the CSA workshop.

Build plan: `docs/plans/2026-11-14-backend-saturday.md`. The plan's code was built in a scratch folder before this was sent. All 45 tests pass on SQLite and on Postgres 16, and the Mars story was played end to end over HTTP on Postgres.

## Problem

On a trip to Mars a message to Earth takes 3 to 22 minutes each way, and sometimes there is no link at all. A crew member who collapses cannot wait for a doctor who will not hear about it for 11 minutes. Our three screens (suit, base station, Earth) need one ship computer behind them that watches the crew, decides when to raise the alarm, tells the crew what to do, and sends Earth a report that arrives late, the way it would in flight.

## Goals

1. A reading posted by the suit shows on the crew board within one second (block 1).
2. Five bad readings in a row raise one SOS that says why. A loose sensor raises "check your sensor" and never an SOS (block 2).
3. At the Mars stop, Earth cannot see a report until the real light time has passed (11 minutes, played in 11 seconds), and a reply takes the same time back (block 3).
4. The frontend owner's alert screen (acknowledge, send to flight surgeon, round trip, thread with ground) runs on real data, not mock data.
5. Reset and start replay the same story every time, with no server restart.
6. Every number on a screen has a named source, and simulated readings are labelled.

## Not doing

| Left out | Why |
| --- | --- |
| Logins and roles | Two-day demo on our own network |
| A language model on stage | Rules and templates cannot stall or make things up in front of judges |
| A real delay-tolerant network | We model the delay and the queue, not the protocol |
| Diagnosis or treatment advice | The checklist text is demo wording until the documentation owner sources it |
| Baselines, habitat tiles, space weather, check-in schedule, FHIR export | Sunday work, one short plan each, only if the 16:15 run works |

## Who uses it

The astronaut in the suit (Okafor) needs his readings checked every second, so the ship calls for help when he cannot. The crew medical officer at the base station (the frontend owner) needs an alert that says why it fired and what to do, so he can act without waiting for Earth. The flight surgeon on Earth (a judge, with the documentation owner as backup) needs to see only what has reached Earth and how old it is. The person driving the demo (the reviewer) needs one reset call and one start call. The people building screens (the frontend owner, Okafor) need plain JSON they can poll once a second.

## Words we use

| Word | Meaning |
| --- | --- |
| Reading | One set of numbers for one person at one time. Sensed (source `suit` or `scenario`) or `typed` (a check-in) |
| Alert | Something the ship noticed about one vital of one person. Levels: advisory, caution, warning, emergency |
| SOS | An emergency alert. It sends a report to Earth by itself |
| Dial stop | Where the mission is: `station`, `moon`, `mars`, `sun` |
| Delay | One-way light time in seconds. The API always gives the true value |
| Mode | Who decides: `doctor_live`, `crew_first` or `ship_alone` |
| Report, update, message, reply | The four link messages: the handoff for one alert, a thing the crew did (acknowledged, step, resolved), free text from the crew, and Earth's answer |
| Round trip | One alert's path: raised, acknowledged, sent, Earth hears, reply, resolved |
| Speed-up | Delays of a minute or more play 60 times faster on stage. The screens say so |

## Decisions

1. **One Flask app, two blueprints.** `base_station/` serves `/api/base/*` (the ship). `command_center/` serves `/api/earth/*` (the ground). The folder names follow the repo README, with underscores so Python can import them. One process and one port, so there is one thing to start on stage.
2. **Earth sees a report, not the raw stream.** The command center reads only the link table, never the ship's tables. Crew readings stay on the ship unless an alert sends them. This is also our answer to the CSA's advice to keep privacy in mind through the whole life of the data.
3. **One Postgres database.** Set by `DATABASE_URL`. Without it the app falls back to a local SQLite file, so tests and a one-laptop demo run with nothing installed.
4. **The delay is a rule, not a network.** Every message between ship and Earth is a row in `link_message` with a `deliver_at` time. The other side cannot see the row until that time passes. In a blackout the row waits with no send time, and the queue flushes, SOS first, when the dial moves off "Behind the Sun".
5. **Long delays play 60 times faster, and the server keeps the clock.** A delay of 60 s or more plays at one sixtieth, so 11 minutes takes 11 seconds. Each message carries `eta_s`, the mission time left until it lands, worked out on the server, so laptops with different clocks still agree.
6. **Mars light time is real.** It comes from NASA JPL Horizons (quantity 21, one-way light time). If the fetch fails, the app uses the values read from Horizons on 13 November and says so: 660.86 s (14 Nov), 656.62 s (15 Nov), 652.36 s (16 Nov).
7. **Who decides is one rule on the delay.** No link: the crew alone. One-way delay of 300 s or more: the crew medical officer. Otherwise: the flight surgeon on Earth. The 300 s line comes from NASA's NEEMO 16 test (Rader et al. 2013).
8. **Alerts come from fixed rules, and each one names its source.** Bands for blood oxygen, heart rate and systolic blood pressure follow the NEWS2 chart (Royal College of Physicians 2017). NEWS2 is a hospital score and is not validated for space, so we say our tiers are "inspired by" it. Band 1 is a caution, band 2 a warning, band 3 an emergency. Level names are NASA's.
9. **It does not cry wolf.** A suit reading must stay out of range for 5 readings in a row with a clean signal before it alerts (5 seconds at one reading a second). A bad signal raises "check your sensor" and nothing else.
10. **Acknowledge and resolve are two steps.** Acknowledge means a person has it. Resolve clears it. After a person resolves an alert, that vital stays quiet for 60 seconds unless it gets worse, like the alarm pause on a bedside monitor. The manual SOS button always works.
11. **An SOS goes to Earth by itself. Anything less goes when the crew sends it.** A typed-in reading can raise a warning at most, so a typo cannot send an SOS. Earth gets updates only about alerts it already has a report for.
12. **The round trip is one object.** Every alert carries a `timeline` with the six times of its round trip, so the stepper on the alert screen needs one call.
13. **The story answers the crew.** In the scripted story the patient's blood oxygen stays low until the crew ticks the treatment step, then recovers. What the crew does on stage changes the numbers before Earth has heard anything.
14. **The "ship AI" on Saturday is rules plus a report writer.** An emergency builds a handoff report (situation, background, assessment, request) and a line for the ship to speak. Personal baselines are Sunday work.

## Requirements

Must have on Saturday. Each one has tests in the plan.

| Requirement | How we know it works | Plan task |
| --- | --- | --- |
| Store readings and show a crew board | `tests/test_base_api.py` | 1, 4 |
| Real Mars light time with a dated fallback | `tests/test_lighttime.py` | 2 |
| Dial with four stops and the who-decides rule | `tests/test_modes.py`, `tests/test_base_api.py` | 2, 4 |
| Link that hides messages until they arrive, queues in a blackout, flushes SOS first | `tests/test_link.py` | 3 |
| Alerts with a sustained check, a sensor check and an alarm pause | `tests/test_rules.py` | 5 |
| SOS with reason, source, NASA risk, checklist, spoken line and Earth report | `tests/test_base_api.py` | 6 |
| Acknowledge, send to Earth, crew message, round-trip timeline | `tests/test_base_api.py`, `tests/test_earth_api.py` | 6, 7 |
| Earth inbox and delayed reply | `tests/test_earth_api.py` | 7 |
| Scripted story that answers the crew, with reset | `tests/test_scenario.py` | 8 |
| Runs on Postgres | Task 9 by hand | 9 |

Sunday, in this order, if Saturday's run works:

1. A week of history and personal baselines. This feeds the trend chart, the baseline numbers and the "over baseline for 3 days" alert on the frontend owner's screens.
2. Habitat tiles on real data: ISS cabin readings from NASA's Environmental Data App and space weather from NASA DONKI. The links and the download steps are in `docs/data-sources.md`.
3. One line on the Earth console from NASA's Deep Space Network Now feed: the round-trip light time NASA's own antennas are waiting on for Mars.
4. CSA's open heart-rate filter (github.com/asc-csa/heart-rate-filtering, MIT licence) as a noise rule in front of the sustained check.
5. The check-in schedule and reminders.
6. An "outside at Mars" tile from the CSA's Phoenix weather station data.

Later: FHIR export, logins, a real DTN stack.

## Tables

| Table | Holds |
| --- | --- |
| `crew` | id, code (`C1`), name, role, suit_id; seeded from `data/processed/reference/crew.csv` |
| `reading` | crew_id, at, source (suit, typed, scenario, replay), context, signal_ok, heart_rate, spo2, skin_temp, bp_sys, bp_dia, glucose, sleep_hours, mood (1 to 5) |
| `alert` | crew_id, at, level, vital, value, reason, auto, nasa_risk, steps_done, acknowledged_at, acknowledged_by, report_id, cleared_at, cleared_by, ref (`A1` for an alert loaded with the morning), metric, symptoms |
| `checkin` | crew_id, day, completed_at, mood, sleep_h, pvt_ms, bp_sys, bp_dia (the morning cuff), symptoms, note; one row per person per day |
| `reminder` | crew_id, alert_id, text, due_at, done_at |
| `mission_state` | one row: the dial stop |
| `link_message` | direction (to_earth, to_ship), kind (report, update, message, reply), priority, payload, created_at, sent_at, delay_s, deliver_at, in_reply_to |

## API for the screens

All JSON. The screens poll once a second.

| Call | Used by | Gives |
| --- | --- | --- |
| `GET /api/base/state` | base, suit | `mission_day` (day 1 is the launch date; it stops on the dataset's last day, as the console's dates do) and `platform` (changed: added by the console contract), dial stop, label, delay_s (Mars light time for the mission date: 660.86 s on the demo morning), link_up, mode, who_decides, light_time_source, path_km (delay x speed of light), round_trip_s (2 x delay), plays_as_s (real seconds one leg takes in the demo), ship_ai_role (what LIGHTTIME does at this distance), speedup, all four stops, and `ship_ai` (name, line, version, parts) |
| `POST /api/base/dial` `{stop}` | base | new state; flushes the queue when the link is back |
| `POST /api/base/readings` | suit, hardware, check-in | stores a reading, runs the rules, returns any alerts raised. `crew_id` may be `"C2"` or `2`. A value that is not a finite number, an unknown `crew_id`, or a `source` or `context` that is not text of at most 12 characters gets 400 naming the field |
| `GET /api/base/crew` | base | changed: four Crew objects (`id` is `"C1"` to `"C4"`, `name`, `role`, `suit_id`, `state`, `note`, `baseline`, `today`, `metric_states`, `checkin_from`, `last_packet_at`), plus the ship AI's `level`, `latest` sensed reading, `typed` reading and `usual` |
| `GET /api/base/crew/<id>` | console | one Crew object. `<id>` is `C1` or `1` everywhere a crew id appears in a path |
| `GET /api/base/crew/<id>/history?metric=&days=7` | console | `crew_id`, `metric`, `unit`, `band` (null without one), `days` (`date`, `value`, up to 30), `days_out_of_band`, `simulated`. An unknown metric gets 400 with `field` `metric` |
| `GET /api/base/crew/<id>/readings?limit=120` | base | readings for the trend chart, oldest first |
| `GET /api/base/thresholds` | console | the printed rules: for each console metric and `co2_mmHg`, `unit`, `watch`, `alert` and `source` |
| `GET /api/base/station` | console | cabin `co2_mmHg`, `ppo2_mmHg`, `pressure_kPa`, `temp_c`, `rh_pct` and `dose_mSv_today`, each `{value, state, simulated}`, plus `updated_at`, `habitat`, `source` |
| `GET /api/base/space-weather` | console | `state`, `headline`, `advisory`, `event_at`, `source`, `simulated` |
| `GET /api/base/checkins/today` | console | `date`, `done` and `due` (crew ids), `streak`, `next_badge_at` |
| `POST /api/base/crew/<id>/checkins` `{mood, sleep_h, symptoms, note, pvt_ms, bp_sys, bp_dia}` | console | saves today's check-in (a second one the same day replaces it), copies the symptoms to the person's open alerts; 201 with `crew_id`, `completed_at`, `first_today`, `streak`, `metric_states` (sleep, mood, reaction time), `open_alert_id`. A bad field gets 400 naming it |
| `GET /api/base/alerts?open=1` | base, suit | changed: alerts, each with the fields listed below; `id` is `"A1"` and `crew_id` `"C1"` |
| `GET /api/base/alerts/<id>` | console | one alert. `<id>` is `A1` or `1` everywhere an alert id appears in a path |
| `GET /api/base/alerts/<id>/thread` | console | `alert_id` and `messages` (`id` `"M5"`, `alert_id`, `from` crew or ground, `author` (`"Ship (auto SOS)"` for the report an SOS sends by itself), `text`, `kind`, `sent_at`, `arrived_at`, `status`), oldest first: everything sent about the alert, and what has arrived from Earth |
| `POST /api/base/alerts/<id>/accept-plan` `{by}` | console | once Earth's reply has arrived: resolves the alert, sets four "Take temperature" reminders four hours apart and tells Earth; returns `alert` and `reminders`. Before that it changes nothing |
| `GET /api/base/reminders?crew=&open=1` | console | reminders: `id` `"R1"`, `crew_id`, `text`, `due_at`, `done_at` |
| `POST /api/base/reminders/<id>/done` | console | ticks a reminder off |
| `POST /api/base/alerts/<id>/ack` `{by, symptoms}` | base | a person acknowledges the alert (changed: `symptoms` are kept on the alert) |
| `POST /api/base/alerts/<id>/steps` `{index}` | base | ticks a checklist step |
| `POST /api/base/alerts/<id>/send` | base | sends a report to the flight surgeon (an SOS has already gone). Changed: for an alert raised by a console rule the report's payload adds `bundle` (seven days of `hr_rest`, `bp_sys`, `bp_dia`, `temp_c`, `sleep_h`, today's check-in, and `simulated: true`) and `text`; its `why` is the lines the crew sees, and it carries no strip of readings (`recent` is empty, `usual` and the sbar's latest vitals are left out, `asked_ahead` is empty) |
| `POST /api/base/alerts/<id>/clear` `{by, note}` | base | a person resolves the alert; `note` is their reason in their own words (up to 280 characters), kept as `cleared_note` and sent to Earth with the resolved update; a note that is not text gets 400. `by` is cut to 40 characters |
| `POST /api/base/sos` `{crew_id}` | suit | manual SOS |
| `POST /api/base/messages` `{text, alert_id, from}` | base | free text from the crew to the flight surgeon. An `alert_id` that matches no alert gets 400 with `field` `alert_id` |
| `GET /api/base/outbox` | base | everything the ship has sent, with status (queued, in_flight, delivered), eta_s and the three times |
| `GET /api/base/inbox` | base, suit | replies from Earth that have arrived |
| `POST /api/base/scenario/start` `{name, replay}` and `/scenario/stop` | base | starts or stops the scripted story ("stage", "full" or "real"; `replay: true` plays real wrist data) |
| `GET /api/base/habitat` | base | cabin temperature, humidity, CO2 and radiation dose, with source and date (NASA EDA, RR-1) |
| `POST /api/base/summary/send` | base | sends the daily summaries to Earth (link kind `summary`) |
| `GET /api/base/sources` | base | every outside source the app uses: id, agency, name, kind (live, file, hand), url, used_for, as_of |
| `POST /api/base/reset` | base | clears readings, alerts, messages, check-ins and reminders for a fresh run. Changed: in morning mode (`LIGHTTIME_MORNING=1`) it loads the demo morning again, 14 November 2026 at 06:30 UTC with `A1` raised |
| `GET /api/earth/inbox` | earth | link_up, mode, and everything that has arrived |
| `POST /api/earth/reply` `{message_id or alert_id, text, from}` | earth | sends advice back, with the same delay. `alert_id` replies to that case's report. 400 `{error, field}` for bad input, 404 for a message or case Earth has not received |
| `GET /api/earth/state` | earth | link_up, delay_s, mode, who_decides, light_time_source, speedup, last_contact_at, last_contact_age_s, arrived, ground_outbox counts (added 14 Nov by Ore) |
| `GET /api/earth/cases` | earth | one case per alert whose report has reached Earth, open and most serious first (added 14 Nov by Ore) |
| `GET /api/earth/cases/<alert_id>` | earth | one case, plus the report's SBAR, steps and recent readings; 404 if Earth has not received it (added 14 Nov by Ore) |
| `GET /api/earth/cases/<alert_id>/thread` | earth | every message about the case Earth can see, oldest first, in the contract's ThreadMessage shape (added 14 Nov by Ore). Ids on `/state`, `/cases` and the thread are the ship's string ids (`alert_id` `"A1"`, `crew_id` `"C1"`, message `id` and `in_reply_to` `"M5"`); `<alert_id>` and the reply's `alert_id` or `message_id` take `A1` or `1` |
| `GET /api/earth/network` | earth | two NASA figures for the Mars delay side by side: `passes` (dish, craft, round_trip_s from DSN Now), `source`, `url`, `dsn_one_way_s` (median round trip / 2, or null when no antenna is on Mars), `horizons_one_way_s` (for today's real date, the moment DSN Now measures; the dial's `delay_s` is for the mission date, so on the demo morning the two differ by a few seconds), `differ_s` |
| `GET /api/earth/outbox` | earth | everything Earth has sent, newest first, with status and eta_s, so Earth can watch its reply in flight |

The shapes of the console's objects (Crew, the console rules, Alert, ThreadMessage, Reminder, errors) are in `docs/specs/2026-11-14-console-data-design.md` section 7. Errors on `/api/base` are JSON: 404 is `{"error": "not found"}` (also for a path no route has), 400 is `{"error", "field"}`, and a method a route does not take is 405 `{"error": "method not allowed"}` with the usual `Allow` header.

An alert carries: `id` (`"A1"`), `crew_id` (`"C1"`), `crew`, `at`, `level`, `state` (`WATCH`, `ALERT`, `SOS`, or `RECHECK` for a sensor check), `stage` (`raised`, `acknowledged`, `sent`, `replied`, `resolved`, worked out from the times), `metric` (the console metric, or the vital's name, `signal` or `manual`), `rule`, `symptoms`, `vital`, `value`, `unit`, `reason`, `source`, `auto`, `nasa_risk`, `steps`, `steps_done`, `next_step` (the first step not yet ticked, or null), `acknowledged_by`, `cleared_at`, `cleared_by`, `cleared_note`, `why` (how the ship reached the alert, in plain lines: what was seen, the last readings, the rule, the band table, and who decides), `speak` (for an emergency or a falling trend; say it once per alert id and level), `lookahead` and `timeline`.

`lookahead` is null unless a falling trend was found. It holds `now`, `per_min`, `eta_s`, `red_line`, `at`, `red_line_at`, `reply_s`, `earth_in_time` and `agreement` (how steady the fall is, 0.5 to 1), frozen when the report left, so count down to `red_line_at`. The crew board adds `usual.heart_rate` (`low`, `high`, `n`, or null for the first ten minutes). Details: `docs/specs/2026-11-14-ship-ai-and-data-design.md` section 7.

The `timeline` holds `raised_at`, `acknowledged_at`, `sent_at`, `earth_eta_s`, `earth_at`, `earliest_reply_at`, `reply_at` and `resolved_at`. A time is null until that step has happened. `earliest_reply_at` is the report's landing time plus the same leg back, as if the doctor answered at once; it is null while the report waits in the queue. It is on the demo clock, like every link time; `lookahead.red_line_at` is real time, so screens use `earth_in_time` for the verdict. `earth_eta_s` counts down in mission time to the moment Earth hears.

The three times on a sent message are `sent_at`, `arrives_after_s` (the one-way delay) and `earliest_reply_after_s` (twice the delay). Every update, message and reply carries `payload.alert_id`, so the thread for one alert is the outbox and inbox filtered by that id. A report's payload also carries `why`, the same lines the crew sees on the alert, and `raised_at`, when the alert was raised (UTC, the same as the alert's `at`), so Earth can tell how old the problem is and not only when the report left. The reports loaded with the demo morning carry it too.

## the frontend owner's screens against the API

| On the lo-fi screens | Comes from | Saturday |
| --- | --- | --- |
| Header: ground link, one-way delay | `GET /api/base/state` | Real. Show these values, not fixed text. NASA's range for Mars is 3 to 22 minutes |
| Crew cards: heart rate, SpO2, temperature | `/crew`, under `latest` | Real. Label the tile "Skin temp": the suit reads skin temperature, as the CSA's Bio-Monitor does |
| Crew cards: blood pressure, sleep, mood | `/crew`, under `typed` | Real once a check-in is posted. Mood is 1 to 5 |
| OK, WATCH, ALERT badges | `level` | Use the map below, and add an SOS state |
| Alert list and alert detail | `/alerts?open=1` | Real: `reason`, `value`, `unit`, `source`, `nasa_risk` |
| "What to do now" | `steps`, `steps_done` | Real |
| Round trip stepper | `timeline` | Real. Add "Earth hears" between "Sent to ground" and "Flight surgeon reply" |
| Acknowledge, Send to flight surgeon | `/ack`, `/send` | Real |
| Thread with ground and its message box | `/outbox`, `/inbox`, `/messages` | Real |
| Restart demo | `/reset`, then `/scenario/start` | Real |
| Check-in steps 2 and 3 | `POST /readings` with `source: "typed"` | Real |
| Trend chart | `/crew/<id>/readings` | Real for the live minutes. The 7-day view is Sunday |
| Baseline numbers and "over baseline for 3 days" | Not built | Sunday, first in line. Mock and label it until then |
| Cabin CO2, pressure, radiation, space weather tiles | Not built | Mock, labelled SIMULATED. Do not print "DONKI" or "RadLab" on a mocked tile |
| Schedule, streaks, badges, reaction test, body map | Frontend only | Frontend only |

| API level | Badge on screen | NASA name |
| --- | --- | --- |
| `nominal` | OK | |
| `advisory`, `caution` | WATCH | Advisory, Caution |
| `warning` | ALERT | Warning |
| `emergency` | SOS | Emergency |

Three more notes for the screens. The crew the API returns is Okafor, the frontend owner and the hardware owner, the people on stage; the names on the lo-fi are placeholders. Source lines printed on a card should come from the API's `source` field or from the documentation owner's checked list: NASA lists V1 3004 as "In-Mission Medical Care", not "vital-sign trending". The lo-fi's example alert is a slow trend; Saturday's live alert is the collapse, so the alert screen needs a red SOS look and the spoken line.

## Data sources

| Source | Used for | Box on the project page |
| --- | --- | --- |
| NASA JPL Horizons API | Real Earth to Mars light time | NASA Data |
| NASA-STD-3001 Volume 2 | Alert level names | NASA Data |
| NASA HRP risks page (challenge resource) | A NASA risk label on each alert, such as "Risk of Hypoxia" | NASA Data |
| NASA HRP five hazards page (challenge resource) | "Distance from Earth" as the hazard we take on | NASA Data |
| CSA "Why do we conduct science experiments in space?" (challenge resource) | Names communication delay and emergency medical help as deep-space risks | Space Agency Partner |
| CSA Topical Teams 2023 report, Astronaut Health chapter | The Canadian research community asks for this: AH-EHI-06 (autonomous healthcare decision-making AI), AH-05 (monitoring that explains itself), AH-03 (guidance that does not wait on the ground) | Space Agency Partner |
| CSA Bio-Monitor pages | The model for what the suit measures | Space Agency Partner |
| NEWS2, Royal College of Physicians 2017 | Alert bands | Other Data |
| Our own scripted readings | Crew vitals, labelled SIMULATED | Other Data |

If we use any file from the CSA open data portal, the project page must name the source and link the Open Government Licence - Canada. That is the licence's condition.

## Risks

| Risk | What we do |
| --- | --- |
| The venue Wi-Fi stops laptops reaching each other | Test from the frontend owner's laptop in block 1 (plan Task 4, step 5). Fall back to a phone hotspot, then to one laptop |
| Horizons cannot be reached from the venue | The dated values load by themselves and the screen says so |
| The screens and the API drift apart | The table above is the contract. A field or route changes only together with this file |
| The hardware sends faster or slower than once a second | "5 readings in a row" still holds; the wording "for 5 s" in the reason needs a tweak |
| A printed source is wrong | The documentation owner checks every source line on a screen before the 16:15 run |

## Open questions

| Question | Who | Blocks |
| --- | --- | --- |
| Which Sunday picks in `docs/data-sources.md` do we wire, and has the cabin data been downloaded into `data/eda/`? | The backend owner | Sunday backlog |
| Which Postgres do we point at: The backend owner's laptop or a hosted one? | The backend owner, the reviewer | Task 9 |
| Do the `reading` field names and the level map suit the frontend? | The frontend owner | Block 2 |
| What does the hardware send, how often, and can it flag a bad signal? | The hardware owner | Block 2 |
| Sourced checklist wording for `base_station/procedures.json` | The documentation owner | Sunday pitch |
| Is any Bio-Monitor sample data open? Ask the CSA mentor on Discord | The documentation owner | Sunday backlog |

## Timeline

Block 1: Tasks 1 to 4 (a posted heartbeat on the crew board). Block 2: Tasks 5 and 6 (SOS with its reason, acknowledge, round trip). Block 3: Tasks 7 and 8 (the report leaves, lands late, and the reply comes back). Before the 16:15 run: Task 9 (Postgres, README, pull request, hand the API to the screens).
