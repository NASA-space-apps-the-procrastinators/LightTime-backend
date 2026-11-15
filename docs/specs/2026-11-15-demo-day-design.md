# Finishing the app: every screen on the real ship

Date: Saturday 14 November 2026, 22:30. This is the spec for what is left to build. It covers the app only.

Plans: `docs/plans/2026-11-15-backend-polish.md` (this repo) and `docs/plans/2026-11-15-console-wiring.md` (console repo). The order to run them in: `docs/plans/2026-11-15-tonight.md`. Words: `CONTEXT.md`. Why no trained model decides: `docs/adr/0001-rules-decide-learned-models-advise.md`. Shapes the console and the ship already agreed on: `docs/specs/2026-11-14-console-data-design.md`.

## 1. Where we stand

The ship's backend is built, tested and on `main`: `Tj-Backend` at `5c5eff3` with `main` merged in, put on `main` by pull request #6, 37 routes, 175 tests passing on SQLite and Postgres 16. It serves the console's screens from the generated month, on a mission clock that restarts at 06:30 on 14 November every time. LIGHTTIME is in the API by name, with its reasons and its time-left line. The cloud `Dockerfile` came with `main` and starts two workers.

The console is built and polished on its own seed data. It makes no call to the ship. It has no dial and there is no Earth console. So nothing on a screen has crossed the link the project is named after. That is the gap this spec closes.

How it is hosted, from the deployment owner's write-up of 14 November: both repos deploy to Google Cloud Run by themselves on every merge to `main`, each from its own `Dockerfile`. A load balancer with a fixed address points at the console. The backend and the database sit behind it: the backend cannot be reached from a browser, and the database takes connections only from listed addresses. The console's image is built with no ship address, so the hosted console is the built-in demo.

Not in any repo yet: the data owner's six Earth console routes.

## 2. What finished means

1. A person can read an alert and act on it from the console, and every step goes through the ship's delayed link.
2. The distance is a control. Moving it changes the delay, who decides and what LIGHTTIME says, on every screen within two seconds.
3. LIGHTTIME's sentence is heard once, and its card shows the time left, whether Earth can answer first, the checklist and the reasons.
4. A second page is Earth. It shows only what the link has delivered, as old as the light time, and a reply from it takes the same road back.
5. The crew cards, the station strip, the check-in and the log show the ship's data. With no ship, the console says so and runs its built-in demo.
6. The suit can post with its own field names, and the reading is on a crew card a second later.

Not goals: a trained model that decides anything (ADR 0001); phone push; storing the suit's radiation; a console rule that raises an alert by itself; any change to the console's styling or to its scoring rules.

## 3. Decisions

