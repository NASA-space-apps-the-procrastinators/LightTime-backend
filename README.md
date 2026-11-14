# LightTime Backend

The ship's computer and the link to Earth for LIGHT-TIME (NASA Space Apps 2026).

## Code Organization

- Code intended for base stations belongs in the `base_station` folder. It serves `/api/base`.
- Code intended for the command center belongs in the `command_center` folder. It serves `/api/earth`.
- Code both sides share belongs in the `common` folder: tables, the delayed link, Mars light time, the who-decides rule.

The folder names use underscores because Python cannot import a folder with a hyphen in its name.

## Run

    python -m venv .venv
    .venv\Scripts\activate
    pip install -r requirements.txt
    python app.py

The server listens on port 5000 and does not reload on its own: stop it with Ctrl+C
and start it again after a change. Without a `.env` file it uses a local SQLite file.
For Postgres, copy `.env.example` to `.env` and set `DATABASE_URL`.

## Test

    python -m pytest -v

## API

The API table, the field names and the design decisions are in `docs/specs/2026-11-14-backend-design.md`.

## Data and honesty notes

- Mars light time comes from NASA JPL Horizons. If the call fails, dated values read on 13 November are used and labelled.
- Crew readings in the scripted story are simulated.
- Alert bands follow the NEWS2 chart (Royal College of Physicians 2017), which is not validated for spaceflight.
- Checklist wording in `base_station/procedures.json` is demo text, not medical advice.
- AI use is logged in `AI_USE.md`.
