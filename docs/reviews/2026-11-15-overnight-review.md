# Where LIGHT-TIME stands: review of the overnight work

Written Sunday 15 November 2026, before the 10:00 mentor hours. It answers four questions: what was done, whether it does what was asked, what is wrong, and what to do first. The fixes are specified in `docs/specs/2026-11-15-finish-design.md` and planned in `docs/plans/2026-11-15-backend-finish.md` and, for the frontend owner, `docs/handoff/2026-11-15-frontend-tasks.md` with `docs/handoff/2026-11-15-console-finish-plan.md`.

## 1. In short

The overnight run did what it was asked to do. Every task meant for the night is built: the console now runs on the real ship, the dial is on every screen, LIGHTTIME is seen and heard, the Earth console exists, the check-in, the crew cards, the cabin and the log read the ship, and the suit can post with its own field names. Nothing is merged; three pull requests wait for the reviewer.

The work was checked again today from a clean copy, by running it. The backend's 192 tests pass. The console installs, type-checks, lints, passes its 11 tests and builds. The alert loop and both stories were driven end to end against a running ship.

That run found three things that would spoil a live demo unless they are fixed or worked around, and a handful of places where a screen shows a wrong number. None of them is in the rules or the mathematics. They are all in how a second run starts and how time is printed.

## 2. What was checked today, and how

| Check | Result |
|---|---|
| Backend test suite in a fresh environment, SQLite | 192 passed |
| Console: install from the lockfile, type check, lint, tests, production build with an absolute ship address, with `/` and with none | All pass: 68 files linted, 11 tests, three builds |
| Console run the way its Dockerfile runs it, against a running ship, in a headless browser at 1440 px | Overview, alert page, Earth page, story, fallback and voice exercised |
| Alert A1 across the link at Mars, both directions | Works. Report visible on Earth after 11 real seconds, reply back after 11 more |
| Story `full` at Mars, timed from the start | Early warning at 32 s, SOS at 45 s |
| Story `stage` at Mars | SOS at 8 s, no early warning |
| 1,813 requests against the ship with a story running | No error |
| Reset | 0.04 s. Stops the story, clears live alerts and messages, clock back to 06:30:00. A second run matched the first |
| Evidence scripts (`check_spo2_rules.py`, `crossval_lookahead.py`, `learn_hr_normal.py`) | Every published figure reproduced |
| Every outside source and reference | Checked against its publisher. Eight kinds of misstatement found in our own documents, listed in section 8 |

Not verified today: the 192 tests on Postgres, the hosted copy, a real suit sensor, and the voice as heard by a person.

## 3. Did we meet the goals?

The six things "finished" was defined to mean (demo-day spec, section 2):

| Goal | Met? |
|---|---|
| 1. A person can read an alert and act on it from the console, and every step goes through the ship's delayed link | Yes |
| 2. The distance is a control: moving it changes the delay, who decides and what LIGHTTIME says, on every screen within two seconds | Yes |
| 3. LIGHTTIME's sentence is heard once, and its card shows the time left, whether Earth can answer first, the checklist and the reasons | Mostly. The time-left figure does not count down, and a second run in the same tab is silent |
| 4. A second page is Earth, showing only what the link has delivered, with a reply taking the same road back | Yes. The page asks only `/api/earth/*` |
| 5. The crew cards, the station strip, the check-in and the log show the ship's data, and with no ship the console says so | Yes on first load. A ship that drops mid-session leaves a mix of old and built-in data |
| 6. The suit can post with its own field names, and the reading is on a crew card a second later | Yes, tested with posted readings, not with the physical sensor |

Requirement by requirement:

| Requirement | Backend | Console |
|---|---|---|
| R1. The alert loop crosses the real link | Done | Done. The reply time on the status line is wrong (finding 4) |
| R2. The dial is on the console | Done | Done |
| R3. LIGHTTIME is seen and heard | Done for the story `full` | Partly (findings 1, 2, 5) |
| R4. The Earth console exists | Four routes work. The data owner's six case routes are on their branch, not merged | Done. The arrival time printed is wrong (finding 6) |
| R5. The check-in reaches the ship | Done | Done. The form was not clicked through today |
| R6. The suit can post, and its reading is seen | Done | Done |
| R7. The crew cards and the station strip read the ship | Done | Done |
| R8. One process, on the demo morning | Done. The image starts one worker | Not applicable |
| R9. The log shows the ship's packets | Done | Done |
| R10. The hosted copy can run the real ship | Code done. Host settings are the deployment owner's and were not checked | Done. The hosted build argument was not checked |
| Optional. A learned normal heart rate, as an adviser | Fitted offline, passed its gate, not connected to the app | Not applicable |

