# AI use log

One line per use: date, who, tool, what for.

- 2026-11-14, TJ, Claude: backend design, build plan and first version of the Flask backend code and tests.
- 2026-11-14, TJ, Claude Code (Opus 5.5): built the backend plan Tasks 1 to 9 test-first, and checked the Mars story over HTTP on SQLite and on a Postgres 16 container.
- 2026-11-14, Ore, Claude Code (Opus 5.5): repo and data audit (PROJECT_NOTES.md, DATA_PLAN.md), then the seeded data generator, anomaly injection, validator and backend replay harness in data/scripts/, and the generated data in data/processed/. No backend code changed.
- 2026-11-14, Ore, Claude Code (Opus 5.5): Earth console endpoints in command_center/ (cases, threads, data age, state, ground outbox, reply validation) with tests in tests/test_earth_cases.py, and the new rows in the spec's API table.
