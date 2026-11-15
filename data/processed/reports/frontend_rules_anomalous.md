# Frontend scoring rules on the anomalous build

The contract's Scoring table applied to the data by `score_frontend_rules.py` (not by the backend). The assumptions are at the top of the script.

| id | type | expected | rules gave | verdict |
| --- | --- | --- | --- | --- |
| AN01 | hr_rest_3day | ALERT | ALERT | caught |
| AN02 | spo2_drop | ALERT | ALERT | caught |
| AN03 | tachycardia_rest | ALERT | none | MISSED |
| AN04 | bradycardia_sleep | ALERT | none | MISSED |
| AN05 | fever | ALERT | ALERT | caught |
| AN06 | co2_buildup | ALERT | ALERT | caught |
| AN07 | sep_event | ALERT | ALERT | caught |
| AN08 | sep_event | WATCH | WATCH | caught |
| AN09 | sos_glove_tap | SOS | SOS | caught |
| AN10 | spo2_drop | ALERT | ALERT | caught |
| SF01 | dropout | RECHECK | RECHECK | caught |
| SF02 | flatline | RECHECK | none | MISSED |
| SF03 | spike | none | none | ok |
| SF04 | motion_artifact | RECHECK | RECHECK | caught |

Caught 10 of 13.

## Flags with no anomaly behind them

| state | metric | count |
| --- | --- | --- |
| ALERT | sleep_h | 13 |
| ALERT | mood | 1 |
| WATCH | sleep_h | 35 |
| WATCH | co2_mmHg | 24 |
| WATCH | bp_sys | 11 |
| RECHECK | signal | 262 |