## 4. Findings

### Would spoil a live demo unless fixed or worked around

| # | What happens | Where | Fix |
|---|---|---|---|
| 1 | A second story in the same browser tab is silent. The console remembers which alerts it has spoken and never forgets, and a restarted ship reuses the same alert id | Console `console-effects.tsx:20-28` | Console plan Task 1 |
| 2 | The SOS beep cannot be stopped. An SOS is already "sent" when it appears, and the Acknowledge button is offered only before sending. The beep goes on after the alert is resolved | Console `alert-actions.tsx:41-57`, `console-effects.tsx:11-17` | Console plan Task 2 |
| 3 | A second story without a restart raises nothing. The first story's SOS is still open, an open alert cannot be raised again, and ticking the oxygen step no longer ends the fall | Backend `scenario.py:27-34`, `rules.py:46-60` | Backend plan Task 1 |

### A screen shows something wrong

| # | What a person sees | Where | Fix |
|---|---|---|---|
| 4 | "Earliest possible reply: 06:31" for a report sent at 06:31 with a 22-minute round trip. The stamp is on the demo clock, where the leg plays in 11 seconds | Backend `routes.py:27-32`, printed by console `alert-actions.tsx:31-33` | Backend plan Task 2, console plan Task 4 |
| 5 | "Time left to the red line: 1 min 10 s" never changes, and still reads that when the reading is 86 % and the alert is an SOS | Console `lighttime-card.tsx:35`; the schema drops `red_line_at` | Console plan Task 3 |
| 6 | On Earth, "raised 06:31 UTC, reached Earth 06:31 UTC" for an 11-minute leg | Console `earth-console.tsx:144-148` | Console plan Task 4 |
| 7 | If one answer from the ship is missed, the console drops to its built-in demo for that second. If the ship stays away mid-session, the screen mixes the ship's last alerts with built-in crew, and a sent alert gets an invented reply | Console `mission-store.tsx:345-351`, `use-ground-link.ts:13-36` | Console plan Task 5 |
| 8 | If the ship hangs instead of refusing, the screen freezes with no sign, and a first load stays on "Loading console" | Console `ship-api.ts:340-350`, no timeout | Console plan Task 5 |
| 9 | The fourth crew card is red with nothing in the alert list. It is the data: four short nights with no alert raised | Dataset; console `alerts-rail.tsx:26-32` | Spec, listed for later |
| 10 | "Recent packets" on the overview are the console's own built-in rows while everything around them is the ship's | Console `alerts-rail.tsx:193` | Spec, listed for later |
| 11 | "Why the ship says this" lists the latest readings, so after recovery an SOS for 86 % lists readings of 98 % | Backend `reports.py:47-51` | Spec, listed for later |
| 12 | The Earth page says the Deep Space Network figure is "measured". NASA's feed reports it; nothing says it is a measurement | Console `earth-console.tsx:247`, backend `sources.py:10` | Both plans, the words task |

### Smaller things

The story started with no name is `stage`, which has no early warning; the console sends `full`, but the earlier plan's run-through used `stage` (backend plan Task 1). The scripted fall is a 20-second drift and then a jump to 86 %, so the ship says "about 70 seconds" and the SOS comes 13 seconds later; that is the story's design and worth saying aloud in the demo ("then it falls off a cliff"). The console's tests are ignored by git, so a fresh clone runs none and still reports success. The header wraps to three rows at 1440 px. The first call to the log takes 0.4 s alone and up to 4.7 s if eight pages ask at once. `POST /api/base/readings` accepts some values it should refuse (an empty reading, a heart rate of -5). `AI_USE.md` holds six lines twice, once with names. The constants of the time-left rule live in `lookahead.py`, not in `limits.json` beside the other thresholds. `GET /api/base/health` is not in the API table.

