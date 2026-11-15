# Sending suit readings to the ship

The ESP32 sends one JSON reading a second over Wi-Fi to the backend laptop.

    POST http://<backend laptop IP>:5000/api/base/readings
    Content-Type: application/json

    {"crew_id": "C4", "source": "suit", "heart_rate": 71, "spo2": 97, "signal_ok": true}

- `crew_id`: `"C1"` to `"C4"`, or the numbers 1 to 4 (C1 Okafor, C2 Lindqvist, C3 Sato, C4 Mensah). Use C4 for the live sensor: the scripted stories play on C1 and also send background readings for C2 and C3, which would mix with the sensor's on those crew cards.
- `heart_rate` in beats a minute and `spo2` in percent, as the MAX30102 board reports them. Leave a field out if there is no value.
- `signal_ok`: send `false` when no finger is on the sensor. It must be the JSON literal `true` or `false`, not a quoted string. The ship then raises a sensor check (state `RECHECK`, "Check your sensor") and judges nothing.
- `source` and `context` are at most 12 characters each.
- A blood oxygen number under 50 or over 100 is treated as a dropout. After a dropout nothing can alarm for the next ten readings.
- Blood oxygen, with a clean signal for five readings in a row: at or under 95 is a caution, at or under 93 a warning, at or under 91 an SOS. An SOS sends Earth a report by itself.
- A steady fall can raise a caution while the number is still above 95: at least 15 readings, a fall of 2 points or more across the last 60, and on course to reach 91 within ten minutes. That caution also sends Earth a report.
- A heart rate from the suit never raises an alarm. It is shown and compared with the person's usual range.
- A blood pressure from the suit is stored and shown but never raises an alarm. A cuff reading counts when it is posted with `"source": "typed"` (judged at once, never above a warning), or typed at the morning check-in (`POST /api/base/crew/C4/checkins`), where the console's daily rule judges it against the person's own band.
- Not stored: muscle activity and radiation.
- The answer is 201 with `{"reading": ..., "alerts": [...]}`: the stored reading and any alert it raised. A 400 means a field was not a number or the crew id is unknown, with a JSON body `{"error": ..., "field": ...}`.

Test from a laptop first:

    curl -X POST http://<IP>:5000/api/base/readings -H "Content-Type: application/json" -d '{"crew_id": "C4", "heart_rate": 71, "spo2": 97}'
