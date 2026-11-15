# Blood oxygen overnight (Apnea-ECG)

Two overnight recordings from the PhysioNet Apnea-ECG Database, version 1.0.0. `c01r` is a control (under five minutes of apnoea all night). `a01r` is a sleep apnoea patient. Each CSV has one row a second: `time_s,SpO2_pct`.

These CSVs are derived, not original. The originals (`c01r.dat`, `a01r.dat`, 23 MB each, four signals at 100 samples a second) are not in the repo. Each CSV is the SpO2 signal, taking the first sample of every second. A value of 0 means the probe was off.

Source: https://physionet.org/content/apnea-ecg/1.0.0/ . Licence: Open Data Commons Attribution License v1.0.

Cite: Penzel T, Moody GB, Mark RG, Goldberger AL, Peter JH (2000). The Apnea-ECG Database. Computers in Cardiology 27: 255-258. doi:10.1109/CIC.2000.898505. Database: doi:10.13026/C23W2R

How we use it: `scripts/check_spo2_rules.py` plays both through the ship's rules. On 14 November 2026 the control gave 4 false SOS with every number believed, 1 with impossible numbers rejected, and 0 with a ten-reading settle time after a dropout. The patient's 579 fast falls show the limit of the trend warning: it came first for 32% of them.
