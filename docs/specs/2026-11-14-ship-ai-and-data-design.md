# LIGHT-TIME: data and ship AI design

Date: Saturday 14 November 2026. Owner: The backend owner. Reviewer: The reviewer. Build plan: `docs/plans/2026-11-14-ship-ai-and-data.md`.

This is the second spec. The first (`2026-11-14-backend-design.md`) covers the API, the delayed link and the alert rules, and it is built. This one covers what is left: where the data comes from, how it is cleaned and mapped, what the ship's AI does with it, and the fixes from the code review.

## 1. Where the backend stands

The backend in the first spec is implemented. Your repo matches the reference build file for file (25 of 26 identical, the other differs by two comments), all 45 tests pass, and the branch is pushed. An independent review played the stage story over HTTP on SQLite and Postgres: SOS at 8.5 s, Earth sees it only after the delay, the reply comes back, no server errors.

The review found ten problems, none on the scripted happy path. All are fixed in this plan:

| # | Problem | Fix |
|---|---|---|
| 1 | An unknown `crew_id` on `/sos` or `/readings` made `/alerts` fail on every poll until reset | Checked first, answers 400 |
| 2 | A second sender for the same person (the story plus the hardware owner's sensor) hid the SOS | Each sender is judged on its own readings |
| 3 | Pressing Resolve before ticking the mask step left Okafor at 86% for a minute | Resolving also ends the collapse |
| 4 | Two Start presses played two stories at double speed | One lock, one story |
| 5 | One bad reading, or `"by": null`, killed the story thread silently | Caught and logged, story continues |
| 6 | Reset moved the dial back to Station, so a restarted demo lost Mars | Reset leaves the dial alone |
| 7 | An empty box on the check-in form returned 500 and lost the whole check-in | Empty means no reading |
| 8 | A sent caution that became an SOS produced two reports | Earth gets an update instead |
| 9 | Resolve or SOS pressed twice told Earth twice | Second press changes nothing |
| 10 | The first screens to load waited on JPL if the network was slow | JPL is asked once at start-up |

Two things the review noted that we are leaving: Earth's screen sees the dial move instantly (the dial is a demo control, not telemetry), and `GET /crew/<id>/readings` includes typed check-ins (filter on `source`).

## 2. Data collection

Three ways in, as in the data-sources spec: a live API, a file in the repo, or a fact copied by hand. Nothing is scraped.

| Data | Source | Licence | How | State |
|---|---|---|---|---|
| Mars light time | JPL Horizons | NASA, public | Live API, dated fallback | Built |
| Heart rate, skin temperature, activity | PPG-DaLiA, 15 volunteers, wrist | CC BY 4.0 | `data/ppg_dalia/` | In repo |
| Cabin temperature, humidity, CO2, radiation dose | NASA OSDR EDA, mission RR-1 on the ISS | NASA, public | `data/eda/` | In repo |
| Blood oxygen falling and recovering | UW induced-hypoxemia study, 6 healthy volunteers, 1 reading a second | MIT | `data/spo2_uw/` | Added today |
| Blood oxygen in a person who is fine, 8 hours | Apnea-ECG, control record c01r | ODC-By 1.0 | `data/spo2_apnea_ecg/` | Added today |
| Fast oxygen falls, 579 of them | Apnea-ECG, patient record a01r | ODC-By 1.0 | `data/spo2_apnea_ecg/` | Added today |
| Risk names on alerts | NASA HRP risk list | NASA, public | Copied by hand | Built |

Still to download, none of it blocking today: Harespod (15 students in a pressure chamber at simulated altitude, the closest thing to a cabin leak, 72 MB, licence terms need a read first) as an unseen test for the oxygen rules; the PhysioNet five-device set (13 healthy adults walking, 27 MB each) as an awake false-alarm test; CSA PRET reaction-time files only if we build the reaction test. Live feeds (DONKI, DSN Now) need no download and are Sunday work.

No NASA or CSA open dataset with blood oxygen could be found. The NASA resource that makes us eligible for Global Awards is still the HRP risk list, which is on every alert.

## 3. Data cleaning

One script, `scripts/build_clean_data.py`, reads the raw folders and writes `data/clean/`. Raw files are never changed. A row that looks wrong is kept and flagged, not deleted.

Wrist files: heart rate (one a second) and skin temperature (four a second) are lined up on one-second steps, and temperature becomes the middle of its four values. A second is marked `exercise` during stairs, soccer, cycling or walking and for five minutes after. A second is flagged when heart rate jumps more than 10 bpm (the default in the CSA's own heart-rate filter) or skin temperature more than 0.5 C. Across 15 volunteers that flags 0 to 2 seconds each.

Cabin: 12,087 rows, none dropped. Radiation: 39 daily doses.

Blood oxygen, at the door (`ingest`): a number below 50 or above 100 is a sensor dropout, not a reading. For ten readings after a dropout nothing can raise an alert, because a finger probe that has just been put back on reads low while it settles. Both rules came from the control recording, section 6.

## 4. Data mapping

| Clean column | Goes to | Notes |
|---|---|---|
| wrist `heart_rate`, `skin_temp` | `reading.heart_rate`, `reading.skin_temp` | Crew 1, 2, 3 replay volunteers S15, S12, S2 (calm, clean stretches) |
| wrist `context` | `reading.context` (new column) | `rest` or `exercise` |
| wrist `signal_ok` | `reading.signal_ok` | |
| spo2 event `spo2`, `pulse` | `reading.spo2`, `reading.heart_rate` of the patient | Only in the `real` story |
| cabin `temp_c`, `humidity_pct`, `co2_ppm` | `GET /api/base/habitat` | One five-minute row every 5 s. CO2 in mmHg is ppm x 0.00076, so 2641 ppm is 2.0 mmHg |
| radiation `total_mgy_day` | `GET /api/base/habitat` | Shown, never alerts |

Every replayed reading has `source: "replay"`, so a screen can label it.

## 5. The 24-hour recorder

The reading table is the base station's recorder. When a story starts with real data, each crew member's previous two hours are loaded first, so charts and the usual range have a past. `POST /api/base/summary/send` sends Earth one summary per person (low, middle and high of each vital, minutes of exercise, alerts) through the same delayed link, then deletes readings older than 24 hours.

## 6. Ship AI

One rule governs it: nothing may raise an alarm until it has been tried on real recordings, and the results are written down. Two results came out of that today.

### Heart rate does not alarm

On 15 healthy volunteers at a desk, the hospital heart-rate bands raised a caution for 14, a warning for 5 and an SOS for 1. A personal range learned from each person's own readings only stopped the false alarms once it was too wide to catch a 30 bpm rise (caught for 1 of 15). So heart rate is displayed, compared with the person's usual range, and sent to Earth. It never raises an alert on its own. This agrees with wearable studies that needed many nights of resting data to detect anything (Mishra 2020, Alavi 2022) and with the frontend owner's rule of 20 bpm over baseline for three days, which needs more days than we hold.

### Blood oxygen: cleaning first

On 7.8 hours of a sleeper with nothing wrong:

| Rule | False SOS |
|---|---|
| Five readings at or under 91, every number believed | 4 |
| Impossible numbers rejected | 1 |
| Ten readings to settle after a dropout | 0 |

### Blood oxygen: the time-left test

The idea is borrowed and we say so. Spacecraft fault management compares a fault's time to criticality with how long the ground needs to respond, and NASA's Fault Management Handbook requires on-board autonomy once the ground is the slower of the two. A 2026 preprint applies the same test to cabin CO2. We did not find it applied to a crew member's own vital signs. That is our step.

Each second the ship fits a robust line (Theil-Sen) to the last 60 clean oxygen readings. If the fall is steady (falling pairs outnumber rising pairs by half of all pairs), at least 2 points across the window, and on course to reach 91% within ten minutes, the ship has a time left. It compares that with the earliest possible reply from Earth, which is twice the one-way delay:

- Earth can answer in time (Station, Moon): the report goes now, without waiting for the red line.
- Earth cannot (Mars: 22 minutes round trip today): the report still goes, and the ship tells the crew medical officer to check on the person now.
- No link (behind the Sun): the report is queued and the ship says the same.

Tried on six healthy volunteers breathing low-oxygen gas:

| Volunteer | Warning before the SOS | Ship's estimate at that moment |
|---|---|---|
| 100001 | 159 s | 142 s |
| 100002 | 106 s | 56 s |
| 100003 | 98 s | 87 s |
| 100004 | 96 s | 58 s |
| 100005 | 68 s | 84 s |
| 100006 | 14 s | 26 s |

Six of six warned before the red line, a median of 97 seconds ahead. On the control sleeper it warned twice in 7.8 hours, both real dips of 2 to 3 points that recovered. On 579 fast falls in a sleep apnoea patient it came first in 32%, about 42 seconds ahead. For the rest the fixed rule is what catches the fall.

What these numbers do not show. The first version of this test, the one that worked on the scripted story, caught 2 of 6. The settings were then checked held-out (`python scripts/crossval_lookahead.py`, 14 Nov): chosen from 18 settings on five volunteers, tested on the sixth, six times. Held-out result: warned before the SOS for 6 of 6, median 97 s ahead (159, 106, 98, 96, 68 and 14 s). Every fold chose the settings the ship already uses. Limits of that check: the false-alarm cap (at most 3 trend warnings) uses the same control recording in every fold, so it is not held out, and volunteer 100006 is warned only 14 s ahead. Six people in one lab on finger oximeters is a small sample, and a fall this slow is the easy case. Harespod is the unseen test for Sunday. `python scripts/check_spo2_rules.py` reprints every number above.

A second check, on generated data (14 Nov, evening). A simulated 30-day month for four crew, with a healthy copy, was read against these rules (`docs/reviews/2026-11-14-dataset-review.md`). Three results. The shirt's estimated blood pressure sat in the caution band or worse on 77,647 of 168,600 healthy minutes, so it no longer raises an alarm (the same decision as heart rate, for the same reason). The two injected oxygen falls are slow, about 0.2 and 0.5 points a minute: the bands caught both, 18 and 9 minutes before the red line, and the time-left test fired on neither, because it needs 2 points inside a minute. And minute data must never be fed to these one-a-second rules: it produced 24 false trend warnings. None of this is evidence that a rule is right. Generated data can only show that a rule is noisy or blind.

### Asked ahead

A flight surgeon's first questions take 22 minutes each way to ask. So the report answers them before it leaves: how the reading moved over the last minute, how long until it is critical, whether the heart rate is normal for this person, whether the sensor is clean, what the crew has done, and the last check-in.

### The learning part

Today everything is statistics you can explain in a sentence, which is the right call for a safety rule built in a day. A learned model earns its place on Sunday only if it beats this baseline on recordings it has not seen. Without that test it stays out.

## 7. What changes for the screens

| Where | Change |
|---|---|
| Alert | New `lookahead`: `now`, `per_min`, `eta_s`, `red_line`, `at`, `red_line_at`, `reply_s`, `earth_in_time`. Null unless a falling trend was found. Frozen when the report left, so count down to `red_line_at` |
| Alert | `speak` is now also set for a falling trend. Say it once per alert id and level |
| Crew board | New `usual.heart_rate`: `low`, `high`, `n`, or null for the first ten minutes |
| Reading | New `context`. `source` can be `replay` |
| New | `GET /api/base/habitat`: cabin and radiation with source and date |
| New | `POST /api/base/summary/send`: daily summaries to Earth |
| Story | `POST /api/base/scenario/start` takes `{"name": "stage" or "full" or "real", "replay": true}`. `real` plays a recorded oxygen fall and takes about three and a half minutes to reach SOS. Keep `stage` for the pitch |
| Report to Earth | New `asked_ahead` (list of `q` and `a`), `lookahead`, `usual`. The strip is 60 readings. New link kind `summary`, new update event `escalated` |
| Behaviour | Heart rate alone raises nothing. Reset keeps the dial. A second SOS press returns the same alert with 200. Bad input returns 400 |

## 8. The frontend owner's project document against this

Mostly the same product. His OK, WATCH and ALERT are our nominal, caution and warning, with SOS on top. "Send to flight surgeon" is `POST /alerts/<id>/send`. His daily summary is `POST /summary/send`. His blood-oxygen ALERT under 94% is our warning at 93. His baseline idea is the usual range.

Five differences to settle with him:

1. He proposes a small Node service with WebSocket for scoring. The Flask API already scores, delays and stores. Screens poll once a second. A second backend would split the rules in two.
2. His WATCH never leaves the station on its own. Ours has one exception: a falling trend sends its report early. That exception is the point of the project, so it should stay.
3. Mars one-way delay is 3 to 22 minutes (11.0 today from JPL), not 4 to 24.
4. He has four crew. Three are seeded. A fourth is one line in `seed()`.
5. His seven-day bundle. The ship holds 24 hours. The report carries the last minute, the answers and the usual range.

A correction to something said earlier in this project: his citation of NASA-STD-3001 V1 3004 is sound. The requirement is In-Mission Medical Care, and it lists monitoring and trending vital signs. His sources PRET and Canadian Healthcare in Deep Space both exist on the CSA portal and go into `docs/data-sources.md`. His thresholds for core temperature, glucose, VO2 and sleep have no sensor data behind them here, so they stay as typed check-in values.

## 9. Not doing

Multi-day baselines, a learned model, a second backend, alerts from skin temperature or cabin readings, and seven-day storage.

## 10. Open

The reviewer's Postgres host is `kyler.visserfamily.ca` (the `.cs` name was a typo). Checked on 14 November: Postgres 17.9, database `lighttime`, user `svc-lighttime`. The app created all five tables on first start, `reading.context` included, so no column change was needed, and the stage story reached its SOS there. The password goes in `.env` only, which git ignores.

One round trip from the backend owner's laptop to that host takes about 160 ms, and one reading makes 7 queries, so a reading takes about half a second. Played from the laptop against that database, a story runs about two and a half times slower than on SQLite: the stage SOS came at about 20 s instead of about 12 s. For the pitch, either run the server on a machine close to the database, or run it on the laptop with SQLite.

## References

- Theil H (1950). A rank-invariant method of linear and polynomial regression analysis, I to III. Proc. Koninklijke Nederlandse Akademie van Wetenschappen 53: 386-392, 521-525, 1397-1412.
- Sen PK (1968). Estimates of the regression coefficient based on Kendall's tau. J Am Stat Assoc 63(324): 1379-1389. doi:10.1080/01621459.1968.10480934
- NASA-HDBK-1002, Fault Management Handbook, Draft 2 (2012, never formally approved).
- Badger J et al. (2018). Spacecraft Dormancy Autonomy Analysis for a Crewed Martian Mission. NASA/TM-2018-219965.
- Shahin A, Sultan B (2026). ARIA: An Autonomous Reasoning and Intervention Architecture for Bioregenerative Life Support Systems on Long-Duration Mars Missions. Research Square preprint, not peer reviewed. doi:10.21203/rs.3.rs-9151255/v1
- NASA-STD-3001 Volume 1 Revision C (2023), requirement V1 3004.
- Royal College of Physicians (2017). National Early Warning Score (NEWS) 2.
- Gorges M, Markewitz BA, Westenskow DR (2009). Improving alarm performance in the medical intensive care unit using delays and clinical context. Anesth Analg 108(5): 1546-1552. doi:10.1213/ane.0b013e31819bdfbb
- Drew BJ et al. (2014). Insights into the Problem of Alarm Fatigue with Physiologic Monitor Devices. PLoS ONE 9(10): e110274. doi:10.1371/journal.pone.0110274
- Mishra T et al. (2020). Pre-symptomatic detection of COVID-19 from smartwatch data. Nat Biomed Eng 4(12): 1208-1220. doi:10.1038/s41551-020-00640-6
- Alavi A et al. (2022). Real-time alerting system for COVID-19 and other stress events using wearable data. Nat Med 28(1): 175-184. doi:10.1038/s41591-021-01593-2
- Hoffman JS et al. (2022). Smartphone camera oximetry in an induced hypoxemia study. npj Digital Medicine 5(1): 146. doi:10.1038/s41746-022-00665-y
- Penzel T, Moody GB, Mark RG, Goldberger AL, Peter JH (2000). The Apnea-ECG Database. Computers in Cardiology 27: 255-258. doi:10.13026/C23W2R
- PPG-DaLiA, UCI Machine Learning Repository. doi:10.24432/C53890
