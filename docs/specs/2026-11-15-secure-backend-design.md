# Secure backend: design

Date: 15 November 2026, written after the pitch. Start state: `main` at `0fa4441`, 236 tests.

**Status: archived draft, stopped by the backend owner on 15 November.** Nothing is built. This design has not been reviewed: a five-way review was started and stopped before it reported. None of the plans and handoff listed below has been written. The research behind this draft is in `docs/build-log/extra/secure-backend-research/` (untracked).

Plans, in the order they would be built (none exists yet):

1. `docs/build-log/plans/2026-11-15-secure-1-hardening.md`
2. `docs/build-log/plans/2026-11-15-secure-2-sign-in-and-roles.md`
3. `docs/build-log/plans/2026-11-15-secure-3-fhir-export.md`
4. `docs/build-log/plans/2026-11-15-secure-4-hosting-runbook.md` (commands the backend owner runs; no code)
5. `docs/build-log/handoff/2026-11-15-console-sign-in.md` (for the frontend owner)

## Problem

The ship holds health records and proves nothing about who is asking. Three things were measured on `main`:

| What | Evidence |
|---|---|
| Anyone on the internet can empty the ship | `POST /api/base/reset` deletes five tables with no check (`base_station/routes.py:430`). So can `demo/start`, and `dial` changes who decides for both consoles |
| The role rule trusts what the caller says | `X-LightTime-Viewer` is "not a login: nothing here proves who the person is" (`base_station/access.py:4`). Leaving the header out returns every record. The console never sends it |
| Earth is wide open | No route under `/api/earth` checks anything. Anyone can send advice signed "Dr. Damola" (`command_center/routes.py:126`) |

The team's own risk table says it: "No login, no encryption on the link ... a flight system would need both." The mentors said one thing firmly, twice: "if you just have everybody seeing everybody's records, that's when you run into the problem", and the design they asked for is "a chief medical officer who has access to all the records, but then individual interfaces are for their own records". The advisor added that health data needs "confidentiality" and a system that is "secure". None of them asked for FHIR or named a law. FHIR is the backend owner's requirement, and it was in the team's first brainstorm ("HL7 FHIR R4 ... surgeon packet") and in two specs as later work.

What the conversations in `docs/extra` change in this design:

| They said | So |
|---|---|
| Flight surgeon is the doctor on Earth; on board it is the crew medical officer, an astronaut with about 40 hours of medical training | Roles are named `crew`, `cmo`, `flight_surgeon`. The CMO role is assigned, not a credential |
| An SOS "dispatch[es] people to one location" and that is acceptable | An SOS stays a short notice to everyone (who, what, where). It does not open the record |
| "Nobody wants to be monitored from a distance"; share only "unless there's a specific outcome to require it" | Earth still sees only what the link delivered. FHIR export on Earth is built from the delivered report and nothing else |
| With no link "the crew medical officer will decide" | Sign-in lives on the ship and needs no link and no outside identity service |
| Users must "clearly track how the decision is made" | An audit log records who did what. `by` and `from` come from the signed-in account, not from the request body |
| Judging is remote and global; the reviewer could not open a link; the demo hops between four roles in four minutes | The hosted site stays open until judging ends, and a one-press demo sign-in exists for afterwards |

## Decisions (made with the backend owner, 15 November)

| # | Decision |
|---|---|
| S1 | **A switch.** `LIGHTTIME_AUTH=1` locks the ship. Without it the ship is open and behaves as it does today. The hosted site stays open until judging ends. Every test of the new rules runs locked |
| S2 | **Local accounts and a cookie.** Accounts live in the ship's database. A person signs in with a password and gets a signed, HttpOnly, SameSite=Strict, Secure cookie. A suit sends a key in a header. No bearer tokens, no outside identity provider |
| S3 | **FHIR is a read-only export.** Pure mapping functions build FHIR R4 resources from data the ship already has. Nothing is stored as FHIR, nothing on the link changes, nothing is sent to an outside server |
| S4 | **Backend only.** The console is changed by its owner from a handoff document |
| S5 | **No new runtime dependency.** Flask's own signed session and Werkzeug's password hashing are already installed. The one new package, `fhir.resources`, is for tests only |
| S6 | **Default deny.** Locked, a route with no entry in the policy table refuses. A test walks every route the app serves and fails if one has no entry |
| S7 | **Nothing here merges to `main` before the 23:59 submission on 15 November.** Work is on `Tj-Backend` |

