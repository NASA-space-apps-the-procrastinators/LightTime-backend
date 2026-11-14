# Replay through the backend: anomalous build

2000 events replayed through the backend in 9 s (in-process, SQLite in memory). 8 alerts raised. The harness clears an alert after 10 data-minutes back in range, with `by: "auto: replay"` so the backend's 60 s quiet window does not apply.

An anomaly counts as caught only if at least one matching alert has no twin (same crew, same vital, within 15 min) in the clean replay; otherwise the alert would have fired anyway.

## Anomalies

| id | type | expected (correct system) | expected from current backend | backend raised | first alert after start | verdict |
| --- | --- | --- | --- | --- | --- | --- |
| AN01 | hr_rest_3day | ALERT | none | none |  | MISSED: within NEWS2 bands |
| AN02 | spo2_drop | ALERT | emergency | none |  | MISSED |
| AN03 | tachycardia_rest | ALERT | warning | none |  | MISSED |
| AN04 | bradycardia_sleep | ALERT | emergency | none |  | MISSED |
| AN05 | fever | ALERT | not_ingested | none |  | MISSED: channel not ingested |
| AN06 | co2_buildup | ALERT | not_ingested | none |  | MISSED: channel not ingested |
| AN07 | sep_event | ALERT | not_ingested | none |  | MISSED: channel not ingested |
| AN08 | sep_event | WATCH | not_ingested | none |  | MISSED: channel not ingested |
| AN09 | sos_glove_tap | SOS | emergency | none |  | MISSED |
| AN10 | spo2_drop | ALERT | emergency | none |  | MISSED |
| SF01 | dropout | RECHECK | advisory | none |  | MISSED |
| SF02 | flatline | RECHECK | none | none |  | MISSED: within NEWS2 bands |
| SF03 | spike | none | none | none |  | ok (stayed quiet) |
| SF04 | motion_artifact | RECHECK | advisory | none |  | MISSED |

**Caught 0, missed 13** of the anomalies that should raise something.

## False alarms (alerts with no anomaly behind them)

Total: **8** alerts.

| class | crew | vital | level | count |
| --- | --- | --- | --- | --- |
| NC01 exercise HR/BP | C1 | heart_rate | caution | 1 |
| NC01 exercise HR/BP | C4 | heart_rate | caution | 1 |
| NC02 sleeping HR/BP (normal night dip) | C1 | bp_sys | caution | 1 |
| NC02 sleeping HR/BP (normal night dip) | C1 | heart_rate | caution | 1 |
| NC02 sleeping HR/BP (normal night dip) | C2 | bp_sys | caution | 1 |
| NC02 sleeping HR/BP (normal night dip) | C3 | bp_sys | caution | 1 |
| NC02 sleeping HR/BP (normal night dip) | C4 | bp_sys | caution | 1 |
| NC02 sleeping HR/BP (normal night dip) | C4 | heart_rate | caution | 1 |

By class: NC02 sleeping HR/BP (normal night dip) 6, NC01 exercise HR/BP 2

## Link (Earth outbox)

| data time | dial | queued before | flushed | queued reports (flushed first, priority 0) |
| --- | --- | --- | --- | --- |
| 2026-10-16T00:00:00Z | mars | 0 | 0 |  |
