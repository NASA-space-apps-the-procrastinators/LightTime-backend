# 1. Rules decide; a learned model may only advise

Date: 14 November 2026. Status: accepted by the backend owner.

## Context

LIGHTTIME tells a crew far from Earth when a reading matters and who has to act. The team expected "the AI" to be a trained model, and the project summary said it would predict illness from Earth and space datasets.

The data we have:

- Six overnight blood oxygen recordings and two apnea recordings from real people. Eight people, one of them a patient.
- Fifteen wrist recordings of heart rate with activity labels from real, healthy people. No recording contains an emergency.
- A generated 30-day month for four crew. It is simulated: a model trained on it would learn the generator's own formulas, and any score on it would be circular.

There is no labelled emergency from any crew, and one night to build.

The CSA mentor's advice on 14 November: crews and flight surgeons need reasoning they can trace, alarms in proportion to the risk, and a human who owns every override.

## Decision

No trained model raises, changes, silences or ranks an alert. Every alert comes from a fixed rule with a source, and each rule is tried on real recordings before it is allowed to alarm. A rule that fails that trial is switched off, and the result is kept.

A model learned from data may be added only as an adviser: it may put a remark beside a reading ("unusual for someone at rest"), it must be tested on people it was not fitted on, it must pass a stated false-flag gate before it ships, and removing it must change no alert.

No language model runs in the request path.

## What follows from this

- Every screen and document says "rules and statistics, on purpose", and never "machine learning", "trained", "validated" or "predicts illness".
- What LIGHTTIME learns is per person and explainable: each person's usual range from their own last 24 hours, and settings chosen by holding out one volunteer at a time.
- Two rules were already switched off under this decision: heart rate judged with hospital bands (tripped for 14 of 15 healthy people at a desk) and the suit's blood pressure estimate (in the caution band or worse on 77,647 of 168,600 minutes of the generated month's healthy build, the figure recorded in `base_station/limits.json`).
- Gaps stay visible: nothing catches a fast heart rate at rest, a slow one in sleep, or a stuck sensor. Each is listed with the evidence a rule would need first.
- The one adviser allowed so far is a learned normal heart rate by activity (`docs/plans/2026-11-15-backend-polish.md`, Task 8), behind its gate.

## What was considered and not chosen

- **A forecaster for falling blood oxygen trained on the eight recordings.** It would learn those eight people. The median-slope rule already warned for six of six volunteers held out in turn, a median of 97 seconds ahead, and can be explained in one sentence.
- **An anomaly detector trained on the generated month.** Circular: it would find what the generator injected.
- **A language model writing the spoken lines or the reports.** Its sentences could not be traced to a rule, and it would need a link the ship may not have.

## When to revisit

When there is labelled data from the people and sensors the system is used on, and a way to test a model on people it has not seen. Until then a model that cannot explain itself is the wrong thing to hand a crew eleven light-minutes from a doctor.
