# LIGHT-TIME data sources spec

Date: 14 November 2026. Owner: TJ. Status: waiting for TJ's sign-off. No plan is written yet.

Companion files: `docs/data-sources.md` (every source, with links) and `docs/specs/2026-11-14-backend-design.md` (the backend this plugs into).

## Problem

We have found a dozen NASA and CSA sources. Right now only one of them, Mars light time, is wired into the backend. The cabin, radiation and space weather tiles on Damola's screens are mock numbers. We need one simple, repeatable way to bring a source into the backend, keep it working when the venue network drops, and show on screen where every number came from.

## What Global Awards require

The Global Organizing Team answered this for our challenge (Space Apps GitHub, discussion 1994): the pages on the challenge's Resources tab count as the required NASA data source, and it does not have to be a dataset. An earlier ruling (discussion 1827) says the required source must come from that tab. Other NASA data, partner data and third-party data are welcome on top, but they do not replace it. Everything used must be cited.

So we are already eligible: the NASA HRP risks page is on the Resources tab, and every alert carries the name of the NASA risk it relates to. Nothing in this spec is needed for eligibility. It is here to raise Validity and Impact, and to turn mock tiles into real ones.

## Goals

1. Two live NASA feeds in the backend: space weather (DONKI) and the Deep Space Network's own light time to Mars (DSN Now).
2. Real ISS cabin readings (NASA OSDR Environmental Data App) behind the cabin tiles, replayed from downloaded files and labelled as such.
3. One call that lists every source we use, with its link, how fresh it is and its credit line. The screens and the project page both read from it.
4. The demo runs the same with no internet at all.

## Not doing

| Left out | Why |
| --- | --- |
| Scraping web pages | Pages change without notice, the CSA portal turns automated readers away, and a judge cannot check a scraped number. We use published APIs and published files |
| Health data that can identify a person | We use only open, de-identified research data under its licence, without its questionnaire files, and we label it as replayed |
| A scheduler or a job queue | Two feeds do not need one |
| Alerts from space weather or cabin data | Saturday and Sunday these are tiles only. Crew alerts stay on crew vitals |
| Unit conversion by guesswork | We show the source's units, or convert with a factor we can cite |

## Decisions

1. **Three ways in, and no others.** A live API, a file a person downloaded into `data/`, or a fact a person copied from a page into `data/reference/` with the link and the date. No page scraping.
2. **Every live feed follows the Mars light time pattern.** Ask with a short timeout. Save the last good answer in `data/cache/`. If the next ask fails, serve the saved answer and say how old it is. If nothing was ever saved, say "no data".
3. **A screen never waits on the internet twice.** Each feed has a refresh window (60 s for DSN, 15 minutes for DONKI). Inside the window the backend answers from memory. After a failure it waits 60 s before trying again.
4. **One switch for the stage.** With `LIGHTTIME_OFFLINE=1` the backend makes no outside calls at all, Horizons included. It uses saved answers and files only.
5. **Every value says where it came from.** Each one carries `source`, `url`, `kind` and `as_of`. `kind` is one of `live`, `cached`, `file`, `reference` or `simulated`.
6. **Downloaded data is replayed, and the label says so.** The cabin files are past ISS readings. The tile reads "ISS cabin, NASA OSDR, replayed", not "our cabin now".
7. **Tests never touch the network.** Each feed has a saved sample answer in `tests/fixtures/`, and the parser is tested against it.
8. **The loader for a file is written after the file is in the folder.** We read the real column names and units first. We do not guess them.

## The data folder

| Folder | Holds | In git |
| --- | --- | --- |
| `data/reference/` | Small files of facts copied from NASA and CSA pages, each with its link and the date it was read | Yes |
| `data/eda/` | Cabin and radiation tables from NASA's Environmental Data App, fetched through its API. Rodent Research 1 is in the folder | Yes |
| `data/ppg_dalia/` | Wrist heart rate and skin temperature for three volunteers, cut from the PPG-DaLiA dataset | Yes |
| `data/cache/` | The last good answer from each live feed, written by the app | No |
| `data/README.md` | What goes where, the credit lines, and the rule against identifiable health data | Yes |

## Sources and how each comes in

