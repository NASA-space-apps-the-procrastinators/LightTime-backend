# LIGHTTIME, the ship AI: design

Date: 14 November 2026, revised in the evening after the generated crew month arrived. Plan: `docs/build-log/plans/2026-11-14-console-contract.md`, Tasks 10 and 11. Evidence: `docs/specs/2026-11-14-ship-ai-and-data-design.md`, section 6, and `docs/build-log/reviews/2026-11-14-dataset-review.md`, findings F2, F3 and section 5.

## 1. Problem

Far from Earth the doctor answers late or not at all. A monitor that only shows numbers leaves a crew member who is not a doctor to work out what matters and whether to wait. A monitor that alarms too often gets ignored. The ship needs something between the sensors and the crew that knows three things: whether a reading can be trusted, what is normal for this person, and how far away help is.

## 2. What LIGHTTIME is

LIGHTTIME is the base station's medical assistant, the "Med bay AI" box in the system design. It is a set of fixed, explainable parts. It trains no model and calls no language model. It suggests and never decides.

| Part | Question it answers | Code |
|---|---|---|
| Don't cry wolf | Can this reading be trusted, and is this rule fit to alarm? | `base_station/rules.py`, `routes.ingest` |
| Know each person | What is usual for this person? | `base_station/usual.py` |
| Time left | How long until this is critical, and can Earth answer first? | `base_station/lookahead.py`, `reports.deadline` |
| Ask ahead | What will the flight surgeon ask first? | `reports.asked_ahead`, `reports.why` |
| Voice | What does the crew need to hear, once? | `reports.speak`, `reports.speak_falling` |

## 3. Goals

1. No alarm from a rule that failed on real recordings. Measured: `scripts/check_spo2_rules.py` prints 0 false SOS on the control recording.
2. A falling blood oxygen is flagged before the red line. Measured: 6 of 6 held-out volunteers, median 97 s.
3. Every alert can be traced by a non-doctor in under a minute: what was seen, the last readings, the rule, the source of the limits.
4. The crew hears whether to wait for Earth or act, in one sentence.
5. Nothing LIGHTTIME does depends on the link to Earth being up.

## 4. Not doing

- A learned model. Six recordings cannot train and test one honestly.
- An offline language model for the voice. Fixed templates are checkable. A model that rephrases medical text is not, in a day.
- Diagnosis. LIGHTTIME names a reading and a rule, never a condition.
- Alarms from heart rate alone, an estimated blood pressure, skin temperature, or cabin readings. Each was tested and failed, or has no test data.
- Judging data that arrives once a minute. Every rule here assumes one reading a second (requirement A11).
- The console's daily rules. Those compare one value a day with the person's own band and belong to `base_station/scoring.py`. LIGHTTIME watches seconds; the console rules watch days. An alert says which of the two raised it.

## 5. How its behaviour changes with distance

| One-way delay | Mode | LIGHTTIME's role | What the crew hears on an SOS |
|---|---|---|---|
| Under 5 minutes, link up | `doctor_live` | Drafts the report. The flight surgeon directs care | "Flight surgeon notified, live." |
| 5 minutes or more, link up | `crew_first` | Coaches the crew medical officer through the checklist. Earth reviews afterwards | "Earth will hear this in N minutes. Earliest reply in 2N minutes. Crew medical officer, start the checklist." |
| No link | `ship_alone` | Main reference until the link returns. Everything is kept for Earth | "No signal to Earth. Report queued. Crew medical officer, start the checklist." |

The five-minute line comes from NASA's NEEMO 16 communication-delay test (reference in `common/modes.py`).

## 6. Requirements

### Must have (built unless marked)

**A1. Name and parts in the API (plan Task 11).** `GET /api/base/state` returns `ship_ai` with `name` ("LIGHTTIME"), `line`, `version` and `parts` (four items, each `name` and `does`).
- [ ] The console shows the name from the API, never a hard-coded one.

**A2. Role by distance (plan Task 11).** Each dial stop carries `ship_ai_role`.
- [ ] Given the dial is on Mars, when the state is read, then `ship_ai_role` starts with "Coaches".
- [ ] Given the dial is behind the Sun, then it starts with "Main reference".

