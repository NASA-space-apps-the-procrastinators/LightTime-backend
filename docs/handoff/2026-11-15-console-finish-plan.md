# Console Finish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make a second story speak, let an SOS be acknowledged, make the time left count down, print the true length of each link leg, and stop one missed answer from flipping the console to its built-in demo.

**Architecture:** Five small changes on top of `feat/live-ship` (commit `05ac88c`), delivered as one patch, `docs/handoff/2026-11-15-console-finish.patch` in the backend repository, with the logic in two small pure modules that have unit tests. The spec is `docs/specs/2026-11-15-finish-design.md` (decisions F1 to F5, F7 and F8); the findings are in `docs/reviews/2026-11-15-overnight-review.md` and, as a task list for the frontend owner, in `docs/handoff/2026-11-15-frontend-tasks.md`.

**This plan is kept in the backend repository and is for the frontend owner to run or to ignore. Nothing in the console repository has been changed.**

**Tech Stack:** Next.js 16, React 19, TypeScript, zod, Biome, Vitest, pnpm through corepack.

---

## What was checked before this plan was written

The patch was applied to a clean copy of `feat/live-ship` at `05ac88c`. There, `corepack pnpm typecheck`, `corepack pnpm lint` and `corepack pnpm test` pass (18 tests: the 11 that existed and 7 new), and `corepack pnpm build` succeeds. It has not been driven in a browser. Task 3 is that check, and it is not optional.

The patch works with the backend as it is today. One line reads a field the backend finish plan adds (`timeline.earliest_reply_after_s`) and falls back to the dial's round trip until the ship sends it.

## What the patch changes

| File | Change | Finding it fixes |
|---|---|---|
| `src/lib/alerts.ts` (new) | `beeps(alert)`: raised, or a live SOS nobody has acknowledged, never once resolved. `canAcknowledge(alert)`: a live alert past "raised" that nobody has acknowledged | 2 |
| `src/components/base-station/console-effects.tsx` | The beep uses `beeps`. The console forgets it spoke for an alert once that alert leaves the list, so a restarted story speaks again. "Sound off" cuts a sentence in progress | 1, 2 |
| `src/components/base-station/alert-actions.tsx` | A second button, Acknowledge, when `canAcknowledge` is true. The status line reads "Earliest possible reply: 22 min 2 s after sending" in place of a clock time | 2, 4 |
| `src/lib/format.ts` | `timeLeft(look, now, level)`: counts down to `red_line_at` on the ship's clock, "Due now" at zero, "Red line crossed" at an emergency, the frozen figure if an older ship sends no deadline | 5 |
| `src/components/base-station/lighttime-card.tsx` | The tile shows `timeLeft`, in the alert colour when urgent | 5 |
| `src/lib/ship-api.ts` | The alert shape keeps `lookahead.at`, `lookahead.red_line_at`, `timeline.earth_after_s` and `timeline.earliest_reply_after_s`. A request gives up after four seconds | 5, 4, 8 |
| `src/components/command-center/earth-console.tsx` | "reached Earth 11 min 1 s after it was sent" in place of a clock time. An update shows when it was sent. "reported by NASA's Deep Space Network" in place of "measured by" | 6, 12 |
| `src/components/base-station/round-trip.tsx`, `alert-detail.tsx` | A caption under the stepper when the link is playing faster than real time: "Clock times are the demo's. The link plays 60 times faster: 11 min 1 s of light time passes in 11 s." | 4 |
| `src/lib/mission-store.tsx` | One or two missed answers change nothing. Three in a row, or a first load with no ship, switch the whole console to the built-in demo, never a mix | 7 |
| `src/lib/alerts.test.ts`, `src/lib/format.test.ts` (new) | Seven unit tests for the two pure modules | |

---

### Task 1: Apply the patch on the wiring branch

**Files:** the twelve in the table above.

- [ ] **Step 1: Be on the right commit with a clean tree**

```powershell
git checkout feat/live-ship
git status --short
git log -1 --format=%h
```

Expected: no output from `git status --short`, and `05ac88c`. If pull request #4 has been merged, branch from `main` instead (`git checkout main; git pull; git checkout -b fix/console-finish`): the patch applies there too, because #4 is this branch.

- [ ] **Step 2: Check the patch applies, then apply it**

```powershell
git apply --check --ignore-whitespace ..\LightTime-backend\docs\handoff\2026-11-15-console-finish.patch
git apply --ignore-whitespace ..\LightTime-backend\docs\handoff\2026-11-15-console-finish.patch
git status --short
```

Expected: no output from the first two commands. `git status --short` lists ten modified or new files under `src/`. The two test files do not appear, because this repository's `.gitignore` ignores `*.test.ts`; they are on disk and they run.

If `--check` reports a conflict, someone has changed one of these files since `05ac88c`. Stop and tell the backend owner which file it names. Do not edit the patch by hand.

- [ ] **Step 3: Run the checks**

```powershell
corepack pnpm install --frozen-lockfile
corepack pnpm lint:fix
corepack pnpm typecheck
corepack pnpm lint
corepack pnpm test
```

