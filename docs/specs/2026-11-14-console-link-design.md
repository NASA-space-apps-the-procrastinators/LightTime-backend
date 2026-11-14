# Console, ship and Earth: how the screens connect

Date: 14 November 2026, revised in the evening. Plan: `docs/plans/2026-11-14-console-contract.md`. Contract: the frontend owner's API contract of 14 November, served as described in `docs/specs/2026-11-14-console-data-design.md`.

**What changed since the first version.** The frontend owner wrote an API contract and is wiring his own screens to it, one at a time. So the "live layer" this spec first proposed (a provider, a bar and a panel added beside his screens) is not being built, and sections 4 and 5 below are rewritten. Sections 6 and 7 (the two clocks, and what leaves the ship) still hold and matter more now, because his screens will read these fields directly.

## 1. Problem

The crew console and the ship's computer were built apart. The console scores seed data in the browser and keeps its state in browser storage. The ship's computer holds the dial, the delayed link and the ship AI, and no screen shows them. There is no Earth screen at all. A judge would see a good monitor, not a system that knows how far away help is.

## 2. Goals

1. One dial, shown on the console, changes the delay and who decides on every screen within a second.
2. The ship AI's alerts appear on the console with their reason, countdown and round trip.
3. An Earth console on a second screen hears nothing until the light delay has passed, and its reply takes the same time back.
4. The existing seeded console keeps working with the backend off.
5. A crew member can see everything that has left the ship about them.

## 3. Not doing

- Rewriting the console's scoring, storage or components.
- A second backend service or WebSocket. The ship is polled once a second, which is enough for three screens.
- Login. Said plainly if asked: a flight system would need one.

## 4. Design

The console keeps its screens and its components. Each screen switches from the seed file to the API when its step of the contract lands on the backend: crew overview, astronaut page, check-in, alert loop. The backend returns the objects those components already take. Which endpoint feeds which screen, and the exact shapes, are in `docs/specs/2026-11-14-console-data-design.md`, sections 6 to 8.

Three things from the first version of this spec are still needed and have no owner yet:

| Piece | Why it matters | State |
|---|---|---|
| The dial on the console | Without it a judge cannot see the delay change who decides | The API is ready (`GET /state` with all four stops, `POST /dial`). No control on any screen |
| An Earth screen | The delayed link is the project. Without a second screen nothing shows a message arriving late | The API is ready and tested (`/api/earth/inbox`, `/outbox`, `/reply`, `/network`). No page. Open question Q1 in the console data spec |
| LIGHTTIME's live alerts on the console | The ship AI's warnings, its time-left line and its spoken sentence | They arrive in `GET /alerts?open=1` beside the console's own alert, with `state` `SOS` or `WATCH` and `lookahead` and `speak` filled. The console must accept `metric` values `signal` and `manual` |

**Two speeds of trouble, one list.** The console's alert `A1` (a resting heart rate out of band for three days) and a LIGHTTIME alert (blood oxygen falling in the last minute) now share one shape and one list. They are raised by different rules, and each says which in `rule` and `source`.

## 5. How the two sides' words map

| Console | Ship | Rule |
|---|---|---|
| `OK` | `nominal` | |
| `WATCH` | `caution`, and `advisory` that is not a sensor check | |
| `RECHECK` | `advisory` on `signal` | Never an alert on its own |
| `ALERT` | `warning` | |
| `SOS` | `emergency` | An alert's `state` can be `SOS`. A crew member's `state` never is: it stays `ALERT`, and `level` says `emergency` |
| raised, acknowledged, sent, replied, resolved | `stage`, worked out from `timeline` | A live SOS is `sent` before anyone acknowledges it |
| `C1` to `C4`, `A1`, `M5`, `R2` | The same strings in every Crew and Alert object and every new endpoint | Routes also take the bare number |
| `sleep_h`, `mood`, `pvt_ms`, cuff blood pressure | The `checkin` table | Not typed readings |
| `hr_rest`, `temp_c`, `resp`, `dose_mSv_day` | The dataset's daily summary | Not `heart_rate` or `skin_temp`, which are per-second readings of something else |