## Goals

1. Locked, no route returns a person's health data, or changes anything, for a caller who has not proved who they are. Measured by a test that calls every route with no sign-in.
2. Each role can do its job and nothing else: a crew member reads their own record, the crew medical officer reads all, the flight surgeon works only from what the link delivered, the operator runs the demo, a suit sends readings for its own wearer.
3. Every action that changes something, and every refusal, is on a record that says who.
4. A hospital-style client can read vital signs, alerts and the crew as FHIR R4 resources, under the same role rule.
5. The ship answers bad input, a missing dependency and its own errors in JSON, with a status that tells an operator what failed.
6. Every network hop that exists is encrypted, and the ones that do not exist are named as not built.
7. Open, the 236 tests that pass today still pass unchanged.

## Not doing

| Not doing | Why |
|---|---|
| Encrypting the ship to Earth link | The link is a time filter on one table in one process. There is no hop to encrypt. A flight link uses Bundle Protocol Security (RFC 9172) and CCSDS Space Data Link Security; the documents say so, the code does not pretend to |
| An emergency unlock ("break the glass") | Only the AI-written cue notes raised it; no person did. The SOS notice already carries what a responder needs |
| A family, mission control or auditor role | Nobody defined one |
| Storing or receiving FHIR; a FHIR server; SMART on FHIR; pushing to HAPI | S3. The public HAPI server must never get real data, and the ship must work with no link |
| Any claim of FHIR conformance, HIPAA or PHIPA compliance | `CONTEXT.md` forbids "validated". The honest words are in the FHIR section below |
| Sensor timestamps and de-duplication of readings | A real defect (`docs/build-log/PROJECT_NOTES.md:107`), but it changes the rules engine. Its own plan, later |
| Self-pruning of old readings and link messages | Pruning before the daily summary loses data. Later, with the item above |
| Field-level encryption of notes at rest | The hosted database is in the instance's memory; Cloud SQL encrypts at rest by itself |
| Console code | S4 |
| Two-factor sign-in, password reset by email, account screens | No mail service, no link to Earth. The operator sets secrets |

## Who uses it

| Role | Who | Signs in with | May |
|---|---|---|---|
| `crew` | A crew member (C1, C3, C4) | password | Read their own record; see name cards and SOS notices for the rest; check in; acknowledge and work their own alerts; help with anyone's SOS; message Earth |
| `cmo` | The crew medical officer (C2) | password | Everything `crew` may, for every crew member; read the audit log |
| `flight_surgeon` | Dr. Damola, Dr. Youssef, on Earth | password | Read what the link delivered; reply |
| `operator` | Whoever runs the demo | password | Dial, reset, start and stop the story and the suits' feed, send summaries. Sees name cards, never a record |
| `suit` | A suit's microcontroller (LT-01 to LT-04) | key in a header | Send readings and an SOS for its own wearer |
| `service` | The suits' feed thread inside the ship | a key made at start, held in memory | Send readings for any crew member |

## Words we use (to add to `CONTEXT.md` in plan 2, task 1)

**Account.** A person or a suit the ship knows. It has a sign-in name, a role and, for crew and suits, the crew member it belongs to.

**Sign-in.** Proving who you are to the ship. Not "login", not "auth" in anything a person reads.

**Role.** What an account may do: `crew`, `cmo`, `flight_surgeon`, `operator`, `suit`. Not the same as `crew.role`, which is a job title on a card ("Flight Engineer").

**Open ship, locked ship.** Open: nobody signs in, as on demo day. Locked (`LIGHTTIME_AUTH=1`): every route asks who is calling.

**Operator.** The person running the demo. Not a crew member and not a clinician.

**Suit key.** The secret a suit sends with every reading.

**Audit log.** The record of who did what and what was refused. Nothing edits it, and a reset does not empty it.