**A3. Reasoning travels with the report (plan Task 11).** The report to Earth carries `why`, the same lines the crew sees.
- [ ] Given a report has left, when Earth reads it, then `payload.why[0]` starts with "What was seen".

**A4. How steady the fall is (plan Task 11).** `lookahead.agreement` is the share of reading pairs that fall minus the share that rise, from 0.5 to 1.
- [ ] Shown as "steady" at 0.8 or more and "uneven" below. It is not a probability and must not be called confidence.

**A5. Next step (plan Task 11).** Each alert carries `next_step`, the first checklist step not yet ticked, or null.
- [ ] Given step 0 is ticked, then `next_step` is step 1.

**A6. Don't cry wolf (built).**
- [ ] A blood oxygen number under 50 or over 100 is a sensor dropout, not a reading.
- [ ] For ten readings after a dropout from the same sender, nothing alarms.
- [ ] An alarm needs five readings in a row in the band, each with a clean signal, from one sender.
- [ ] A typed number counts once and stops at a warning.
- [ ] Heart rate alone raises nothing.
- [ ] An estimated blood pressure from the suit raises nothing (A10).

**A7. Time left (built).** Theil-Sen slope over the last 60 clean readings; fall of at least 2 points across the window; agreement of at least 0.5; red line within 10 minutes. Earth is in time only if twice the one-way delay is less than the time left.
- [ ] A falling trend sends its report at once, whatever the level.
- [ ] If the reading later crosses the red line, Earth gets an update, not a second report.

**A8. Know each person (built for heart rate).** The usual range is the 1st to 99th percentile of the person's own non-exercise readings in the last 24 hours, once there are ten minutes of them.
- [ ] Shown on the crew board and sent in reports. It never raises an alarm.

**A9. Suggests, never decides (built).** Every `why` ends with "This is a fixed rule, not a diagnosis. A person, not the ship, decides." Resolving an alert stores who did it and their note in their own words, and tells Earth.

**A10. An estimated blood pressure never alarms (plan Task 10).** The suit's systolic estimate is stored and shown. Only a cuff reading typed by the crew is judged against the bands.
- [ ] Given six suit readings of 95 mmHg in a row, then no alert exists.
- [ ] Given one typed reading of 88 mmHg, then a warning is raised, as before.
- Why: on 30 healthy generated days for four crew, the once-a-minute estimate sat in the caution band or worse on 77,647 of 168,600 minutes, mostly asleep, and would have sent three reports to Earth by itself. This is the heart rate failure again, measured on a second dataset.

**A11. One reading a second, or not at all (rule, no code tonight).** `POST /api/base/readings` is for a sender that reports once a second. Data that arrives once a minute must not be posted there.
- Why: fed minute rows, "five in a row" becomes five minutes, and the time-left rule reads a fall per minute as a fall per second. Re-run offline on the generated month it raised 24 false trend warnings on ordinary evening drift, and on a real fall it said 88 seconds were left when the red line was 14 minutes away.
- [ ] No code path in the demo posts minute data to `/readings`. The console's daily values come from files and check-ins.

**A12. Both rule sets in one alert shape (plan Task 4).** Every alert carries `state` (`OK`, `WATCH`, `ALERT`, `RECHECK`, `SOS`), `stage`, `metric`, `rule` and `source`. A sensor check is `RECHECK` and never `ALERT`.

### Should have (after tonight's run-through passes)

**B1. Usual range for blood oxygen and skin temperature.** `usual.usual_range` already takes any vital. Add both to the crew board's `usual`.
**B2. "Outside usual" tag.** A display-only flag on the crew board when the last five-minute median is outside the usual range. No alarm, no sound.
**B3. Cabin and radiation in the daily summary.** Add the day's cabin CO2 range and radiation dose to each summary, so Earth's periodic view matches the design.
**B4. Health-record format.** `GET /api/base/alerts/<id>/fhir` returns the report as a FHIR Bundle of Observations (heart rate, blood oxygen, blood pressure, temperature), so a hospital system could read it. The LOINC codes must be checked at loinc.org before this is built.