| # | Decision | Why |
|---|---|---|
| D1 | Wire the console in the order the delay shows: alert loop, header and dial, LIGHTTIME card, Earth console, check-in, crew and station, log | The alert loop and the dial are where the link is felt. Each step leaves a working console, so the work can stop after any of them |
| D2 | The data owner's Earth console routes are accepted. Conditions: rebased on this branch, inside `command_center/` only, reading only `link_message`, with tests, and with their rows in the API table. Until they are merged, the Earth console groups inbox messages into cases in the browser | They are needed and the wall rule is the only thing that must not bend. Nothing waits for them |
| D3 | The suit keeps its own field names. The ship accepts them at the door and lists what it did not store. The live sensor is suit `LT-04` (crew `C4`). One reading a second | Changing firmware is the riskier side. `C4` keeps the sensor out of the scripted story, which plays on `C1`. The alarm rules count readings |
| D4 | Crew two to four: once the crew cards read the ship there is one source, so the console's seed and the generated month cannot disagree on a screen. The rebuild of the month from the console's seed is still asked of the data owner, and nothing waits for it | In the generated month `C4` sleeps under her own band all week, so her card is red, and no alert was ever raised for it. That is a fault in the data, not in a rule |
| D5 | The ship builds the log from the suits' minute stream that is already in git. `packets.csv` is no longer needed | It removes a wait, and one generator of packets is enough |
| D6 | No trained model raises, changes, silences or ranks an alert. One learned adviser may be added behind a gate, last | ADR 0001 |
| D7 | The backend runs as one process: one worker (`--workers 1`), and on the host one instance (maximum 1, minimum 1) with CPU kept between requests | The mission clock lives in the process, and every start reloads the morning. Two workers or two instances mean two clocks and a database emptied while someone is using it. The scripted story is a thread in the web process, and the host's default setting gives a thread no CPU between requests |
| D8 | A crew member's card turns `ALERT` while LIGHTTIME has a warning or an emergency open for them, and `WATCH` for a caution. A sensor check never colours the card | The console link spec said so and the code did not. A poor signal is about the sensor, not the person |
| D9 | Duplicate check-ins or reminders from two requests at the same instant: left as is | The console blocks a double click. A fix needs a table change |
| D10 | The Earth console reads only `/api/earth/*`. The console's store is moved under `/base-station`, so the Earth page never asks the ship's own routes | Earth knows only what the link delivered. That has to be true in the browser too |
| D11 | On a single packet only a limit that holds for a single value is checked: blood oxygen under 94 % and core temperature over 38.0 °C. A signal quality under 0.6 is `RECHECK`. The other streams are logged without a state. The suit's blood pressure estimate is not a packet. `sent_to_ground` is always false | The band rules are for a morning's resting value. On the last generated day core temperature is above the resting band for a third to two thirds of each person's minutes. The ship sends reports and summaries, never raw packets |
| D12 | The crew object carries the week (seven daily values a metric). In live mode the console shows the ship's states and never scores by itself | One place decides a state. The console's own week is invented around the seed |
| D13 | If the ship cannot be reached, the console says so in the header and runs its built-in demo. A crew member the ship's answer does not cover keeps the built-in card | A health console is never blank and never drops a person |
| D14 | The suit's newest reading shows as one line on the crew card, with its time. A poor signal says to check the sensor | It is the only place a person sees what LIGHTTIME is judging, and the only place the live sensor shows |
| D15 | The console reaches a hosted ship at the address it is served from: the load balancer sends `/api/*` to the backend, and the console is built with `NEXT_PUBLIC_API_URL=/`. A full address still works, for a local run or for a backend with a public address of its own. With no address the console is the built-in demo | The console asks the ship from the browser, and the backend cannot be reached from outside. One address needs no cross-site permission, and the build does not need to know the domain |
| D16 | `main` is the hosted copy. A change goes to `main` only when it is safe to be live: the console's built-in mode still works, and the backend's suite is green. A backend merge restarts the hosted demo at 06:30 | Every merge deploys by itself |

## 4. The alert loop on the link

| Stage | What the console shows | From |
|---|---|---|
| Raised | The alert as the ship worded it: reason, value, rule, source | `GET /alerts`: `reason`, `value`, `unit`, `rule`, `source`, `raised_by` |
| Acknowledged | Who acknowledged, and when | `POST /alerts/<id>/ack {"by"}`; `timeline.acknowledged_at` |
| Sent | "Earth is 11 min 1 s away. Earliest possible reply: 22 min 2 s after sending." (Changed on 15 November by the finish spec, decision F1: the stamp is on the demo clock, so the true length is printed.) With no link: the report is queued and leaves when the link returns | `POST /alerts/<id>/send`; `timeline.earliest_reply_at`; `state.link_up`, `delay_s`, `round_trip_s` |
| Replied | The reply in the thread, when it lands and not before. Nothing replies by itself | `GET /alerts/<id>/thread`; `timeline.reply_at` |
| Resolved | The plan accepted, four reminders | `POST /alerts/<id>/accept-plan`; `GET /reminders?open=1` |

A message in the thread says where it is on the link: queued, on its way, or delivered. Times are the ship's clock in UTC. A countdown is counted from the ship's `now`, never from the browser's clock.

## 5. The dial

One control in the console's header, four buttons. Everything on it comes from `GET /api/base/state`; a click is `POST /api/base/dial {"stop": ...}`.