**Demo sign-in.** One press that signs you in as a seeded account with no password. Only when `LIGHTTIME_DEMO_SIGNIN=1`. The account says `demo: true`.

Words to avoid: "secure" on its own (say what is protected from whom); "compliant", "conformant", "certified" (FHIR or privacy law).

## Requirements

P0 is what "secure backend" means; without it the work is not done. P1 is built in the same plans. P2 is recorded so the design leaves room.

### Plan 1: hardening and robustness

| # | P | Requirement | Accepted when |
|---|---|---|---|
| H1 | P0 | Every error on `/api/` is JSON `{error, field}`: 401, 403, 413, 429, 500 join 400, 404, 405 | An exception inside a route gives 500 JSON with no traceback and no exception text |
| H2 | P0 | A request body over 64 KB is refused | 413 JSON; nothing stored |
| H3 | P0 | Readings are strict: a JSON boolean is not a number; every vital has a possible range; `signal_ok` is a JSON boolean | `spo2: true`, `skin_temp: 1e300`, `signal_ok: "false"` each give 400 naming the field. A blood oxygen of 40 is still stored as a sensor check, as today |
| H4 | P0 | Text has a length everywhere: ship messages (text 2000, from 40), symptoms on acknowledge, Earth's `from` | 400 naming the field |
| H5 | P0 | Ids and limits cannot crash a route: Earth ids are ASCII digits, at most 9; `limit` has a floor | `message_id: 10**30` gives 400; `limit=-1` gives 400 |
| H6 | P0 | Security headers on every `/api/` answer: `Cache-Control: no-store`, `X-Content-Type-Options: nosniff`, `Strict-Transport-Security`, `Referrer-Policy: no-referrer`, `X-Frame-Options: DENY`, a deny-all `Content-Security-Policy` | Present on a 200 and on a 404 |
| H7 | P0 | Cross-origin calls come only from listed origins (`LIGHTTIME_ORIGINS`; default the two localhost console addresses). Same origin needs no listing | An unlisted `Origin` gets no `Access-Control-Allow-Origin` |
| H8 | P0 | A Postgres address that is not local and not a socket connects with TLS (`sslmode=require` unless the address or `LIGHTTIME_DB_SSLMODE` says otherwise); connections are checked before use | Engine options asserted for four example addresses |
| H9 | P0 | `LIGHTTIME_REQUIRE_HTTPS=1` refuses a request the load balancer marked as plain HTTP | `X-Forwarded-Proto: http` gives 403 JSON; health still answers |
| H10 | P1 | `GET /api/base/ready` says whether the ship can serve: database, dataset, clock. `/health` stays as it is | Database down gives 503 naming `database` |
| H11 | P1 | One open alert per person and vital, and one check-in per person and day, are rules of the database, not only of the code | A second row raises an integrity error; the routes still answer as before |
| H12 | P1 | Background threads survive one error and never run twice; a reset stops the suits' feed | Named tests in `tests/test_threads.py` |
| H13 | P1 | Runtime packages are pinned to the versions the suite passes on; test packages move to `requirements-dev.txt`; the image leaves out docs, the answer key and transcripts | `pip install -r requirements.txt` then the app starts; `.dockerignore` lists them |
| H14 | P1 | Pull requests run the suite (GitHub Actions) | `.github/workflows/test.yml` |
| H15 | P1 | `docs/build-log/extra/` is in `.gitignore`: meeting transcripts with real people's words do not go into a public repository | `git status` no longer lists it |

### Plan 2: sign-in and roles

