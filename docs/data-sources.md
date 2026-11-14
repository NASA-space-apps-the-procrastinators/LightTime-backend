# LIGHT-TIME data sources

Checked on 14 November 2026. Every link below was opened or returned by a search on that day. "Use" says where it goes in our system.

There is no open stream of astronaut vital signs at NASA or the CSA (see the last table). So crew vitals stay simulated and labelled, and real data goes into everything around the crew: the light time, the link, the cabin, radiation, space weather and Mars.

## In the build now

| Source | Link | Use |
| --- | --- | --- |
| NASA JPL Horizons API | https://ssd.jpl.nasa.gov/api/horizons.api | One-way light time, Earth to Mars. Live call, no download. Plan Task 2 |
| NASA-STD-3001 Volume 2 | https://www.nasa.gov/ochmo/human-spaceflight-and-aviation-standards | Alert level names |
| NASA HRP risks and hazards pages | https://www.nasa.gov/hrp/risks/ and https://www.nasa.gov/hrp/hazards/ | Risk label on each alert |
| CSA Topical Teams 2023 report (this is what dataset 520fe919 is: a report, with no measurements) | https://open.canada.ca/data/en/dataset/520fe919-0868-4086-ba3f-1964b80ec26c | Citations for the pitch: sections 2.3, 2.5 and 4.1.6 of the Astronaut Health chapter |

## Picked for Sunday

| # | Source | Link | What it holds | Use | To do |
| --- | --- | --- | --- | --- | --- |
| 1 | NASA OSDR Environmental Data App (EDA) | https://visualization.osdr.nasa.gov/eda | ISS cabin temperature, relative humidity and CO2, plus radiation dose, for the Rodent Research missions | Real numbers for the cabin tiles (CO2, temperature, humidity, radiation today) | TJ downloads one mission's telemetry table and radiation table from the Data Tables tab into `data/eda/` |
| 2 | NASA DONKI space weather (CCMC) | https://ccmc.gsfc.nasa.gov/DONKI/WS/get/SEP?startDate=2026-10-15&endDate=2026-11-14 | Solar particle events as JSON. Swap `SEP` for `FLR` to get solar flares. No key | The space weather tile | Live call, no download. Tested: it answers, with no particle events since 1 October |
| 3 | NASA Deep Space Network Now feed | https://eyes.nasa.gov/dsn/data/dsn.xml | Which antenna is talking to which spacecraft, with round-trip light time (`rtlt`, seconds) | One line on the Earth console: NASA's own antennas are waiting about 22 minutes for Mars right now | Live call. Check the timestamp first: the copy read on 14 Nov was stamped 13 Nov 05:28 UTC |

The feed's Mars orbiters showed `rtlt="1330"`, which is 22.2 minutes there and back. Half of that is 665 s, and Horizons gives 661 s one way a day later. Two NASA systems agree.

## Optional, if there is time

| Source | Link | What it holds | Use |
| --- | --- | --- | --- |
| NASA OSDR RadLab | https://visualization.osdr.nasa.gov/radlab/gui/data-overview/ | Radiation readings from detectors on the ISS, with CSV and JSON export and an API | A dose-rate trend behind the radiation tile |
| CSA Radi-N2 | https://www.asc-csa.gc.ca/eng/sciences/radi-n2.asp | Canadian neutron bubble detectors on the ISS. The page gives a typical neutron dose of 150 microsieverts a day | One sourced Canadian number on the radiation tile |
| CSA Radi-N2 and You (Space Apps 2019 dataset) | https://donnees-data.asc-csa.gc.ca/users/OpenData_DonneesOuvertes/pub/Space%20Apps%20Challenge%202019/RADi-N2/Radi-N2_Challenge%20description_ENG.pdf | Neutron readings taken in Canadian schools, described next to the ISS experiment | Earth against station comparison, if wanted |
| CSA Phoenix weather station (MET) | https://open.canada.ca/data/en/dataset/0e338f52-25e4-465c-8104-bb9d7c8d3df3 | Mars temperature at three heights and pressure, 2008, CSV. The CSA file holds raw instrument numbers; calibrated values are at https://atmos.nmsu.edu/data_and_services/atmospheres_data/phoenix/ | An "outside at Mars" tile when the dial is on Mars |
| CSA heart-rate-filtering (code, MIT licence) | https://github.com/asc-csa/heart-rate-filtering | A filter that flags heart-rate swings above a threshold | A noise rule in front of the sustained check |
| NASA SUITS telemetry server | https://github.com/SUITS-Techteam/TSS_2024 | NASA's simulated spacesuit telemetry for its student challenge | A reference for suit telemetry, not real data |

## Looked at and not usable for live vitals

| Source | Link | Why not |
| --- | --- | --- |
| CSA Bio-Monitor astronaut data | https://asc-csa.gc.ca/eng/sciences/space-flight-improve-monitor-health-earth.asp | Not on the open portal. The CSA funds named research teams to analyse it |
| Inspiration4 crew data on NASA OSDR | https://www.nasa.gov/osdr-latest-news-i4-mission-datasets/ | Processed lab and omics results are public; raw data needs an application. It is not a heart-rate or oxygen stream |
| NASA Life Sciences Portal | https://www.nasa.gov/hrp/nlsp | Most human data needs a request. It has open bed-rest study datasets; we did not confirm what they measure |
| Astroskin data from Virgin Galactic's Galactic 05 flight | https://ntrs.nasa.gov/api/citations/20240001562/downloads/hrp%20iws%202024%20osdr%2020240202_fin.pdf | A 2024 NASA slide lists it as coming to OSDR. We did not find it open |

## Credit lines the project page needs

- NASA OSDR asks for this wording when its apps are used: "Data and visualizations are courtesy of the Environmental Data Application (EDA) (https://visualization.osdr.nasa.gov/eda/), Version #." RadLab has the same wording with its own link.
- Any CSA portal file: name the Canadian Space Agency as the source and link the Open Government Licence - Canada (https://open.canada.ca/en/open-government-licence-canada).
