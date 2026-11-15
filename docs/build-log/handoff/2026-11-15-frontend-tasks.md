# Console: errors found and a task list, for the frontend owner

Sunday 15 November 2026. Nothing in the console repository has been changed. This is a list of what is wrong and what to do about it, for the frontend owner to carry out.

**How these were found.** The console at `feat/live-ship`, commit `05ac88c`, was installed from its lockfile, type-checked, linted, tested and built, then run the way its Dockerfile runs it against a running ship and driven in a headless browser at 1440 px. The hosted site, https://lighttime.health/, was fetched from outside. Line numbers are for `05ac88c`. The console's `main` has moved since then, so find each place by the code quoted, not by the number.

**What passes.** Install, type check, lint (68 files), the 11 tests and three production builds (an absolute ship address, `/`, and none) all pass. The Earth page asks only `/api/earth/*`. Timers are cleared on unmount. Speech never starts before a click.

## A. Do before the pitch

| # | What a person sees | Where | What to do | Done when |
|---|---|---|---|---|
| A1 | A second story in the same tab is silent. The console remembers every alert it has spoken for and never forgets, and a restarted ship reuses the same alert id | `console-effects.tsx:20-28`, the `said` set | At the top of the speech effect, delete every key whose alert id is no longer in `state.alerts`. When sound is off, also call `window.speechSynthesis.cancel()` so a sentence in progress stops | Restart demo, Start story, twice in one tab without reloading: both sentences are spoken both times |
| A2 | An SOS beeps and cannot be acknowledged. A live SOS is already at stage `sent` when it appears, and Acknowledge is offered only at stage `raised`. The beep also continues after the alert is resolved | `alert-actions.tsx:41-57` (`primary`), `console-effects.tsx:11-17` (the `useAlarm` condition) | Offer an Acknowledge button for any live alert that has no `acknowledgedAt` and is not resolved, at any stage. It dispatches the existing `acknowledge` action; the ship's `/alerts/<id>/ack` accepts it at any stage. Add "not resolved" to the beep condition | On a live SOS page there is an Acknowledge button; pressing it stops the beep and fills the stepper's time. A resolved alert never beeps |

## B. Wrong numbers on screen

| # | What a person sees | Where | What to do | Done when |
|---|---|---|---|---|
| B1 | "Time left to the red line: 1 min 10 s" never changes, and still reads that when the reading is 86 % and the alert is an SOS | `lighttime-card.tsx:35` prints `span(look.eta_s)`. `ship-api.ts:60-67` (`lookaheadSchema`) lists neither `at` nor `red_line_at`, so zod drops them | Add `at` and `red_line_at` as optional strings to the schema. Show `red_line_at` minus the ship's `state.now` (both are on the ship's clock, which runs at real speed), "Due now" at zero, and "Red line crossed" once the alert's level is `emergency` | The figure falls about one second a second, then reads "Red line crossed" in the alert colour |
| B2 | "Earliest possible reply: 06:31" for a report sent at 06:31 with a 22-minute round trip | `alert-actions.tsx:31-33` prints `timeline.earliest_reply_at` as a clock time. That stamp is on the demo clock, where a Mars leg plays in 11 seconds | Print a length, not a clock time: "Earliest possible reply: 22 min 2 s after sending". The backend is adding `timeline.earliest_reply_after_s` (true seconds, optional until it ships); until then use `ship.round_trip_s` | The line reads "Sent. Earth is 11 min 1 s away. Earliest possible reply: 22 min 2 s after sending." |
| B3 | On the Earth page, "raised 06:31 UTC, reached Earth 06:31 UTC" for an 11-minute leg | `earth-console.tsx:144-148` and `:189` print `deliver_at`, also a demo-clock stamp | The inbox message already carries `delay_s` in true seconds. Print "reached Earth 11 min 1 s after it was sent". For the update rows, print when each was sent | The heading states the true length of the leg |
| B4 | The round-trip stepper shows the reply at the same minute as the send, with nothing to explain it | `round-trip.tsx`, used at `alert-detail.tsx:77` | One caption under the stepper when `ship.plays_as_s < ship.delay_s`: "Clock times are the demo's. The link plays 60 times faster: 11 min 1 s of light time passes in 11 s." | The caption shows at Mars and not at the space station or the Moon |
| B5 | The Earth page says the Deep Space Network figure is "measured". NASA's feed reports a round-trip light time and does not say it is a measurement | `earth-console.tsx:247` | "reported by NASA's Deep Space Network" | The word is "reported" |

