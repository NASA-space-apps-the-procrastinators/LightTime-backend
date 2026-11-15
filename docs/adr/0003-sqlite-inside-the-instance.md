# 3. The hosted ship keeps its tables in SQLite inside its one instance

Date: 15 November 2026. Status: accepted for the hosted demo (hosted-site design, decision H2). Confirm the live setting as `docs/tech/architecture.md` says.

## Context

The app reads `DATABASE_URL` and falls back to a SQLite file when it is not set (`create_app()` in `app.py`). The team had a Postgres database, but it accepted connections only from listed addresses, and tables made before a schema change on 14 November would stop a new revision from starting. The demo needs no history: every start and every reset loads the same demo morning.

## Decision

The hosted ship runs with no `DATABASE_URL`, so it keeps its tables in a SQLite file inside its one Cloud Run instance and reloads the demo morning at every start.

## What follows from this

- No database service to reach, allow or migrate, and no password to keep.
- Everything is lost when the instance restarts or a new revision deploys. For a demo that always begins at 06:30 that is the intended behaviour; for real crew data it would not be acceptable.
- It works only because there is one instance ([ADR 0002](0002-one-process-holds-the-clock.md)). Two instances would hold two different databases.
- Postgres still works: set `DATABASE_URL` in `.env` or through Secret Manager. A real deployment would use a managed database with backups and encryption at rest ([security and privacy](../tech/security-privacy.md)).