| On screen | Field | Example at Mars |
|---|---|---|
| Four stops, the current one marked | `stops[].stop`, `stops[].label`, `stop` | Space station, Moon, **Mars**, Behind the Sun |
| One-way light time | `delay_s` | 11 min 1 s |
| Round trip, "earliest reply" | `round_trip_s` | 22 min 2 s |
| Who decides | `who_decides` | The crew medical officer |
| What LIGHTTIME does at this distance | `ship_ai_role` | Coaches the crew medical officer |
| Link | `link_up` | Up. At the Sun: "No link to Earth" in the alert colour, and no delay shown |
| Where the number comes from | `light_time_source`, `path_km` | NASA JPL Horizons, 14 Nov, 198 million km |
| Speed-up label | `plays_as_s`, `speedup`, shown when `delay_s` is 60 or more | "plays as 11 s" |
| Mission day and platform | `mission_day`, `platform` | ISS, day 158 |
| The ship's clock | `now` | 06:31:07 |

Rule: never show the played seconds as the delay.

## 6. LIGHTTIME on the console

On the alert page, for an alert LIGHTTIME raised (`raised_by` is `lighttime`), one card:

| On screen | Field |
|---|---|
| "LIGHTTIME" and its role at this distance | `state.ship_ai.name`, `state.ship_ai_role` |
| The sentence, spoken once when it first appears and once more if the level rises | `alert.speak` |
| Time left to the red line, and whether Earth can answer first | `alert.lookahead.eta_s`, `reply_s`, `earth_in_time` |
| The reasons, as a list | `alert.why` |
| The checklist, with the next step marked | `alert.steps`, `steps_done`, `next_step`; a tick is `POST /alerts/<id>/steps {"index": n}` |
| "Suggests. A person decides." | fixed text |

An alert a console rule raised keeps its week chart and has no card. An emergency beeps until it is acknowledged, even though the ship has already sent it.

What LIGHTTIME is, so the screens word it correctly. Three questions, each answered by a rule a person can check:

1. **Can this reading be trusted?** A reading with a poor signal, or a blood oxygen outside 50 to 100, is never judged, and nothing may alarm for the next ten readings. An alarm needs five clean readings in a row.
2. **Is this unusual for this person?** The usual range is the 1st to 99th percentile of the person's own last 24 hours outside exercise, once there are 600 readings. It is shown, not alarmed on.
3. **How long is left, and can Earth answer first?** Over the last 60 readings the ship takes the slope between every pair and keeps the middle one. It needs a fall of 2 points and most pairs agreeing. Time left is the distance to the red line divided by that slope, compared with twice the light time.

What it was tried on, and where the app says so (`GET /sources`, `base_station/limits.json`, the `why` lines):

| Result | Source |
|---|---|
| Warned before the emergency for 6 of 6 volunteers, a median of 97 seconds ahead (159, 106, 98, 96, 68, 14) | Six laboratory recordings of induced low oxygen, 14 to 19 minutes each (Hoffman et al. 2022, University of Washington), each volunteer held out in turn |
| False emergencies on a healthy sleeper over 7.8 hours: 4 with the first rules, then 1, then 0 as they were tightened | Record c01r of the Apnea-ECG Database on PhysioNet (Penzel et al. 2000), a different dataset |
| Heart rate judged with hospital bands tripped for 14 of 15 healthy people at a desk. Switched off | PPG-DaLiA wrist recordings |
| The suit's blood pressure estimate sat in the caution band or worse on 77,647 of 168,600 healthy minutes. Switched off | The generated month's healthy build, so a noise check only (`limits.json`) |
| The Mars delay: 660.86 s on 14 November. The Deep Space Network measured about 657 s the same hour | NASA JPL Horizons; NASA DSN Now |

Limits the app does not hide: it does not diagnose. It was checked on six people on clinical finger sensors, not on our own sensor. It sees fast falls: on the generated month's two slow falls the time-left rule did not fire and the fixed bands caught them, 18 and 9 minutes before the red line. It has no rule for a fast heart rate at rest, a slow one in sleep, or a stuck sensor.

Words no screen, comment or document uses for it: "machine learning", "trained", "validated", "predicts illness".

