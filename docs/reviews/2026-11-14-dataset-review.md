# Review of the generated crew dataset (commit a25791f)

Date: 14 November 2026, evening. Reviewed for the backend owner. Scope: commit `a25791fa10928afd9f0891c5005ac9089dd17af4` on the data branch (58 files, 493,456 added lines), read against the console's API contract, the console's own seed and rules (`src/data/crew-seed.json`, `src/data/thresholds.json`, `src/lib/scoring.ts` on the console's `feat/alert-loop-and-log` branch) and the backend on `main` at `75d6c5f` (110 tests).

How this was checked: the commit was read file by file; small scripts counted and compared values; the backend's time-left rule was re-run offline on the dataset's two oxygen falls. No backend code was run and no file in the commit was changed. Numbers below come from those checks unless a line says otherwise.

What follows from this review: `docs/specs/2026-11-14-console-data-design.md` (what the backend serves from this data) and `docs/plans/2026-11-14-console-contract.md` (how to build it).

## 1. Verdict

Use it. The dataset is the right base for the console's four screens tonight, and it is built with care: one seeded command, byte-identical rebuilds, a hash for every output, a clean and an anomalous version that differ only inside the injected events, and an answer key kept apart from the data the ship reads. The guidance that came with it is correct: the backend reads `data/processed/reference/` and `data/processed/anomalous/`, never `ground_truth/` or `reports/`, and `clean/` only in tests.

Five things in it are not what they first look like. None blocks tonight. Each is listed in section 4 with what the backend does about it and what, if anything, the data owner is asked to do.

## 2. What the commit contains

| Part | Files | What it is |
| --- | --- | --- |
| Reference | `reference/mission.csv` (1 row), `crew.csv` (4), `habitats.csv` (2), `metrics.csv` (16), `channels.csv` (9), `baselines.csv` (36), `thresholds.csv` (12), `link_windows.csv` (31) | Shared by both builds. Launch on 10 June 2026, so 14 November is mission day 158. Crew `C1` to `C4`. One link window a day with that day's JPL Horizons light time, plus one 18-hour blackout |
| Demo build | `anomalous/`: `daily_summary.csv` (632 rows, days 1 to 158), `checkins.csv` (119), `alerts_seed.csv` (7), `messages.csv` (82), `reminders.csv` (4), `cabin_env.csv` (16,843), `radiation_daily.csv` (30), `space_weather_events.csv` (2), `sos_events.csv` (1), `vitals_1min.csv` (168,600), `vitals_1hz_demo.csv` (57,900) | The 30 days ending at `demo_now`, 14 November 06:30 UTC, with 10 medical or environmental events and 4 sensor faults injected |
| Healthy build | `clean/`: the same files with nothing injected | For testing only |
| Answer key | `ground_truth/anomalies.csv` (17 rows) | What was injected and what a correct system should raise |
| Reports | `reports/validation.txt` (PASS), `coverage.md`, two replay reports, two rule-scoring reports | For scoring. Not for the ship |
| Scripts | `data/scripts/` (11 files, standard library only) | Generator, injector, validator, replay harness, console-rule scorer |
| Notes | `DATA_PLAN.md`, `PROJECT_NOTES.md`, `data/README.md` | The plan, an audit of the backend as it was at the fork, and how to rebuild |

Three corrections to the notes that came with it. The two `vitals_*.csv` files are in the commit (24.6 MB and 10.0 MB in the demo build); only `packets.csv` is ignored by git and has to be rebuilt. The README names a `reports/REPLAY_SUMMARY.md` that is not in the commit. The folder `data/processed/clean/` (a healthy crew) has the same last name as the backend's existing `data/clean/` (cleaned NASA files): they are different things.

## 3. What is right, and should be kept

1. The honesty model. Every generated row carries `simulated` and `provenance`. The solar particle events are marked simulated and laid out like NASA DONKI records, not presented as real ones. This settles an open point in the contract, which showed the 05:58 event with `"simulated": false`.
2. Real NASA data where it exists. Hab A's cabin CO2, temperature and humidity are the ISS Rodent Research 1 record from NASA's Environmental Data App, shifted onto the mission calendar with the 2014 time kept in `orig_ts`. All 8,422 rows match the raw file. The radiation columns in mGy match the raw file on 30 of 30 days.
3. No invented unit conversion. CO2 goes from ppm to mmHg by Dalton's law with the row's own cabin pressure. Radiation is not converted from mGy to mSv: the mSv column is simulated and says so.
4. Core and skin temperature are separate. This agrees with the backend's position that skin temperature must not be renamed `temp_c`.
5. Negative controls. Exercise, an athlete's sleeping heart rate and slow microgravity drift are in the data on purpose, so a rule that fires on them is caught.
6. The backend audit in `PROJECT_NOTES.md` section 6. Of its eight findings, two were already fixed on `main` before this review (an unknown crew now returns 400, and a bad `limit` no longer returns 500). The ones that matter next are listed in section 6 below.

## 4. Findings

### F1. The replay reports describe an older backend, and one of them is a smoke run

The replay harness imports the backend from the branch it sits on, which forked from `main` before the ship AI work. `BUILD_INFO.json` records that commit (`5569795`). Two consequences.

`reports/replay_anomalous.md` says "Caught 0, missed 13". It replayed 2,000 events in 9 seconds, which is the harness's `--limit` smoke test: about the first eight hours of 16 October, before any injected event. It is not a score and must not be quoted as one.

`reports/replay_clean.md` is a full run (225,657 events) and is useful, but against rules that have since changed. Its 1,030 alerts on 30 healthy days split as 384 heart rate, 320 estimated blood pressure and 326 sensor checks. On `main` heart rate no longer raises an alarm, so the 384 cannot occur. The 320 can and the 326 can.

What the backend does: treats the clean-build count as the measurement that motivates finding F2, and nothing more. Asked of the data owner: after the dataset is merged, re-run both replays in full against the merged backend and replace both reports.

### F2. The estimated blood pressure still alarms on healthy sleep

The shirt's systolic estimate arrives once a minute and is judged with the hospital NEWS2 bands (caution at 110 mmHg or below). The crew's own bands start between 104 and 112, and the estimate dips about 10 in sleep. In the healthy build 54,021 minute rows sit in the caution band, 23,427 in the warning band and 183 at or below 90. An offline re-run of today's rules gives about 300 blood pressure alerts in 30 healthy days, three of them reaching emergency and sending a report to Earth by themselves. 45 of the 119 morning cuff readings are also at or below 110 and would each raise a typed caution.

This is the same failure the ship AI already fixed for heart rate, measured on a second dataset. Root cause: a fixed hospital band applied to a continuous estimate, for people whose normal range crosses that band.

What the backend does: blood pressure stops raising a live alarm and is judged once a day against the person's own band by the console rule, from the cuff (plan Task 9, spec requirement A10). The sensor-check advisories stay: the signal really was poor in those minutes.

### F3. The dataset is one row a minute; the ship AI's rules assume one a second

`POST /api/base/readings` assumes one reading a second from one sender. Fed minute rows, "five readings in a row" becomes five minutes while the reason still says "5 s", the settle period becomes ten minutes, and the time-left rule reads a slope per minute as a slope per second. Re-run offline on the minute rows it raised 24 trend warnings on ordinary evening oxygen drift, each of which would send a report to Earth, and on the first injected fall it reported 88 seconds left when the red line was 14 minutes away.

What the backend does: minute data never goes through `/readings`. The console's daily values come from `daily_summary.csv` and the check-ins. Only one-a-second data (the suit on stage, the recorded replays, the dataset's 1 Hz windows) goes to the ship AI. Stated as a rule in `docs/specs/2026-11-14-suit-data-design.md`. Asked of the data owner: the replay harness should post only the 1 Hz windows to `/readings`.