| # | P | Requirement | Accepted when |
|---|---|---|---|
| A1 | P0 | Accounts are seeded at start from `reference/crew.csv` (four crew, four suits) and a short staff list (two flight surgeons, one operator). An account with no secret cannot sign in by password | Eleven accounts after start; a second start adds none |
| A2 | P0 | Secrets come from `LIGHTTIME_ACCOUNTS`, a JSON object of sign-in name to hash. No secret is in the repository. `scripts/hash_secret.py` makes a hash from a password typed at a prompt, or makes a suit key | The script's output signs in |
| A3 | P0 | `POST /api/auth/sign-in`, `POST /api/auth/sign-out`, `GET /api/auth/me`. The cookie is HttpOnly, SameSite=Strict, Secure, 12 hours | Flags asserted on the `Set-Cookie` header |
| A4 | P0 | Five wrong passwords for one name in five minutes locks that name for the rest of the five minutes | 429 with `Retry-After`; a right password is also refused while locked |
| A5 | P0 | Signing out ends every session of that account | An old cookie gives 401 |
| A6 | P0 | Locked, a call with no sign-in gives 401, except health, ready, the auth routes and the FHIR capability statement | The walk test (goal 1) |
| A7 | P0 | One policy table, `common/policy.py`, says which roles may call each route. Default deny (S6) | A wrong role gives 403 `{error, field: "role"}`; the completeness test |
| A8 | P0 | Locked, the viewer is the signed-in account. The `X-LightTime-Viewer` header and `?viewer=` are ignored. There is no "nobody is the medical station" | A crew member sending `X-LightTime-Viewer: C2` still sees only their own record |
| A9 | P0 | Buttons follow the record rule: the alert a button returns is shaped for the caller; clearing, sending and accepting a plan are for the person and the CMO; anyone on the crew may acknowledge and tick steps on an SOS; a check-in is typed by the person it is about | C3 acknowledging C1's caution gets 403; C3 acknowledging C1's SOS gets the notice back |
| A10 | P0 | `by` and `from` are the signed-in account's name. The body's value is ignored when locked | A reply sent as Dr. Youssef says Dr. Youssef whatever the body says |
| A11 | P0 | A suit key works only for readings and an SOS, only for its wearer, and the reading's source is `suit`. A crew member may type a reading for themself; its source is `typed` | LT-01's key posting for C2 gives 403 |
| A12 | P0 | A cookie-signed request that changes something must come from this site: an `Origin` header naming another site is refused | 403 `{field: "origin"}` |
| A13 | P0 | The audit log records sign-in, failed sign-in, sign-out, every refusal (401, 403), and every change a person makes, with who, role, what, whose record, and the answer. Suit and feed readings are not logged one by one. A reset does not empty it. `GET /api/base/audit` is for the CMO and the operator | Rows asserted after each kind of event |
| A14 | P0 | Locked without `LIGHTTIME_SECRET_KEY` the ship refuses to start | `create_app` raises with a message that names the setting and not its value |
| A15 | P1 | `POST /api/auth/demo` signs in as a seeded person with no password, only when `LIGHTTIME_DEMO_SIGNIN=1`; otherwise the route is 404. Suits cannot be entered this way | `me` says `demo: true` |
| A16 | P1 | Locked, one log line per request: time, sign-in name, role, method, path without its query, status | Captured in a test |
| A17 | P1 | Open, a signed-in account is used as the viewer in place of the header, so the console can adopt sign-in before the ship is locked | Signed in as C3 on an open ship, the board is shaped for C3 |
| A18 | P2 | An emergency unlock, a `station` account for a shared screen, expiry of passwords | Not built |

### Plan 3: FHIR export

| # | P | Requirement | Accepted when |
|---|---|---|---|
| F1 | P0 | `common/fhir.py`: pure functions from plain dicts to FHIR R4 resources. No database, no Flask, so Earth may use it | Imports nothing from `base_station` or `flask` (a test checks) |
| F2 | P0 | `GET /api/base/fhir/metadata`: a CapabilityStatement, `fhirVersion` 4.0.1, listing exactly the interactions below and saying the data is simulated | Passes the R4B model |
| F3 | P0 | `GET /api/base/fhir/Patient/<code>`, `GET /api/base/fhir/Observation?patient=<code>&_count=` (newest first, 20 by default, 100 at most), `GET /api/base/fhir/Flag?patient=<code>` | Searches return a `searchset` Bundle; each entry passes its model |
| F4 | P0 | `GET /api/base/alerts/<id>/fhir`: one `collection` Bundle with the Patient, the suit Device, the alert as a Flag, and the readings behind it as Observations. (This is B4 of the ship AI spec.) | Golden file |
| F5 | P0 | `GET /api/earth/cases/<id>/fhir`: the same Bundle built only from the delivered report | Equal to the ship's Bundle for the same alert, apart from the ids the report does not carry; `tests/test_wall.py` still passes |
| F6 | P0 | The record rule applies: a FHIR route answers exactly when the plain route for the same record would | C3 asking for C1's Observations gets 403 as an OperationOutcome |
| F7 | P0 | Only codes checked on hl7.org are used: the HL7 vital signs profiles below. A value with no checked code is left out and named in the capability statement | The code table in the plan cites the page for each |
| F8 | P0 | Labels: every resource carries `meta.security` `HTEST` (test health data) and `R` (restricted); a reading with a poor signal has no value and `dataAbsentReason: error`; times are mission clock and tagged so | Asserted |
| F9 | P1 | Errors on FHIR routes are an OperationOutcome; the content type is `application/fhir+json` | Asserted |
| F10 | P2 | Communication for the report and the reply thread; QuestionnaireResponse for the check-in; daily values; AuditEvent; the HL7 Java validator | Not built |

