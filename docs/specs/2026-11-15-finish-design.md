# Finishing touches: what a judge sees and hears

Sunday 15 November 2026. This spec covers the defects found by running the overnight work (`docs/build-log/reviews/2026-11-15-overnight-review.md`). It adds no feature. Two plans build it: `docs/build-log/plans/2026-11-15-backend-finish.md`, and for the console `docs/build-log/handoff/2026-11-15-console-finish-plan.md`, which the frontend owner runs (the console repository itself is not touched from here; its task list is `docs/build-log/handoff/2026-11-15-frontend-tasks.md`).

## 1. Problem

The app works, and it was built to be shown live. Three things can break a live showing: a second story in the same tab says nothing, an SOS beeps with no way to acknowledge it, and a second story without a restart raises no alert. Beside those, a few numbers on screen contradict the app's own message. The header says Earth is 11 minutes away while the line under it says the earliest reply is in the same minute, and the time left to the red line stands still while the reading falls through it. A judge who notices one of these has reason to doubt the rest.

Who is affected: the person driving the demo, and anyone who opens the app afterwards from the project page.

## 2. Goals

1. A story can be run twice in a row, in the same tab, and plays the same both times: one alert, one early warning spoken, one SOS spoken.
2. Every alert that beeps can be silenced by acknowledging it, from its own page.
3. No screen prints a clock time for a link leg that the demo played faster than real time. The true length of the leg is printed instead.
4. The time left to the red line counts down, and says so when the line has been crossed.
5. A one-second network blip changes nothing on screen.

## 3. Not goals

- No new rule, threshold or setting in LIGHTTIME. The findings are about display and restart, not about the rules.
- No change to how fast the link plays, or to the ship's clock. Changing either on the day of the pitch risks the whole loop.
- No change to the scripted fall. It drifts for 20 seconds and then drops, so the ship says "about 70 seconds" and the SOS comes 13 seconds later. That is the script, and it is said aloud in the demo.
- No styling work beyond the lines named in the plans.
- The data owner's Earth case routes, the rebuilt month, and the host settings are other owners' work and stay in the earlier plans.

## 4. Decisions

**F1. A played leg is described by its length, not by a clock time.** The ship's clock runs at real speed and the link plays a minute of light time in a second. A stamp in true mission time would put a reply at 06:52 on an alert that the same screen shows resolved at 06:31. So the stamps stay as they are, on the demo clock, where they also decide when a message becomes visible to the other side. The console stops printing them for link legs and prints the true length: "Earliest possible reply: 22 min 2 s after sending", "reached Earth 11 min 1 s after it was sent". Where a row of clock times remains (the round-trip stepper), one caption says the link plays 60 times faster. This replaces the example "Earliest possible reply: 06:53" in section 4 of the demo-day spec.

**F2. The ship gives each leg's true length on the alert.** The alert's `timeline` gains `earth_after_s` and `earliest_reply_after_s`, in mission seconds, taken from the report that left. The console uses them and falls back to the dial's current figures if an older ship does not send them. The API table, the contract test and the typed client change in the same commit.

**F3. The time-left tile counts down on the ship's clock.** The ship already sends `red_line_at` with the frozen verdict; the console was dropping it. The tile shows `red_line_at` minus the ship's `now`, "Due now" at zero, and "Red line crossed" once the alert is an emergency. The frozen figure stays what Earth sees, under "When this left".

**F4. Any unacknowledged live alert can be acknowledged from its page, at any stage.** An SOS sends its own report, so it is never at the stage where the button used to appear. The ship's acknowledge route already accepts it. The beep stops when the alert is acknowledged or resolved.

**F5. The sentence is spoken once for each alert, level and run.** When an alert leaves the list, which a restart causes, the console forgets it spoke for it. "Sound off" also cuts a sentence that is being spoken.

**F6. A new story closes what the last one left open.** Starting a story resolves the patient's open blood-oxygen alert from an earlier run, marked as closed automatically, and tells Earth. The story with no name is `full`, the one with the early warning.

**F7. One missed answer is not an outage.** The console falls back to its built-in demo after three misses in a row, or after the first miss when it has never reached the ship. A request gives up after four seconds. During an outage the whole console is the built-in demo, with its header saying so, and not a mix of old ship alerts and built-in crew.

**F8. The Deep Space Network figure is "reported", not "measured".** NASA's feed gives a round-trip light time and does not say how it is obtained.

