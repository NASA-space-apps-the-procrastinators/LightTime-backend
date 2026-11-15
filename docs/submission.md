# Submission text for the project page

Copy-ready text for each field of the NASA Space Apps project page, in the order the form asks for them, followed by a checklist. The fields and limits are those of the 2026 Project Submission Guide. Everything here is in English, as the guide requires, and every claim can be traced to this repository: the evidence is in [How it works](how-it-works.md).

Two fields need links that only the team can supply. They are marked "paste the public link".

## Project Name

LIGHT-TIME

## High-Level Project Summary

LIGHT-TIME is health monitoring software for a crew that may be minutes from medical help, or out of contact. It watches each crew member's vital signs once a second, raises an alert only on readings it can trust, and for a falling reading works out how much time is left before a red line. It then compares that time with the earliest possible reply from a flight surgeon on Earth, which is twice the light time, and tells the crew in one sentence who must act first. A dial moves the ship between the space station (0.25 seconds), the Moon (1.3 seconds), Mars (11 minutes on 14 November 2026, from NASA JPL Horizons) and behind the Sun (no link), and every screen follows it. A second console shows Earth only what the delayed link has delivered. Monitoring today assumes a doctor is a second away. On the way to Mars that assumption fails, and the software has to know it.

## Link to Project Demo

Paste the public link to the seven-slide deck or the 30-second video. Open it in a private browser window first: it must need no sign-in.

## Link to Final Project

Paste the public link to the hosted console, and the two repositories:

- Backend (the ship and the link): https://github.com/NASA-space-apps-the-procrastinators/LightTime-backend
- Console (crew and Earth): https://github.com/NASA-space-apps-the-procrastinators/LightTime-frontend

Both repositories must be set to public before these links will open for a judge.

## Detailed Project Description

**What it does.** LIGHT-TIME has two consoles and a link between them. The crew console shows four crew members, each scored against their own baseline, and the cabin: carbon dioxide, oxygen, pressure, temperature, radiation and space weather. The Earth console is the flight surgeon's. It shows only what has arrived, as old as the light time, and a reply takes the same road back. A dial sets how far the ship is from Earth, and with it the delay, who decides and what the ship says.

**How it works.** The ship's adviser, LIGHTTIME, asks three questions of every reading. Can it be trusted: an impossible value or a poor signal is never judged, and a band must hold for five clean readings in a row. Is it normal for this person: each crew member has their own baseline band and a usual range learned from their last 24 hours. How long is left: for a falling reading it fits a robust trend line (the Theil-Sen estimator, the median of the slopes between every pair of the last 60 readings), works out the time until the reading reaches the red line, and compares it with the round-trip light time. The alert bands follow the NEWS2 chart of the Royal College of Physicians.

When Earth cannot answer in time the ship says so: "Blood oxygen 96 and falling. At this rate it reaches the red line in about 70 seconds. Earth's earliest reply is 22 minutes away. That is too late. Crew medical officer, check on Okafor now." It shows a checklist and its reasons, and sends Earth a handoff report that already answers the questions a flight surgeon asks first, because at Mars each question costs 22 minutes.

**What makes it trustworthy.** No trained model makes or changes a decision, and no language model runs in the app. Every alert is a fixed rule that prints its reasons and its source, and ends with the same line: "This is a fixed rule, not a diagnosis. A person, not the ship, decides." Each rule was tested on real recordings before it was allowed to alarm. On six recorded falls in blood oxygen the ship warned before the emergency level in six of six, by a median of 97 seconds, with each volunteer held out of the tuning. On 7.8 hours of a healthy sleeper the trust rules took false emergency alarms from four to none. Two rules were switched off because real data showed they would cry wolf: hospital heart-rate bands flagged 14 of 15 healthy people at a desk. The backend has 192 automated tests.

**What is real and what is simulated.** The Mars delay comes from NASA JPL Horizons and is checked against the round-trip light time NASA's Deep Space Network reports. Cabin carbon dioxide, temperature and humidity are a NASA record from the International Space Station. NASA publishes no open stream of astronaut vital signs, so crew vital signs are simulated, and the screens label them.