## 5. If nothing is fixed before the pitch

The demo still works if the person driving it does four things.

1. Reload the browser tab and press "Sound on" before each run.
2. Press "Restart demo" before every story.
3. Use the "Start story" button, which plays `full`. Do not start a story by hand without a name.
4. Expect the beep to continue during an SOS. "Sound off" stops it, and has to be turned on again before the next story.

Keep the live sensor on suit LT-04: the stories play on the first three crew.

## 6. Order of work today

1. Reviewer: merge backend pull request #7 (one worker), then #9 (the backend work), then console #4.
2. Console plan Tasks 1 and 2, which are small and remove the two demo risks. Then backend plan Task 1.
3. Console plan Tasks 3 to 5 and backend plan Task 2, which fix the wrong numbers.
4. The run-through at the end of each plan, on the laptop that will drive the pitch.
5. Deployment owner: the host settings in `docs/deployment.md`, part C. Until the ship can be reached from a browser the hosted console is the built-in demo, which is a safe thing to link.
6. Before 23:59: make both repositories public and submit, using `docs/submission.md`.

## 7. Questions for other owners

- Data owner: the Earth case routes are on your branch and need a rebase onto `Tj-Backend`. Can the month be rebuilt so that the fourth crew member's short nights raise an alert, or stop being short?
- Hardware owner: does the suit send once a second, and with which set of field names? It has not been tried against the ship.
- Deployment owner: which way in for the browser, `/api/*` on the load balancer or a public address for the backend? Is the backend set to one instance with CPU between requests?
- Frontend owner: the console's tests are ignored by git on purpose. May the one test file for the ship adapter be committed, so the pull request carries its tests?

## 8. Corrections to our own documents

Checking the references turned up these. They are corrected in the documents written today; the older files are fixed by backend plan Task 4.

| Where | It says | It should say |
|---|---|---|
| Demo-day spec, section 6 table; decision record 0001 | The six volunteers are "overnight oximetry" recordings, and the healthy sleeper is "the same set's control recording" | The six are 14 to 19 minute laboratory recordings of induced low oxygen (Hoffman et al., 2022). The sleeper is record c01r of the Apnea-ECG Database (Penzel et al., 2000), a different dataset |
| Demo-day spec, section 4 | The status line reads "Earliest possible reply: 06:53" | The stamp is on the demo clock. The line is to state the true length of the round trip instead (finish spec, decision F1) |
| `docs/data-sources.md`, `data/spo2_apnea_ecg/README.md` | The Apnea-ECG paper has doi:10.13026/C23W2R | That is the database's DOI. The paper is doi:10.1109/CIC.2000.898505 |
| `docs/data-sources.md`, `data/README.md`, `data/ppg_dalia/README.md` | PPG-DaLiA is cited as Reiss, Indlekofer and Schmidt (2019) | That is the dataset record. The dataset asks for the paper, which has a fourth author: Reiss, Indlekofer, Schmidt and Van Laerhoven (2019), Sensors 19(14): 3079 |
| `docs/specs/2026-11-14-data-sources-design.md` | The PPG-DaLiA folder holds three volunteers | Fifteen |
| `common/sources.py`, `common/dsn.py`, the Earth page | The Deep Space Network "measures" the light time | It reports a round-trip light time to three significant figures |
| `data/reference/console_thresholds.json` and the console's `thresholds.json`, shown on the alert and crew pages | "Every number is traceable to the NASA source named", for example the resting heart rate rule sourced to OCHMO TB-031 | A text search of each document found the carbon dioxide, fitness, bone and career-dose numbers, and did not find the triggers for resting heart rate, blood oxygen under 94 %, breathing rate, 2 mSv a day, sleep, mood, reaction time, hydration or nutrition. Those are fair design choices and need the label "project threshold" in place of a NASA source. The oxygen tile judges cabin oxygen against 145 to 155 mmHg, a range NASA states for inspired oxygen. Owner: frontend. Not fixed by any plan today |
| `common/modes.py` comment | NEEMO 16 as the source of the 300 s rule | NEEMO 16 ran one simulated emergency at a five-minute delay and recommended more crew autonomy at five minutes or more (Rader et al., 2013). The switch at exactly 300 s is our design choice |
