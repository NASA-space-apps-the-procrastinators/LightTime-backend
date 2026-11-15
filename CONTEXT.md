# LIGHT-TIME: the words we use

A glossary, and nothing else. One meaning per word, used the same way in the code, the screens and the documents. If a word here is used differently somewhere, that place is wrong.

## Places and screens

**Ship.** Where the crew is, and the computer there. In the code: `base_station/`, served at `/api/base`. Everything that keeps a crew member safe runs here and needs no link.

**Earth.** Mission control and the flight surgeon. In the code: `command_center/`, served at `/api/earth`. Earth sees only what the link has delivered.

**Console.** The crew's screen on the ship: crew overview, astronaut page, check-in, alert page, log.

**Earth console.** The flight surgeon's screen. It shows the ship's past: everything on it left the ship at least one light time ago.

**Suit.** The sensors a crew member wears, and the microcontroller that sends their readings to the ship.

## Distance and time

**Light time.** How long a signal takes one way between the ship and Earth. The number comes from NASA JPL Horizons for Mars and from the path length for the station and the Moon.

**Round trip.** Twice the light time: the earliest any answer from Earth can arrive, if the flight surgeon replies at once.

**Dial.** The control that says where the ship is. It has four stops.

**Stop.** One position of the dial: space station, Moon, Mars, or behind the Sun. Behind the Sun there is no link.

**Link.** The delayed channel between ship and Earth. A message is queued (no link), in flight, or delivered. A queued SOS leaves first when the link returns.

**Mode.** Who decides, worked out from the stop. Flight surgeon live (short delay), crew first (five minutes or more one way), ship alone (no link).

**Mission clock.** The ship's clock on the demo morning. It starts at 14 November 2026, 06:30 UTC and runs in real time. Every time the API returns is on it.

**Demo morning.** The moment every restart returns to: mission day 158, alert `A1` just raised, three of four crew checked in.

**Speed-up.** A leg of a minute or more plays 60 times faster in the demo. The numbers shown are always mission time.

## The ship AI

**LIGHTTIME.** The ship AI. Fixed, explainable rules and statistics. It suggests and never decides. It trains no model and calls no language model.

**Reading.** One set of sensor values from a suit, once a second. Judged by LIGHTTIME.

**Time left.** LIGHTTIME's estimate of how long until a falling reading reaches its red line, compared with the round trip.

**Red line.** The value at which a reading is an emergency. For blood oxygen, 91 %.

**Usual range.** What is normal for one person, learned from their own last 24 hours.

**Sensor check.** A reading with a poor signal. It is never judged. Its state is `RECHECK`.

## The console's daily rules

**Daily value.** One value a day for a measurement, such as resting heart rate. Judged by the console rules against the person's band.

**Band.** A person's own normal range for one measurement, set before launch.

**Check-in.** What a crew member types each morning: mood, sleep, symptoms, a reaction test, and a cuff blood pressure.

**Packet.** One measurement in the console's log, at most once a minute. Not a reading: packets are never judged by LIGHTTIME.

## Alerts

**Alert.** One problem for one crew member. Raised by a console rule (a daily value) or by LIGHTTIME (readings), and it says which.

**State.** The colour on the screen: `OK`, `WATCH`, `ALERT`, `RECHECK`, `SOS`. A crew member's own state is only ever `OK`, `WATCH` or `ALERT`.

**Level.** LIGHTTIME's own word for severity: nominal, advisory, caution, warning, emergency. State is what a screen shows; level is what the rule said.

**Stage.** Where an alert is on its round trip: raised, acknowledged, sent, replied, resolved.

**Report.** What the ship sends Earth about an alert: what was seen, why, what the crew has done, and the data behind it.

**Thread.** Every message about one alert, both directions, in order.

## Data

**Generated month.** The 30 days of crew data built by the data owner's scripts. Simulated, and labelled so. In `data/processed/`.

**Demo build.** The generated month with events injected (`data/processed/anomalous/`). The ship reads this.

**Healthy build.** The same month with nothing injected (`data/processed/clean/`). For tests only. Not the same thing as `data/clean/`, which holds cleaned real recordings.

**Answer key.** What was injected and what should be raised (`data/processed/ground_truth/`, `reports/`). The ship never reads it.

**Real recordings.** Measurements from people or spacecraft: NASA's cabin record from the station, JPL light times, the Deep Space Network feed, and three public sets of heart rate and blood oxygen.

## Words to avoid

**"Model", "ML", "trained", "predicts illness".** Nothing here was trained and nothing predicts an illness. Say "rule", "measured on real recordings" and "time left".

**"Validated".** Six volunteers is a check, not a validation.

**"Clean data"** without saying which: the cleaned real recordings, or the healthy build.
