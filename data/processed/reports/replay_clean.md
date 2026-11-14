# Replay through the backend: clean build

225657 events replayed through the backend in 1722 s (in-process, SQLite in memory). 1030 alerts raised. The harness clears an alert after 10 data-minutes back in range, with `by: "auto: replay"` so the backend's 60 s quiet window does not apply.

## False alarms (alerts with no anomaly behind them)

Total: **1030** alerts.

| class | crew | vital | level | count |
| --- | --- | --- | --- | --- |
| inside the personal band, outside NEWS2 | C3 | bp_sys | caution | 147 |
| NC02 sleeping HR/BP (normal night dip) | C1 | heart_rate | caution | 127 |
| sensor check (signal) outside a fault | C3 | signal | advisory | 100 |
| sensor check (signal) outside a fault | C1 | signal | advisory | 80 |
| sensor check (signal) outside a fault | C4 | signal | advisory | 76 |
| sensor check (signal) outside a fault | C2 | signal | advisory | 70 |
| NC01 exercise HR/BP | C2 | heart_rate | caution | 48 |
| NC01 exercise HR/BP | C3 | heart_rate | caution | 48 |
| NC01 exercise HR/BP | C1 | heart_rate | caution | 46 |
| NC01 exercise HR/BP | C4 | heart_rate | caution | 45 |
| inside the personal band, outside NEWS2 | C4 | heart_rate | caution | 45 |
| inside the personal band, outside NEWS2 | C1 | bp_sys | caution | 40 |
| unexplained | C4 | bp_sys | caution | 36 |
| NC02 sleeping HR/BP (normal night dip) | C2 | bp_sys | caution | 34 |
| unexplained | C1 | bp_sys | caution | 26 |
| NC02 sleeping HR/BP (normal night dip) | C4 | bp_sys | caution | 12 |
| NC02 sleeping HR/BP (normal night dip) | C4 | heart_rate | caution | 8 |
| inside the personal band, outside NEWS2 | C4 | bp_sys | caution | 8 |
| unexplained | C2 | bp_sys | caution | 8 |
| NC01 exercise HR/BP | C4 | heart_rate | emergency | 3 |
| typed check-in value | C1 | bp_sys | caution | 3 |
| NC01 exercise HR/BP | C1 | heart_rate | emergency | 2 |
| NC01 exercise HR/BP | C1 | heart_rate | warning | 2 |
| NC01 exercise HR/BP | C3 | heart_rate | emergency | 2 |
| NC01 exercise HR/BP | C3 | heart_rate | warning | 2 |
| NC01 exercise HR/BP | C4 | heart_rate | warning | 2 |
| typed check-in value | C4 | bp_sys | caution | 2 |
| NC01 exercise HR/BP | C2 | heart_rate | emergency | 1 |
| NC01 exercise HR/BP | C2 | heart_rate | warning | 1 |
| NC02 sleeping HR/BP (normal night dip) | C1 | bp_sys | caution | 1 |
| NC02 sleeping HR/BP (normal night dip) | C2 | heart_rate | caution | 1 |
| NC02 sleeping HR/BP (normal night dip) | C3 | bp_sys | caution | 1 |
| typed check-in value | C2 | bp_sys | caution | 1 |
| unexplained | C3 | bp_sys | caution | 1 |
| unexplained | C4 | heart_rate | caution | 1 |

By class: sensor check (signal) outside a fault 326, inside the personal band, outside NEWS2 240, NC01 exercise HR/BP 202, NC02 sleeping HR/BP (normal night dip) 184, unexplained 72, typed check-in value 6

## Link (Earth outbox)

| data time | dial | queued before | flushed | queued items (kind, priority, alert) |
| --- | --- | --- | --- | --- |
| 2026-10-16T00:00:00Z | mars | 0 | 0 |  |
| 2026-11-12T18:00:00Z | sun | 0 | 0 |  |
| 2026-11-13T12:00:00Z | mars | 4 | 4 | update/1/1001, report/0/1001, update/1/993, report/0/993 |