### F4. Crew two to four differ from the console's seed

The dataset says its demo morning matches the contract exactly. That holds for crew `C1`, the only one the contract spells out. For `C2` to `C4` the dataset used draft values because the console's seed file was not to hand, and they differ from what the console shows today:

| | Console seed | Dataset |
| --- | --- | --- |
| C2 role, resting HR band, today | Flight engineer, 55 to 67, 61 bpm, sleep 6.1 h, mood 3 | Flight Engineer, 58 to 70, 65 bpm, sleep 6.0 h, mood 4 |
| C3 role, resting HR band, today | Science officer, 50 to 62, 56 bpm | Flight Engineer, 60 to 72, 68 bpm |
| C4 role, resting HR band, today | Medical officer, 54 to 66, 60 bpm, sleep 7.1 h | Mission Specialist, 46 to 56, 51 bpm, sleep 6.2 h |
| Crew medical officer | C4 | C2 |
| Dose, day and mission | 0.50 / 79.6, 0.49 / 78.9, 0.50 / 80.2 | 0.51 / 81.0 for everyone |

The two cannot be mixed: C3's and C4's 30 days of resting heart rate sit outside the console's bands on 7 of the last 7 days, so the console's bands on the dataset's values would raise two false alerts. With the dataset's own bands and the console's own rules the morning scores `C1` ALERT, `C2` WATCH (sleep), `C3` OK and `C4` ALERT (sleep below band for three days), where the console's seed shows `C4` OK.

What the backend does: reads crew, bands and values from the dataset only, so they are always consistent, and pins only `C1` in its tests. Asked of the data owner: copy the four crew blocks from the console's `crew-seed.json` into `data/scripts/config.py` (`CREW` and `BASELINES`), rebuild and commit. It is one edit and a 90-second build, and the backend needs no change when it lands.

### F5. Four of crew one's morning values exist only after the demo starts

At 06:30 crew `C1` has not checked in. Blood pressure 128/82, mood 2 and reaction time 312 ms are in the dataset only as the check-in at 06:38, flagged `live_demo`, which is the one the presenter does on stage. The contract's example shows those values already on the card, and also shows `C1` as due for check-in. Both cannot be true at once.

