# data

Everything the backend reads that is not code. The rules and the reasons are in `docs/specs/2026-11-14-data-sources-design.md`. The full list of sources and links is in `docs/data-sources.md`.

| Folder | Holds |
| --- | --- |
| `reference/` | Small files of facts copied from NASA and CSA pages, each with its link and the date it was read |
| `eda/` | Tables from NASA's Environmental Data App (https://visualization.osdr.nasa.gov/eda), fetched through its API: ISS cabin temperature (degrees C), humidity (%), CO2 (ppm) and radiation (mGy a day) |
| `ppg_dalia/` | Wrist heart rate and skin temperature for three volunteers, cut from the PPG-DaLiA dataset (https://archive.ics.uci.edu/dataset/495/ppg+dalia, CC BY 4.0) |
| `cache/` | The last good answer from each live feed. The app writes it. It is not in git |

## Rules

- No health data that can identify a person goes in this folder. Open, de-identified research data is fine under its licence; we leave out its questionnaire files (age, weight and the like). On screen it is labelled as replayed research data, never as our crew's own readings.
- Every file has a source. Write the link and the download date in the table below when you add one.
- No scraped pages. A source comes in as a live API, a downloaded file, or a fact copied by hand with its link.

## What is in here

| File | From (link) | Downloaded on | By |
| --- | --- | --- | --- |
| `eda/rr1_telemetry.json` | https://visualization.osdr.nasa.gov/eda/api/missions/RR-1/telemetry_data/ | 14 Nov 2026 | Claude, for TJ |
| `eda/rr1_radiation.json` | https://visualization.osdr.nasa.gov/eda/api/missions/RR-1/radiation_data/ | 14 Nov 2026 | Claude, for TJ |
| `eda/missions.json` | https://visualization.osdr.nasa.gov/eda/api/missions/ | 14 Nov 2026 | Claude, for TJ |

## Credit lines for the project page

- NASA OSDR: "Data and visualizations are courtesy of the Environmental Data Application (EDA) (https://visualization.osdr.nasa.gov/eda/), Version #."
- PPG-DaLiA: Reiss, A., Indlekofer, I. and Schmidt, P. (2019). PPG-DaLiA. UCI Machine Learning Repository. https://doi.org/10.24432/C53890. Licence CC BY 4.0.
- Canadian Space Agency files: name the CSA as the source and link the Open Government Licence - Canada (https://open.canada.ca/en/open-government-licence-canada).
