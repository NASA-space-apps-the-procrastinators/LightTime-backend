# 5. Legs of a minute or more play sixty times faster

Date: 15 November 2026. Status: accepted, in the code since 14 November.

## Context

On 14 November 2026 a message from Mars takes 660.86 seconds to reach Earth, and a reply needs 22 minutes. A pitch lasts a few minutes. The audience has to see a report leave, land and be answered, and the screens still have to tell the truth about the delay.

## Decision

A leg of 60 seconds or more plays 60 times faster on the demo clock, and a shorter leg plays at its true length (`SPEEDUP` and `real_delay_s()` in `common/link.py`).

## What follows from this

- Mars plays as 11.01 seconds a leg; the station (0.25 seconds) and the Moon (1.3 seconds) play as they are.
- Two kinds of number travel with each message. The stamps `sent_at` and `deliver_at` are on the demo clock. The fields `delay_s`, `arrives_after_s`, `earliest_reply_after_s` and `eta_s` are true mission seconds, so the screens can say "11 minutes" while the message lands 11 seconds later. The state route gives `speedup` and each stop's `plays_as_s` so the console can say so.
- Who decides and what the ship says use the true delay, never the played one.
- Anyone reading the stamps directly must know which clock they are on. `timeline()` in `base_station/routes.py` works out the earliest reply on the clock the report used.
- Setting `SPEEDUP` to 1 plays every leg at its true length.