What the backend does: until today's check-in exists, the card shows the most recent check-in (13 November: mood 3, 301 ms, 110/71, symptoms headache and short sleep), and the suit's values for today (resting heart rate 84, temperature 37.2, sleep 5.1 h). Crew `C1` still scores ALERT at 06:30 on three metrics. After the live check-in the card matches the contract, with one gap: the check-in body in the contract has no blood pressure, so 128/82 can only arrive if the console sends the cuff reading (spec decision D9).

### F6. Smaller points

| # | Point | Effect | Action |
| --- | --- | --- | --- |
| a | `thresholds.csv` has `pending` as the source on 10 of 12 rows | "pending" must never reach a screen | The backend takes rule text and sources from a copy of the console's `thresholds.json` |
| b | The contract's Scoring table, the console's `thresholds.json` text and the console's `scoring.ts` code are three different rule sets (for example reaction time: "+15 % with a symptom", "+30 % with a sleep flag", and in code any out-of-range value with any symptom) | The screen can alert on a rule it does not print | The backend mirrors the code, which is what runs. The frontend owner is asked to make the text match (spec section 9) |
| c | Read literally, "resting HR > baseline + 20 bpm for 3 consecutive days" is not met by 80, 82, 84 against a band of 52 to 64 (64 + 20 = 84) | The demo alert's printed rule is stricter than the rule that raised it | Same as (b) |
| d | Alerts `A4` and `A5` (heart rate 133 at rest, 37 in sleep) cite "HR far over band at rest" and "HR far under band" | No such rule exists in the console or in the ship AI. Both would miss these two events today | The backend does not load `A4` and `A5` or their messages. A context-aware heart rate rule is listed as later work in the ship AI spec |
| e | Seeded alert values differ from the minute data at the same minute (`A3` says 93, data 93.9; `A7` says 91, data 93.8) | Cosmetic | None tonight |
| f | Hab A rows are flagged `simulated=true` although three columns are real | Understates the NASA data | `GET /station` flags each value separately, from `real_fields` |
| g | `gateway_ts` is earlier than `sensor_ts` on 123,741 of 168,600 minute rows | Two clocks, by design; a loader must not assume order | None tonight (the backend loads neither column) |
| h | 966 minute rows cover minutes that also have 1 Hz rows | Loading both files double counts | The backend loads neither tonight |
| i | `activity_label` values `exercise_ared` and `exercise_cevis` are longer than the backend's 12-character `context` column, and the backend looks for the exact word `exercise` | A loader that sends them fails on Postgres and loses the exercise flag | If these labels are ever sent, send `exercise` |
| j | Message delays are real mission seconds (665 to 777 s). The live backend plays a delay of a minute or more 60 times faster | Loaded history and live messages are on different clocks | Loaded messages are all in the past, so they simply show as delivered |
| k | `channels.csv` names (`pulse_ox`, `bp_est`, `core_temp`) are not in the console's packet schema (`ppg`, `cuff`, `thermistor`) | The health log would reject them | For the data owner and the frontend owner to settle before step 5 of the contract |
| l | The core temperature channel is modelled on a sensor the CSA Bio-Monitor does not list (the file says "check before citing") | A citation risk in the pitch | Do not name the Bio-Monitor as the source of core temperature |
| m | `DATA_PLAN.md`, `PROJECT_NOTES.md`, `data/README.md` and the `AI_USE.md` line name team members | The backend owner asked for roles, not names, in project documents | The backend owner's call |

## 5. What the ship AI learns from this dataset

Two honest results, both on generated data, so they are consistency checks and not evidence.

The injected oxygen falls are slow: about 0.2 points a minute for the first (crew `C3`, 6 November) and 0.5 for the second (13 November, during the blackout). The ship AI's time-left rule needs a fall of 2 points inside one minute and did not fire on either at one reading a second (0 of 7,800 and 0 of 7,200 seconds). The band rules caught both: first caution at 14:20:54, warning at 14:30:08 and emergency at 14:39:15 for the first; 03:08:00, 03:12:50 and 03:17:19 for the second. So the time-left rule covers fast falls (the real recordings it was tuned on reach the red line in about a minute) and the bands cover slow ones, with 18 and 9 minutes between the first caution and the red line.

A slower version of the same rule was tried on the minute rows (15-minute window, 30-minute horizon): no warning in 30 healthy days for four crew, and both falls flagged, but no earlier than the first caution, and its estimate of the time left was too long by half (29 minutes against 19) and by a factor of three (23 against 7), because both falls speed up. It is not worth building.

## 6. Still open from the audit in `PROJECT_NOTES.md`, in order of what matters next

1. Readings carry no sensor time. `Reading.at` is the ship's clock on arrival. For replayed or buffered data this loses the real time. Not needed tonight; needed before any minute data is stored.
2. An open alert hides a later breach of the same vital until a person clears it. By design (one card per problem), but a replay must clear alerts as the harness does.
3. The link is down only while the dial is on the Sun stop. There is no calendar of contact windows. `link_windows.csv` is the first data that could drive one.
4. There is no flat-line check: a sensor stuck at one value with a good signal passes. The dataset's fault `SF02` is the test case.
