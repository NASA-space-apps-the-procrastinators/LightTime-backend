# Final fix: design

Date: 15 November 2026, written 11:30 for a 15:30 pitch. Plan: `docs/plans/2026-11-15-final-fix.md`.

## What we found on the hosted site

The site was checked at 11:10 with a headless browser (Playwright) and with plain requests.

| Check | Result |
|---|---|
| `https://lighttime.health/base-station` | Loads, but the header says "Ship unreachable: built-in demo". No dial, no Start story button, no LIGHTTIME card |
| `https://lighttime.health/command-center` | "Cannot reach mission control's server." |
| What the console calls | `https://lighttime-backend-672099769345.northamerica-northeast2.run.app/api/...`. Every call fails. That address answers 404 from Google's front end, so no service lives there |
| `https://lighttime.health/api/base/health`, `/state`, `/crew`, `/api/earth/cases` | All 200. The load balancer already sends `/api/*` to the ship |
| The ship's clock | `/api/base/state` gives today's real time and the station stop, so `LIGHTTIME_MORNING` is not set on the hosted ship. Every crew card has `latest: null` and a last packet from 14 November 06:29 |
| The story on the hosted ship | `/api/base/alerts` holds one blood-oxygen SOS for C1 raised at 16:18 UTC by LIGHTTIME. The story runs there when it is started through the API |
| Crew names on the hosted ship | Okafor, Linda Rodenburg, Sato, Rebecca Qi |

## Where the story went

Nothing was lost. The dial, the Start story button and the LIGHTTIME card are in the console's `main` (`src/components/base-station/app-header.tsx`), and the story is in the ship (`base_station/scenario.py`, `POST /api/base/scenario/start`). The console draws them only when it can reach the ship. The hosted console was built with a ship address that does not exist, so it falls back to its built-in demo, which has none of them. The fix is one build setting, not code.

The second-story defect found this morning (a second run raised its SOS at once, on the first run's low readings) is already fixed on `Tj-Backend` at `c983fe4`. It was checked again for this spec: two full stories in a row with no restart each gave the early warning first and the SOS after it.

## Problem

Judges will open `lighttime.health`. Today they get a static demo with invented names and no story. Three things are also missing for the pitch: one button that plays the demo, the team's names on the crew, and the access rule a Canadian Space Agency mentor asked for at 10:17 (a crew member's health record is for that person and the crew medical officer; an SOS still reaches everyone).

## Goals

1. The hosted console talks to the hosted ship: the header shows the dial, and no screen says "built-in demo" or "Cannot reach".
2. One button plays the whole demo from a clean start, any number of times, with no restart.
3. The six team names are on the mission: on the ship TJ (commander), Rebecca (crew medical officer), Kyler and David; on Earth Dr. Youssef (flight surgeon) and Damola (flight director, the name the Earth console signs with).
4. The ship gives a crew member their own record in full, a name card for the others, and a short notice of anyone's SOS. The crew medical officer and the medical station see everything.
5. The suite goes from 212 to 220 tests and stays green.

## Not in this fix

- A login. The console says who is looking; nothing proves it. The pitch must say "role-based views", not "secure". A real system would tie this to a sign-in.
- A fifth or sixth crew member. The generated month has four people. Each extra person needs baselines, a month of readings and new checksums, which is hours of work. So four names fly and two work the Earth console.
- Guarding the buttons (acknowledge, tick a step, clear). In an emergency any crew member must be able to act. Only reading is shaped.
- Access rules on the Earth side. Earth sees only what the ship sent over the link, which is already the flight surgeon's view.
- Any console code written from the backend side. Console work is listed below for the frontend owner.
- Any change to rules, thresholds or the story's script.

## Who it is for

