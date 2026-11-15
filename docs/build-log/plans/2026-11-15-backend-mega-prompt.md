# One prompt: finish the backend, then put it behind lighttime.health

Paste everything in the block below into Claude Code, opened in `LightTime-backend`. It runs Part 1 (code, unattended) and then Part 2 (Google Cloud, where it stops for your yes before every command that changes something).

Before you paste: `gcloud auth login` and `gcloud config set project <your project>` in the same terminal, or Part 2 will only print its commands for you to run in Cloud Shell.

```
You are finishing the LIGHT-TIME backend and then making it reachable at https://lighttime.health/api. Work in this repository only. Use these skills: superpowers:executing-plans, test-driven-development, systematic-debugging, verification-before-completion, karpathy-guidelines, avoid-ai-writing (for anything you write in prose).

READ FIRST, in this order: CLAUDE.md, docs/reviews/2026-11-15-overnight-review.md, docs/specs/2026-11-15-finish-design.md, docs/plans/2026-11-15-backend-finish.md, docs/specs/2026-11-15-hosted-site-design.md, docs/plans/2026-11-15-hosted-site.md, docs/deployment-commands.md (reference only: open the section a step names).

RULES THAT ARE NEVER BROKEN
1. Never open, print, edit or commit .env. Never print the value of DATABASE_URL or any secret.
2. Every test and local run forces SQLite: prefix test commands with $env:DATABASE_URL='sqlite:///:memory:' and local runs with $env:DATABASE_URL='sqlite:///lighttime.db'; $env:LIGHTTIME_MORNING='1'.
3. Tests first. After every task run: $env:DATABASE_URL='sqlite:///:memory:'; python -m pytest -q. If the count is not the one stated below, stop that task, write what you saw to the run log, and go on to the next independent task.
4. Build what the plan says and nothing else. A new idea goes in the run log as a note, not in the code.
5. Do not touch the LightTime-frontend repository at all. Not a file, not a branch.
6. command_center/ never imports the ship's tables. Do not rename an API field or route. An API change and its row in docs/specs/2026-11-14-backend-design.md go in the same commit.
7. Work on branch Tj-Backend. Never push to main and never merge a pull request: the reviewer does that. Never force-push.
8. No team member's name in any file you write.
9. Log the work in AI_USE.md (date, "the backend owner", "Claude Code", what for).
10. Keep a run log at ..\lighttime-backend-run.md (outside the repository): one line per step with the command and its result.

PART 1: CODE (unattended)

Step 0. Get current.
  git fetch origin
  git checkout Tj-Backend
  git status --short        (untracked docs under docs/ and a modified README.md, CLAUDE.md, AI_USE.md, docs/adr/0001-*.md and docs/specs/2026-11-15-demo-day-design.md are expected: they are today's documentation. Commit them first as one commit: "docs: project documentation, how it works, deployment, submission text, review, finish and hosted-site specs and plans".)
  git merge origin/main     (main holds pull requests #7 and #9; expect a clean or trivial merge)
  Run the suite. Expected: 192 passed.

Step 1. Run docs/plans/2026-11-15-backend-finish.md, Tasks 1 to 4, exactly as written, one commit per task. Expected counts after each: 194, 195, 196, 196. Task 4 Step 3 adds one line to AI_USE.md; a line for today's review is already there, so do not add a second one for it.

Step 2. Bring in the Earth case routes from the data owner's branch.
  git merge origin/Ore-backend
  Expect one conflict, in AI_USE.md: keep every line from both sides, each once. If any file other than AI_USE.md conflicts, run git merge --abort, write which file to the run log, and skip to Step 3.
  Run the suite. Expected: 207 passed (196 plus the branch's 11 in tests/test_earth_cases.py). tests/test_wall.py must pass: it now also guards command_center/cases.py.
  Check the four new routes on the demo morning with the Flask test client (create_app("sqlite:///:memory:", morning=True)): GET /api/earth/state, /api/earth/cases, /api/earth/cases/<first case's alert_id>, /api/earth/cases/<same>/thread must each answer 200. Add the rows for any of these that are missing from the API table in docs/specs/2026-11-14-backend-design.md, taking their fields from the code, in the merge's follow-up commit.

Step 3. Harden what a hosted ship needs. Each is test-first, one commit each, and small. Skip any whose test already passes.
  a. GET /api/base/health answers 200 with {"ok": true} without touching the database tables beyond a trivial query, and is listed in the API table. (It exists; add the table row and a test if there is none.)
  b. The first GET /api/base/packets is slow because the minute file is read on first use. In create_app, after the morning loads, warm that cache once inside the app context, guarded so a missing data file cannot stop the app from starting. Test: after create_app(morning=True), the function the route uses returns without reading the file again (assert on the cache, or time two calls).
  c. POST /api/base/readings refuses a body with no vital sign at all and a heart rate outside 20 to 250 with a 400 and a plain message. Read tests/test_review.py first so you do not break what it pins. Do not change any alert rule.
  Expected count after Step 3: 207 plus the tests you added. Write the final number in the run log and in CLAUDE.md's "Now" line.

Step 4. Run it once the way the pitch will: docs/plans/2026-11-15-backend-finish.md, Task 5, Steps 1 to 4. Record the printed values in the run log.

Step 5. Check the image starts as one worker.
  docker build -t lighttime-backend .          (skip with a note if Docker is not installed)
  docker run --rm -d -p 8080:8080 -e LIGHTTIME_MORNING=1 --name lt lighttime-backend
  Ask http://localhost:8080/api/base/state ten times, a second apart: every "now" must be later than the one before, stop is "mars", mission_day is 158.
  docker logs lt must show exactly one "Booting worker". Then docker stop lt.

Step 6. Push the branch and open the pull request.
  git push origin Tj-Backend
  gh pr create --base main --head Tj-Backend --title "Backend finish: second story, leg lengths, Earth case routes, wall test, hosted hardening" --body "<the task list with the test count after each, then: Spec docs/specs/2026-11-15-finish-design.md>"
  Do not merge it. Tell the user it is ready for the reviewer and that merging redeploys the ship and resets its clock to 06:30.

PART 2: GOOGLE CLOUD AND THE DOMAIN (ask before every change)

Facts, checked from outside this morning: https://lighttime.health/ already resolves to the team's load balancer and serves the console over HTTPS, so the domain and its certificate are connected. What is missing is that the load balancer does not send /api/* to the backend (https://lighttime.health/api/base/health fails), and the console was built with no ship address.

First run: gcloud config get-value project and gcloud auth list. If either shows nothing usable, do not try to log in. Print Part 2's commands in order for the user to run in Cloud Shell, and stop.

Otherwise follow docs/plans/2026-11-15-hosted-site.md:
  Task 0 (look), then Task 1 (one always-on instance, LIGHTTIME_MORNING=1, no DATABASE_URL), then Task 2 (send /api/* to the backend).
Rules for this part:
  - Read-only commands (list, describe, logs read, url-maps export, curl) run freely. Record their output in the run log, with any secret value replaced by <hidden>.
  - Before EVERY command that changes something (services update, compute ... create, add-backend, add-path-matcher, url-maps import, builds triggers update), show the exact command with the real names filled in, say in one line what it changes and how to undo it, and wait for the user to type yes.
  - Fill the names from what the list commands return: REGION, BACKEND_SERVICE, FRONTEND_SERVICE, URL_MAP_NAME, FRONTEND_BACKEND_SERVICE. If two candidates fit, ask which.
  - Export the URL map to urlmap-before.yaml before changing it, and say where the file is.
  - If the load balancer turns out to be regional or classic, stop and show the matching commands from docs/deployment-commands.md section 7.8 before going on.
  - Do not do Task 3 (the console's cloudbuild.yaml) or Task 4: they are in the frontend repository. Instead print, for the frontend owner, the exact cloudbuild.yaml from Task 3 Step 2 with REGION and FRONTEND_SERVICE filled in, and the one sentence: "merge this only after https://lighttime.health/api/base/health answers".
  - Stop rule: if https://lighttime.health/api/base/health does not answer by 13:00 local time, stop, change nothing more, and report.

Finish Part 2 with Task 2 Step 5's checks against https://lighttime.health: / is 200, /api/base/health is JSON, ten reads of /api/base/state have a "now" that only goes forward, stop is "mars", mission_day is 158, and /api/earth/cases answers 200 once the pull request from Part 1 is merged and deployed.

FINAL REPORT (in chat, and at the end of the run log): what was done, the test count, each expected value against what you saw, anything skipped and why, the pull request link, the Google Cloud names you found, what is left for the reviewer, the frontend owner and the user. State plainly anything you did not verify.
```

## What "connect to the domain" means here

`lighttime.health` already points at the load balancer and has a working certificate. Nothing needs doing at the domain registrar. The backend joins the domain when the load balancer's URL map gets one rule, `/api/*` to the backend service, which is Part 2, Task 2. If you ever need to attach a new domain from scratch, `docs/deployment-commands.md` section 7.7 has the certificate and DNS steps.