## 7. The Earth console

One page, `/command-center`, for the flight surgeon.

| Part | What it shows | From |
|---|---|---|
| Top line | How far the ship is, and "everything on this screen left it at least that long ago" | `GET /api/earth/inbox`: `delay_s`, `link_up`, `mode`, `who_decides` |
| Cases | One card for each alert that has reached Earth: who, what, how severe, when it was raised and when it arrived; the handoff in four parts; the time-left verdict as it stood when the report left; the week for an alert a console rule raised; the reasons; every later update | Report messages in the inbox: `payload.crew`, `reason`, `level`, `raised_at`, `sbar`, `lookahead`, `bundle`, `why`; updates with the same `payload.alert_id` |
| Reply | A text box on each case. After sending: "arrives on the ship in 10 min 42 s", counting down | `POST /api/earth/reply {message_id, text, from}`, then `GET /api/earth/outbox`: `eta_s`, `status` |
| No link | "No link to the ship. Replies are queued and leave when it returns" | `link_up` false; outbox `status` `queued` |
| NASA cross-check | Two NASA figures for the Mars delay side by side | `GET /api/earth/network`: `horizons_one_way_s`, `dsn_one_way_s`, `differ_s` |

When the data owner's case routes are merged, the cases part reads them in place of grouping inbox messages in the browser. The page does not change.

## 8. The crew, the cabin and the suit's live reading

In live mode the console's store carries three more things from the ship, asked once a second with everything else.

| What | From | On screen |
|---|---|---|
| The crew: values, bands, the ship's state for each metric and for the person, the week, the last packet time | `GET /api/base/crew`: `today`, `baseline`, `metric_states`, `state`, `week`, `last_packet_at`, `note` | Crew cards, the astronaut page and its charts, the check-in's captured vitals, the alerts rail's silent list |
| Who has checked in today, and the streak | `GET /api/base/checkins/today`: `done`, `streak` | The check-in box, "Start check-in" on a card |
| The cabin: five values and whether each is a real record; today's dose; the solar event | `GET /api/base/station`, `GET /api/base/space-weather` | The station strip. Each tile says "NASA record" or SIMULATED. CO2, temperature and humidity are NASA's cabin record, replayed |
| The newest reading from each suit | `crew[].latest`: `at`, `heart_rate`, `spo2`, `skin_temp`, `signal_ok` | One line on the crew card: "Suit now 88 bpm · SpO2 93 % · 06:31:07 UTC". After 30 seconds without a new one: "Last suit reading". With a poor signal: "no clean signal: check the sensor" |

The station tiles keep the console's own limits and their sources. Only the numbers come from the ship.

Known, and not fixed in code: `C4`'s card is red on sleep with no alert in the list (D4).

## 9. The health log

| Route | Answer |
|---|---|
| `GET /api/base/packets?crew=&state=&limit=` | `{packets, transmitted_to_ground_today, simulated}`. Packets at or before the ship's clock, newest first. `limit` defaults to 200, at most 1000. `crew` is a crew or suit id; `state` is `OK`, `WATCH`, `ALERT` or `RECHECK`; a wrong value is a 400 that names the field |
| `GET /api/base/stream-health` | `{sensors: [{source, lowest_signal_quality, state}], window_minutes: 60, simulated}`: the lowest signal quality each sensor reported over the newest hour of packets |

A packet is one sensor stream for one minute from the generated month's last day, in the console's own packet shape:

| Stream | `source` | `metric` | Checked against |
|---|---|---|---|
| Heart rate | `ecg` | `hr` | nothing |
| Breathing rate | `chest_band` | `resp` | nothing |
| Blood oxygen | `ppg` | `spo2` | under 94 % is `ALERT`; carries the person's band and the rule's words |
| Core temperature | `thermistor` | `temp_c` | over 38.0 °C is `ALERT`; carries the person's band and the rule's words |
| Skin temperature | `thermistor` | `skin_temp_c` | nothing |
| Movement | `imu` | `activity_g` | nothing |

`transmitted_to_ground_today` counts the messages the ship has sent toward Earth on the ship's date. `POST /api/base/packets` is not built: nothing sends packets.

