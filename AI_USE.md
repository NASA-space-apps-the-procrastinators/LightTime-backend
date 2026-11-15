# AI use log

One line per use: date, who, tool, what for.

- 2026-11-14, the backend owner, Claude: backend design, build plan and first version of the Flask backend code and tests.
- 2026-11-14, the backend owner, Claude Code (Opus 5.5): built the backend plan Tasks 1 to 9 test-first, and checked the Mars story over HTTP on SQLite and on a Postgres 16 container.
- 2026-11-14, the backend owner, Claude: the time-left rule and its settings were designed with Claude and chosen on six real recordings; the results and their limits are in section 6 of `docs/specs/2026-11-14-ship-ai-and-data-design.md`.
- 2026-11-14, the backend owner, Claude Code (Opus 5.5): ran the ship AI and data plan Tasks 0 to 5 (copied the prepared files, 91 tests passed, evidence script and live stories checked) and wrote the doc updates.
- 2026-11-14, the backend owner, Claude Code (Opus 5.5): ran the tonight integration plan: light-time working in the state, earliest reply time and Earth outbox, alert `why` and resolve notes, sources route, DSN Now cross-check, the field contract test and typed frontend client, the data verification script and the leave-one-volunteer-out check.
- 2026-11-14, data owner, Claude Code (Opus 5.5): repo and data audit (PROJECT_NOTES.md, DATA_PLAN.md), then the seeded data generator, anomaly injection, validator and backend replay harness in data/scripts/, and the generated data in data/processed/. No backend code changed.
- 2026-11-14, the backend owner, Claude Code (Opus 5.5): console contract: dataset reader, console rules, morning loader, alert loop.
- 2026-11-14, the backend owner, Claude Code (Opus 5.5): a multi-agent review of the console contract work, each finding checked by reproducing it, then the confirmed bugs fixed test-first (alert ids, bad input, the report for a console alert, reset, the mission date).
- 2026-11-14, the backend owner, Claude Code (Opus 5.5): a second review of those fixes (each finding reproduced), its findings fixed test-first, raised_at added to the report payload, and the suite run on SQLite and on a Postgres 16 container.
- 2026-11-14, TJ, Claude: backend design, build plan and first version of the Flask backend code and tests.
- 2026-11-14, TJ, Claude Code (Opus 5.5): built the backend plan Tasks 1 to 9 test-first, and checked the Mars story over HTTP on SQLite and on a Postgres 16 container.
- 2026-11-14, Ore, Claude Code (Opus 5.5): repo and data audit (PROJECT_NOTES.md, DATA_PLAN.md), then the seeded data generator, anomaly injection, validator and backend replay harness in data/scripts/, and the generated data in data/processed/. No backend code changed.
- 2026-11-14, TJ, Claude: the time-left rule and its settings were designed with Claude and chosen on six real recordings; the results and their limits are in section 6 of `docs/specs/2026-11-14-ship-ai-and-data-design.md`.
- 2026-11-14, TJ, Claude Code (Opus 5.5): ran the ship AI and data plan Tasks 0 to 5 (copied the prepared files, 91 tests passed, evidence script and live stories checked) and wrote the doc updates.
- 2026-11-14, TJ, Claude Code (Opus 5.5): ran the tonight integration plan: light-time working in the state, earliest reply time and Earth outbox, alert `why` and resolve notes, sources route, DSN Now cross-check, the field contract test and typed frontend client, the data verification script and the leave-one-volunteer-out check.
- 2026-11-14, Ore, Claude Code (Opus 5.5): Earth console endpoints in command_center/ (cases, threads, data age, state, ground outbox, reply validation) with tests in tests/test_earth_cases.py, and the new rows in the spec's API table.
- 2026-11-14, Ore, Claude Code (Opus 5.5): merged main into Ore-backend (resolved the spec table and Earth routes conflicts, kept TJ's `/api/earth/outbox` list shape) and switched the Earth case routes to the ship's string ids (`A1`, `C1`, `M5`).
- 2026-11-15, Ore, Claude Code (Opus 5.5): Earth cases and threads on the demo morning: read crew, reason and state from preloaded report text (listed in `inferred`), recognise "Resolved by" updates, match the ship thread's text and author, pass `simulated` through, handle `escalated` updates; three tests.