- As a judge opening the site, I want to press one button and watch the oxygen fall, the early warning, the SOS and the 11-minute wait, so that I understand the idea in a minute.
- As a presenter, I want to run the demo twice in a row without touching a terminal, so that a second audience sees the same thing.
- As a crew member, I want my screen to show my own record and not my crewmates', so that my health data stays mine.
- As the crew medical officer, I want every record, so that I can lead care when Earth is 11 minutes away.
- As any crew member, I want to hear about an SOS at once, with who it is and what kind, so that I can go and help.

## Requirements

### Must have

**R1. The console is built with the ship's address set to the same site.** `NEXT_PUBLIC_API_URL` is `/` (or `https://lighttime.health`) in the image that is live.
- Given the live site, when the base station loads, then the header shows the dial and "Start story", and no request goes to a `run.app` address.
- Given the live site, when the command center loads, then it lists cases or shows an empty inbox, not "Cannot reach".

**R2. The hosted ship starts on the demo morning and runs as one process.** `LIGHTTIME_MORNING=1`, one instance, CPU always on, SQLite inside the instance (no `DATABASE_URL`).
- Given the live ship, when `/api/base/state` is read after a reset, then `now` starts with `2026-11-14T06:30`.
- Given a story is playing, when 60 seconds pass with no page open, then the story has still advanced (CPU is not throttled between requests).

**R3. `POST /api/base/demo/start`.** One call: the demo starts again, the dial goes to Mars, the full story plays. Returns `ok`, `name` ("full") and `state`.
- Given a ship with messages and alerts from an earlier run, when the call is made, then they are gone, the stop is `mars`, and within about 40 seconds C1 has a caution with a spoken time-left line, then an emergency.
- Given a story is already playing, when the call is made again, then one story plays, from the start.

**R4. The mission carries the team's names.** C1 TJ (Commander), C2 Rebecca (Crew Medical Officer, the role text changes from Flight Engineer because the data already marks C2 `is_cmo`), C3 Kyler, C4 David. Ground replies in the generated month come from Dr. Youssef. Damola is the Earth console's default signer, which is a console task. Suits, baselines and every number stay as they are.
- Given a new database, when `/api/base/crew` is read, then the names are TJ, Rebecca, Kyler, David in that order, and C2's role is Crew Medical Officer.
- The three changed data files match their checksums in `BUILD_INFO.json`.

### Should have

**R5. Role-based views on the ship.** The console sends `X-LightTime-Viewer: C3` (or `?viewer=C3`).

| Who is looking | Crew board | One person's record, history, readings | Alerts | Packet log |
|---|---|---|---|---|
| No viewer (the medical station) | every record | allowed | all, in full | every suit |
| The crew medical officer (`is_cmo` in `reference/crew.csv`, C2) | every record | allowed | all, in full | every suit |
| Any other crew member | own record in full; a name card for the rest (`id`, `name`, `role`, `suit_id`, `is_cmo`, `restricted: true`) | own: allowed. Others: 403 `{"error": "...", "field": "viewer"}` | own in full; someone else's SOS as a notice (who, level, which vital, when, stage; no value, reason, steps or report); their quieter alerts not listed | own suit only |

- With no viewer every answer is what it was before, plus two new fields: `restricted` on crew and alerts, `is_cmo` on crew. So the console keeps working unchanged until it starts sending the header.
- The 403 covers `GET /crew/<id>`, `/crew/<id>/history`, `/crew/<id>/readings`, `/alerts/<id>` (when it is not an SOS) and `/alerts/<id>/thread`.

### Later

- An emergency unlock: while an SOS is open, the person helping can open that crewmate's record. NASA's Mars medical concept describes this; the notice above is the first half of it.
- A sign-in, so the viewer is proven.
- The same shaping on check-ins and reminders.

## Design

One new file, `base_station/access.py`, holds the whole rule: who the viewer is, who the medical officers are, `may_read(code)`, and two shapers (`crew_view`, `alert_view`). Routes ask it; they do not repeat it. The rule reads `is_cmo` through `common/dataset.py`, as CLAUDE.md requires. `command_center/` is untouched.