## 10. Running it

**Locally.** One process. `.env` has `LIGHTTIME_MORNING=1` and no `DATABASE_URL`, so the database is SQLite and nothing local can touch the hosted one. Both browser windows read `http://localhost:5000`. Every restart returns to the demo morning.

**Hosted.** What the backend's service needs. All of it is the deployment owner's to set, and none of it is code (backend plan, Task 4):

| Setting | Why |
|---|---|
| The demo tables dropped once, from an address the database allows | The backend has no migrations: it creates missing tables and never changes one. A revision that cannot start is not served, and the one before it keeps running with no error on the site |
| One worker, maximum instances 1, minimum instances 1 | One clock, one load of the morning (D7) |
| Instance-based billing, so CPU is kept between requests | The scripted story is a thread in the web process |
| `LIGHTTIME_MORNING=1` | The demo morning |
| `/api/*` on the load balancer sent to the backend, and the console built with `NEXT_PUBLIC_API_URL=/` | The browser has to reach the ship (D15). The console reads the address when it is built, not when it runs |

Until the last line is done the hosted console is the built-in demo. A hosted ship is one ship: everyone who opens it shares its alerts, its dial and its restart button.

## 11. Requirements

In the order they are built. R1 to R4 and R8 are the core. R5 to R7 complete the console. R9, the hosted copy and the adviser come last.

**R1. The alert loop crosses the real link.** Console plan Tasks 1, 2 and 4.
- [ ] Given the console is pointed at the ship, when A1 is acknowledged and sent, then the status line shows the earliest reply time from the ship, and nothing replies by itself.
- [ ] Given a reply is sent from Earth, when 11 real seconds pass at Mars, then it appears in A1's thread and the stage is `replied`.
- [ ] Given the ship cannot be reached when the page loads, then the console says so and runs on its built-in demo.

**R2. The dial is on the console.** Console plan Task 3; backend plan Task 1.
- [ ] Given the dial is moved to the Sun, then within two seconds the header says there is no link, in the alert colour, and shows no delay.
- [ ] Given the dial is on Mars, then the header shows the one-way time, the round trip and who decides, all from the ship.

**R3. LIGHTTIME is seen and heard.** Console plan Task 5; backend plan Task 1.
- [ ] Given the scripted story is started at Mars, then one new alert appears for `C1`, its sentence is spoken once, and the card shows the time left and that Earth cannot answer in time.
- [ ] Given a step on the checklist is ticked, then the ship has it and the next step is marked.

**R4. The Earth console exists.** Console plan Task 6; later, backend plan Task 6.
- [ ] Given a report is sent at Mars, then the Earth console shows nothing new for about 11 real seconds and then the case, with the time it was raised.
- [ ] Given the link is down, then a reply typed on Earth shows as queued, and leaves when the dial returns to Mars.
- [ ] Given the Earth page is open, then the browser asks only `/api/earth/*`.

**R5. The check-in reaches the ship.** Console plan Task 7.
- [ ] Given Okafor completes a check-in, then the ship's list of who is due is empty, the streak is 13, and A1 carries his symptoms.

**R6. The suit can post, and its reading is seen.** Backend plan Task 2; console plan Task 8.
- [ ] Given the suit's own field names and the suit id `LT-04`, then the reading is stored for `C4`, the answer lists the fields that were not stored, and the fourth crew card shows the reading within two seconds.
- [ ] Given `signal_ok` is false, then the card says to check the sensor and its colour does not change.

**R7. The crew cards and the station strip read the ship.** Backend plan Task 1; console plan Task 8.
- [ ] Given the ship is on the morning, then the four cards show the ship's values and states, and Okafor's heart chart ends 80, 82, 84.
- [ ] Given LIGHTTIME has an emergency open for a crew member, then that card is `ALERT`.
- [ ] Given the ship is on the morning, then the CO2 tile reads 2.99 mmHg in `WATCH` and says it is a NASA record, and the oxygen tile says it is simulated.
- [ ] Given no ship address is set, then every screen is exactly as it is today.

