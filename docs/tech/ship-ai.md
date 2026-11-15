# LIGHTTIME in the code

LIGHTTIME is the ship's adviser: fixed rules and simple statistics, with no trained model deciding anything. This page is for developers. It says where each rule lives and what its settings are. Why each rule works the way it does, with worked examples, is in section 5 of the [concept document](../concept.md); the evidence from real recordings is in [How it works](../how-it-works.md), section 5.

The settings below are the values in the code. The same values are written to [`docs/generated/numbers.json`](../generated/numbers.json) by `scripts/paper_numbers.py`, so the documents quote the code and not a copy.

## The rules

| Rule | Where | Settings | Concept section |
|---|---|---|---|
| Light time for the mission date | `common/lighttime.py`, `mars_seconds()` | Asked from JPL Horizons (quantity 21); dated fallback 660.86 s for 14 November 2026. Station 0.25 s and Moon 1.3 s are fixed in `common/modes.py` | 5.1, 5.2 |
| Who decides | `common/modes.py`, `mode_for()` | No link: the crew alone. One-way delay of 300 s or more: the crew medical officer first. Otherwise: the flight surgeon on Earth, live | 5.3 |
| The demo clock | `common/link.py`, `real_delay_s()` | Legs of 60 s or more play 60 times faster; Mars plays as 11.01 s | 5.4 |
| Can the reading be trusted? | `base_station/routes.py`, `ingest()`; `base_station/rules.py`, `evaluate()` and `_settling()` | Blood oxygen outside 50 to 100 is stored as a poor signal and never judged. A poor signal raises a RECHECK notice. Nothing alarms for the 10 readings after a poor signal | 5.5 |
| How bad is it? | `base_station/rules.py`, `band()` and `sustained()`; bands in `base_station/limits.json` | Blood oxygen: caution at 95 or below, warning at 93, emergency (SOS) at 91. A band must hold for 5 clean readings in a row from one sender. A typed number counts once and stops at a warning. After a person clears an alert, the same alert cannot come back for 60 s unless it is worse | 5.6 |
| Is this normal for this person? | `base_station/usual.py`, `usual_range()` | Heart rate: the 1st and 99th percentile of the person's resting readings over their last 24 hours, once there are at least 600 (ten minutes at one a second). Shown and sent to Earth; it raises no alarm | 5.7 |
| How long is left? | `base_station/lookahead.py`, `falling()` and `check()` | The last 60 clean readings; at least 15; the median of the slopes between every pair of readings; "now" is the median of the last 5; the fitted line must fall at least 2.0 points across the window; stay quiet if the red line (91) is more than 600 s away | 5.8 |
| Do the readings agree? | `base_station/lookahead.py`, `falling()` | Share of pairs that fall minus share that rise must be at least 0.5 | 5.9 |
| Can Earth answer first? | `base_station/reports.py`, `deadline()` and `speak_falling()` | Earth is in time if the round trip (twice the one-way delay) is shorter than the time left. Otherwise the ship says it is too late and calls the crew medical officer | 5.10 |
| Ask ahead | `base_station/reports.py`, `asked_ahead()` | The report answers six questions before it leaves: how the reading moved, how long until critical, whether the heart rate is normal for this person, whether the sensor reads cleanly, what the crew has done, and how they slept and felt | |

Two rules are switched off, with the reason kept in `base_station/limits.json`. Heart rate judged with hospital bands tripped for 14 of 15 healthy volunteers at a desk (PPG-DaLiA), so heart rate is shown and compared with the person's usual range but raises no alarm. The shirt's once-a-minute blood pressure estimate sat in the caution band or worse on 77,647 of 168,600 minutes of the healthy simulated month, so only a cuff reading typed by the crew is judged.

The bands are inspired by NEWS2, a hospital score from the Royal College of Physicians. NEWS2 has not been checked in spaceflight, and these are demo tiers.

## The spoken line and the reasons

Every alert carries `why`, a short list of plain lines a crew medical officer can check: what was seen, the last readings, the rule, the band table's source, and "This is a fixed rule, not a diagnosis. A person, not the ship, decides." (`reports.why()`). A manual SOS says instead that a person raised it and a person decides. The spoken line (`speak` on the alert) is built from templates in `reports.speak()` and `reports.speak_falling()`; the browser reads it aloud. No language model writes any of it.

## The heart-rate adviser that is not wired in

`scripts/learn_hr_normal.py` learns how far heart rate normally sits above a person's resting rate in each activity, from the 15 PPG-DaLiA volunteers, holding one out at a time. It writes `base_station/hr_normal.json`. It would flag a minute only when every second sat more than 72.9 bpm from the person's expected rate for that activity; on the worst held-out volunteer that flagged 0.39 minutes an hour, inside its gate of one. It is an adviser: it can say "unusual", never "dangerous". No code in `base_station/`, `command_center/` or `common/` reads the file, so it changes no alert. [ADR 0001](../adr/0001-rules-decide-learned-models-advise.md) says why: no recording holds an emergency, a model fitted on fifteen people learns those fifteen, and a rule that prints its reasons is something a crew medical officer can check.
