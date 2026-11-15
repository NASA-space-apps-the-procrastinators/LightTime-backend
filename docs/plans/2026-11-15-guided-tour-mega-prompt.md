# Guided tour: prompts for Claude Code

Two prompts. Prompt A is for the backend owner's Claude Code, opened in `LightTime-backend`. Prompt B is for the frontend owner's Claude Code, opened in `LightTime-frontend`. B depends on A only for the live endpoint; both can start at the same time, because B can be built against the response shape below and checked once A is deployed.

Checked before writing: `Tj-Backend` is at `890fb21`, 234 tests pass, and the plan applied to a copy of that commit gives 238 passing tests. The tour was timed against a running ship: bubbles at 0, 14.5, 20.6 and 25.6 seconds.

---

## Prompt A: backend (paste into Claude Code in `LightTime-backend`)

```text
You are finishing one feature on the LIGHT-TIME backend before a 15:30 pitch: a 30 second guided tour.
The plan is written, tested on a copy of this exact commit, and must be followed as written.

READ FIRST, IN THIS ORDER
1. CLAUDE.md (repo rules; they override anything below if they conflict)
2. docs/specs/2026-11-15-guided-tour-design.md (what and why)
3. docs/plans/2026-11-15-guided-tour.md (the steps, with every line of code)

SKILLS TO LOAD AND HOW TO USE THEM
- /executing-plans: run Tasks 1, 2 and 3 of the plan in order, one step at a time, ticking each checkbox.
  Do not run Task 4; that is the console's.
- /test-driven-development: Task 1 writes tests/test_tour.py first. Run it and SEE 4 failures before
  writing any code. Then make them pass with the code in Task 2 and nothing more.
- /karpathy-guidelines: surgical changes only. Touch exactly the files the plan names: tests/test_tour.py,
  base_station/tour.py (new), base_station/scenario.py, base_station/routes.py, app.py, and the docs in
  Task 2 Step 7. No refactors, no extra features, no renamed fields, no "improvements" to nearby code.
- /systematic-debugging: if any test fails in a way the plan does not predict, stop, find the root
  cause with evidence (read the failing assertion, the code path, the data), and report it to me before
  changing anything. Do not loosen a rule, a threshold or a test to make it pass.
- /verification-before-completion: never say a step worked without running it and showing the output.
  The count after Task 2 must be exactly "238 passed". The timings in Task 3 must be measured.
- /avoid-ai-writing: commit messages, the API table row and the AI_USE.md line in plain, specific
  sentences. No em dashes.
- /engineering:code-review: before opening the pull request, review your own diff against the plan and
  the spec. Every changed line must trace to a plan step. Report anything that does not.
- /engineering:deploy-checklist: before asking for the merge, confirm: suite green, API table and
  docs/frontend/lighttime-api.ts updated in the same commit as the route change (CLAUDE.md rule),
  no secrets in the diff, one process assumption unchanged.
- /playwright-skill and /10x-Team:qa-engineer: after the merge deploys, check the live site (step 5 below).

HARD RULES
- Work on the Tj-Backend branch. Start with: git status (only the three untracked docs under docs/ may
  show), git log --oneline -1 (expect 890fb21), python -m pytest -q (expect 234 passed). If any of these
  differ, stop and tell me what you see.
- Never open, print or edit .env. Never print the value of DATABASE_URL.
- No language model calls in the request path. The bubble text is fixed templates plus the ship's numbers.
- command_center/ must not import anything from base_station or the ship's tables. The tour lives in
  base_station/ only.
- Commit with explicit paths (git add <files>), never git add -A.
- Do not push to main. Open a pull request into main; the reviewer merges; the merge deploys.

STEPS
1. Plan Task 1 (failing tests). Commit nothing yet.
2. Plan Task 2 Steps 1 to 6. Expected: "238 passed".
3. Plan Task 2 Step 7 (docs, same commit) and Step 8 (commit). Also add the spec, the plan and this
   prompt file to that commit:
   docs/specs/2026-11-15-guided-tour-design.md docs/plans/2026-11-15-guided-tour.md
   docs/plans/2026-11-15-guided-tour-mega-prompt.md
   Leave docs/team-recap.md for a separate "docs:" commit.
4. Plan Task 3 Steps 1 to 3 on a local ship (python app.py, one process, move lighttime.db aside
   first). Measure with a stopwatch or a loop that prints the bubble each half second. Pass: step 4
   ("Earth hears") is up by 27 seconds. Show me the four texts and their times.
5. Plan Task 3 Step 4: push, open the pull request with gh, and after the merge has deployed:
   - curl -s https://lighttime.health/api/base/tour  -> "running": false, "step": 0 (not 404)
   - curl -s -X POST https://lighttime.health/api/base/demo/start -H "content-type: application/json"
     -d "{\"name\":\"tour\"}", then poll /api/base/tour every second for 30 seconds and print each
     change with its time. Pass: four bubbles, the last by about 27 seconds.
   - Use /playwright-skill to load https://lighttime.health/base-station once afterwards and confirm
     the page still loads with the dial and Start story (the tour must not break the existing screen).
   - Finally POST /api/base/reset on the live ship so the stage starts clean.
6. Report: commits, test count, the measured timings local and live, the PR link, and anything you
   could not verify.

IF TIME RUNS OUT
The tour endpoint is useful only once the console draws it. If the merge cannot happen by 14:45, stop
and say so; the pitch falls back to the existing "Start story" button and the presenter's cue card at
the end of the plan.
```