## C. Connection to the ship: make it robust

These matter most for the hosted site, where the network is not a laptop's loopback.

| # | What happens | Where | What to do | Done when |
|---|---|---|---|---|
| C1 | One failed answer from the ship flips the whole console to its built-in demo for that second | `mission-store.tsx:345-351`, the `catch` of `refresh` | Count misses in a row. Fall back after three, or at once on a first load that has never reached the ship. One or two misses change nothing on screen | Stop and restart the ship within two seconds: nothing changes |
| C2 | When the ship stays away mid-session, the screen mixes the ship's last alerts with built-in crew and cabin under a header that says "built-in demo", and an alert the ship had at stage `sent` gets an invented reply within two seconds | `mission-store.tsx:345-351` keeps `state` and clears only `board` and `ship`. `use-ground-link.ts:13-36` schedules the built-in reply for any `sent` alert | On an outage, replace the whole state with the built-in demo (keeping `soundOn`), so every panel agrees with the header. Then the built-in reply only ever answers the built-in alert | After three misses every panel is the built-in one. When the ship returns, the next answer replaces everything |
| C3 | If the ship hangs instead of refusing, the screen freezes with no sign, polling stops, and a first load stays on "Loading console…" | `ship-api.ts:340-350`, `request()` has no timeout | Add `signal: AbortSignal.timeout(4000)` to the `fetch` | A ship that accepts the connection and never answers leads to the fallback, not a frozen page |
| C4 | One missing field in `/api/base/state` gives "Ship unreachable: built-in demo" with nothing in the browser console to say why | `ship-api.ts:362`, `shipStateSchema.parse` | Log the zod issue with `console.error` before falling back, and make fields the header does not need optional | A changed backend field shows its name in the browser console |
| C5 | A crew member whose answer does not fit the shape silently gets the built-in card | `ship-api.ts:408-411` | Log it, and mark that card as built-in | Not urgent |
| C6 | The overview asks the ship eight times a second (nine during a story); the Earth page twice | `mission-store.tsx` `pull()` | The cabin and the space weather change once a minute at most: ask for those two every tenth second | Six a second on the overview |
| C7 | The hosted console is the built-in demo because it was built with no ship address | Build time, not code | Nothing to change in the code. The image must be built with `--build-arg NEXT_PUBLIC_API_URL=/` once the load balancer sends `/api/*` to the ship. The backend owner is doing that part (`docs/plans/2026-11-15-hosted-site.md`, Task 3). It needs a `cloudbuild.yaml` in this repository's root: agree who adds it | The hosted header reads "Earth is 11 min 1 s away" |

## D. The hosted site

| # | What a visitor sees | Where | What to do |
|---|---|---|---|
| D1 | https://lighttime.health/command-center shows "Set NEXT_PUBLIC_API_URL to the ship's address to open the Earth console", with instructions about `.env.local`, port 5001 and AirPlay on a Mac. That is written for a developer and a judge can reach it | `earth-console.tsx`, the `if (!LIVE)` block | Say instead that this copy is running the built-in demo and that the Earth console needs the live ship, with the link back to the crew console. Move the developer instructions to the README |
| D2 | In the built-in demo there is no dial, no "Start story", no LIGHTTIME card and no Earth link, so the hosted site shows none of the project's idea until it is live | By design: those need a ship | Nothing in the code. It is why making the hosted site live matters |