### Plan 4: hosting (commands for the backend owner)

| # | P | Requirement |
|---|---|---|
| G1 | P0 | A read-only inventory first: forwarding rules, proxies, certificate and who renews it, SSL policy, service accounts, the trigger, the database. Saved in the repo |
| G2 | P0 | Port 80 redirects to HTTPS; the load balancer's SSL policy is TLS 1.2 or later |
| G3 | P0 | `LIGHTTIME_SECRET_KEY` and `LIGHTTIME_ACCOUNTS` are Secret Manager secrets, set with `--update-secrets` |
| G4 | P0 | The unused hosted Postgres is deleted, or it requires TLS, loses its public address list and gets a new password. The owner chooses |
| G5 | P1 | A runtime service account with only what the ship needs; a startup probe on `/api/base/ready`; an uptime check |
| G6 | P1 | A rate limit at the load balancer (Cloud Armor), if the regional load balancer supports it |
| G7 | P0 | The switch: after judging, `LIGHTTIME_AUTH=1`, `LIGHTTIME_DEMO_SIGNIN=1`, `LIGHTTIME_REQUIRE_HTTPS=1`, `LIGHTTIME_ORIGINS=https://lighttime.health`, with the check that proves it and the one command that undoes it |

## Sign-in, in detail

**Who is calling** is worked out once, before any route, in `common/auth.py` (shared code lives in `common/` because Earth may not import the ship):

1. The service key header (the suits' feed inside the ship).
2. `X-LightTime-Suit-Key`: the account whose stored hash is the SHA-256 of the key.
3. The session cookie: account id and session version, both must match the row.
4. Otherwise nobody.

**Secrets.** A person's password is hashed with scrypt (Werkzeug's `generate_password_hash`). A suit key is 32 random bytes; the ship stores `sha256:<hex>`, because a key that long needs no slow hash and a suit sends one every second.

**The cookie** is Flask's signed session. It holds the account id and the session version, nothing about health. `LIGHTTIME_INSECURE_COOKIE=1` drops the Secure flag for a console on plain `http://localhost`.

**Cross-site requests.** SameSite=Strict keeps the cookie off requests from other sites. As a second lock, a changing request with an `Origin` header is accepted only if the origin's host is the request's own host or the origin is in `LIGHTTIME_ORIGINS`.

**Settings**

| Setting | Meaning | Secret |
|---|---|---|
| `LIGHTTIME_AUTH=1` | Locked ship | no |
| `LIGHTTIME_SECRET_KEY` | Signs the cookie. Required when locked. Open without it, a random one is made at start | yes |
| `LIGHTTIME_ACCOUNTS` | JSON object: sign-in name to hash | yes |
| `LIGHTTIME_DEMO_SIGNIN=1` | Demo sign-in on | no |
| `LIGHTTIME_ORIGINS` | Comma list of other origins allowed to call | no |
| `LIGHTTIME_INSECURE_COOKIE=1` | Cookie without Secure, for local work | no |
| `LIGHTTIME_REQUIRE_HTTPS=1` | Refuse what the load balancer marked plain HTTP | no |
| `LIGHTTIME_DB_SSLMODE` | Overrides the TLS mode for Postgres | no |

