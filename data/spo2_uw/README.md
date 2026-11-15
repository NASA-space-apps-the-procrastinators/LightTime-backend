# Blood oxygen falling and recovering (UW)

Six healthy adults breathed lowered-oxygen gas mixes in a clinical lab for 14 to 19 minutes each, with finger oximeters reading once a second. Files `100001.csv` to `100006.csv` are the study's ground-truth oximeter files, unchanged. We use the column `SpO2 5` (and `Pulse 5`), the Masimo Radical-7. Column `SpO2 3` is all zeros. Each file ends with a line that is not data.

Source: https://github.com/ubicomplab/oximetry-phone-cam-data (folder `data/gt`). Licence: MIT, see `LICENSE` in this folder.

Cite: Hoffman JS, Viswanath VK, Tian C, Ding X, Thompson MJ, Larson EC, Patel SN, Wang EJ (2022). Smartphone camera oximetry in an induced hypoxemia study. npj Digital Medicine 5(1): 146. doi:10.1038/s41746-022-00665-y

How we use it: `scripts/build_clean_data.py` cuts rows 110 to 878 of `100001.csv` into `data/clean/spo2_event.csv`, which the `real` story plays. `scripts/check_spo2_rules.py` plays all six through the ship's rules. On 14 November 2026 the falling-trend warning came before the SOS for 6 of 6, between 14 and 159 seconds ahead (median 97). The settings were chosen on these same recordings, so that is a fit, not a validation.
