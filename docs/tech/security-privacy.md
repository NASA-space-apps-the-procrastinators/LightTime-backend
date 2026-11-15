# Security and privacy

This page is for reviewers and judges. It says what the LIGHT-TIME demo protects today, what it does not, and what a real deployment would add. Every line below was checked against the code on 15 November 2026, and the viewer behaviour was checked by running the app on the demo morning and calling it with `curl`.

The short version: LIGHT-TIME has role-based views, not a login. The ship shapes what each screen gets by who the screen says is looking, and believes it. Nothing in the demo proves who anyone is. For a demo that holds only simulated data, that is acceptable. For a real crew it would not be.

## What is protected

### Role-based views on the ship's records

The console can name who is looking in the `X-LightTime-Viewer` header (or `?viewer=`). The rule is in [`base_station/access.py`](../../base_station/access.py), and the crew medical officer is whoever `data/processed/reference/crew.csv` marks with `is_cmo`.

| Who is looking | Crew board (`GET /api/base/crew`) | Another person's record, history or readings | Alerts | Messages about one person (outbox, inbox) |
|---|---|---|---|---|
| No header: the medical station | every record in full | allowed | every alert | all |
| The crew medical officer (C2 in the demo) | every record in full | allowed | every alert | all |
| Any other crew member (for example C3) | their own record in full, a name card (id, name, role, suit id, CMO flag) for each of the others | refused with 403: "this record is for the person it is about and the crew medical officer" | their own; someone else's SOS as a short notice; nothing for someone else's quieter alerts | only their own and those about no one |
| Earth | not served: Earth has no route to the ship's tables | not served | only what the link has delivered, as cases | only what the link has delivered |

What the running app answered on the demo morning: with no header, all four crew records came back in full. With `X-LightTime-Viewer: C3`, C3's record came back in full and the other three as name cards; `GET /api/base/crew/C1/history?metric=hr_rest` answered 403; the alert list held C3's two alerts and C4's SOS as a notice, and not C1's or C2's warnings. With `X-LightTime-Viewer: C2`, every record came back in full.

### Earth's code can only read the link

[`tests/test_wall.py`](../../tests/test_wall.py) fails if any file in `command_center/` imports the ship's code or its tables. Earth's routes build everything from link messages whose `deliver_at` has passed.

### No language model in the request path

Alerts come from fixed rules and the spoken line from templates. No reading, record or report is sent to an outside model ([ADR 0001](../adr/0001-rules-decide-learned-models-advise.md)).

### Impossible input is refused

`POST /api/base/readings` refuses an unknown crew member, a value that is not a finite number, a reading with no vital sign, a heart rate outside 20 to 250, and a `source` or `context` longer than 12 characters, each with a 400 that names the field. A blood-oxygen value outside 50 to 100 is stored as a poor signal and never judged. The check-in, reply and message routes check their own fields the same way ([`tests/test_hardening.py`](../../tests/test_hardening.py), [`tests/test_review.py`](../../tests/test_review.py)).

### Secrets stay out of the repository

A Postgres address goes in `.env`, which `.gitignore` excludes; the repository holds only `.env.example`. The deployment tutorial sets it through Google Secret Manager.

### HTTPS on the hosted site

The documented setup puts the site behind Google Cloud's HTTPS load balancer at `lighttime.health` ([architecture](architecture.md)). Confirm the live settings as that page says.

### No real health data

The crew's vital signs, the mission month and the story are simulated and labelled. The only real recordings are published research datasets from volunteers on Earth, used offline to test the rules ([data](data.md)).

## What is not protected

| Gap | Where in the code | What it means |
|---|---|---|
| No login | `access.viewer()` reads the header or `?viewer=` and nothing else | Anyone can send `X-LightTime-Viewer: C2` and read every record as the crew medical officer. Leaving the header out gives the medical station's view, which is also every record |
| The console does not send the header | the console's ship client, `src/lib/ship-api.ts`, in the copy checked on 15 November | Every screen the console draws gets the medical station's view. The role-based views exist in the API, but the hosted screens do not use them yet |
| Routine vitals are not filtered | `command_center/feed.py` sends each two-minute vitals tick as one message with no crew id, and the outbox shows messages by crew id | Any crew viewer sees every crew member's routine readings in `GET /api/base/outbox`. Found by running the app as C3 on 15 November |
| Write routes ignore the viewer | `ack`, `steps`, `send`, `clear` in `base_station/routes.py`; `accept-plan`, `checkins`, `reminders/<id>/done` in `base_station/console.py` | Any caller can acknowledge, tick, send or resolve anyone's alert, or file anyone's check-in. The answer to a write is the full alert, whatever the header says |
| Reset, story and dial need nothing | `POST /api/base/reset`, `POST /api/base/demo/start`, `POST /api/base/scenario/start`, `POST /api/base/dial` | Anyone who can reach the API can empty the ship's tables, restart the story, or move the dial, which changes who decides on both consoles |
| Earth checks nothing | every route under `/api/earth` | Anyone can read every delivered report, start or stop the vitals feed, and send a reply under any name |
| CORS allows any origin | `CORS(app)` in `app.py` | Any web page can call the API from a visitor's browser. The running app echoed `Access-Control-Allow-Origin` back for an unrelated origin |
| Data is lost on redeploy | SQLite inside the one Cloud Run instance ([ADR 0003](../adr/0003-sqlite-inside-the-instance.md)) | A new revision starts from the demo morning. Nothing is backed up |
| No record of who viewed what | nothing logs reads by person | gunicorn's access log shows requests, not who made them |
| No encryption at rest | SQLite file inside the container | Anyone with access to the instance can read the tables |

## What a real deployment would add

- A sign-in tied to each role, so the ship knows who is looking instead of being told. The crew medical officer sees every record; each crew member sees their own.
- An emergency unlock, so whoever is helping during an open SOS can see that person's record, with the unlock recorded.
- Authentication on every write, on reset, the story and the dial, and on every Earth route, with the flight surgeon's name taken from the sign-in, not from the request.
- CORS limited to the console's own address.
- A managed database with encryption at rest and backups, in place of SQLite inside the instance.
- An access log of who read which record, kept where the crew medical officer and Earth can review it.
- Data-sharing rules for each partner agency that receives crew data.

A design for the first steps exists as an archived draft, [`docs/specs/2026-11-15-secure-backend-design.md`](../specs/2026-11-15-secure-backend-design.md). Nothing in it is built, and it has not been reviewed.
