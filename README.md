# LIGHT-TIME backend

**Crew health monitoring that knows how far away Earth is.** NASA Space Apps Challenge 2026, challenge "Create Health Monitoring Software for Astronauts on Space Missions".

A message from the space station reaches a flight surgeon and comes back in half a second. From Mars on 14 November 2026 the same round trip takes 22 minutes, and behind the Sun there is no link at all. LIGHT-TIME is health monitoring software built around that fact. It watches the crew's readings, works out how much time a falling reading has left, compares that with the time a reply from Earth needs, and tells the crew plainly who has to act: the flight surgeon, the crew medical officer, or the crew alone.

This repository is the ship's computer and the delayed link to Earth: a Flask API with a rule-based adviser called LIGHTTIME. The crew console and the Earth console are a Next.js app in the `LightTime-frontend` repository.

![The crew console on the demo morning](docs/screens/overview.png)

## Documentation

| Read this | For |
|---|---|
| [Project documentation](docs/project-documentation.md) | What the system does, every screen, the architecture, the API and the data |
| [How it works](docs/how-it-works.md) | The light-time math, LIGHTTIME's rules and statistics, the evidence and its limits |
| [Deployment tutorial](docs/deployment.md) | Running it on a laptop, in Docker and on Google Cloud Run |
| [Submission text](docs/submission.md) | Copy-ready text for each field of the project page, and the checklist |
| [Where things stand](docs/reviews/2026-11-15-overnight-review.md) | What is built, what was checked and what is left |
| [Design and API contract](docs/specs/2026-11-14-backend-design.md) | The API table the console builds against |

## Code Organization

- Code intended for base stations belongs in the `base_station` folder. It serves `/api/base`.
- Code intended for the command center belongs in the `command_center` folder. It serves `/api/earth`.
- Code both sides share belongs in the `common` folder: tables, the delayed link, Mars light time, the who-decides rule.

The folder names use underscores because Python cannot import a folder with a hyphen in its name.

## Quick start

Windows PowerShell:

    python -m venv .venv
    .venv\Scripts\activate
    pip install -r requirements.txt
    $env:DATABASE_URL = 'sqlite:///lighttime.db'; $env:LIGHTTIME_MORNING = '1'; python app.py

macOS or Linux:

    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    DATABASE_URL=sqlite:///lighttime.db LIGHTTIME_MORNING=1 python app.py

The ship answers at http://localhost:5000/api/base/state on the demo morning, 14 November 2026 at 06:30 UTC. Run one process only: the mission clock lives in its memory. The server does not reload on its own: stop it with Ctrl+C and start it again after a change.

Setting `DATABASE_URL` on the command line keeps the run on a local SQLite file whatever a `.env` file says. For Postgres, copy `.env.example` to `.env` and set `DATABASE_URL` there instead.

To see it, start the console from the `LightTime-frontend` repository with `NEXT_PUBLIC_API_URL=http://localhost:5000` in its `.env.local`, then `corepack pnpm install` and `corepack pnpm dev`, and open http://localhost:3000. The full walk-through, Docker and Google Cloud are in [the deployment tutorial](docs/deployment.md).

## Run with Docker

Build and run the production container:

    docker build -t lighttime-backend .
    docker run --rm -p 8080:8080 --env-file .env lighttime-backend

The container listens on port 8080 and uses `DATABASE_URL` from `.env`. It binds
to `0.0.0.0` and runs as a non-root user. For Cloud Run, the platform supplies
`PORT`; the container already uses that value.

Deploy directly from the repository with Cloud Build:

    gcloud run deploy lighttime-api --source . --region us-central1 --port 8080

Set `DATABASE_URL` through Secret Manager rather than committing it to the
repository:

    gcloud run services update lighttime-api --region us-central1 --set-secrets DATABASE_URL=database-url:latest

## Test

    python -m pytest -v

## API

The API table, the field names and the design decisions are in `docs/specs/2026-11-14-backend-design.md`.

What the ship AI and data work changed (from `docs/specs/2026-11-14-ship-ai-and-data-design.md`, section 7):

| Where | Change |
|---|---|
| Alert | New `lookahead`: `now`, `per_min`, `eta_s`, `red_line`, `at`, `red_line_at`, `reply_s`, `earth_in_time`. Null unless a falling trend was found. Frozen when the report left, so count down to `red_line_at` |
| Alert | `speak` is now also set for a falling trend. Say it once per alert id and level |
| Crew board | New `usual.heart_rate`: `low`, `high`, `n`, or null for the first ten minutes |
| Reading | New `context`. `source` can be `replay` |
| New | `GET /api/base/habitat`: cabin and radiation with source and date |
| New | `POST /api/base/summary/send`: daily summaries to Earth |
| Story | `POST /api/base/scenario/start` takes `{"name": "stage" or "full" or "real", "replay": true}`. `real` plays a recorded oxygen fall and takes about three and a half minutes to reach SOS. Use `full` for the pitch: it is the story with the early warning, and `stage` has none |
| Report to Earth | New `asked_ahead` (list of `q` and `a`), `lookahead`, `usual`. The strip is 60 readings. New link kind `summary`, new update event `escalated` |
| Behaviour | Heart rate alone raises nothing. Reset keeps the dial. A second SOS press returns the same alert with 200. Bad input returns 400 |

What tonight's integration plan added (`docs/plans/2026-11-14-tonight-integration.md`). All additive, no renames:

| Where | Change |
|---|---|
| State | Each stop adds `path_km`, `round_trip_s` and `plays_as_s` (real seconds one leg takes in the demo) |
| Alert | New `why` (how the ship reached it, in plain lines) and `cleared_note`. The timeline adds `earliest_reply_at` |
| Resolve | `POST /api/base/alerts/<id>/clear` takes `{"by", "note"}`. The note goes to Earth with the resolved update |
| New | `GET /api/base/sources`: every outside source, with what it is used for and how fresh it is |
| New | `GET /api/earth/outbox`: what Earth has sent, with status and `eta_s` |
| New | `GET /api/earth/network`: NASA DSN Now round-trip light time to Mars spacecraft beside the Horizons figure |
| Frontend | `docs/frontend/` holds a typed client and a polling hook. `tests/test_contract.py` checks the field names it expects |

## Data

`python scripts/verify_data.py` checks the light-time numbers against Horizons and DSN Now, the NEWS2 bands, the clean tables and the raw-file checksums (`--offline` skips the network, `--write` records new checksums). The checks a person must do are in `docs/data-verification.md`. `python scripts/crossval_lookahead.py` chooses the time-left settings on five volunteers and tests them on the sixth, six times (about three minutes).

`python scripts/build_clean_data.py` rebuilds `data/clean/` from the raw downloads, and `python scripts/check_spo2_rules.py` reprints the blood-oxygen evidence. Sources and licences are in `docs/data-sources.md`.

## Data and honesty notes

- Mars light time comes from NASA JPL Horizons. If the call fails, dated values read on 13 November are used and labelled.
- Crew readings in the scripted story are simulated.
- Alert bands follow the NEWS2 chart (Royal College of Physicians 2017), which is not validated for spaceflight.
- Checklist wording in `base_station/procedures.json` is demo text, not medical advice.
- AI use is logged in `AI_USE.md`.