---

## Prompt B: console (paste into Claude Code in `LightTime-frontend`)

```text
You are adding a 30 second guided tour to the LIGHT-TIME ship console before a 15:30 pitch. The ship
(backend) decides which speech bubble to show; the console only asks once a second and draws it.

READ FIRST
- AGENTS.md and README.md in this repo (repo rules win if they conflict with this prompt)
- Task 4 of the backend's plan, pasted below in full. It holds the component code.

SKILLS TO LOAD AND HOW TO USE THEM
- /frontend-design: the bubble must look deliberate and match the console's existing theme (square
  corners, lime accent, dark mode). Use the console's existing tokens (bg-background, text-foreground,
  border, muted-foreground). It should read as a comic speech bubble: a bold border, a hard offset
  shadow, and a small tail pointing at the anchor.
- /karpathy-guidelines: add one component (src/components/base-station/tour-bubble.tsx), three
  data-tour attributes, one mount, one button. Nothing else. Do not restyle or refactor existing screens.
- /test-driven-development: add a vitest test for TourBubble first: with a mocked fetch returning
  {"running": false, ...} it renders nothing; with {"running": true, "title": "SOS", "text": "...",
  "anchor": "alerts", ...} it renders the title and text in an element with role="status". See it fail,
  then build. Run: pnpm test.
- /design:accessibility-review: the bubble uses role="status" and aria-live="polite", has enough
  contrast in light and dark mode, and never covers the button that started it.
- /verification-before-completion and /playwright-skill: do not say it works until you have run it
  against the live ship and seen all four bubbles (steps below). Take a screenshot of each.
- /avoid-ai-writing: commit message and any visible text in plain words. No em dashes.

THE ENDPOINT (already defined by the backend)
GET /api/base/tour returns:
{"running": bool, "step": 0-4, "of": 4,
 "id": "calm" | "time_left" | "sos" | "earth_hears" | null,
 "title": str | null, "text": str | null,
 "anchor": "crew:C1" | "alerts" | "earth" | null, "simulated": true}
With no story playing, running is false and the console draws nothing.
POST /api/base/demo/start with {"name": "tour"} resets the demo, sets the dial to Mars and starts it.

STEPS
1. Mark the anchors: data-tour={`crew:${crew.id}`} on each crew card's outer element,
   data-tour="alerts" on the alerts panel, data-tour="earth" on the "Earth" link in the header.
2. Write the test, see it fail, then create tour-bubble.tsx from the plan's Task 4 Step 2 and make it
   pass. Keep the fetch through the existing API_URL and LIVE from src/lib/ship-api.ts; if LIVE is false
   (built-in demo) the component renders nothing.
3. Mount <TourBubble /> once in the base station layout. Add the "Take the tour" button beside
   "Start story" in src/components/base-station/app-header.tsx, posting {"name": "tour"} to
   /api/base/demo/start, then refresh.
4. Run pnpm test and pnpm build. Both must pass. Run the project's lint (biome) on the changed files.
5. Check against the live ship once the backend's tour is deployed (curl
   https://lighttime.health/api/base/tour must answer, not 404). Run the console locally with
   NEXT_PUBLIC_API_URL=https://lighttime.health, open /base-station with /playwright-skill, press
   "Take the tour", and screenshot at about 2, 16, 22 and 28 seconds. Expected: the bubble beside the
   commander's card, then beside the alerts panel, then the SOS text, then pointing at the Earth link.
   Then check a 390 px wide phone view: if the bubble covers what it points at, pin it to the bottom of
   the screen under 768 px.
6. Commit on a feature branch, push, open a pull request into main. Do not push to main directly.
   Report the screenshots, the test and build output, and the PR link.

IF TIME RUNS OUT
If this cannot merge and deploy by 15:00, stop and say so. The pitch uses "Start story" and the
presenter's cue card instead.

--- Task 4 of docs/plans/2026-11-15-guided-tour.md (paste it here from the backend repo) ---
```

---

## Presenter's cue card (30 seconds)

Press "Take the tour" and talk over the bubbles.

| Second | Bubble | Say |
|---|---|---|
| 0 | The suits are talking | "We are at Mars. Every suit reports once a second. Earth is 11 minutes away." |
| 14 | Time left | "Nothing is out of range yet, but the ship sees the trend and says how long is left: seconds. Earth's answer takes 22 minutes." |
| 20 | SOS | "Now it is an emergency. Earth has not even heard. So the crew medical officer decides." |
| 26 | Earth hears | "And only now does the first warning reach Earth. That gap is LIGHT-TIME." |
