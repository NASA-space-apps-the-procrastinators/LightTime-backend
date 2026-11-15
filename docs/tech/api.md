# API reference

Written by `scripts/api_reference.py` from the running app on the demo morning. Do not edit by hand:
run the script again after a route changes. The contract the console builds against is the API table
in `docs/specs/2026-11-14-backend-design.md`; this page shows what the code answers today.

| Methods | Route | What it does |
|---|---|---|
| GET | `/api/base/alerts` | Every alert the viewer may see, newest first; ?open=1 for the ones not yet cleared. |
| GET | `/api/base/alerts/<alert_id>` | One alert from "A1" or 1, or a short notice of someone else's SOS. |
| POST | `/api/base/alerts/<alert_id>/accept-plan` | The crew accepts the flight surgeon's reply. For the demo the plan is always the same four checks. |
| POST | `/api/base/alerts/<alert_id>/ack` | A crew member acknowledges an alert, with optional symptoms; Earth gets an update if it has the report. |
| POST | `/api/base/alerts/<alert_id>/clear` | Resolve an alert, with who and an optional note; a second press changes nothing. |
| POST | `/api/base/alerts/<alert_id>/send` | The crew sends an alert to the flight surgeon. An SOS has already gone. |
| POST | `/api/base/alerts/<alert_id>/steps` | Tick one checklist step on an alert by its index; Earth gets an update if it has the report. |
| GET | `/api/base/alerts/<alert_id>/thread` | Everything the ship sent about one alert, and everything from Earth that has arrived. Oldest first. |
| GET | `/api/base/checkins/today` | Who has checked in today and who is due, the streak, and the next badge. |
| GET | `/api/base/crew` | All four crew: a full record for those the viewer may read, a name card for the rest. |
| GET | `/api/base/crew/<ref>` | One crew member's full record, or 403 if the viewer may not read it. |
| POST | `/api/base/crew/<ref>/checkins` | Save today's check-in for one person (mood, sleep, symptoms, optional cuff and reaction time). |
| GET | `/api/base/crew/<ref>/history` | Up to 30 days of one daily metric for one person, with their band; ?metric= is required. |
| GET | `/api/base/crew/<ref>/readings` | One person's recent readings for the trend chart, oldest first; ?limit= up to 600 (default 120). |
| POST | `/api/base/demo/start` | One button for the stage: the demo starts again, the dial goes to Mars, the full story plays. |
| POST | `/api/base/dial` | Move the dial to station, moon, mars or sun; a link that comes back sends its queue, most urgent first. |
| GET | `/api/base/habitat` | The cabin and radiation values for this moment of the replayed record, with source and date. |
| GET | `/api/base/health` | Is the ship up? Always {"ok": true}; reads no table. |
| GET | `/api/base/inbox` | What Earth has sent that has reached the ship so far, newest first. |
| POST | `/api/base/messages` | Free text from the crew to Earth, optionally about one alert, sent with the current delay. |
| GET | `/api/base/outbox` | What the ship has sent toward Earth, with each message's status and time left to land. |
| GET | `/api/base/packets` | The health log: the suits' minute stream as packets, newest first; ?crew=, ?state=, ?limit= up to 1000. |
| POST | `/api/base/readings` | Store one reading and run the rules; returns the reading, any alert it raised, and the fields it ignored. |
| GET | `/api/base/reminders` | Reminders, soonest first; ?crew=C1 for one person, ?open=1 for those not done. |
| POST | `/api/base/reminders/<ref>/done` | Mark one reminder done; a second press changes nothing. |
| POST | `/api/base/reset` | Clear readings, alerts, messages, check-ins and reminders; reload the demo morning if it is on. |
| POST | `/api/base/scenario/start` | Play a scripted story: {"name": "full", "stage" or "real"}, with "replay": true for recorded data. |
| POST | `/api/base/scenario/stop` | Stop the story that is playing. |
| POST | `/api/base/sos` | A crew member presses SOS: an emergency alert whose report leaves for Earth at once. |
| GET | `/api/base/sources` | Every outside source the ship uses, what it is for and how fresh it is. |
| GET | `/api/base/space-weather` | The simulated solar particle event in progress, or a calm reading. |
| GET | `/api/base/state` | The dial stop, its delay and who decides, the ship's clock, the mission day and all four stops. |
| GET | `/api/base/station` | The cabin now: CO2, oxygen, pressure, temperature, humidity and today's dose, each marked simulated or not. |
| GET | `/api/base/stream-health` | The lowest signal quality each sensor reported over the newest hour of packets. |
| POST | `/api/base/summary/send` | Send Earth each person's daily summary, then let readings older than 24 hours go. |
| GET | `/api/base/thresholds` | The printed console rules: for each daily metric and cabin CO2, the unit, watch and alert values and the source. |
| GET | `/api/earth/cases` | One case per alert whose report has reached Earth, built only from delivered messages. |
| GET | `/api/earth/cases/<alert_id>` | One case by alert id; 404 until its report has reached Earth. |
| GET | `/api/earth/cases/<alert_id>/thread` | Everything about one case that Earth has received or sent; 404 until its report has reached Earth. |
| GET | `/api/earth/feed` | Whether the vitals feed to Earth is running, and how often it sends. |
| POST | `/api/earth/feed/start` | Start the suits' vitals feed to Earth. {"interval_s": 120} is optional. |
| POST | `/api/earth/feed/stop` | Stop the suits' vitals feed to Earth. |
| GET | `/api/earth/inbox` | Every message from the ship that has reached Earth, newest first, with the current delay and mode. |
| GET | `/api/earth/network` | Two NASA figures for the same thing: Horizons works the Mars delay out from the orbits, |
| GET | `/api/earth/outbox` | What Earth has sent, with the mission time left until each lands on the ship. |
| POST | `/api/earth/reply` | Advice back to the ship, with the same delay. Reply to a message (message_id) |
| GET | `/api/earth/state` | Earth's view of the dial, the last contact from the ship, and what Earth has queued, in flight and delivered. |
| GET | `/api/earth/vitals` | The suit readings Earth has received, newest first, and the latest per crew member. |