**New tables** (made by `db.create_all()`; no existing table changes, so no migration is needed)

| Table | Columns |
|---|---|
| `account` | `id`, `login` (unique, upper case), `name`, `role`, `crew_code`, `secret_hash`, `session_version` |
| `audit` | `id`, `at` (real UTC), `mission_at` (the ship's clock), `login`, `role`, `action` (the route's name, or `sign-in`, `sign-in-failed`, `sign-out`), `method`, `path`, `subject` (crew code, when the route is about one person), `status`, `forwarded_for` |

Neither is in the lists `reset` and the demo morning empty.

**New routes** (the API table in `docs/specs/2026-11-14-backend-design.md` changes in the same commit as each)

| Method, path | Body | Answers |
|---|---|---|
| `POST /api/auth/sign-in` | `{login, password}` | 200 `{account}` and the cookie; 401 `{error: "sign-in failed", field: "login"}`; 429 |
| `POST /api/auth/demo` | `{login}` | 200 `{account}`; 404 when demo sign-in is off |
| `POST /api/auth/sign-out` | | 200 `{ok: true}` |
| `GET /api/auth/me` | | Always 200: `{signed_in, locked, demo_signin, account}`. `account` is `{login, name, role, crew_id, demo}` or null. A console asks this first |
| `GET /api/base/audit` | `?limit=` (100; at most 500) | Newest first |
| `GET /api/base/ready` | | 200 `{ok: true, checks}` or 503 |

**The policy table** (locked). "People" is `crew`, `cmo`, `flight_surgeon`, `operator`. "Ship" is `crew`, `cmo`, `operator`. The record rule (own record or CMO) applies on top wherever a route is about one person.

| Routes | Roles |
|---|---|
| `GET /api/base/health`, `/ready`, `/fhir/metadata`; everything under `/api/auth` | no sign-in needed |
| `GET /api/base/sources`, `/thresholds`; `GET /api/earth/network`, `/feed` | People |
| Every other `GET` under `/api/base` except `/audit` | Ship |
| `GET /api/base/audit` | `cmo`, `operator` |
| `POST /api/base/readings` | `suit`, `service`, `crew`, `cmo` |
| `POST /api/base/sos` | `suit`, `crew`, `cmo` |
| `POST` on alerts (`ack`, `steps`, `send`, `clear`, `accept-plan`), `/messages`, `/crew/<ref>/checkins`, `/reminders/<ref>/done` | `crew`, `cmo` |
| `POST /api/base/dial`, `/reset`, `/demo/start`, `/scenario/start`, `/scenario/stop`; `POST /api/earth/feed/start`, `/feed/stop` | `operator` |
| `POST /api/base/summary/send` | `cmo`, `operator` |
| `GET /api/earth/state`, `/inbox`, `/cases`, `/cases/<id>`, `/cases/<id>/thread`, `/cases/<id>/fhir`, `/vitals`, `/outbox`; `POST /api/earth/reply` | `flight_surgeon` |

What a role sees through the record rule: `cmo` every record; `crew` their own; `operator` name cards and SOS notices only.

## FHIR, in detail

**What it is.** A second way to read what the ship already serves. A client that speaks FHIR R4 can list a crew member's vital signs and alerts. Nothing is written, stored or sent.

**What to say about it:** "exports FHIR R4 resources; their structure is checked against the R4B models in tests; not run through the HL7 validator; simulated data." Never "compliant", "conformant", "certified" or "validated".

**Version.** The capability statement says 4.0.1. The tests check with `fhir.resources` R4B models (4.3.0), which is the nearest the library offers: for the resources used here R4B differs from R4 only in the allowed targets of `Observation.subject`.

**Mapping**

