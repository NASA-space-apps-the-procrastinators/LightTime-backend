# LightTime backend

Flask and Postgres backend for LIGHT-TIME (NASA Space Apps 2026). It is the ship's computer and the delayed link to Earth. The frontend lives in another repo and polls this API once a second.

## Read first

- Design and API contract: `docs/specs/2026-11-14-backend-design.md`
- Build plan: `docs/plans/2026-11-14-backend-saturday.md`
- Tonight's plan: docs/plans/2026-11-14-tonight-integration.md

Build the plan task by task, in order. Every step has the exact code and the exact test count to expect. The plan was run end to end before it was written down: 110 tests pass on SQLite and on Postgres 16.

## Rules

- Tests first. Run `python -m pytest -v` after every task. Stop and tell TJ if the count differs from the plan.
- Build what the plan says and nothing else. New ideas go in a note to TJ, not in the code.
- `command_center/` may read only the `link_message` table. It must never import the ship's tables (`crew`, `reading`, `alert`).
- Do not rename an API field or route without changing the API table in the spec in the same commit. The frontend builds against that table.
- Simulated data is labelled simulated. Every threshold has a source in `base_station/limits.json`.
- No language model calls in the request path. Rules and templates only.
- Log AI use in `AI_USE.md`: date, who, tool, what for.
- Work on the `Tj-Backend` branch. Kyler reviews pull requests into `main`.

## Layout

- `base_station/` is the ship: readings, rules, alerts, reports, the scripted story. It serves `/api/base`.
- `command_center/` is the Earth console's API. It serves `/api/earth`.
- `common/` is shared: tables, the delayed link, Mars light time, the who-decides rule.

## Commands

- Install: `python -m venv .venv`, then `.venv\Scripts\activate`, then `pip install -r requirements.txt`
- Test: `python -m pytest -v`
- Run: `python app.py` (port 5000, SQLite unless `DATABASE_URL` is set in `.env`)
