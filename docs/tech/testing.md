# Testing

This page is for developers. It says how to run the backend's tests, what each test file covers, and what is not tested.

## Run the suite

    python -m pytest -q

On 15 November 2026 the suite is **236 tests, all passing**, in about 45 seconds. Run it after every change; if the count differs from the plan you are working from, stop and tell the backend owner (CLAUDE.md).

The fixtures in [`tests/conftest.py`](../../tests/conftest.py) start the app on an in-memory SQLite database and replace the calls to JPL Horizons and DSN Now with a function that fails, so the tests never touch the network and the light time comes from the dated fallback table. The `morning` fixture starts the app on the demo morning (14 November 2026, 06:30 UTC). The fixtures do not read `DATABASE_URL`: the runs on Postgres 16 that CLAUDE.md records were made by hand, and the suite as it stands always uses SQLite.

## What each file covers

| File | Tests | What it checks |
|---|---|---|
| `test_access.py` | 9 | Who may read whose health record on the ship (`base_station/access.py`) |
| `test_app.py` | 2 | The app starts with four crew and the dial at the station; the health route answers |
| `test_base_api.py` | 13 | The ship's main routes: readings reach the crew board, the dial changes who decides, an emergency sends a report with its times and a spoken line |
| `test_clean_data.py` | 5 | The scripts that clean the raw recordings: one-second steps, exercise marked, impossible jumps flagged, cabin gaps dropped |
| `test_clock.py` | 3 | The mission clock starts where it is told and keeps running; without one the ship keeps real time |
| `test_console.py` | 19 | The console's routes: alerts in the console's words, a sensor check as a recheck, the crew cards, the trend chart, check-ins |
| `test_contract.py` | 1 | The exact fields each screen gets; `docs/frontend/lighttime-api.ts` mirrors these sets |
| `test_dataset.py` | 4 | The files the ship reads match the recorded build, and the ship cannot open the answer key |
| `test_demo_day.py` | 13 | The demo morning's screens: the ship's clock in the state, a live emergency turns the card red, simulated values say so, every alert says who decides |
| `test_demo_start.py` | 1 | One button for the stage: the demo starts again, the dial goes to Mars, the full story plays |
| `test_earth_api.py` | 6 | Earth sees nothing until the light arrives; a reply takes the same time back; a blackout queues the report and flushes it |
| `test_earth_cases.py` | 14 | The Earth console: cases, threads, data age, link state and Earth's outbox |
| `test_feed.py` | 11 | The vitals feed lives on the Earth side: each tick goes over the link and Earth keeps it |
| `test_habitat.py` | 3 | The cabin strip replays NASA's record and loops |
| `test_hardening.py` | 13 | Wrong input, a second press, a second sender (found by the code review on 14 November) |
| `test_lighttime.py` | 2 | Horizons' answer is read correctly; offline, the dated table is used |
| `test_link.py` | 4 | Short legs play in real time and long ones faster; a message is invisible until it lands; a blackout flushes the SOS first |
| `test_log.py` | 7 | The health log: the suits' minute packets and each sensor's lowest signal |
| `test_lookahead.py` | 10 | The time-left rule: one wild reading does not move the trend, a steady fall raises a caution while the reading is still normal, and what the ship says at Mars and near Earth |
| `test_modes.py` | 5 | Who decides at each dial stop |
| `test_morning.py` | 4 | The demo morning starts at 06:30 on day 158 at Mars, and a restart puts the same morning back |
| `test_recorder.py` | 3 | Readings older than a day leave the recorder; the daily summary travels to Earth |
| `test_replay.py` | 6 | The stories on real wrist and oximeter recordings |
| `test_review.py` | 23 | Found by the review of the console contract on 14 November |
| `test_rules.py` | 10 | The bands, the five-reading rule, escalation without duplicates, a loose sensor never sending an SOS |
| `test_scenario.py` | 9 | The scripted story plays the same every run, raises one SOS, and ends when the crew treats the patient |
| `test_scoring.py` | 6 | The console's daily rules against each person's own band |
| `test_signal.py` | 3 | An impossible oximeter number counts as a dropout, and a sensor just put back on cannot raise an alarm |
| `test_tonight.py` | 22 | The light-time working shown on screen, the earliest-reply time, and the other fixes from the integration night |
| `test_usual.py` | 4 | Each person's usual range comes from their own resting history, and exercise does not stretch it |
| `test_wall.py` | 1 | Earth's code may read the link and the dial, never the ship's own tables |

## What is not tested

- The console end to end. The backend's tests check the fields the console reads (`test_contract.py`), not the screens. The console repository has its own tests.
- The hosting: the load balancer, Cloud Run's settings and the one-instance rule are checked by hand ([operations](operations.md)).
- Postgres, in the automatic suite (see above).
- Real sensors. The suit's field names are accepted and tested, but no test runs against a live ESP32 or a real oximeter.
- The live NASA services. The tests run offline; `python scripts/verify_data.py` checks Horizons and DSN Now when the network is there.
- Security. There is no login to test; [security and privacy](security-privacy.md) lists what is not protected.