## Example answers

### GET `/api/base/alerts`

Status 200

```json
[
  {
    "acknowledged_by": null,
    "at": "2026-11-14T06:12:00Z",
    "auto": true,
    "cleared_at": null,
    "cleared_by": null,
    "cleared_note": null,
    "crew": "TJ",
    "crew_id": "C1",
    "id": "A1",
    "level": "warning",
    "lookahead": null,
    "metric": "hr_rest",
    "nasa_risk": "Risk of Cardiovascular Adaptations",
    "next_step": "Go to the crew member and check that they respond",
    "raised_by": "console",
    "reason": "Resting heart rate 84 bpm, 3rd day over baseline",
    "restricted": false,
    "rule": "resting HR > baseline + 20 bpm for 3 consecutive days",
    "source": "OCHMO Exercise Overview brief (TB-031); Cardiovascular evidence report",
    "speak": null,
    "stage": "raised",
    "state": "ALERT",
    "steps": [
      "Go to the crew member and check that they respond",
      "... 2 more"
    ],
    "steps_done": [],
    "symptoms": [
      "headache"
    ],
    "timeline": {
      "acknowledged_at": null,
      "earliest_reply_after_s": null,
      "earliest_reply_at": null,
      "earth_after_s": null,
      "earth_at": null,
      "earth_eta_s": null,
      "raised_at": "2026-11-14T06:12:00Z",
      "reply_at": null,
      "resolved_at": null,
      "sent_at": null
    },
    "unit": "bpm",
    "value": 84.0,
    "vital": "heart_rate",
    "why": [
      "What was seen: Resting heart rate 84 bpm, 3rd day over baseline.",
      "... 3 more"
    ]
  },
  "... 4 more"
]
```

### GET `/api/base/alerts/A1`

Status 200