**Benefits.** A crew gets a monitor that does not wait for an answer that cannot arrive in time, and that says plainly who acts. A flight surgeon gets a report that needs no follow-up questions. The same software works at the space station, the Moon and Mars, because distance is a setting and not an assumption.

**What we hope to achieve.** To show that communication delay belongs inside health monitoring software as a number it computes with, and to give mission designers a working example to argue with. Next steps are testing the time-left rule on more recordings, rules for the cases it does not cover yet, and a trial with a real suit sensor.

**Tools.** Python, Flask, SQLAlchemy, SQLite and PostgreSQL, pytest. TypeScript, Next.js, React, zod, Tailwind CSS, Vitest, Playwright. Docker and Google Cloud Run. An ESP32 with a MAX30102 pulse oximeter for the suit sensor. NASA JPL Horizons, NASA Deep Space Network Now and the NASA Open Science Data Repository for data.

## Use of Super Intelligence (SI)

Yes. AI assistants (Claude and Claude Code, from Anthropic) were used as tools to draft designs and build plans, to write and review code and tests, to check data and references, and to write documentation. Every use on the backend is logged with its date and purpose in `AI_USE.md` in that repository. The seeded generator that produced the simulated mission month was written with an assistant; its output is labelled simulated wherever it appears. The idea, the design decisions and the review of every result are the team's.

The application itself uses no AI. No language model is called while it runs, and no trained model makes or changes a decision: alerts come from fixed rules and simple statistics. The sentence the ship speaks is built from fixed templates and read aloud by the browser's built-in speech synthesis.

The figures in the documentation are plots of the project's own data, drawn by scripts written with an assistant. Any generated image or video added to the demo must carry a visible watermark, as the submission guide requires.

## NASA Data

NASA data is the core of the project: the delay that drives every screen is a NASA number.