Expected: the type check prints "Types generated successfully" and no error, the linter prints "No fixes applied", and the tests print `Tests  18 passed (18)`.

- [ ] **Step 4: Commit**

```powershell
git add src
git commit -m "fix: a second story speaks, an SOS can be acknowledged, time left counts down, legs show their true length, a missed answer is not an outage"
```

The two new test files stay on disk only, like the existing one. Whether the console's tests should be committed is the frontend owner's decision; to include these two, run `git add -f src/lib/alerts.test.ts src/lib/format.test.ts` before the commit.

---

### Task 2: Know what each change does, in case one misbehaves

Nothing to run. If the run-through in Task 3 shows a problem, this is where to look.

- [ ] **The voice.** `console-effects.tsx` keeps a set of `alertId:level` keys it has spoken. At the top of the effect it now deletes every key whose alert id is no longer in `state.alerts`. A restart empties the alert list for at least one poll, so the key goes, and the next story is spoken. If a second run is still silent, check that "Sound on" is pressed: every page load starts muted, because browsers allow speech only after a click.
- [ ] **The Acknowledge button.** `canAcknowledge` is true for a live alert that is not "raised", not "resolved" and has no `acknowledgedAt`. The button dispatches the same `acknowledge` action the first button does, which posts `/api/base/alerts/<id>/ack`. The ship accepts that at any stage.
- [ ] **The time left.** `timeLeft` subtracts the ship's `state.now` from `lookahead.red_line_at`. Both are on the ship's clock, which runs at real speed, so the tile falls one second a second. If it shows the frozen figure instead, the ship is not sending `now` or `red_line_at`: open `/api/base/state` and `/api/base/alerts` and look.
- [ ] **The fallback.** In `mission-store.tsx`, `misses` counts failed polls in a row and `reached` says whether the ship has ever answered since the last outage. To watch it, stop the ship: the screen holds for three seconds, then the header reads "Ship unreachable: built-in demo" and every panel is the built-in one. Start the ship: the next poll brings its data back.

---

### Task 3: The run-through, twice in the same tab

Needs the ship running on the demo morning (backend repository: `$env:DATABASE_URL='sqlite:///lighttime.db'; $env:LIGHTTIME_MORNING='1'; python app.py`) and `NEXT_PUBLIC_API_URL=http://localhost:5000` in this repository's `.env.local`.

- [ ] **Step 1: Start the console**

```powershell
corepack pnpm dev
```

Open http://localhost:3000. Expected: the header shows "Earth is 11 min 1 s away" and Mars is selected on the dial.

- [ ] **Step 2: First run**

Press "Sound on", then "Start story", then open "Alerts".

Expected, in order:
1. After about half a minute a blood-oxygen alert appears and a sentence is spoken that ends "check on Okafor now".
2. On that alert's page the tile "Time left to the red line" falls by about a second each second.
3. About 13 seconds later a second sentence is spoken, the alert is an SOS, the tile reads "Red line crossed" in red, and the console beeps.
4. An "Acknowledge" button is on the page. Press it. The beep stops and the stepper shows a time under "Acknowledged".
5. The status line reads "Sent. Earth is 11 min 1 s away. Earliest possible reply: 22 min 2 s after sending."
6. Under the stepper: "Clock times are the demo's. The link plays 60 times faster: 11 min 1 s of light time passes in 11 s."

- [ ] **Step 3: Earth**

Open "Earth". Expected: the case heading ends "reached Earth 11 min 1 s after it was sent", and the line under the title says "reported by NASA's Deep Space Network".

- [ ] **Step 4: Second run, same tab, no reload**

Go back to the crew console. Press "Restart demo", then "Start story".

Expected: both sentences are spoken again, and everything in Step 2 happens again.

- [ ] **Step 5: A blip and an outage**

Stop the ship (Ctrl+C in its window) and start it again within two seconds. Expected: nothing on the console changes. Stop it and leave it stopped. Expected: after about three seconds the header reads "Ship unreachable: built-in demo" and the crew, cabin and alerts are all the built-in ones. Start the ship. Expected: within a second the ship's data is back.

- [ ] **Step 6: Record what was seen**

If every expectation held, push the branch and add to the pull request's description: "Console finish applied: checked twice in one tab on <date and time>." If one did not, write down which step and what was seen, and tell the backend owner before changing anything.

- [ ] **Step 7: New screenshots for the documentation**

With the story at the SOS, take a screenshot of the alert page from the top of the page to the bottom of the LIGHTTIME card, and one of the Earth page, at 1440 px wide. Save them over `docs/screens/lighttime-card.png` and `docs/screens/earth-console.png` in the backend repository. The ones there now were taken before this work and show the old time-left tile and the old arrival time.

---

## Not in this plan

Listed in the finish spec under "Later, not today": naming a red crew card that has no alert behind it, reading the ship's log for "Recent packets", the header's three rows at 1440 px, committing the console's tests, and relabelling the daily rules' sources as project thresholds where the NASA document named does not contain the number.
