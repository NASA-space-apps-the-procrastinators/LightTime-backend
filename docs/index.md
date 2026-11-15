# LIGHT-TIME documentation

Every document in this repository, grouped by who it is for. The project in one line: crew health monitoring software that knows how far away Earth is, and tells the crew who has to act.

## Start here

| Document | For | What it holds |
|---|---|---|
| [README](../README.md) | anyone | What it is, the live links, how to run it in five minutes |
| [Concept](concept.md) | judges, reviewers, anyone new | The idea, the words, the math and a glossary |
| [How it works](how-it-works.md) | reviewers | The evidence from real recordings and what it does not show |
| [Submission text](submission.md) | the team captain | Copy-ready text for each field of the project page, and the checklist |

## Build and run

| Document | For | What it holds |
|---|---|---|
| [Architecture](tech/architecture.md) | developers, reviewers | Hosting, the parts, the tables, the path of one reading, the life of an alert, the mission clock and the link |
| [API reference](tech/api.md) | console developers | Every route and an example answer, generated from the running app |
| [LIGHTTIME in the code](tech/ship-ai.md) | developers | Where each rule lives and its settings |
| [Data](tech/data.md) | developers, reviewers | Each dataset, its licence, what the ship may read, how to rebuild and check it |
| [Security and privacy](tech/security-privacy.md) | reviewers, judges | What is protected, what is not, and what a real deployment would add |
| [Testing](tech/testing.md) | developers | How to run the 236 tests and what each file covers |
| [Operations](tech/operations.md) | whoever runs the demo or the hosting | Health, reset, the story, the dial, the vitals feed, logs, roll back, common faults |
| [Deployment tutorial](deployment.md) | whoever deploys | A laptop, Docker and Google Cloud Run, step by step |
| [Deployment commands](deployment-commands.md) | whoever deploys | Each `gcloud` command beside the Google page it was checked against |
| [Sending suit readings](hardware.md) | hardware | How the prototype suit sensor posts one reading a second |
| [Console client](frontend/README.md) | console developers | The typed client and polling hook the console can copy |
| [Word list](../CONTEXT.md) | developers | The words the code and the documents use |
| [AI use log](../AI_USE.md) | anyone | Each use of an AI assistant on the backend: date, who, tool, what for |

## Decisions

| ADR | Decision |
|---|---|
| [0001](adr/0001-rules-decide-learned-models-advise.md) | Rules decide; a learned model may only advise |
| [0002](adr/0002-one-process-holds-the-clock.md) | One process holds the mission clock |
| [0003](adr/0003-sqlite-inside-the-instance.md) | The hosted ship keeps its tables in SQLite inside its one instance |
| [0004](adr/0004-the-viewer-header-is-a-view-not-a-login.md) | The viewer header shapes a view; it is not a login |
| [0005](adr/0005-long-legs-play-sixty-times-faster.md) | Legs of a minute or more play sixty times faster |

## History

These were written while the system was built and are kept as they were. Where they disagree with the code, the code and the pages above are right.

| Date | Kind | Document |
|---|---|---|
| 14 Nov | spec | [Backend design and API contract](specs/2026-11-14-backend-design.md) (the API table the console builds against) |
| 14 Nov | spec | [Console data](specs/2026-11-14-console-data-design.md), [console link](specs/2026-11-14-console-link-design.md), [data sources](specs/2026-11-14-data-sources-design.md), [LIGHTTIME](specs/2026-11-14-lighttime-ai-design.md), [ship AI and data](specs/2026-11-14-ship-ai-and-data-design.md), [suit data](specs/2026-11-14-suit-data-design.md) |
| 14 Nov | plan | [Backend Saturday](build-log/plans/2026-11-14-backend-saturday.md), [tonight's integration](build-log/plans/2026-11-14-tonight-integration.md), [console contract](build-log/plans/2026-11-14-console-contract.md), [ship AI and data](build-log/plans/2026-11-14-ship-ai-and-data.md), [connect everything](build-log/plans/2026-11-14-connect-everything.md) |
| 14 Nov | review | [Dataset review](build-log/reviews/2026-11-14-dataset-review.md) |
| 15 Nov | spec | [Finish](specs/2026-11-15-finish-design.md), [demo day](specs/2026-11-15-demo-day-design.md), [final fix](specs/2026-11-15-final-fix-design.md), [hosted site](specs/2026-11-15-hosted-site-design.md), [secure backend (archived draft, not built)](specs/2026-11-15-secure-backend-design.md) |
| 15 Nov | plan | [Backend finish](build-log/plans/2026-11-15-backend-finish.md), [final fix](build-log/plans/2026-11-15-final-fix.md), [backend polish](build-log/plans/2026-11-15-backend-polish.md), [tonight](build-log/plans/2026-11-15-tonight.md), [hosted site](build-log/plans/2026-11-15-hosted-site.md), [one shot](build-log/plans/2026-11-15-one-shot.md), [mega prompt](build-log/plans/2026-11-15-backend-mega-prompt.md) |
| 15 Nov | plan | Documentation: [overview](build-log/plans/2026-11-15-docs-00-overview.md), [A, concept](build-log/plans/2026-11-15-docs-a-concept.md), [B, paper](build-log/plans/2026-11-15-docs-b-paper.md), [C, technical](build-log/plans/2026-11-15-docs-c-technical.md) |
| 15 Nov | review | [Overnight review](build-log/reviews/2026-11-15-overnight-review.md) |
| 15 Nov | handoff | [Frontend tasks](build-log/handoff/2026-11-15-frontend-tasks.md), [console finish plan](build-log/handoff/2026-11-15-console-finish-plan.md), [console README tasks](build-log/handoff/2026-11-15-console-readme.md) |
| 15 Nov | moved | [Project documentation](project-documentation.md), [data sources](data-sources.md), [data verification](data-verification.md), [system](system.md): older pages, now pointers or sources for the pages above |
