# Guided tour: design

Date: 15 November 2026, 13:20. Plan: `docs/plans/2026-11-15-guided-tour.md`.

## What the live site does now (checked 13:05 with a headless browser)

The site is fixed. `lighttime.health/base-station` reaches the ship: the dial, "Start suits" and "Start story" are in the header, every `/api/` call answers 200, the clock is on the demo morning, and the crew are TJ, Rebecca, Kyler and David.

The story also works. Pressing Start story raised the SOS for TJ about 50 seconds later and the report left for Earth. What looks broken is the wait:

| Seconds after the press | What the home screen showed |
|---|---|
| 0 to 40 | Nothing changed. No sign that a story is running |
| about 32 | The ship raised the early warning (the time-left line). The home screen did not show the sentence anywhere we could find |
| about 50 | SOS in the alerts list, TJ's card red |

So a viewer presses the button, sees nothing for most of a minute, and the best moment (time left against Earth's reply) passes without words.

## Goal

One press starts a tour that fits in 30 seconds of the pitch, with a speech bubble for each moment and nobody pressing anything else.

1. The first bubble is on screen at once.
2. The last bubble is on screen by 27 seconds. Measured on a running ship: 0, 14.5, 20.6 and 25.6 seconds.
3. Each bubble appears because the ship did the thing, not because a timer ran out. A bubble can never be ahead of the screen.
4. Each bubble is 26 words or fewer, with the ship's own numbers in it.

## Not in this change

- The "full" story and the stage button stay as they are.
- No change to rules or thresholds. The tour story is the same script with no calm and a 16 second drift.
- Nothing is done on the crew's behalf. The tour does not tick the treatment step or answer for Earth. That is why it ends when Earth first hears, which needs no person.
- No language model writes the bubbles. They are fixed sentences with the ship's numbers in them, as CLAUDE.md requires.
- No console code from the backend side. The console part is one small component, given in the plan for the frontend owner.

## Why 30 seconds is the floor

Two rules set the pace, and neither is loosened for the demo. The trend rule will not speak until it has 15 readings, one a second, so the early warning cannot come before about 14 seconds. The SOS needs five readings in a row out of range, so it cannot follow in under about 5. The report then takes 11 seconds to reach Earth on the demo clock (11 minutes, played 60 times faster). The first report leaves with the early warning, so it lands at about 25 seconds. A full answer back from Earth would land at about 36, which is why the tour ends on "Earth hears" and not on "Earth answers".

## Design

**A shorter story.** `"tour"`: no calm, 16 seconds of drift, then the collapse.

**The ship says where the story is.** `GET /api/base/tour` returns one bubble:

```json
{"running": true, "step": 2, "of": 4, "id": "time_left", "title": "Time left",
 "text": "Still in range, but falling. LIGHTTIME gives it about 13 seconds. Earth's answer takes 22 minutes.",
 "anchor": "alerts", "simulated": true}
```

| Step | At about | Shown when | Anchor | Text |
|---|---|---|---|---|
| 1 calm | 0 s | a story is playing and the patient has no blood-oxygen alert | `crew:C1` | "One reading a second from every suit. Earth is 11 minutes away. Watch TJ's blood oxygen." |
| 2 time_left | 14 s | the alert exists and is below an emergency | `alerts` | "Still in range, but falling. LIGHTTIME gives it about 13 seconds. Earth's answer takes 22 minutes." |
| 3 sos | 20 s | the alert is an emergency | `alerts` | "SOS. Earth will not hear this for 11 minutes, so Rebecca, the crew medical officer, decides." |
| 4 earth_hears | 26 s | anything the ship sent about the alert has landed on Earth | `earth` | "Earth is only now hearing the first warning. Its answer is 11 minutes more away. The crew had to act alone." |

With no story playing, `running` is false, `step` is 0 and the text is null, so the console draws nothing. Stopping the story or resetting the demo ends the tour. After bubble 4 the story keeps running, so the presenter can still open the SOS, tick the treatment and answer from Earth by hand.

**Starting it.** `POST /api/base/demo/start` takes `{"name": "tour"}`. With no body it plays "full" as before.

**The console.** One component polls `/api/base/tour` once a second and draws a comic bubble beside the element whose `data-tour` attribute equals `anchor`. A "Take the tour" button posts the call above.

## Tests

Four new tests (234 to 238): the tour story warns by 16 seconds and calls SOS by 22; no bubble with no story; the four bubbles in order, each caused by what the ship did; the demo call accepts "tour" and refuses other names.

## Risks

- The time-left bubble is up for about 6 seconds and the SOS bubble for about 5. They are short on purpose; the presenter speaks over them (cue card at the end of the plan).
- The hosted site polls once a second and the network adds a little, so allow 27 seconds, not 25.6.
- The dial must be at Mars. The demo call sets it. At the Moon or the station the last bubble would come almost at once.
- The bubble text was timed against a live scratch ship. The console component in the plan was not run; the local copy of the console is behind the deployed one.
