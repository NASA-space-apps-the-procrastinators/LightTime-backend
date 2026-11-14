# Wiring the frontend to the backend

1. Copy `lighttime-api.ts` and `use-poll.ts` into `src/lib/` in the frontend repo.
2. Put `NEXT_PUBLIC_API_URL=http://<backend laptop IP>:5000` in `.env.local`. The backend allows any origin.
3. In a client component: `const { data: crew } = usePoll(api.crew)`.

| Screen | Poll (once a second) | Buttons |
|---|---|---|
| Crew board and dial | `api.state`, `api.crew`, `api.alerts` | `api.dial`, `api.startStory`, `api.reset`, `api.sos` |
| Alert | `api.alerts` | `api.acknowledge`, `api.tickStep`, `api.sendToEarth`, `api.resolve`, `api.message` |
| What Earth has seen | `api.outbox`, `api.inbox` | `api.sendSummaries` |
| Earth console | `api.earthInbox`, `api.earthOutbox`; `api.network` every 30 s | `api.earthReply` |
| Data | `api.sources`, `api.habitat` (every 5 s) | none |

Rules that save you a bug each:

- Never work out a delay or a countdown from your own maths. Show `delay_s`, `round_trip_s`, `eta_s` as given, and count down to the times `red_line_at` and `earliest_reply_at`.
- Mission seconds and demo seconds differ. A Mars leg is 661 mission seconds and plays in 11 real seconds. Label it "playing 60x faster" using `speedup`.
- For the stop `sun`, show "No link". Ignore its `delay_s`.
- Call `speakOnce(alert)` for every open alert on every poll. It only speaks once.
- Show `why` on the alert screen and ask for a note when the crew resolves. The CSA advisor asked for both.
- Alert ids can be reused after a reset (on SQLite they start again at 1). Never store one.
- An empty form box can be sent as "". The backend treats it as no reading.
- Readings for one crew member include typed check-ins. Filter on `source` for a chart.