```json
{
  "acknowledged_by": null,
  "at": "2026-11-14T06:12:00Z",
  "auto": true,
  "cleared_at": null,
  "cleared_by": null,
  "cleared_note": null,
  "crew": "TJ",
  "crew_id": "C1",
  "id": "A1",
  "level": "warning",
  "lookahead": null,
  "metric": "hr_rest",
  "nasa_risk": "Risk of Cardiovascular Adaptations",
  "next_step": "Go to the crew member and check that they respond",
  "raised_by": "console",
  "reason": "Resting heart rate 84 bpm, 3rd day over baseline",
  "restricted": false,
  "rule": "resting HR > baseline + 20 bpm for 3 consecutive days",
  "source": "OCHMO Exercise Overview brief (TB-031); Cardiovascular evidence report",
  "speak": null,
  "stage": "raised",
  "state": "ALERT",
  "steps": [
    "Go to the crew member and check that they respond",
    "... 2 more"
  ],
  "steps_done": [],
  "symptoms": [
    "headache"
  ],
  "timeline": {
    "acknowledged_at": null,
    "earliest_reply_after_s": null,
    "earliest_reply_at": null,
    "earth_after_s": null,
    "earth_at": null,
    "earth_eta_s": null,
    "raised_at": "2026-11-14T06:12:00Z",
    "reply_at": null,
    "resolved_at": null,
    "sent_at": null
  },
  "unit": "bpm",
  "value": 84.0,
  "vital": "heart_rate",
  "why": [
    "What was seen: Resting heart rate 84 bpm, 3rd day over baseline.",
    "... 3 more"
  ]
}
```

### GET `/api/base/alerts/A1/thread`

Status 200

```json
{
  "alert_id": "A1",
  "messages": []
}
```

### GET `/api/base/checkins/today`

Status 200

```json
{
  "date": "2026-11-14",
  "done": [
    "C2",
    "... 2 more"
  ],
  "due": [
    "C1"
  ],
  "next_badge_at": 14,
  "streak": 12
}
```

### GET `/api/base/crew`

Status 200

```json
[
  {
    "baseline": {
      "bp": [
        [
          108.0,
          "... 1 more"
        ],
        "... 1 more"
      ],
      "hr_rest": [
        52.0,
        "... 1 more"
      ],
      "pvt_ms": 265.0,
      "resp": [
        12.0,
        "... 1 more"
      ],
      "sleep_h": [
        6.8,
        "... 1 more"
      ],
      "spo2": [
        96.0,
        "... 1 more"
      ],
      "temp_c": [
        36.3,
        "... 1 more"
      ],
      "vo2max_ml_min_kg": 44.0
    },
    "checkin_from": "2026-11-13",
    "id": "C1",
    "is_cmo": false,
    "last_packet_at": "2026-11-14T06:29:00Z",
    "latest": null,
    "level": "warning",
    "metric_states": {
      "bp_dia": "OK",
      "bp_sys": "OK",
      "dose_mSv_day": "OK",
      "hr_rest": "ALERT",
      "mood": "OK",
      "pvt_ms": "OK",
      "resp": "OK",
      "sleep_h": "ALERT",
      "spo2": "OK",
      "temp_c": "ALERT"
    },
    "name": "TJ",
    "note": "Out of band: resting heart rate, temperature, sleep. Symptoms: headache, short sleep",
    "restricted": false,
    "role": "Commander",
    "simulated": true,
    "state": "ALERT",
    "suit_id": "LT-01",
    "today": {
      "bp": [
        110.0,
        "... 1 more"
      ],
      "dose_mSv_day": 0.51,
      "dose_mSv_mission": 81.0,
      "hr_rest": 84.0,
      "mood": 3,
      "pvt_ms": 301,
      "resp": 17.0,
      "sleep_h": 5.1,
      "spo2": 97.0,
      "symptoms": [
        "headache",
        "... 1 more"
      ],
      "temp_c": 37.2
    },
    "typed": null,
    "usual": {
      "heart_rate": null
    },
    "week": {
      "bp_dia": [
        76.0,
        "... 6 more"
      ],
      "bp_sys": [
        113.0,
        "... 6 more"
      ],
      "dose_mSv_day": [
        0.534,
        "... 6 more"
      ],
      "hr_rest": [
        60.0,
        "... 6 more"
      ],
      "mood": [
        3.0,
        "... 6 more"
      ],
      "pvt_ms": [
        273.0,
        "... 6 more"
      ],
      "resp": [
        13.0,
        "... 6 more"
      ],
      "sleep_h": [
        6.7,
        "... 6 more"
      ],
      "spo2": [
        97.0,
        "... 6 more"
      ],
      "temp_c": [
        36.52,
        "... 6 more"
      ]
    }
  },
  "... 3 more"
]
```

### GET `/api/base/crew/C1`

Status 200