## 5. Requirements

### Must have before the pitch

**FR1. A second run speaks.** Console plan Task 1.
- [ ] Given a story has played with sound on, when "Restart demo" and "Start story" are pressed in the same tab, then the early warning and the SOS are each spoken once more.
- [ ] Given a sentence is being spoken, when "Sound off" is pressed, then it stops.

**FR2. An SOS can be acknowledged.** Console plan Task 2.
- [ ] Given a live SOS that nobody has acknowledged, then its page shows an Acknowledge button.
- [ ] Given that button is pressed, then the ship records who acknowledged it, the beep stops, and the stepper shows the time.
- [ ] Given an alert is resolved, then it does not beep.

**FR3. A second story raises its own alert.** Backend plan Task 1.
- [ ] Given a story's SOS was left open, when a new story starts, then that alert is resolved by "auto: a new story started" and the new story raises a new alert.
- [ ] Given a story is started with no name, then it is `full`.

### Should have before the pitch

**FR4. Legs are given their true length.** Backend plan Task 2, console plan Task 4.
- [ ] Given A1 is sent at Mars, then the status line reads "Sent. Earth is 11 min 1 s away. Earliest possible reply: 22 min 2 s after sending."
- [ ] Given a report has arrived on Earth, then its heading reads "raised 06:31 UTC, reached Earth 11 min 1 s after it was sent".
- [ ] Given the dial is on Mars, then the round trip carries the caption that the link plays 60 times faster. At the space station and the Moon it does not.

**FR5. The time left counts down.** Console plan Task 3.
- [ ] Given the early warning has been raised, then the tile's figure falls by about one second a second.
- [ ] Given the alert is an emergency, then the tile reads "Red line crossed" in the alert colour.

**FR6. A blip is not an outage.** Console plan Task 5.
- [ ] Given one answer from the ship fails, then nothing on screen changes.
- [ ] Given three in a row fail, then the header says the ship is unreachable and every panel is the built-in demo.
- [ ] Given the ship does not answer at all, then the console gives up on that request after four seconds.
- [ ] Given the ship returns, then the next answer replaces everything.

**FR7. Words.** Both plans.
- [ ] The Earth page and the sources list say the Deep Space Network figure is reported.
- [ ] `AI_USE.md` holds each line once, with no names.

### Later, not today

These are real and small, and none is needed for the pitch.

- The fourth crew card is red with no alert. Either the month is rebuilt, or the alerts list names any card state that has no alert behind it.
- "Recent packets" on the overview should read the ship's log in live mode.
- "Why the ship says this" should list the readings that raised the alert, not the latest ones.
- The header wraps to three rows at 1440 px.
- The console's tests should travel with its pull request.
- The log's first answer should be prepared when the ship starts.
- `POST /api/base/readings` should refuse an empty reading and impossible heart rates.
- The time-left settings should sit in `limits.json` with their source, beside the bands.
- A stricter setting of the time-left rule (a fall of 2.5 points) gave no false cautions on the control night for about 5 seconds less warning. Worth testing on more recordings before changing anything.
- At the start of a fast fall the 60-reading window still holds flat readings, so the stated time left is too long. Fitting only the falling part would fix it and needs its own evidence.

## 6. How we will know it worked

One run-through on the laptop that drives the pitch, twice in a row without reloading the tab: restart, sound on, start the story, hear the warning, watch the tile count down, hear the SOS, acknowledge it, hear the beep stop, tick the checklist, open Earth, reply, accept the plan. Then again. Both runs must look and sound the same. The backend suite must pass with the count each task states, and the console's type check, lint and tests must pass.

## 7. Open questions

- Frontend owner: these changes touch `console-effects.tsx`, `alert-actions.tsx`, `lighttime-card.tsx`, `earth-console.tsx`, `round-trip.tsx`, `mission-store.tsx` and `ship-api.ts`. Is other work in progress on those files? Not blocking: the tasks are small and separate.
- Reviewer: the console plan assumes pull request #4 is merged first, or that this work goes onto the same branch. Which do you prefer?

## 8. Time

Mentor hours are at 10:00 and 13:00, pitch registration closes at 14:00, the pitch is at 15:30 and the submission closes at 23:59. The three must-haves are each a few lines and come first. Everything in "should have" can also be done after the pitch and before the submission, since judges open the project page later.
