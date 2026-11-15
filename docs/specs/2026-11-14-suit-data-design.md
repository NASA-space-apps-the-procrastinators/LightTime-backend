# The suit and its data: design

Date: 14 November 2026, revised in the evening. Plans: `docs/build-log/plans/2026-11-14-connect-everything.md`, Tasks 5 and 6 (hardware note and sensor test), and `docs/build-log/plans/2026-11-14-console-contract.md`, Tasks 2 and 10. Hardware note: ESP32 DevKitC with a MAX30102 optical sensor (heart rate and blood oxygen), a muscle-activity input, a radiation input and a Bluetooth cuff.

## 1. Problem

The ship AI was tested on clinical finger oximeters. The sensor on stage is a hobby-grade optical sensor on a fingertip, read by a microcontroller over Wi-Fi. If it sends junk and the ship believes it, the demo raises a false SOS in front of the judges. If the ship ignores it, the hardware adds nothing.

## 2. Goals

1. One reading a second from the suit reaches the ship and shows on a crew tile.
2. A finger off the sensor shows "Check your sensor" and never an alarm.
3. Ten minutes at rest on the real sensor raise no alert, or the team knows before the pitch that they do.
4. Recorded data and the live sensor can run at the same time without hiding each other's alarms.

## 3. Not doing

- MQTT, per-suit certificates, encryption. The design calls for them; the demo uses plain HTTP on a local network.
- Storing muscle activity, radiation or cuff pressure from the suit. There is no column and no rule for them.
- A raw 60-second strip from the suit. The ship keeps the last 60 readings itself.

## 4. The packet

One JSON object, once a second:

    POST http://<ship laptop>:5000/api/base/readings
    {"crew_id": 2, "source": "suit", "heart_rate": 71, "spo2": 97, "signal_ok": true}

| Field | Type | Meaning | If missing |
|---|---|---|---|
| `crew_id` | `C1` to `C4`, or 1 to 4 | Whose reading | 400 |
| `source` | text | `suit` for hardware | `suit` |
| `heart_rate` | number, beats a minute | From the sensor's own processor | No reading |
| `spo2` | number, percent | From the sensor's own processor | No reading |
| `skin_temp` | number, Celsius | Optional | No reading |
| `signal_ok` | true or false | False when no finger is detected | true |
| `context` | `rest` or `exercise` | Optional. At most 12 characters, and only the exact word `exercise` counts as exercise | Counted as rest |

An empty string counts as no reading. Anything that is not a number returns 400 and stores nothing.

## 5. What the ship does with it

| Step | Rule | Why |
|---|---|---|
| 1 | Blood oxygen under 50 or over 100 becomes a dropout | No oximeter reads there on a living person |
| 2 | A dropout, or `signal_ok` false, raises the advisory "Check your sensor" and judges nothing | A loose sensor is the common case |
| 3 | For ten readings after a dropout from this sender, nothing alarms | A probe just put back reads low while it settles |
| 4 | Each sender is judged on its own readings | A live sensor and a replayed story for the same person must not cancel each other |
| 5 | Five clean readings in a row in a band raise the alert | One reading means nothing |
| 6 | Heart rate is shown and never alarms alone | It tripped for 14 of 15 healthy people at a desk |
| 7 | A blood pressure from the suit is shown and never alarms. A cuff reading typed by the crew is judged | A once-a-minute estimate sat in the caution band or worse on 77,647 of 168,600 healthy minutes (nearly half) in the generated month |

## 5a. One reading a second, or a different door

Everything in section 5 assumes one reading a second from one sender. "Five in a row" means five seconds. The settle period is ten seconds. The time-left rule reads a fall per reading as a fall per second.

So data that arrives once a minute must never be posted to `/api/base/readings`. Tried offline on the generated month, minute rows gave 24 false trend warnings in 30 healthy days and a time-left figure wrong by a factor of 60 (`docs/build-log/reviews/2026-11-14-dataset-review.md`, F3).

| Data | Speed | Door | Judged by |
|---|---|---|---|
| Suit sensor on stage, recorded replays, the scripted story | One a second | `POST /api/base/readings` | LIGHTTIME |
| The console's packets (one per measurement per minute) | One a minute | `POST /api/base/packets`, not built yet | The console's daily rules, and `RECHECK` under a signal quality of 0.6 |
| Morning check-in | Once a day | `POST /api/base/crew/<id>/checkins` | The console's daily rules |

When the packet door is built, a `signal_quality` under 0.6 is the same thing as `signal_ok: false` here.

## 6. Data sources feeding the same path

| Source | Sender name | What it is | Labelled on screen |
|---|---|---|---|
| Suit sensor | `suit` | Live, one person | Live |
| Recorded wrist data, 15 volunteers | `replay` | Real heart rate and skin temperature, replayed | Recorded |
| Recorded oxygen fall, one volunteer | `replay` | A real desaturation in a lab, replayed | Recorded |
| Scripted story | `scenario` | Invented numbers for the stage | Simulated |
| A cuff reading posted on its own | `typed` | Typed by the crew | Typed |

Not on this path: the generated crew month (its daily values are read from files, and its check-ins have their own table) and the morning check-in.

## 7. Requirements

**Must have**
- [ ] Given the sensor posts a valid reading, then the answer is 201 and the reading is the crew member's `latest` within a second.
- [ ] Given no finger on the sensor, when it posts `signal_ok: false` or a blood oxygen of 0, then only the advisory appears.
- [ ] Given the story is playing for crew 1 and the sensor posts normal readings for crew 1, then the story's SOS still fires.
- [ ] Given the sensor posts text where a number belongs, then the answer is 400 and nothing is stored.

**Should have**
- [ ] A signal quality number from 0 to 1 in the packet, with under 0.6 treated as a dropout. The console's packet format already has this field.
- [ ] The crew tile shows which sender the reading came from.

**Later**
- Muscle activity, radiation and cuff readings, each with a column, a unit and a source for any limit.
- MQTT with a certificate per suit.

## 8. The test that has to happen tonight

One person, sensor on, ten minutes sitting still, posting as crew 2.

| Count | Good | If not |
|---|---|---|
| Alerts raised | 0 | On stage, send heart rate only from the sensor and say why |
| "Check your sensor" advisories | A few, each clearing by itself | Check the finger contact and the `signal_ok` logic |
| Lowest blood oxygen shown | 94 or more | Look at what the sensor sends when the finger moves |

Write the three numbers into section 6 of `docs/specs/2026-11-14-ship-ai-and-data-design.md`. Do not tune the ship's rules to the sensor tonight.

## 9. Open questions

- Hardware owner: can the microcontroller reach the ship laptop's address on the venue network? Blocking.
- Hardware owner: which crew member wears the sensor on stage? With the demo morning loaded, `C1` already has an open alert, so `C2` keeps the two stories apart. Not blocking.
- Hardware owner: does the sensor board report a "no finger" state the microcontroller can read? If not, send a blood oxygen of 0 when the reading is invalid. Not blocking.
