# 2. One process holds the mission clock

Date: 15 November 2026. Status: accepted, in the code since 14 November.

## Context

The demo starts at the same moment every time: 14 November 2026, 06:30 UTC, mission day 158, with alert A1 just raised. The ship's clock is real time plus an offset, set when the demo morning loads (`set_clock()` in `common/models.py`, called from `base_station/morning.py`). The scripted story and the vitals feed run as threads inside the app. All three live in the memory of one Python process.

## Decision

The backend runs as exactly one process with one worker: `python app.py` on a laptop, and gunicorn with `--workers 1` on one Cloud Run instance (`Dockerfile`).

## What follows from this

- A second worker or instance would hold a second clock, load the morning again, and run a story the first cannot stop. The screens would show the time jumping back and forth. The deployment notes and the operations runbook say to check that `now` in `/api/base/state` only moves forward.
- One process caps the load the ship can take. For a handful of judges on one shared demo ship that is enough.
- Every redeploy restarts the clock at 06:30, so nothing is merged to `main` during a pitch (hosted-site design, H7).
- To run more than one process, the clock offset, the story and the feed would have to move into the database or a separate worker, with one owner for each.
