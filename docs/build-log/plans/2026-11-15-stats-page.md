# Stats page: plan

**Goal:** a public page at `lighttime.health/api/stats/page` that shows page views, clicks, visitors and API traffic for the site.

**Decisions (backend owner, 2026-11-15):**

1. Count clicks and page views, reported by the console, plus the API traffic the backend sees itself.
2. The page is public. No key.
3. Visitors are told apart by a daily anonymous hash. No cookies, no stored IP addresses.
4. Stats must survive a deploy. They go in the Postgres database that is already running on Google Cloud and is unused. See "Storage" for why not a new service.

**Words (add to `CONTEXT.md` in Task 1):**

- **Page view.** One screen opened in a browser, reported by the console.
- **Click.** One press of a button or link, reported by the console with the button's name.
- **Visitor.** One browser on one day, known only by a hash that changes daily.
- **Request.** One API call the backend received. Polling requests are counted apart from the rest.

## How it works

- New package `stats/`, served at `/api/stats`. It is neither ship nor Earth, and imports neither.
- The load balancer sends only `/api/*` to the backend, so the page lives under `/api/stats/` and needs no load balancer change.
- Two tables, both daily totals, never one row per event:
  - `stat_count(day, kind, name, n)` with `kind` one of `pageview`, `click`, `request`, `poll`. Unique on `(day, kind, name)`.
  - `stat_visitor(day, visitor)` with `visitor` the hash. Unique on `(day, visitor)`.
- Counts are held in memory and written every 30 seconds by one background thread, and once more at shutdown. The console polls once a second, so writing on every request would lock SQLite.
- The visitor hash is `sha256(salt + ip + user agent)`, first 16 hex characters. The salt is random, made at start and replaced when the UTC day changes, and never stored. The IP is the second from last entry of `X-Forwarded-For` (the one the Google load balancer adds), else `remote_addr`.
- Stats use real UTC time, not the mission clock, and are not touched by `/api/base/reset` (the reset names its tables, and these are not among them).
- Requests whose user agent contains `bot`, `crawler`, `spider`, `GoogleHC` or `UptimeChecks` are not counted.

## Storage

The hosted ship runs on SQLite inside the instance, which is erased on every deploy. The stats tables use a second SQLAlchemy bind, `STATS_DATABASE_URL`. When it is unset, they fall back to the main database, so tests and local runs need nothing.

Postgres is used because it is already paid for and running, and needs no new dependency or code path. Firestore would be the choice if the Postgres instance is shut down to save money: it has no fixed cost, but needs a new library, a second storage code path, and a fake for tests. Not built now.

## API (add to the API table in `docs/specs/2026-11-14-backend-design.md` in the same commit as each route)

| Method | Path | Body or query | Returns |
|---|---|---|---|
| POST | `/api/stats/events` | `{"events": [{"kind": "pageview" or "click", "name": "..."}]}`, at most 20 events, names cut to 80 characters | `204` |
| GET | `/api/stats` | `?days=7` (1 to 90) | `{"days": [{"day", "visitors", "pageviews", "clicks", "requests", "polls"}], "top_pages": [{"name", "n"}], "top_clicks": [{"name", "n"}], "top_routes": [{"name", "n"}]}` |
| GET | `/api/stats/page` | none | one HTML page that reads `/api/stats` |

## Tasks

Tests first for every task. Run `python -m pytest -v` after each and check the count. Work on `Tj-Backend`.

### Task 1: tables and the counter

- Create `stats/__init__.py`, `stats/models.py` (the two tables, `__bind_key__ = "stats"`), `stats/counter.py` (`add(kind, name)`, `see(visitor)`, `flush()`, all behind one lock).
- Modify `app.py`: set `SQLALCHEMY_BINDS = {"stats": os.getenv("STATS_DATABASE_URL") or <main url>}`.
- Modify `CONTEXT.md`: the four words above.
- Tests in `tests/test_stats.py`:
  - `add` twice then `flush` gives one row with `n == 2`.
  - a second `flush` after one more `add` gives `n == 3` (the row is updated, not duplicated).
  - `see` with the same visitor twice gives one `stat_visitor` row.
  - `POST /api/base/reset` leaves the stats rows in place.

### Task 2: the visitor hash

- Create `stats/visitor.py`: `client_ip(request)`, `visitor_id(request)`, `is_bot(user_agent)`.
- Tests:
  - same IP and user agent give the same id; a different IP gives a different one.
  - the id changes when the day changes (pass the day in, do not patch the clock).
  - `X-Forwarded-For: 1.1.1.1, 2.2.2.2, 3.3.3.3` gives `2.2.2.2`; no header gives `remote_addr`.
  - the raw IP appears in no table after a flush.
  - `is_bot("GoogleHC/1.0")` is true, a Chrome user agent is false.

