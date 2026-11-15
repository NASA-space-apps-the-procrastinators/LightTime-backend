# LightTime backend

Flask and Postgres backend for LIGHT-TIME (NASA Space Apps 2026). It is the ship's computer and the delayed link to Earth. The frontend lives in another repo and polls this API once a second.

## Read first

- Design and API contract: `docs/specs/2026-11-14-backend-design.md`
- Build plan: `docs/plans/2026-11-14-backend-saturday.md`
- Done: `docs/plans/2026-11-14-tonight-integration.md` (110 tests on `main`)
- Done: `docs/plans/2026-11-14-console-contract.md` (148 tests). Its spec is `docs/specs/2026-11-14-console-data-design.md`, and the dataset it uses is reviewed in `docs/reviews/2026-11-14-dataset-review.md`
- The ship AI: `docs/specs/2026-11-14-lighttime-ai-design.md`
- Now: `docs/plans/2026-11-15-backend-finish.md` (spec `docs/specs/2026-11-15-finish-design.md`, findings `docs/reviews/2026-11-15-overnight-review.md`). The suite is at 192 tests before it and 196 after
- Now: `docs/plans/2026-11-15-backend-polish.md`, in the order `docs/plans/2026-11-15-tonight.md` gives. Its spec is `docs/specs/2026-11-15-demo-day-design.md`. The words are in `CONTEXT.md`, and why no trained model decides is in `docs/adr/0001-rules-decide-learned-models-advise.md`

Build a plan task by task, in order. The first two plans were run end to end before they were written down: 110 tests pass on SQLite and on Postgres 16. The console contract plan was written by reading the code and the data, then run task by task on SQLite: 148 tests pass. Two reviews of that work followed; their fixes and `raised_at` on reports brought the suite to 175 tests, passing on SQLite and on Postgres 16 (the review tests are in `tests/test_review.py`).

## Rules

- Tests first. Run `python -m pytest -v` after every task. Stop and tell the backend owner if the count differs from the plan.
- Build what the plan says and nothing else. New ideas go in a note to the backend owner, not in the code.
- `command_center/` may read only the `link_message` table. It must never import the ship's tables (`crew`, `reading`, `alert`, `checkin`, `reminder`).
- Do not rename an API field or route without changing the API table in the spec in the same commit. The frontend builds against that table.
- Simulated data is labelled simulated. Every threshold has a source: `base_station/limits.json` for the ship AI's rules, `data/reference/console_thresholds.json` for the console's daily rules.
- The ship reads the generated dataset only through `common/dataset.py`, and only `data/processed/reference/` and `data/processed/anomalous/`. Never `ground_truth/`, `reports/` or `clean/`: they are the answer key and the test copy.
- One reading a second on `POST /api/base/readings`. Data that arrives once a minute never goes there.
- No language model calls in the request path. Rules and templates only.
- Log AI use in `AI_USE.md`: date, who, tool, what for.
- Work on the `Tj-Backend` branch. The reviewer reviews pull requests into `main`.

## Layout

- `base_station/` is the ship: readings, rules, alerts, reports, the scripted story. It serves `/api/base`.
- `command_center/` is the Earth console's API. It serves `/api/earth`.
- `common/` is shared: tables, the delayed link, Mars light time, the who-decides rule.

## Commands

- Install: `python -m venv .venv`, then `.venv\Scripts\activate`, then `pip install -r requirements.txt`
- Test: `python -m pytest -v`
- Run: `python app.py` (port 5000, SQLite unless `DATABASE_URL` is set in `.env`). With `LIGHTTIME_MORNING=1` in `.env` it starts on the demo morning, 14 November 2026 at 06:30 UTC, and every reset goes back there. Run one process only: the mission clock lives in its memory
