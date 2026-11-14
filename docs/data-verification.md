# Data verification

`python scripts/verify_data.py` checks what a script can: the light-time constants, live Horizons and DSN Now, the NEWS2 bands, the clean tables and the checksums of the raw files. First run on 14 Nov 2026: every check passed (DSN 655.0 s one way against Horizons 660.86 s).

The checks below need a person. Rebecca, tick each line on Sunday morning. About 20 minutes.

| # | Open this | Confirm | Done |
|---|---|---|---|
| 1 | NEWS2 chart, Royal College of Physicians 2017 (link in `limits.json` source) | The three band lists in `scripts/verify_data.py` match the chart | [ ] |
| 2 | https://www.nasa.gov/hrp/risks/ | Each `nasa_risk` name in `limits.json` is spelled as NASA spells it | [ ] |
| 3 | https://ssd.jpl.nasa.gov/horizons/ (web app: Mars, observer Earth centre, quantity 21) | Same light time as `/api/base/state` shows for Mars | [ ] |
| 4 | https://eyes.nasa.gov/apps/dsn-now/ | A Mars spacecraft shown there appears in `/api/earth/network` | [ ] |
| 5 | Each data folder's README | Licence and citation are present and the link opens | [ ] |
| 6 | NASA-STD-3001 Volume 1, requirement V1 3004 | It says what the spec says it says | [ ] |
| 7 | NEEMO 16 reference in `common/modes.py` | The five-minute line is in the source | [ ] |
| 8 | A NASA page on ISS communications through TDRS | The 0.25 s station figure is fair. If none is found, label it "assumed" on the dial | [ ] |
| 9 | The cue list in the CSA advisor record (CMO-DA, STD-3001 section 7.3) | Verified before anyone says it in the pitch, or left out | [ ] |

Note on line 4: DSN Now gives the round trip to three significant figures (1310 s on 14 Nov), so its one-way figure is only good to about 5 s. A gap of a few seconds against Horizons is rounding, not an error.