```json
{
  "baseline": {
    "bp": [
      [
        108.0,
        "... 1 more"
      ],
      "... 1 more"
    ],
    "hr_rest": [
      52.0,
      "... 1 more"
    ],
    "pvt_ms": 265.0,
    "resp": [
      12.0,
      "... 1 more"
    ],
    "sleep_h": [
      6.8,
      "... 1 more"
    ],
    "spo2": [
      96.0,
      "... 1 more"
    ],
    "temp_c": [
      36.3,
      "... 1 more"
    ],
    "vo2max_ml_min_kg": 44.0
  },
  "checkin_from": "2026-11-13",
  "id": "C1",
  "is_cmo": false,
  "last_packet_at": "2026-11-14T06:29:00Z",
  "latest": null,
  "level": "warning",
  "metric_states": {
    "bp_dia": "OK",
    "bp_sys": "OK",
    "dose_mSv_day": "OK",
    "hr_rest": "ALERT",
    "mood": "OK",
    "pvt_ms": "OK",
    "resp": "OK",
    "sleep_h": "ALERT",
    "spo2": "OK",
    "temp_c": "ALERT"
  },
  "name": "TJ",
  "note": "Out of band: resting heart rate, temperature, sleep. Symptoms: headache, short sleep",
  "restricted": false,
  "role": "Commander",
  "simulated": true,
  "state": "ALERT",
  "suit_id": "LT-01",
  "today": {
    "bp": [
      110.0,
      "... 1 more"
    ],
    "dose_mSv_day": 0.51,
    "dose_mSv_mission": 81.0,
    "hr_rest": 84.0,
    "mood": 3,
    "pvt_ms": 301,
    "resp": 17.0,
    "sleep_h": 5.1,
    "spo2": 97.0,
    "symptoms": [
      "headache",
      "... 1 more"
    ],
    "temp_c": 37.2
  },
  "typed": null,
  "usual": {
    "heart_rate": null
  },
  "week": {
    "bp_dia": [
      76.0,
      "... 6 more"
    ],
    "bp_sys": [
      113.0,
      "... 6 more"
    ],
    "dose_mSv_day": [
      0.534,
      "... 6 more"
    ],
    "hr_rest": [
      60.0,
      "... 6 more"
    ],
    "mood": [
      3.0,
      "... 6 more"
    ],
    "pvt_ms": [
      273.0,
      "... 6 more"
    ],
    "resp": [
      13.0,
      "... 6 more"
    ],
    "sleep_h": [
      6.7,
      "... 6 more"
    ],
    "spo2": [
      97.0,
      "... 6 more"
    ],
    "temp_c": [
      36.52,
      "... 6 more"
    ]
  }
}
```

### GET `/api/base/crew/C1/history?metric=hr_rest`

Status 200

```json
{
  "band": [
    52.0,
    "... 1 more"
  ],
  "crew_id": "C1",
  "days": [
    {
      "date": "2026-11-08",
      "value": 60.0
    },
    "... 6 more"
  ],
  "days_out_of_band": 3,
  "metric": "hr_rest",
  "simulated": true,
  "unit": "bpm"
}
```

### GET `/api/base/crew/C1/readings`

Status 200

```json
[]
```

### GET `/api/base/habitat`

Status 200

```json
{
  "cabin": {
    "as_of": "2014-09-20T03:59:00Z",
    "co2_ppm": 2641.0,
    "humidity_pct": 39.0,
    "temp_c": 24.1
  },
  "kind": "file",
  "radiation": null,
  "source": "NASA OSDR Environmental Data App, Rodent Research 1 (2014), replayed",
  "url": "https://visualization.osdr.nasa.gov/eda/"
}
```

### GET `/api/base/health`

Status 200

```json
{
  "ok": true
}
```

### GET `/api/base/inbox`

Status 200

```json
[
  {
    "arrives_after_s": 665.1,
    "created_at": "2026-11-13T20:16:05Z",
    "delay_s": 665.1,
    "deliver_at": "2026-11-13T20:27:10Z",
    "direction": "to_ship",
    "earliest_reply_after_s": 1330.2,
    "eta_s": 0.0,
    "id": 74,
    "in_reply_to": 73,
    "kind": "reply",
    "payload": {
      "alert_id": null,
      "from": "Dr. Damola",
      "simulated": true,
      "text": "Received, thank you. No change to the plan."
    },
    "priority": 0,
    "sent_at": "2026-11-13T20:16:05Z",
    "status": "delivered"
  },
  "... 32 more"
]
```

