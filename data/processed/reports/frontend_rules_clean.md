# Frontend scoring rules on the clean build

The contract's Scoring table applied to the data by `score_frontend_rules.py` (not by the backend). The assumptions are at the top of the script.

## Flags with no anomaly behind them

| state | metric | count |
| --- | --- | --- |
| ALERT | sleep_h | 9 |
| WATCH | sleep_h | 38 |
| WATCH | co2_mmHg | 24 |
| WATCH | bp_sys | 11 |
| RECHECK | signal | 262 |
