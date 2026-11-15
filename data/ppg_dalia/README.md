# PPG-DaLiA, wrist files only

Real wrist-wearable readings from 15 volunteers during about 2.5 hours of daily activities. This folder is a small cut of the full dataset (4.9 MB out of 2.7 GB).

- Source: https://archive.ics.uci.edu/dataset/495/ppg+dalia
- Licence: CC BY 4.0
- Cite: Reiss A, Indlekofer I, Schmidt P, Van Laerhoven K (2019). Deep PPG: Large-Scale Heart Rate Estimation with Convolutional Neural Networks. Sensors 19(14): 3079. https://doi.org/10.3390/s19143079. Dataset: UCI Machine Learning Repository, https://doi.org/10.24432/C53890
- Cut on 14 November 2026 from `ppg+dalia.zip`. The files are copied as they are; nothing in them was changed.

## What is here

| File | What it is |
| --- | --- |
| `S1_HR.csv` to `S15_HR.csv` | Heart rate from the wrist device (Empatica E4), one value a second, in beats a minute |
| `S1_TEMP.csv` to `S15_TEMP.csv` | Wrist skin temperature, four values a second, in degrees C |
| `S1_activity.csv` to `S15_activity.csv` | When each activity starts, in seconds from the start of the session |
| `PPG_FieldStudy_readme.pdf` | The dataset's own description |
| `rule_check.py` | Reruns the check below |

In `HR.csv` and `TEMP.csv` the first line is the start time (Unix seconds) and the second line is the rate (values a second). The readings follow, one a line. `HR.csv` starts 10 seconds after `TEMP.csv`.

## What was left out, and why

The chest-sensor recordings and the raw wrist signals (most of the 2.7 GB), because we do not use them. The questionnaire files (age, sex, height, weight), because we do not need personal details. The dataset has no blood oxygen.

## How we may use it

Replayed as calm-phase heart rate and skin temperature on the crew tiles, labelled "replayed research data", never as our crew's own readings. And as a test set for alert rules.

## What it showed about our heart-rate rule

Run `python rule_check.py`. With the hospital chart's heart-rate bands (NEWS2) and our 5-second hold, on these 15 healthy volunteers:

| Activity | Trip a caution | Trip a warning | Would send an SOS |
| --- | --- | --- | --- |
| Sitting still, about 10 minutes | 7 of 15 | 1 | 0 |
| Desk work, about 20 minutes | 14 of 15 | 5 | 1 |
| The whole session, with stairs, cycling and walking | 15 of 15 | 15 | 13 |

A longer hold does not fix it: at 120 seconds, 5 of 15 still trip a caution at desk work and 5 would send an SOS over the session. Two cautions on this result: the wrist device's heart rate is an estimate, and NEWS2 was made for hospital patients at rest. That second point is the finding. A generic chart cannot judge a healthy, active crew.

Segments that trip nothing and are safe to replay: sitting for S2, S3, S4, S7, S9, S10, S11 and S14; desk work for S15.