| Ship | FHIR | Code |
|---|---|---|
| Crew member | Patient, id = crew code ("C1"), `identifier` under `https://lighttime.health/fhir/crew` | |
| Suit | Device, id = suit id, `patient` = the wearer | |
| `heart_rate` | Observation, vital signs heart rate profile | LOINC 8867-4, `/min` |
| `spo2` | Observation, oxygen saturation profile | LOINC 2708-6 and 59408-5, `%` |
| `bp_sys`, `bp_dia` | One Observation, blood pressure panel | LOINC 85354-9; components 8480-6, 8462-4, `mm[Hg]`. A missing half carries `dataAbsentReason` |
| Alert | Flag: `status` active or inactive from `cleared_at`, `period` from `at` to `cleared_at`, `code` text = the reason, level under `https://lighttime.health/fhir/alert-level`, `author` the Device for a rule and the Patient for a pressed SOS | |
| Everything else in a reading (`skin_temp`, `glucose`, `sleep_hours`, `mood`) | Left out | No code checked on hl7.org. Skin temperature under the body temperature code would read as hypothermia |

Each code is checked against its page on hl7.org when plan 3 is built, and the plan records the page.

Flag, not DetectedIssue or RiskAssessment: a Flag is "a warning or notification"; the others mean a drug interaction or a predicted illness, and "nothing predicts an illness" (`CONTEXT.md`).

**Why Earth can export too.** The mapping is pure and lives in `common/`. Earth calls it on the report payload the link delivered, so the wall holds and Earth's Bundle can never be newer than the link.

## Encrypted connections: every hop

| Hop | Today | After | Where |
|---|---|---|---|
| Browser to `lighttime.health` | HTTPS works; redirect from port 80, TLS floor and certificate renewal are unrecorded | Redirect, TLS 1.2 or later, HSTS, cookie Secure | G1, G2, H6, H9, A3 |
| Load balancer to the ship | Inside Google's network; plain HTTP inside the container | Unchanged; the runbook records what Google documents for this hop | G1 |
| Ship to Postgres | No TLS asked for; public address with an allowed list | TLS required, or the database is deleted | H8, G4 |
| Ship to NASA JPL and the Deep Space Network | HTTPS, certificates checked | Unchanged, with a test that keeps the addresses on HTTPS | plan 1 |
| Suit to ship | Unbuilt on the hosted site; plain HTTP on stage Wi-Fi | Hosted: HTTPS and a suit key. Stage Wi-Fi stays plain HTTP and the documents say so | A11 |
| Ship to Earth (the link) | One process, one table | Not built (see Not doing) | |

## Risks

| Risk | Answer |
|---|---|
| The switch is flipped and the console cannot sign in | The console work is in the handoff; the switch is one command back (G7). Demo sign-in keeps a no-password path |
| A deploy restarts the ship and every session ends | `LIGHTTIME_SECRET_KEY` is a stored secret, so cookies stay valid; accounts are re-seeded from the reference files and `LIGHTTIME_ACCOUNTS` |
| The hosted database is in memory, so the audit log is lost at restart | The request log line (A16) goes to Cloud Logging, which keeps it. Said plainly in the runbook |
| One process: the sign-in lock and the service key live in memory | Correct for one worker, which the mission clock already requires |
| Stricter input refuses something the demo sends | Plan 1 runs the full story and the suits' feed against the stricter rules before it is written down |
| Unique indexes on a database that already holds duplicates | The index is made with `checkfirst`; on failure the ship logs it and starts |
| Someone reads "FHIR" as "certified" | The words above, in the capability statement itself |

## Success measures

| Measure | Target | How it is checked |
|---|---|---|
| Routes with a policy entry | 100 % | Completeness test over `app.url_map` |
| Routes that answer a locked ship with no sign-in | Only the five public ones | Walk test |
| Health values in a refusal, an error or the request log | None | Tests on 401, 403, 500 and the log line |
| FHIR resources that pass their R4B model | 100 % of those emitted in tests | `tests/test_fhir.py` |
| Tests that passed before and pass open | 236 of 236 | The suite |
| After the switch: `curl` with no cookie to `/api/base/crew` on the hosted site | 401 | Runbook check |

## Open questions for the backend owner

1. Delete the unused hosted Postgres, or keep and lock it (G4)?
2. Who renews the load balancer's certificate, and when does it expire (G1 will show)?
3. The demo crew carry the team's first names on a public site. Keep, or return to invented names before the ship is locked?
4. Should the flight surgeons' sign-in names be `DAMOLA` and `YOUSSEF`, or neutral (`SURGEON1`, `SURGEON2`)?
