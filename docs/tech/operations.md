# Operations

A runbook for whoever runs the demo or the hosting. Each section is a few commands. The hosted ship is at `https://lighttime.health`; for a laptop, use `http://localhost:5000` instead.

The Google Cloud commands below keep the placeholders the plans use: `<ship service>` is the backend's Cloud Run service and `<region>` its region. The deployment owner has the real names. Confirm the live settings with the `gcloud run services describe` commands in [Plan C, Task C3 Step 2](../build-log/plans/2026-11-15-docs-c-technical.md) before changing anything, and never paste a password or a database address into a command, a chat or a document.

## Is it up?

    curl -s https://lighttime.health/api/base/health

Expected: `{"ok":true}`. The route reads no table, so it answers even if the database is slow.

    curl -s https://lighttime.health/api/base/state

Expected on the demo morning: `"stop":"mars"`, `"mission_day":158`, and a `now` on 14 November 2026 that moves forward each time you ask. A `now` that jumps backwards means two processes are running, each with its own clock: see [ADR 0002](../adr/0002-one-process-holds-the-clock.md).

## Before a demo

    curl -s -X POST https://lighttime.health/api/base/reset
    curl -s https://lighttime.health/api/base/state

Reset clears readings, alerts, messages, check-ins and reminders and stops any story. With `LIGHTTIME_MORNING=1` it then reloads the demo morning: 06:30 UTC on 14 November 2026, the dial at Mars, alert A1 waiting. Without it, reset leaves the ship with no readings or alerts, on the real date, with the dial where it was.

The site is one shared ship. Everyone who opens it sees the same alerts and the same dial, and a reset from any browser resets it for all of them.

## Play the story

In the console, Start story opens a click-through tour of the screens that ends with a live emergency at Mars distance. From the command line:

    curl -s -X POST https://lighttime.health/api/base/demo/start

That resets, moves the dial to Mars and plays the full story: the early warning about half a minute in, the SOS shortly after. To play a story without resetting:

    curl -s -X POST -H "Content-Type: application/json" -d '{"name": "full"}' https://lighttime.health/api/base/scenario/start
    curl -s -X POST https://lighttime.health/api/base/scenario/stop

The stories are `full` (with the early warning; use this one for a pitch), `stage` (shorter, no early warning) and `real` (a recorded fall in blood oxygen, about three and a half minutes to the SOS).

## Move the dial

    curl -s -X POST -H "Content-Type: application/json" -d '{"stop": "moon"}' https://lighttime.health/api/base/dial

The stops are `station`, `moon`, `mars` and `sun` (behind the Sun, no link). Moving to a stop with a link sends everything that waited in the queue, most urgent first.

## The vitals feed to Earth

    curl -s -X POST -H "Content-Type: application/json" -d '{"interval_s": 120}' https://lighttime.health/api/earth/feed/start
    curl -s https://lighttime.health/api/earth/feed
    curl -s -X POST https://lighttime.health/api/earth/feed/stop

Start sends one reading per crew member at once and then every `interval_s` seconds (default 120, from 5 to 3600). Each round goes to the ship as readings and to Earth as one `vitals` message with the light delay. `GET /api/earth/feed` shows whether it runs, how many ticks it has sent and how many readings the ship stored. Earth's copy is at `GET /api/earth/vitals`. The values replay the simulated suit data and say so. The console owner reports a Start suits control that calls the start route; it is not in the console copy checked for this page. The feed runs in the ship's process, so a restart or a new revision stops it.

## Logs

    gcloud run services logs read <ship service> --region <region> --limit 100

gunicorn writes one line per request and every error to the log. On a healthy start the log shows "Booting worker" once and no traceback.

## Roll back

    gcloud run revisions list --service <ship service> --region <region>
    gcloud run services update-traffic <ship service> --region <region> --to-revisions <previous revision>=100

The first command lists the revisions, newest first; pick the one before the bad deploy. A new revision starts from an empty SQLite database, so after a rollback the ship is back on the demo morning (with `LIGHTTIME_MORNING=1`) or empty.

## Faults seen this weekend

| What you see | Why | Fix |
|---|---|---|
| The console header says "Ship unreachable: built-in demo" | The console was built with no ship address, or the wrong one. `NEXT_PUBLIC_API_URL` is read when the console is built, not when it runs | Rebuild the console with the right address (`/` on the hosted site, `http://localhost:5000` on a laptop). See [the console handoff](../build-log/handoff/2026-11-15-console-readme.md) |
| The clock shows today instead of the demo morning | `LIGHTTIME_MORNING=1` is not set on the ship | Set it (`gcloud run services update <ship service> --region <region> --update-env-vars=LIGHTTIME_MORNING=1`, or in `.env` on a laptop) and restart |
| A second story fired its SOS at once | The time-left rule looked back into the first story's readings, and the first story's open alert blocked a new one | Fixed in the code: each story's trend starts at the story's own start (`scenario.since()`), and a new story closes the oxygen alert the last one left open (`scenario.close_last_run()`) |
| The time jumps back and forth between requests | Two instances or two workers, each with its own clock | One instance and one worker: `--scaling=1` on Cloud Run, and the `Dockerfile` starts gunicorn with `--workers 1` |
| The time stops moving when no page is open | Cloud Run takes the processor away between requests | Keep the processor on: `--no-cpu-throttling` (from the hosted-site plan, Task 1 Step 2) |
| On a Mac the ship will not start on port 5000 | AirPlay uses port 5000 | Run the ship on another port and point the console at it |

## When judging is over

The hosted-site plan turns the always-on instance off, so it stops costing:

    gcloud run services update <ship service> --region <region> --cpu-throttling --min-instances=0

The site then starts the ship on demand, which loses the shared clock between visits.