- **NASA JPL Horizons** (https://ssd.jpl.nasa.gov/horizons/). The one-way light time between Mars and Earth, asked live for the mission date (observer quantity 21). It sets the delay on every message, who decides, and what the ship says. For 14 November 2026 it is 660.86 seconds.
- **NASA Deep Space Network Now** (https://eyes.nasa.gov/apps/dsn-now/). The round-trip light time the network reports for spacecraft at Mars, shown on the Earth console beside the Horizons figure as an independent check. On 15 November the two were 1.6 seconds apart.
- **NASA Open Science Data Repository, Environmental Data App**, mission Rodent Research 1 on the International Space Station (https://visualization.osdr.nasa.gov/eda/). Cabin carbon dioxide, temperature and humidity on the station strip are this record, replayed.
- **NASA Human Research Program risk list** (https://www.nasa.gov/hrp/risks/). The risk named on each alert.
- **NASA analog mission NEEMO 16**, as reported by Rader and colleagues (2013, NASA Technical Reports Server 20130011552). The basis for handing the lead to the crew medical officer at a delay of five minutes or more.
- **NASA-STD-3001 and the technical briefs of NASA's Office of the Chief Health and Medical Officer**. Background for the console's daily rules. The cabin carbon dioxide levels (2.8 and 4.5 mmHg) are in these documents; the other trigger values are the project's own design choices.

## Space Agency Partner Data and Other References

Canadian Space Agency: the report "Canadian Healthcare in Deep Space" (2019) and the 2023 Topical Teams report were read as background on autonomous medical care. No Canadian Space Agency measurements are used in the app.

Recordings used to test the rules, with their licences:

- University of Washington induced-hypoxemia oximeter recordings (Hoffman et al., 2022), MIT licence.
- Apnea-ECG Database on PhysioNet (Penzel et al., 2000), Open Data Commons Attribution License 1.0.
- PPG-DaLiA wrist recordings (Reiss et al., 2019), CC BY 4.0.

Open-source software: Flask, Flask-SQLAlchemy, Flask-Cors, gunicorn, psycopg, python-dotenv, requests, pytest; Next.js, React, zod, Tailwind CSS, Radix UI, shadcn/ui, lucide-react, Biome, Vitest, Testing Library, Playwright.

References:

Each entry was opened at its publisher, NASA, PhysioNet, UCI or a DOI record on 15 November 2026.

1. Alavi A, Bogu GK, Wang M, et al. (2022). Real-time alerting system for COVID-19 and other stress events using wearable data. Nature Medicine 28(1): 175-184. https://doi.org/10.1038/s41591-021-01593-2
2. Antonsen E, Bayuse T, Blue R, et al. (2017). Evidence Report: Risk of Adverse Health Outcomes and Decrements in Performance due to In-Flight Medical Conditions. NASA Human Research Program, Exploration Medical Capabilities Element, Johnson Space Center. https://ntrs.nasa.gov/citations/20170004604
3. Badger J, Higbee D, Kennedy T, et al. (2018). Spacecraft Dormancy Autonomy Analysis for a Crewed Martian Mission. NASA/TM-2018-219965. https://ntrs.nasa.gov/citations/20180005514
4. Bureau International des Poids et Mesures. SI defining constants. https://www.bipm.org/en/measurement-units/si-defining-constants (read 15 November 2026).
5. Canadian Space Agency (2019). Canadian Healthcare in Deep Space: Advancing our country's leadership in autonomous care in space and on Earth. Report of the Expert Group on the Potential Canadian Healthcare and Biomedical Roles for Deep-Space Human Spaceflight. https://asc-csa.gc.ca/eng/publications/canadian-healthcare-in-deep-space.asp
6. Canadian Space Agency (2025). Science Community Topical Teams 2023 Report on Space Astronomy, Planetary Science and Astronaut Health. https://open.canada.ca/data/en/dataset/520fe919-0868-4086-ba3f-1964b80ec26c (Open Government Licence - Canada).
7. Canadian Space Agency. Why do we conduct science experiments in space? https://asc-csa.gc.ca/eng/iss/science/why-do-we-conduct-science-experiments-in-space.asp (modified 28 October 2025).
8. Drew BJ, Harris P, Zègre-Hemsey JK, et al. (2014). Insights into the problem of alarm fatigue with physiologic monitor devices: a comprehensive observational study of consecutive intensive care unit patients. PLoS ONE 9(10): e110274. https://doi.org/10.1371/journal.pone.0110274
9. Giorgini JD and JPL Solar System Dynamics Group. NASA/JPL Horizons On-Line Ephemeris System. https://ssd.jpl.nasa.gov/horizons/ (data retrieved 15 November 2026).
10. Görges M, Markewitz BA, Westenskow DR (2009). Improving alarm performance in the medical intensive care unit using delays and clinical context. Anesthesia and Analgesia 108(5): 1546-1552. https://doi.org/10.1213/ane.0b013e31819bdfbb
11. Hoffman JS, Viswanath VK, Tian C, Ding X, Thompson MJ, Larson EC, Patel SN, Wang EJ (2022). Smartphone camera oximetry in an induced hypoxemia study. npj Digital Medicine 5(1): 146. https://doi.org/10.1038/s41746-022-00665-y. Data: https://github.com/ubicomplab/oximetry-phone-cam-data (MIT licence).
12. Kendall MG (1938). A new measure of rank correlation. Biometrika 30(1-2): 81-93. https://doi.org/10.1093/biomet/30.1-2.81
13. Lemery J, MacNeill K, Fleming N, Easter B, Marchica A, Berens KL, Lehnhardt K (2024). Earth Independent Medical Operations (EIMO) Definition Workshop. NASA/TM-20240002454. https://ntrs.nasa.gov/citations/20240002454
14. Levin DR, Steller J, Anderson A, Lemery J, Easter B, Hilmers DC, Lehnhardt KR (2023). Enabling Human Space Exploration Missions Through Progressively Earth Independent Medical Operations (EIMO). IEEE Open Journal of Engineering in Medicine and Biology 4: 162-167. https://doi.org/10.1109/OJEMB.2023.3255513
15. Mishra T, Wang M, Metwally AA, et al. (2020). Pre-symptomatic detection of COVID-19 from smartwatch data. Nature Biomedical Engineering 4(12): 1208-1220. https://doi.org/10.1038/s41551-020-00640-6
16. NASA (2012). Fault Management Handbook. NASA-HDBK-1002, Draft 2, 2 April 2012 (not approved). https://nasa.gov/wp-content/uploads/2015/04/636372main_NASA-HDBK-1002_Draft.pdf
17. NASA (2023). NASA Spaceflight Human-System Standard, Volume 1: Crew Health. NASA-STD-3001, Volume 1, Revision C. https://www.nasa.gov/reference/nasa-std-3001v1/
18. NASA (2026). NASA Spaceflight Human-System Standard, Volume 2: Human Factors, Habitability, and Environmental Health. NASA-STD-3001, Volume 2, Revision F. https://www.nasa.gov/reference/nasa-std-3001v2/
19. NASA Community Coordinated Modeling Center. Space Weather Database Of Notifications, Knowledge, Information (DONKI). https://ccmc.gsfc.nasa.gov/tools/DONKI/ (read 15 November 2026).
20. NASA Human Research Program. Hazard: Distance From Earth. https://www.nasa.gov/hrp/hazard-distance-from-earth/ (modified 1 August 2024).
21. NASA Human Research Program. Risks of Human Spaceflight. https://www.nasa.gov/hrp/risks/ (read 15 November 2026).
22. NASA Jet Propulsion Laboratory. Astrodynamic Parameters. https://ssd.jpl.nasa.gov/astro_par.html (read 15 November 2026).
23. NASA Jet Propulsion Laboratory. Deep Space Network Now. https://eyes.nasa.gov/apps/dsn-now/ (data feed https://eyes.nasa.gov/dsn/data/dsn.xml, read 15 November 2026).
24. NASA Office of the Chief Health and Medical Officer (2023). Environmental Control and Life Support System (ECLSS): Human-Centered Approach. OCHMO-TB-002, Revision B. https://www.nasa.gov/wp-content/uploads/2023/12/ochmo-tb-002-eclss.pdf
25. NASA Office of the Chief Health and Medical Officer (2023). Exercise Overview. OCHMO-TB-031. https://www.nasa.gov/wp-content/uploads/2023/12/ochmo-tb-031-exercise-overview.pdf
26. NASA Office of the Chief Health and Medical Officer (2025). Design for Ionizing Radiation Protection. OCHMO-TB-020, Revision G. https://www.nasa.gov/wp-content/uploads/2023/12/ochmo-tb-020-radiation-protection.pdf
27. NASA Office of the Chief Health and Medical Officer. Bone Loss. OCHMO-MTB-013, Revision D. https://www.nasa.gov/wp-content/uploads/2026/02/ochmo-mtb-013-bone-loss.pdf
28. NASA Office of the Chief Health and Medical Officer. Carbon Dioxide (CO2). OCHMO-TB-004, Revision D. https://www.nasa.gov/wp-content/uploads/2023/12/ochmo-tb-004-carbon-dioxide.pdf
29. NASA Open Science Data Repository. Environmental Data App (EDA), mission RR-1 (Rodent Research 1). https://visualization.osdr.nasa.gov/eda/ (read 15 November 2026).
30. NASA Space Science Data Coordinated Archive (2024). Moon Fact Sheet. https://nssdc.gsfc.nasa.gov/planetary/factsheet/moonfact.html
31. NASA Space Science Data Coordinated Archive (2025). Mars Fact Sheet. https://nssdc.gsfc.nasa.gov/planetary/factsheet/marsfact.html
32. Penzel T, Moody GB, Mark RG, Goldberger AL, Peter JH (2000). The Apnea-ECG Database. Computers in Cardiology 27: 255-258. https://doi.org/10.1109/CIC.2000.898505. Data: Apnea-ECG Database v1.0.0, PhysioNet, https://doi.org/10.13026/C23W2R (Open Data Commons Attribution License v1.0).
33. Pollard T, Moody BE, Lehman L-wH, Gow BJ, Fernandes C, Xie C, Johnson A, Mark RG, Heldt T (2026). PhysioNet as a global platform for biomedical research. Nature Health 1(8): 792-795. https://doi.org/10.1038/s44360-026-00096-z
34. Rader SN, Reagan ML, Janoiko B, Johnson JE (2013). Human-in-the-Loop Operations over Time Delay: NASA Analog Missions Lessons Learned. 43rd International Conference on Environmental Systems, Vail, Colorado. AIAA 2013-3520. https://doi.org/10.2514/6.2013-3520. Full text: https://ntrs.nasa.gov/citations/20130011552
35. Reiss A, Indlekofer I, Schmidt P, Van Laerhoven K (2019). Deep PPG: Large-Scale Heart Rate Estimation with Convolutional Neural Networks. Sensors 19(14): 3079. https://doi.org/10.3390/s19143079. Data: PPG-DaLiA, UCI Machine Learning Repository, https://doi.org/10.24432/C53890 (CC BY 4.0).
36. Rousseeuw PJ, Leroy AM (1987, reprinted 2003). Robust Regression and Outlier Detection. New York: Wiley. Pages 67 and 164 give the breakdown point of the median-of-slopes line.
37. Royal College of Physicians (2017). National Early Warning Score (NEWS) 2: Standardising the assessment of acute-illness severity in the NHS. Updated report of a working party. London: RCP. https://www.rcp.ac.uk/improving-care/resources/national-early-warning-score-news-2/
38. Sen PK (1968). Estimates of the regression coefficient based on Kendall's tau. Journal of the American Statistical Association 63(324): 1379-1389. https://doi.org/10.1080/01621459.1968.10480934
39. Theil H (1950). A rank-invariant method of linear and polynomial regression analysis, I, II and III. Proceedings of the Koninklijke Nederlandse Akademie van Wetenschappen 53: 386-392, 521-525, 1397-1412.
40. Valinia A, Allen JR, Francisco DR, Minow JI, Pellish JA, Vera AH (2022). Safe Human Expeditions Beyond Low Earth Orbit (LEO). NASA/TM-20220002905, NESC-RP-20-01589. https://ntrs.nasa.gov/citations/20220002905

## Checklist before "Submit for Judging"

The deadline is Sunday 15 November 2026 at 23:59 local time. Anything saved or submitted later is not judged. The project can be edited and resubmitted until then; only the last saved submission counts.

- [ ] Both repositories are public, and each link above opens in a private browser window with no sign-in.
- [ ] The demo is a slide deck of at most seven slides, title and introduction included, or a video of at most 30 seconds. A longer one makes the project ineligible for global judging.
- [ ] The slides name the team, the team members and the challenge, show the project, and say how NASA data makes it possible.
- [ ] The demo link opens in a private browser window with no sign-in.
- [ ] Every required field on the project page is filled in, in English.
- [ ] The References field lists every outside source, including code and images.
- [ ] No image, video or audio shows or sounds like a person under 18.
- [ ] Nothing in the project uses or alters NASA logos, flags or mission identifiers.
- [ ] The deployment write-up shared inside the team is not linked from the project page as it stands: it lists a home network address beside a person's name. Remove that line first.
- [ ] Both boxes are ticked: the terms and conditions, and the confirmation that all work is original.
- [ ] "Submit for Judging" is pressed, and the confirmation banner appears.

## How the project meets the five judging criteria

| Criterion | Where LIGHT-TIME answers it |
|---|---|
| Impact | Medical care for a crew that Earth cannot reach in time is an open problem for every mission past the Moon. The same software runs at the station, the Moon and Mars |
| Creativity | The communication delay is an input the software computes with: it turns an alarm into a deadline and says who can meet it |
| Validity | Fixed rules from a published chart, a robust statistical estimator, real recordings for every rule, held-out testing, 192 automated tests, and stated limits |
| Relevance | The delay on every message is a live NASA JPL Horizons figure checked against the Deep Space Network; the cabin readings are a NASA record |
| Presentation | One dial and one sentence carry the idea. The story plays the same way every time from a fixed morning |