### Task 3: count API traffic

- Modify `app.py`: one `after_request` hook. It skips `/api/stats`, bots and `OPTIONS`. It names the request by `request.method + " " + request.url_rule.rule` (the rule, so `/crew/C1` and `/crew/C2` count as one). `GET` counts as `poll`, anything else as `request`. It calls `see(visitor_id(request))`.
- Tests:
  - two `GET /api/base/state` then a flush give `poll`, `GET /api/base/state`, `n == 2`.
  - a `POST /api/base/dial` counts as `request`.
  - a 404 path is counted under the name `unmatched`.
  - a bot user agent adds nothing.

### Task 4: accept events from the console

- Create `stats/routes.py` with `POST /events`. Register the blueprint in `app.py` at `/api/stats`.
- Rules: body must be JSON with an `events` list; more than 20 events, an unknown `kind`, or an empty `name` returns `400` with `{"error": ...}` as other routes do. Set `MAX_CONTENT_LENGTH` to 16 KB for this route.
- Tests: one pageview and one click are counted; 21 events return 400; `kind: "x"` returns 400; a name of 200 characters is stored as 80; a bot is answered 204 and not counted.

### Task 5: the totals route

- Add `GET /api/stats` to `stats/routes.py`. It flushes first, so the page is never 30 seconds behind.
- Tests: seeded rows over three days come back as three `days` entries in date order with the right sums; `top_clicks` is sorted by `n` and holds at most 10; `days=0` and `days=91` return 400; an empty database returns empty lists, not an error.

### Task 6: the page

- Create `stats/page.html`: one file, no build step and no outside scripts. A table of the daily totals and three top-ten lists, filled by `fetch("/api/stats?days=7")`, refreshed every 30 seconds. Labelled "Real traffic, not simulated".
- Add `GET /api/stats/page` that returns the file.
- Tests: the route returns 200 with `text/html`, and the body names `/api/stats`.

### Task 7: the background flush

- In `stats/counter.py`: `start(app)` starts one daemon thread that calls `flush()` inside an app context every 30 seconds, and registers `atexit` for a last flush. `create_app` calls it only when not testing, the same way the scenario thread is given the app.
- A failed flush logs a warning and keeps the counts for the next try. Traffic stats must never break a ship request.
- Tests: a flush that raises leaves the counts in memory; the next flush writes them.

### Task 8: the console reports page views and clicks (frontend repo, own pull request)

- Create `src/lib/stats.ts`: `report(kind, name)` queues events and sends them with `navigator.sendBeacon` to `${API_URL}/api/stats/events` every 5 seconds and on `pagehide`. Does nothing in seed mode (`LIVE` is false).
- Create `src/components/shared/stats-reporter.tsx`, a client component mounted in `src/app/layout.tsx`. It reports a page view when the path changes, and has one click listener on `document` that reports the nearest `button` or `a`: its `data-stat` if set, else its `aria-label`, else its text cut to 40 characters. Crew ids in paths are replaced with `[id]`.
- Add `data-stat` to the buttons whose text changes (dial stops, alert actions, start story).
- Read `node_modules/next/dist/docs/` for the path hook before writing, as `AGENTS.md` says.
- Tests (vitest): the name rule for the three cases; nothing is sent in seed mode; events are batched into one beacon.
- This repo is mostly the frontend owner's. Open it as a pull request for their review.

### Task 9: turn it on

- Set `STATS_DATABASE_URL` on the `lighttime-backend` service once by hand (the deploy trigger only swaps the image, so it stays). Use the existing Postgres address. Do not print it.
- Push, open `lighttime.health/api/stats/page`, click around the console, wait 30 seconds, and check that the numbers move. Deploy again and check that they are still there.
- Add the entry to `AI_USE.md`. Update the test count in `CLAUDE.md`.

## Not in this plan

- Location, referrers, device types, session length, funnels.
- Following a visitor across days.
- A key or sign-in on the page. If the archived sign-in design is built, the page moves behind it.
- Raw event history. Only daily totals are kept.

## To check before starting

- That the hosted Postgres is reachable from the `lighttime-backend` service as it is configured now. It was left in place when the ship moved to SQLite, and this was not tested for this plan.
- The exact `X-Forwarded-For` shape on the hosted site: log it once in Task 9 and confirm the second from last entry is the visitor.
