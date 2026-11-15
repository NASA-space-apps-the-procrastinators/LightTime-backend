# Data

This page is for developers and reviewers. It lists every dataset LIGHT-TIME uses, its licence and folder, what the ship may read and what it must not, and how to rebuild and check the data. It replaces `docs/data-sources.md` and `docs/data-verification.md`. How the rules use the data, and what the recordings showed, is in the [concept document](../concept.md) and in [How it works](../how-it-works.md).

NASA and the CSA publish no open stream of astronaut vital signs, so the crew's vital signs stay simulated and labelled. Real data goes into everything around the crew: the light time, the cabin record and the recordings used to test the rules.

## What the ship may read

The ship reads the generated mission data only through [`common/dataset.py`](../../common/dataset.py), and only two folders of it:

| Folder under `data/processed/` | The ship may read it | What it holds |
|---|---|---|
| `reference/` | yes | Facts: the crew list (`crew.csv`), the mission, the console's thresholds, the sensor vocabulary |
| `anomalous/` | yes | The simulated month the demo plays: suit minutes, daily values, cabin, radiation, space weather, with the planted events |
| `clean/` | no | A healthy crew for testing tools. It is the test copy |
| `ground_truth/` | no | Where each planted event is. It is the answer key |
| `reports/` | no | Scores of the rules against the answer key |

`dataset.table()` raises an error for any folder but the first two, and [`tests/test_dataset.py`](../../tests/test_dataset.py) (`test_the_ship_cannot_open_the_answer_key`) checks that it does. The same test file checks that the files the ship reads match the build recorded in `data/processed/BUILD_INFO.json`.

## Datasets

### Used by the running app

| Source | Folder or call | Licence and credit | Use |
|---|---|---|---|
| NASA JPL Horizons API | live call to `https://ssd.jpl.nasa.gov/api/horizons.api` (`common/lighttime.py`); dated fallback values in the code and `data/reference/horizons_mars_light_time.csv` | NASA public service; cite the Horizons system | One-way light time, Earth to Mars, for the mission date (quantity 21) |
| NASA Deep Space Network Now feed | live call to `https://eyes.nasa.gov/dsn/data/dsn.xml` (`common/dsn.py`) | NASA public feed | Round-trip light time NASA reports for spacecraft at Mars, shown beside Horizons as a check |
| NASA OSDR Environmental Data App, Rodent Research 1 (2014) | `data/eda/` (raw, as downloaded), replayed through `data/processed/anomalous/cabin_env.csv` | Credit line OSDR asks for: "Data and visualizations are courtesy of the Environmental Data Application (EDA) (https://visualization.osdr.nasa.gov/eda/), Version #." | Cabin carbon dioxide, temperature and humidity on the station strip |
| PPG-DaLiA (UCI Machine Learning Repository) | `data/ppg_dalia/` | CC BY 4.0. Reiss et al. (2019), Sensors 19(14): 3079, doi:10.3390/s19143079; dataset doi:10.24432/C53890 | Texture for the simulated heart rate and skin temperature; the test that switched off hospital heart-rate bands |
| The generated crew month | `data/processed/` | The project's own, built by `data/scripts/build_all.py` from a fixed seed | Everything about the crew. Every row carries `simulated` and `provenance` |

### Used offline to test the rules

| Source | Folder | Licence and credit | Use |
|---|---|---|---|
| University of Washington induced-hypoxemia study | `data/spo2_uw/` | MIT (`LICENSE` in the folder). Hoffman et al. (2022), npj Digital Medicine 5(1): 146, doi:10.1038/s41746-022-00665-y | Six falls in blood oxygen, one reading a second, to test the time-left rule. Volunteer 100001 is the `real` story |
| Apnea-ECG Database, records c01r and a01r (PhysioNet) | `data/spo2_apnea_ecg/` | Open Data Commons Attribution License v1.0. Penzel et al. (2000), Computers in Cardiology 27: 255-258, doi:10.1109/CIC.2000.898505; database doi:10.13026/C23W2R | c01r, a healthy night, is the false-alarm test. a01r, a sleep apnoea patient, shows where the trend warning stops helping |

### Read as background, no measurements used

| Source | Link | Use |
|---|---|---|
| NASA-STD-3001 and the OCHMO technical briefs | https://www.nasa.gov/ochmo/human-spaceflight-and-aviation-standards | Background for the console's daily rules; the cabin carbon dioxide levels (2.8 and 4.5 mmHg) |
| NASA Human Research Program risks | https://www.nasa.gov/hrp/risks/ | The risk named on each alert |
| CSA Bio-Monitor | https://www.asc-csa.gc.ca/eng/sciences/bio-monitor.asp | The smart shirt we assume the crew wear; the health log's sensor names follow it |
| CSA, Canadian Healthcare in Deep Space (2019) | https://asc-csa.gc.ca/eng/publications/canadian-healthcare-in-deep-space.asp | Why autonomous medical care matters when Earth is minutes away |
| CSA Topical Teams 2023 report | https://open.canada.ca/data/en/dataset/520fe919-0868-4086-ba3f-1964b80ec26c | Background on astronaut health. A report, with no measurements |

### Looked at and not usable for live vitals

| Source | Why not |
|---|---|
| CSA Bio-Monitor astronaut data | Not on the open portal; the CSA funds named research teams to analyse it |
| Inspiration4 crew data on NASA OSDR | Processed lab and omics results are public; raw data needs an application, and it is not a heart-rate or oxygen stream |
| NASA Life Sciences Portal | Most human data needs a request |
| Astroskin data from the Galactic 05 flight | Listed in a 2024 NASA slide as coming to OSDR; not found open |

The full survey, with the optional sources that were not built, is kept in the git history of `docs/data-sources.md`.

## Rebuild and check

| Task | Command | Notes |
|---|---|---|
| Rebuild the generated month | `python data/scripts/build_all.py` | Seeded: the same input gives the same output. It stops if a raw file's checksum in `data/raw_manifest.csv` has changed |
| Check the data | `python scripts/verify_data.py` | Checks the light-time constants, live Horizons and DSN Now, the NEWS2 bands, the clean tables and the raw-file checksums. `--offline` skips the network; `--write` records new checksums |
| Rebuild the clean test recordings | `python scripts/build_clean_data.py` | Rebuilds `data/clean/` from the raw downloads |
| Reprint the blood-oxygen evidence | `python scripts/check_spo2_rules.py` | Plays the recordings through the ship's rules |
| Every number the documents quote | `python scripts/paper_numbers.py` | Writes `docs/generated/numbers.json`; about four minutes, `--quick` skips the cross-check |

Some checks need a person. Each takes a minute or two:

| # | Open this | Confirm |
|---|---|---|
| 1 | The NEWS2 chart (Royal College of Physicians, 2017) | The band lists in `scripts/verify_data.py` match the chart |
| 2 | https://www.nasa.gov/hrp/risks/ | Each `nasa_risk` name in `base_station/limits.json` is spelled as NASA spells it |
| 3 | https://ssd.jpl.nasa.gov/horizons/ (Mars, observer at Earth's centre, quantity 21) | The light time matches what `/api/base/state` shows for Mars |
| 4 | https://eyes.nasa.gov/apps/dsn-now/ | A Mars spacecraft shown there appears in `/api/earth/network` |
| 5 | Each data folder's README | The licence and citation are present and the link opens |

On 15 November at 21:49 UTC, the app's own DSN check gave 655.0 seconds one way against Horizons' 656.6 seconds for that day: 1.6 seconds apart.
