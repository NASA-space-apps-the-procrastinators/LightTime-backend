# Replay through the backend: anomalous build

225658 events replayed through the backend in 10590 s (in-process, SQLite in memory). 1030 alerts raised. The harness clears an alert after 10 data-minutes back in range, with `by: "auto: replay"` so the backend's 60 s quiet window does not apply.

An anomaly counts as caught only if at least one matching alert has no twin (same crew, same vital, within 15 min) in the clean replay; otherwise the alert would have fired anyway.

## Anomalies

| id | type | expected (correct system) | expected from current backend | backend raised | first alert after start | verdict |
| --- | --- | --- | --- | --- | --- | --- |
| AN01 | hr_rest_3day | ALERT | none | caution | 3392 min | caught |
| AN02 | spo2_drop | ALERT | emergency | emergency | 20 min | caught |
| AN03 | tachycardia_rest | ALERT | warning | emergency | 0 min | caught |
| AN04 | bradycardia_sleep | ALERT | emergency | emergency | 1 min | caught |
| AN05 | fever | ALERT | not_ingested | caution | 444 min | caught |
| AN06 | co2_buildup | ALERT | not_ingested | none |  | MISSED: channel not ingested |
| AN07 | sep_event | ALERT | not_ingested | none |  | MISSED: channel not ingested |
| AN08 | sep_event | WATCH | not_ingested | none |  | MISSED: channel not ingested |
| AN09 | sos_glove_tap | SOS | emergency | emergency | 0 min | caught |
| AN10 | spo2_drop | ALERT | emergency | emergency | 8 min | caught |
| SF01 | dropout | RECHECK | advisory | advisory | 0 min | caught |
| SF02 | flatline | RECHECK | none | none |  | MISSED: within NEWS2 bands |
| SF03 | spike | none | none | none |  | ok (stayed quiet) |
| SF04 | motion_artifact | RECHECK | advisory | advisory | 0 min | caught |

**Caught 9, missed 4** of the anomalies that should raise something.

## False alarms (alerts with no anomaly behind them)

Total: **1016** alerts.

| class | crew | vital | level | count |
| --- | --- | --- | --- | --- |
| inside the personal band, outside NEWS2 | C3 | bp_sys | caution | 147 |
| NC02 sleeping HR/BP (normal night dip) | C1 | heart_rate | caution | 115 |
| sensor check (signal) outside a fault | C3 | signal | advisory | 100 |
| sensor check (signal) outside a fault | C1 | signal | advisory | 80 |
| sensor check (signal) outside a fault | C4 | signal | advisory | 76 |
| sensor check (signal) outside a fault | C2 | signal | advisory | 70 |
| NC01 exercise HR/BP | C2 | heart_rate | caution | 48 |
| NC01 exercise HR/BP | C3 | heart_rate | caution | 48 |
| NC01 exercise HR/BP | C4 | heart_rate | caution | 45 |
| inside the personal band, outside NEWS2 | C4 | heart_rate | caution | 45 |
| NC01 exercise HR/BP | C1 | heart_rate | caution | 41 |
| inside the personal band, outside NEWS2 | C1 | bp_sys | caution | 39 |
| unexplained | C4 | bp_sys | caution | 36 |
| NC02 sleeping HR/BP (normal night dip) | C2 | bp_sys | caution | 34 |
| unexplained | C1 | bp_sys | caution | 25 |
| NC02 sleeping HR/BP (normal night dip) | C4 | bp_sys | caution | 12 |
| NC02 sleeping HR/BP (normal night dip) | C4 | heart_rate | caution | 8 |
| inside the personal band, outside NEWS2 | C4 | bp_sys | caution | 8 |
| unexplained | C2 | bp_sys | caution | 8 |
| NC01 exercise HR/BP | C4 | heart_rate | emergency | 3 |
| medical alarm during a sensor fault | C1 | heart_rate | caution | 3 |
| typed check-in value | C1 | bp_sys | caution | 3 |
| NC01 exercise HR/BP | C1 | heart_rate | emergency | 2 |
| NC01 exercise HR/BP | C3 | heart_rate | emergency | 2 |
| NC01 exercise HR/BP | C3 | heart_rate | warning | 2 |
| NC01 exercise HR/BP | C4 | heart_rate | warning | 2 |
| medical alarm during a sensor fault | C1 | bp_sys | caution | 2 |
| typed check-in value | C4 | bp_sys | caution | 2 |
| NC01 exercise HR/BP | C1 | heart_rate | warning | 1 |
| NC01 exercise HR/BP | C2 | heart_rate | emergency | 1 |
| NC01 exercise HR/BP | C2 | heart_rate | warning | 1 |
| NC02 sleeping HR/BP (normal night dip) | C1 | bp_sys | caution | 1 |
| NC02 sleeping HR/BP (normal night dip) | C2 | heart_rate | caution | 1 |
| NC02 sleeping HR/BP (normal night dip) | C3 | bp_sys | caution | 1 |
| medical alarm during a sensor fault | C1 | heart_rate | warning | 1 |
| typed check-in value | C2 | bp_sys | caution | 1 |
| unexplained | C3 | bp_sys | caution | 1 |
| unexplained | C4 | heart_rate | caution | 1 |

By class: sensor check (signal) outside a fault 326, inside the personal band, outside NEWS2 239, NC01 exercise HR/BP 196, NC02 sleeping HR/BP (normal night dip) 172, unexplained 71, typed check-in value 6, medical alarm during a sensor fault 6

## Link (Earth outbox)

| data time | dial | queued before | flushed | queued reports (flushed first, priority 0) |
| --- | --- | --- | --- | --- |
| 2026-10-16T00:00:00Z | mars | 0 | 0 |  |
| 2026-11-12T18:00:00Z | sun | 0 | 0 |  |
| 2026-11-13T12:00:00Z | mars | 8 | 8 | report (priority 0): C3 heart_rate emergency at 2026-11-13T10:30:00Z; report (priority 0): C1 heart_rate emergency at 2026-11-13T08:03:00Z; report (priority 0): C4 heart_rate emergency at 2026-11-13T07:51:00Z; report (priority 0): C3 spo2 emergency at 2026-11-13T03:08:00Z |