**R8. The backend runs as one process, starts on the demo morning, and passes its run-through.** Backend plan Tasks 4 and 5.
- [ ] Given the app is started with `LIGHTTIME_MORNING=1`, then the state says Mars, mission day 158 and 06:30, and a restart returns there.
- [ ] Given the cloud image is built, then it starts one worker.

**R9. The log shows the ship's packets.** Backend plan Task 3; console plan Task 9.
- [ ] Given the ship is on the morning, then the log's newest packets are stamped 06:29, and no packet is from after the ship's clock.
- [ ] Given a packet's signal quality is under 0.6, then its state is `RECHECK` whatever its value.
- [ ] Given a report has left the ship today, then "Sent to ground today" counts it.

**R10. The hosted copy can run the real ship.** Backend plan Task 4; console plan Task 11. Settings on the host, not code, and the deployment owner's to make.
- [ ] Given the hosted backend is asked for its state ten times, then each `now` is later than the one before, and the state says Mars and mission day 158.
- [ ] Given the console's image is built with no ship address, then the hosted console is the built-in demo and says nothing about a ship it cannot reach.
- [ ] Given it is built with `/` and the load balancer sends `/api/*` to the backend, then the hosted console's header shows the ship's light time.

**Optional. A learned normal heart rate, as an adviser.** Backend plan Task 8, behind its gate, only when everything above is done.

## 12. Risks

| Risk | Sign | What to do |
|---|---|---|
| The hosted backend's newest revision cannot start against tables made before pull request #6 | The host keeps serving the revision before it, so new fields are missing and the site shows no error | Drop the demo tables once from a listed address, deploy again, and check which revision is serving |
| Two workers or two instances on the host | `now` goes backwards between two requests, or the demo empties itself | One worker and maximum instances 1 (backend plan, Tasks 0 and 4). The check is ten reads of the state |
| The story stalls on the host | Readings stop when no page is open, or arrive unevenly | Instance-based billing on the backend's service |
| A local `.env` still holds the hosted database's address | `python app.py` fails at start, or a second ship runs on the hosted database | No `DATABASE_URL` in the local `.env` |
| The hosted console is expected to be live | It shows the built-in demo | That is its state until the ship can be reached from a browser and the image is built with the ship's address (D15) |
| A hosted ship is shared by everyone who opens it | Someone else's restart or dial change appears on your screen, and every open page asks the ship eight times a second | It is one ship by design. Keep the public copy as the built-in demo, or give the live address only to the people driving it |
| The hosted backend has no way out to the internet | The light time's source says "read on 2026-11-13", and the Deep Space Network line is empty | The stored JPL figure for the day is used. It is correct, and it is labelled |
| An interface pass and the wiring edit the same header, layout and alert components | Merge conflicts | The wiring branch merges first. Until then other work on those files changes styling only |
| The console now asks the ship eight times a second, and the Earth page twice | The backend's log scrolls fast; a slow machine lags | It is one browser on one process. If it lags, ask the cabin and the weather every tenth second instead of every second |
| The first request to the log reads a month of minute rows | The log page takes a second to fill, once | Expected. The answer is kept after the first call |
| Browsers allow speech only after a click | Nothing is spoken | "Sound on" is that click. The sentence is on the card either way |
| The data rebuild changes values tests pin | A few backend tests fail on `C2` to `C4` | Backend plan Task 7 names each one |
| `C4`'s red card with no alert reads as a bug | Someone "fixes" a rule | It is the data (D4). Do not change a rule for it |

## 13. Open questions

- **Data owner:** when will the Earth console routes be pushed, rebased on `Tj-Backend`? Can the month be rebuilt from the console's seed (backend plan Task 7)?
- **Hardware owner:** does the suit send once a second, and with which of the two sets of field names?
- **Deployment owner:** which way in for the browser: `/api/*` on the load balancer, or a public address for the backend? Was the hosted database made before 22:03 on 14 November?
- **Frontend owner:** the wiring moves the store from the root layout to the `/base-station` layout and touches the header, the alert page and the crew cards. Is there work in progress on those files?