### GET `/api/base/outbox`

Status 200

```json
[
  {
    "arrives_after_s": 665.1,
    "created_at": "2026-11-13T20:00:00Z",
    "delay_s": 665.1,
    "deliver_at": "2026-11-13T20:11:05Z",
    "direction": "to_earth",
    "earliest_reply_after_s": 1330.2,
    "eta_s": 0.0,
    "id": 73,
    "in_reply_to": null,
    "kind": "message",
    "payload": {
      "alert_id": null,
      "from": "Rebecca",
      "simulated": true,
      "text": "Daily crew health summary for mission day 157: 4 of 4 check-ins complete. Table attached."
    },
    "priority": 2,
    "sent_at": "2026-11-13T20:00:00Z",
    "status": "delivered"
  },
  "... 40 more"
]
```

### GET `/api/base/packets`

Status 200

```json
{
  "packets": [
    {
      "ack": null,
      "crew_id": "C4",
      "location": "ISS",
      "metric": "hr",
      "mission_day": 158,
      "sent_to_ground": false,
      "signal_quality": 0.94,
      "source": "ecg",
      "suit_id": "LT-04",
      "ts": "2026-11-14T06:29:00.399Z",
      "unit": "bpm",
      "value": 50.8,
      "window_s": 60
    },
    "... 199 more"
  ],
  "simulated": true,
  "transmitted_to_ground_today": 0
}
```

### GET `/api/base/reminders`

Status 200

```json
[
  {
    "crew_id": "C2",
    "done_at": "2026-11-02T16:14:41Z",
    "due_at": "2026-11-02T16:09:41Z",
    "id": "R1",
    "text": "Take temperature"
  },
  "... 3 more"
]
```

### GET `/api/base/sources`

Status 200

```json
[
  {
    "agency": "NASA JPL",
    "as_of": "JPL Horizons, read on 2026-11-13",
    "id": "horizons",
    "kind": "live",
    "name": "Horizons ephemeris system",
    "url": "https://ssd.jpl.nasa.gov/api/horizons.api",
    "used_for": "Mars light time. It sets the delay on every message and who decides."
  },
  "... 6 more"
]
```

### GET `/api/base/space-weather`

Status 200

```json
{
  "advisory": "Shelter advisory: stay in the shielded module",
  "event_at": "2026-11-14T05:58:00Z",
  "headline": "SEP event in progress",
  "simulated": true,
  "source": "Simulated event, laid out like a NASA DONKI SEP record",
  "state": "WATCH"
}
```

### GET `/api/base/state`

Status 200

```json
{
  "delay_s": 660.86,
  "label": "Mars",
  "light_time_source": "JPL Horizons, read on 2026-11-13",
  "link_up": true,
  "mission_day": 158,
  "mode": "crew_first",
  "now": "2026-11-14T06:30:00.633322Z",
  "path_km": 198120844,
  "platform": "ISS",
  "plays_as_s": 11.014333333333333,
  "round_trip_s": 1321.72,
  "ship_ai": {
    "line": "It knows how long the light takes, so it knows who has to act.",
    "name": "LIGHTTIME",
    "parts": [
      "{...}",
      "... 3 more"
    ],
    "version": "rules 2026-11-14"
  },
  "ship_ai_role": "Coaches the crew medical officer. Earth reviews afterwards.",
  "speedup": 60,
  "stop": "mars",
  "stops": [
    {
      "delay_s": 0.25,
      "label": "Space station",
      "light_time_source": "fixed",
      "link_up": true,
      "mode": "doctor_live",
      "path_km": 74948,
      "plays_as_s": 0.25,
      "round_trip_s": 0.5,
      "ship_ai_role": "Drafts the report. The flight surgeon directs care.",
      "stop": "station",
      "who_decides": "Flight surgeon on Earth"
    },
    "... 3 more"
  ],
  "who_decides": "Crew medical officer"
}
```

### GET `/api/base/station`

Status 200