`demo/start` calls the existing reset, sets the stop, and calls the existing story start. No new state.

The rename is data only: the crew reference, the generator's config, the two generated message logs, the tests and three notes, plus the three checksums. The ship never overwrites a crew row, so a database made before the rename keeps the old names. The hosted ship uses SQLite inside the instance, which is new on every deploy, so the names change with the deploy.

## For the frontend owner (no console code is in the plan)

1. **Demo button.** In the header beside the dial: "Run demo" posts to `/api/base/demo/start` with no body, then refreshes. Keep "Start story" or replace it. The Earth console could carry the same button.
2. **Viewing as.** A picker in the header: Medical station (send no header), TJ, Rebecca (crew medical officer), Kyler, David. Send `X-LightTime-Viewer` with the crew id on every ship request. A card with `restricted: true` has only `id`, `name`, `role`, `suit_id`, `is_cmo`: draw the name and "Record limited to the crew medical officer". An alert with `restricted: true` is a notice: draw who, level and vital, and no values. Treat 403 on a person's page as the same message. `shipCrewSchema` in `src/lib/ship-api.ts` will reject a restricted card as it stands, so it needs a second shape.
3. **Names.** `src/data/crew-seed.json`: Okafor to TJ, Linda Rodenburg to Rebecca (role Crew Medical Officer), Sato to Kyler, Rebecca Qi to David (no longer the medical officer), so the built-in demo agrees with the ship. On the Earth console, sign replies as Dr. Youssef (flight surgeon) by default, and show Damola as flight director. Two test files and a comment in `src/lib/history.ts` also name Okafor.
4. **The built address.** After the next deploy, open the site with the browser's Network tab: every `/api/` request should go to `lighttime.health`.

## How we will know it worked

- Before the pitch: the checks in plan Task 6 pass on the live site (no "built-in demo", dial visible, demo button plays, names right, a 403 for C3 reading C1).
- 220 tests pass on the branch and on `main`.
- In the pitch: the demo runs from one press, twice if asked.

## Sources for the access rule

- The mentor conversation of 15 November 2026, 10:17 (notes and transcript are AI-generated and marked "verify before use").
- NASA-STD-3001 Volume 1, Revision C, section 5.2.1 [V1 5003]: a crew member assigned as Crew Medical Officer is given detailed medical training; CMOs are often, but not always, physicians. https://www.nasa.gov/reference/nasa-std-3001v1/
- LaBarbera et al., "Assessing Crew Medical Officer Preparedness for International Space Station Missions": former CMOs describe the role as a healthcare extender to ground-based flight surgeons. https://ntrs.nasa.gov/citations/20230013415
- Training hours differ by source and should not be quoted as one number. A NASA Johnson deputy chief medical officer said crews get up to 40 hours before launch (HealthTech, November 2021, https://healthtechmagazine.net/article/2021/11/qa-nasas-dr-shannan-moynihan-providing-virtual-care-astronauts-space). A NASA abstract gives about 15 hours of CMO training in the two years before an ISS mission (https://ntrs.nasa.gov/citations/20205008925).
- The Privacy Act point in the notes was not checked against a source. Leave it out of the slides unless someone reads the standard.

## Open questions

- Six names, four seats. This spec puts TJ, Rebecca, Kyler and David on the ship and Youssef and Damola on Earth. Swapping any two is a one-line change to the name list in plan Task 1. (Team, before Task 1.)
- Does the console's deploy run on merge, and did the last one fail? Plan Task 5 step 2 answers it. (Whoever holds the Google Cloud project.)

## Time

Registration closes at 14:00 and the pitch is at 15:30. Order by value: Task 5 (hosting) and Task 1 (names) first, about 40 minutes together. Task 2 (demo call) 15 minutes. Task 3 (access) 30 minutes on the ship; it only shows on screen if the frontend owner has time for the picker, so it is the one to drop. If it is dropped, say in the pitch that the rule is built and tested on the ship and the screen is next.