## 6. Time on screen

Two clocks run, and the screens must not mix them.

| Thing | Clock | Field to show | Never do |
|---|---|---|---|
| The delay, the round trip | Mission seconds | `delay_s`, `round_trip_s` | Work it out in the browser |
| A message in flight | Mission seconds left | `eta_s` | Subtract timestamps |
| Countdown to the red line | Real seconds | time until `lookahead.red_line_at` | Use `eta_s` from the report, it is frozen |
| Countdown to the earliest reply | Real seconds on the demo clock | time until `timeline.earliest_reply_at` | Add `2 x delay_s` to now |
| Label for the speed-up | | "playing 60x faster", from `speedup`, when `delay_s >= 60` | Hide it |
| Every time the API returns | Mission clock: it starts at 14 November 2026, 06:30:00 UTC when the demo morning loads and runs in real time | The ISO time as given, shown in UTC | Format in the browser's zone (06:12Z would read 01:12 in Ontario), or mix with the browser's own clock |
| A message loaded with the morning | Real mission seconds (665 to 777 s a leg), all in the past | "delivered" | Compare its delay with a live one, which plays 60 times faster |

For the stop behind the Sun the screens say "No link" and ignore `delay_s`.

## 7. What goes to Earth, and what the crew can see of it

Continuous on the ship, periodic to Earth. This follows what the space agency advisor said on 14 November: monitoring in space is periodic, crews resist being watched from a distance, and the benefit has to justify the disclosure.

| Leaves the ship | When | Carries |
|---|---|---|
| Report | An SOS, a falling trend, or the crew pressing send | The last 60 readings, the reason, the reasoning, the answers to the surgeon's first questions, the person's usual range |
| Update | Acknowledged, a step ticked, escalated, resolved | The event, who, and the note on resolve |
| Message | The crew types one | The text |
| Report for a console alert | The crew presses send | Seven days of resting heart rate, blood pressure, temperature and sleep, and today's check-in. No strip of readings |
| Daily summary | On request | Low, middle and high of each vital, minutes of exercise, alerts |
| Nothing else | | The raw stream stays in the 24-hour recorder and is then deleted |

The ship's outbox is the complete list. The panel shows its count ("3 messages have left the ship").

## 8. Requirements

The backend's requirements moved to `docs/specs/2026-11-14-console-data-design.md`, section 8. What is left here is what a screen has to do, for whoever builds it.

**Must have**
- [ ] Given the dial is moved to Mars, when one second passes, then the header shows the JPL figure, the round trip, and "Crew medical officer".
- [ ] Given an open alert with a `speak` line, when the console polls ten times, then the line is spoken once.
- [ ] Given an alert is sent at Mars, when Earth's screen is watched, then it shows nothing for about 11 real seconds and then the report.
- [ ] Given a reply is sent from Earth, when 11 real seconds pass, then it appears in the alert's thread and the stage is `replied`.
- [ ] Given the ship is unreachable, then the console says so and falls back to its seed.

**Should have**
- The ship AI's live heart rate and blood oxygen (`latest` on each Crew object) on the crew cards.
- A "Data" page listing `GET /api/base/sources`.

## 9. Risks

| Risk | Sign | What to do |
|---|---|---|
| Lint or the pre-commit hook rejects the new files | `pnpm lint` fails | `pnpm lint:fix`, then fix by hand without changing behaviour |
| The state pill takes different props | Type error in the panel | Change the one line in the panel, not the pill |
| The venue network blocks laptop-to-laptop traffic | "Ship computer not reachable" | Run backend and console on one laptop, Earth in a second window |
| Voice blocked until the first click | Silence on the first alert | Click anywhere on the console before the demo |
| Alert ids restart after "Clear" | A stale card | The panel keys cards by id and time, never by id alone |

## 10. Open questions

- Team: who builds the dial control and the Earth screen, and by when? Blocking for the pitch. The earlier plan has a draft of both (`docs/plans/2026-11-14-connect-everything.md`, Tasks 2 and 4) that would need re-pointing at the frontend owner's structure.
- Team: which laptop is the ship, which is Earth, for the pitch? Not blocking for the build.