## E. Smaller things, after the pitch

| # | What | Where |
|---|---|---|
| E1 | The fourth crew card is red with nothing in the alert list. It is the data (four short nights, no alert raised). Either list any card state that has no alert behind it, in live mode, or wait for the rebuilt month | `alerts-rail.tsx:26-32` |
| E2 | "Recent packets" on the overview are the console's own built-in rows while everything around them is the ship's. Read `/api/base/packets?limit=5` in live mode, or label them | `alerts-rail.tsx:193` |
| E3 | "Current" on a LIGHTTIME alert is the value at the last rise in level, not the newest reading. At 1440 px its summary puts two tiles in a four-column grid | `alert-summary.tsx:74-79` |
| E4 | The header wraps to three rows at 1440 px | `app-header.tsx` |
| E5 | The selected alert in the list is marked by the alert colour only | `alert-detail.tsx:43-48` |
| E6 | "spo2" is lower-case in the alert lists; built-in times print in UTC during a fallback; a failed action (a POST the ship refuses) shows nothing | several |
| E7 | The console's tests are ignored by git (`*.test.ts` in `.gitignore`) and by the linter, and `vitest run --passWithNoTests` reports success on a fresh clone with no tests. A green test step proves nothing | `.gitignore:52-53`, `package.json` |

## F. The sources printed beside the daily rules

A text search of each NASA document named in `src/data/thresholds.json` found these numbers in the documents: the cabin carbon dioxide levels (2.8 and 4.5 mmHg), the fitness and strength floors, the bone limits and the career dose limit. It did not find these: resting heart rate 20 beats over baseline for three days (sourced to OCHMO TB-031), blood oxygen under 94 %, breathing rate over 20, 2 mSv in a day, the sleep lines, the mood, reaction-time, hydration and nutrition lines, and the watch lines at 85 % and 97 %. The file's own first comment says every number is traceable to the NASA source named.

These are fair design choices. They need the label "project threshold" in place of, or in front of, the NASA source, on the alert page and the crew page. One more: the oxygen tile judges cabin oxygen against 145 to 155 mmHg, a range NASA states for inspired oxygen, which is lower than cabin oxygen. The full table is in `docs/reviews/2026-11-15-overnight-review.md`, section 8.

## What the backend is changing, so the console can rely on it

- `timeline.earth_after_s` and `timeline.earliest_reply_after_s` on every alert: the true one-way and round-trip seconds the report left with. New and additive; treat them as optional until the backend pull request is merged.
- Starting a story resolves the alert the last story left open, so a second story raises a new alert with a new id. No console change needed.
- `POST /api/base/scenario/start` with no name will play `full`. The console already sends `full`.
- No field is renamed or removed.

## If it helps: a patch that was already tried

`docs/handoff/2026-11-15-console-finish.patch` in the backend repository holds one way of doing A1, A2, B1 to B5 and C1 to C3. It applies cleanly to `05ac88c`. With it, the type check, the linter, 18 unit tests (the 11 that exist and 7 new ones for two small pure modules) and the build pass. It was not driven in a browser, and it has not been applied to anything. Use it, borrow from it, or ignore it:

```powershell
git apply --check --ignore-whitespace <path to>\2026-11-15-console-finish.patch
```

## One run-through that covers A to C

With the ship on the demo morning and the console pointed at it: Restart demo, Sound on, Start story. Hear the early warning. Watch the time left fall. Hear the SOS, see "Red line crossed", press Acknowledge, hear the beep stop. Read "22 min 2 s after sending" on the status line. Open Earth and read "reached Earth 11 min 1 s after it was sent". Go back, Restart demo, Start story, without reloading: it all happens again, with both sentences spoken. Then stop the ship for one second (nothing changes), and for five (the whole console becomes the built-in demo, and comes back when the ship does).