### Later

**C1. Earth asks for raw data.** A request travels up the link, the crew member approves it, and only then does the raw strip go. This is the consent step the design calls for.
**C2. Signed and encrypted packets.** Not built. The demo link is plain.
**C3. Offline language model for the voice.** Only if it is limited to rephrasing lines LIGHTTIME already produced, and each sentence can be traced back to one.
**C4. A heart rate rule that knows what the person is doing.** The generated month holds two events no rule catches today: 128 to 138 beats a minute at a desk, and 36 to 38 asleep in someone who normally sleeps at 44 to 48. A fixed band cannot catch them without also firing on exercise and on an athlete's sleep. A rule would have to compare the reading with the person's usual range for the same activity. Build it only if, on the 15 real wrist recordings, it raises nothing during desk work.
**C5. A flat-line check.** A sensor stuck at one value with a good signal passes every rule. The generated month has the test case (three hours at exactly 97).
**C6. Offer to send early.** At Mars the round trip is about 22 minutes. On a slow fall the first caution comes 9 to 18 minutes before the red line, and today the report leaves only at the red line or when the crew presses send. LIGHTTIME could say so at the first caution. Not built: it changes what leaves the ship, which needs the team's agreement.

## 6a. What the generated crew month showed

On the evening of 14 November a generated 30-day month for four crew arrived, with ten injected events and a healthy copy. It is simulated data, so everything here is a consistency check and not evidence. Details and method are in the dataset review.

| Question | Result | What was done |
|---|---|---|
| How noisy were the rules on a healthy month? | The rules as they stood at the fork raised 1,030 alerts in 30 healthy days: 384 heart rate, 320 estimated blood pressure, 326 sensor checks | Heart rate was already switched off. Blood pressure is switched off for the suit's estimate (A10). The sensor checks stay: the signal was poor in those minutes, and a check is a `RECHECK`, not an alarm |
| Does Time left see the injected oxygen falls? | No. Both falls are slow (about 0.2 and 0.5 points a minute) and the rule needs 2 points inside one minute. It fired on 0 of 7,800 and 0 of 7,200 seconds | Nothing. The bands caught both, with 18 and 9 minutes between the first caution and the red line. Time left covers fast falls; the bands cover slow ones. Say this when asked |
| Would a slower Time left help? | Tried on the minute rows (15-minute window, 30-minute horizon): no false warning in the healthy month, both falls flagged, but no earlier than the first caution, and the time left was overestimated (29 minutes against 19, and 23 against 7) | Not built |
| What does nothing catch? | A fast heart rate at rest and a slow one in sleep (C4), and a stuck sensor (C5) | Listed as later work, with the test each needs first |

## 7. What must never be claimed

- Not "AI diagnoses". It flags a reading against a rule.
- Not "machine learning". Nothing is trained.
- Not "first". The time-left rule is borrowed from spacecraft fault management, where a fault's time to criticality is compared with the ground's response time. Applying it to a crew member's vital sign is the new step.
- Not "validated". Six volunteers on clinical oximeters, held out one at a time. Our own sensor is untested until the sensor test in `docs/specs/2026-11-14-suit-data-design.md`, section 8.
- Not "tested on a crew". The 30-day crew month is generated. It can show that a rule is noisy or blind. It cannot show that a rule is right.
- Not "caught 10 of 10". On the generated month the bands caught both oxygen falls, Time left caught neither, and two heart rate events were missed.

## 8. Success tonight

- [ ] `python -m pytest -q` prints `148 passed`.
- [ ] `python scripts/check_spo2_rules.py` prints 6 of 6 and 0 false SOS.
- [ ] On the console at Mars, the recorded fall produces a spoken line ending "Crew medical officer, check on Okafor now." before the red line.
- [ ] On the Earth console the same report shows its reasons and its answers.

## 9. Open questions

- Hardware owner: does the MAX30102 raise a false alert in ten minutes at rest (Task 6)? Blocking for using its blood oxygen on stage.
- Team: is B4 (health-record format) worth an hour tomorrow morning, given the pitch is the priority? Not blocking.