```json
{
  "co2_mmHg": {
    "note": "WATCH from 2.8, ALERT from 4.5",
    "simulated": false,
    "state": "WATCH",
    "value": 2.99
  },
  "dose_mSv_today": {
    "note": "ALERT over 2",
    "simulated": true,
    "state": "OK",
    "value": 0.51
  },
  "habitat": "H1",
  "ppo2_mmHg": {
    "simulated": true,
    "state": null,
    "value": 156.5
  },
  "pressure_kPa": {
    "simulated": true,
    "state": null,
    "value": 101.39
  },
  "rh_pct": {
    "simulated": false,
    "state": null,
    "value": 50.0
  },
  "simulated": true,
  "source": "Cabin CO2, temperature and humidity: NASA OSDR Environmental Data App, Rodent Research 1 (2014), replayed. CO2 is NASA's ppm converted with the cabin pressure. Oxygen, pressure and the dose in mSv are simulated.",
  "temp_c": {
    "simulated": false,
    "state": null,
    "value": 22.9
  },
  "updated_at": "2026-11-14T06:29:00Z"
}
```

### GET `/api/base/stream-health`

Status 200

```json
{
  "sensors": [
    {
      "lowest_signal_quality": 0.91,
      "source": "chest_band",
      "state": "OK"
    },
    "... 4 more"
  ],
  "simulated": true,
  "window_minutes": 60
}
```

### GET `/api/base/thresholds`

Status 200

```json
{
  "bp_dia": {
    "alert": "outside pre-flight range on two cuff readings",
    "source": "OCHMO Orthostatic Intolerance brief (TB-019)",
    "unit": "mmHg",
    "watch": "outside pre-flight range on one cuff reading"
  },
  "bp_sys": {
    "alert": "outside pre-flight range on two cuff readings",
    "source": "OCHMO Orthostatic Intolerance brief (TB-019)",
    "unit": "mmHg",
    "watch": "outside pre-flight range on one cuff reading"
  },
  "co2_mmHg": {
    "alert": ">= 4.5 (fatigue, nausea)",
    "source": "OCHMO Carbon Dioxide brief (TB-004); NASA-STD-3001",
    "unit": "mmHg",
    "watch": ">= 2.8 (headaches reported 2.8-4.5)"
  },
  "dose_mSv_day": {
    "alert": "> 2 mSv in a day",
    "source": "NASA-STD-3001 Rev C career limit; OCHMO Radiation Protection brief (TB-020); DONKI",
    "unit": "mSv/day",
    "watch": "SEP event in DONKI (shelter advisory)"
  },
  "hr_rest": {
    "alert": "resting HR > baseline + 20 bpm for 3 consecutive days",
    "source": "OCHMO Exercise Overview brief (TB-031); Cardiovascular evidence report",
    "unit": "bpm",
    "watch": "outside baseline band"
  },
  "mood": {
    "alert": "<= 2 with a symptom or sleep ALERT",
    "source": "OCHMO Behavioral Health brief (TB-016); Behavioral Medicine evidence report 2025",
    "unit": "1-5",
    "watch": "<= 2 two days running"
  },
  "pvt_ms": {
    "alert": "mean > baseline + 30% with sleep WATCH or ALERT",
    "source": "CSA PRET dataset (PVT files) for distributions; HRP Sleep evidence report",
    "unit": "ms",
    "watch": "mean > baseline + 15%"
  },
  "resp": {
    "alert": "> 20 at rest with CO2 above 4.5 mmHg or symptom",
    "source": "OCHMO Carbon Dioxide brief (TB-004)",
    "unit": "/min",
    "watch": "> 20 at rest"
  },
  "sleep_h": {
    "alert": "three nights < 6",
    "source": "HRP Sleep evidence report; OCHMO Circadian Desynchrony brief (MTB-009)",
    "unit": "h",
    "watch": "< 6.5"
  },
  "spo2": {
    "alert": "< 94",
    "source": "Hypoxia and DCS evidence report 2024",
    "unit": "%",
    "watch": "below baseline band"
  },
  "temp_c": {
    "alert": "> 38.0",
    "source": "Clinical fever threshold; NASA-STD-3001 V1 3004 In-Mission Medical Care",
    "unit": "\u00b0C",
    "watch": "above baseline band"
  }
}
```

### GET `/api/earth/cases`

Status 200