| Id | Source | Way in | Refresh | If it fails | Where it shows |
| --- | --- | --- | --- | --- | --- |
| `horizons` | NASA JPL Horizons | Live API (built in the Saturday plan, Task 2) | Once a day | Dated values in the code | The dial and every delay |
| `hrp_risks` | NASA HRP risks page. Our required NASA source | Reference file | Read once | Not applicable | The risk name on every alert |
| `donki` | NASA DONKI, solar particle events and flares | Live API, JSON, no key | 15 minutes | Saved answer with its age | Space weather tile |
| `dsn` | NASA Deep Space Network Now | Live XML feed | 60 s | Saved answer with its age | One line on the Earth console |
| `eda` | NASA OSDR Environmental Data App | Its API (`/eda/api/missions/RR-1/telemetry_data/` and `/radiation_data/`), saved as files in `data/eda/` | Replayed | Tile falls back to simulated, labelled | Cabin CO2 (ppm), temperature (degrees C), humidity (%), radiation (mGy a day) |
| `ppg_dalia` | PPG-DaLiA, UCI Machine Learning Repository, CC BY 4.0 | Files in `data/ppg_dalia/` | Replayed | The scripted numbers | Calm-phase heart rate and skin temperature on the crew tiles, labelled as replayed research data, not our crew's own |
| `radi_n2` | CSA Radi-N2 | Reference number (150 microsieverts of neutron dose a day on the ISS) | Read once | Not applicable | Footnote on the radiation tile |
| `news2` | NEWS2 chart, Royal College of Physicians | Reference file (`base_station/limits.json`) | Read once | Not applicable | Alert bands |
| `scenario` | Our scripted readings | Simulated | Not applicable | Not applicable | Crew vitals |

Optional, only if time allows: NASA RadLab (file export, a dose trend), CSA Phoenix weather station (file, an "outside at Mars" tile), CSA heart-rate filter (code, a noise rule).

Space weather is shown as facts, with no level of our own: the number of solar particle events in the last 30 days and the time of the latest one. We do not have a sourced rule for turning that into a warning, so we do not invent one.

The DSN line reads from the feed's Mars spacecraft: which antenna, which spacecraft, and the round-trip light time. If the feed's own timestamp is more than an hour old, the line shows that time.

## API

| Call | Used by | Gives |
| --- | --- | --- |
| `GET /api/base/habitat` | base | Cabin CO2, temperature and humidity, radiation, and space weather. Each value has its unit, `source`, `kind` and `as_of` |
| `GET /api/base/sources` | base, earth, the project page | Every source: id, name, agency, link, way in, what it is used for, `kind` right now, `as_of`, and its credit line |
| `GET /api/earth/network` | earth | The DSN line: antenna, spacecraft, round-trip seconds, feed time, `kind` |

## Code

| File | Responsibility |
| --- | --- |
| `common/feeds.py` | The ask, save and fall back helper, plus one small parser each for DONKI and DSN |
| `common/sources.py` | The list behind `/api/base/sources` |
| `base_station/habitat.py` | Loads the cabin files, replays them, and assembles the habitat answer |
| `tests/test_feeds.py`, `tests/test_habitat.py`, `tests/fixtures/` | Parsers against saved samples, the fallback order, and the offline switch |

## Build order

1. **Phase A, no downloads needed:** the helper, DONKI, DSN, the sources list, the offline switch, and the three calls (the cabin part of `/habitat` answers "simulated" until phase B).
2. **Phase B, the files are in the folder:** the cabin loader and replay, then the calm-phase replay of wrist heart rate and skin temperature, each written against the real columns.
3. **Phase C, optional:** RadLab, Phoenix, the heart-rate filter.

None of this starts before the Saturday plan's Task 9 is done and the 16:15 run works.

## Risks

| Risk | What we do |
| --- | --- |
| A feed changes shape or goes quiet during the weekend | The saved answer keeps the tile alive, and the tile shows its age |
| The DSN feed is stale (the copy read on 14 November was stamped 13 November) | Show the feed's own time; never call it "live" unless it is under an hour old |
| A screen shows cabin CO2 in mmHg, as Damola's mock does, while NASA's file is in ppm | Show ppm as given. Convert only with a cited factor |
| This work eats Saturday | It is gated behind Task 9 and the 16:15 run |

## Open questions

| Question | Who | Blocks |
| --- | --- | --- |
| Do the crew tiles replay PPG-DaLiA in the calm phase, or keep the scripted numbers? | TJ | Phase B |
| Does the Earth console want the DSN line? | David, Damola | Phase A, the last step |
| Do Damola's cabin tiles keep their OK and WATCH badges? We have no sourced rule for them yet | Damola, Rebecca | Phase B |