```json
{
  "cases": [
    {
      "acknowledged_at": null,
      "acknowledged_by": null,
      "alert_id": "A7",
      "awaiting_reply": false,
      "crew": "Kyler",
      "crew_id": null,
      "data_age": "{...}",
      "inferred": [
        "crew",
        "... 2 more"
      ],
      "last_heard_at": "2026-11-13T12:11:05Z",
      "level": null,
      "mode_at_send": null,
      "nasa_risk": null,
      "raised_at": "2026-11-13T03:11:00Z",
      "reason": "Blood oxygen 91 % in sleep, link down",
      "replies": 1,
      "reply_status": "delivered",
      "resolved_at": "2026-11-13T04:20:00Z",
      "resolved_by": "Rebecca",
      "simulated": true,
      "state": "SOS",
      "status": "resolved",
      "steps_done": [],
      "timeline": "{...}",
      "value": null,
      "vital": null,
      "who_decides_at_send": null
    },
    "... 3 more"
  ]
}
```

### GET `/api/earth/cases/A1`

Status 404

```json
{
  "error": "not found"
}
```

On the demo morning no report has reached Earth yet, so Earth has no case A1 and this 404 is the right answer. Once a report lands, the same call returns the case.

### GET `/api/earth/cases/A1/thread`

Status 404

```json
{
  "error": "not found"
}
```

On the demo morning no report has reached Earth yet, so Earth has no case A1 and this 404 is the right answer. Once a report lands, the same call returns the case.

### GET `/api/earth/feed`

Status 200

```json
{
  "interval_s": 120,
  "last_tick_at": null,
  "running": false,
  "simulated": true,
  "started_at": null,
  "stored_on_ship": 0,
  "ticks": 0
}
```

### GET `/api/earth/inbox`

Status 200

```json
{
  "delay_s": 660.86,
  "link_up": true,
  "messages": [
    {
      "arrives_after_s": 665.1,
      "created_at": "2026-11-13T20:00:00Z",
      "delay_s": 665.1,
      "deliver_at": "2026-11-13T20:11:05Z",
      "direction": "to_earth",
      "earliest_reply_after_s": 1330.2,
      "eta_s": 0.0,
      "id": 73,
      "in_reply_to": null,
      "kind": "message",
      "payload": "{...}",
      "priority": 2,
      "sent_at": "2026-11-13T20:00:00Z",
      "status": "delivered"
    },
    "... 40 more"
  ],
  "mode": "crew_first",
  "who_decides": "Crew medical officer"
}
```

### GET `/api/earth/network`

Status 200

```json
{
  "differ_s": null,
  "dsn_one_way_s": null,
  "horizons_one_way_s": 656.62,
  "passes": [],
  "source": "NASA DSN Now could not be reached",
  "url": "https://eyes.nasa.gov/dsn/data/dsn.xml"
}
```

### GET `/api/earth/outbox`

Status 200

```json
[
  {
    "arrives_after_s": 665.1,
    "created_at": "2026-11-13T20:16:05Z",
    "delay_s": 665.1,
    "deliver_at": "2026-11-13T20:27:10Z",
    "direction": "to_ship",
    "earliest_reply_after_s": 1330.2,
    "eta_s": 0.0,
    "id": 74,
    "in_reply_to": 73,
    "kind": "reply",
    "payload": {
      "alert_id": null,
      "from": "Dr. Damola",
      "simulated": true,
      "text": "Received, thank you. No change to the plan."
    },
    "priority": 0,
    "sent_at": "2026-11-13T20:16:05Z",
    "status": "delivered"
  },
  "... 32 more"
]
```

### GET `/api/earth/state`

Status 200

```json
{
  "arrived": 41,
  "delay_s": 660.86,
  "ground_outbox": {
    "delivered": 33,
    "in_flight": 0,
    "queued": 0
  },
  "label": "Mars",
  "last_contact_age_s": 37800.8,
  "last_contact_at": "2026-11-13T20:11:05Z",
  "light_time_source": "JPL Horizons, read on 2026-11-13",
  "link_up": true,
  "mode": "crew_first",
  "path_km": 198120844,
  "plays_as_s": 11.014333333333333,
  "round_trip_s": 1321.72,
  "ship_ai_role": "Coaches the crew medical officer. Earth reviews afterwards.",
  "speedup": 60,
  "stop": "mars",
  "who_decides": "Crew medical officer"
}
```

### GET `/api/earth/vitals`

Status 200

```json
{
  "latest": {},
  "readings": [],
  "simulated": true
}
```
