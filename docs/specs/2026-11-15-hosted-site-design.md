# The hosted site, lighttime.health: what a judge gets when they open the link

Sunday 15 November 2026, 07:10. This spec covers the public copy at https://lighttime.health/. It changes no rule and adds no feature. The plan is `docs/build-log/plans/2026-11-15-hosted-site.md`. The commands behind it are in `docs/deployment-commands.md`, each beside the Google page it was checked against.

## 1. What was checked, and what was found

Checked from outside, at 07:00, by fetching pages without running their scripts. The site could not be opened in a real browser from here, so what a visitor sees after the scripts run is inferred from the code, not observed.

| Address | Result | What it means |
|---|---|---|
| `https://lighttime.health/` and `/base-station` | 200 over HTTPS. The page as delivered holds one line, "Loading console…", and the title "Light Time" | The console is up and the certificate works. Everything on it is drawn by scripts in the browser |
| `https://lighttime.health/command-center` | 200. It shows "Earth console", then "Set NEXT_PUBLIC_API_URL to the ship's address to open the Earth console", then instructions about `.env.local`, port 5001 and AirPlay on a Mac | The console was built with no ship address. It is the built-in demo. A visitor who reaches this page reads instructions meant for a developer |
| `https://lighttime.health/api/base/state` and `/api/base/health` | Refused with a client error | The load balancer does not send `/api/*` to the ship. No browser can reach the ship |
| Backend `main` | Pull requests #7 (one worker) and #9 (the backend work) were merged at 06:57 and 06:58 | The hosted ship should now be rebuilding from the right code. Whether its newest revision started is not known |
| Console `main` | The hosted Earth page carries wording that is not in `feat/live-ship` at `05ac88c` | The console's `main` has moved past the copy on the backend owner's laptop. Fetch before applying anything |

## 2. Problem

The link on the project page is the app a judge will open, alone, after the pitch. Today that link is the built-in demo. In the built-in demo there is no dial, no "Start story", no LIGHTTIME card, no spoken sentence and no Earth console: those exist only when the console can reach a ship. So the hosted site shows a crew health dashboard and none of the idea the project is about.

Three things stand between the site and the real app, and all three are settings, not code: the ship cannot be reached from a browser, the console was built without the ship's address, and nobody has confirmed the ship runs as one instance that keeps its processor between requests.

## 3. Goals

1. A visitor to https://lighttime.health/ sees the header "Earth is 11 min 1 s away", can move the dial, start the story and open the Earth console.
2. The ship behind it has one clock: ten reads of its time in a row only go forward.
3. A visitor never reads developer instructions.
4. If the live site cannot be finished in time, the site is still safe to link and says honestly what it is.

## 4. Not goals

- A ship for each visitor. There is one ship. Everyone who opens the site shares its dial and its story.
- Sign-in, rate limits or any protection of the ship. It is a demo with simulated data and a restart button.
- Changing the domain, the certificate or the load balancer's address.

## 5. Decisions

**H1. Make the hosted site live, on one address.** The load balancer sends `/api/*` to the ship and everything else to the console, and the console is built with the ship's address `/`. One origin means no cross-site rules and no second address to publish.

**H2. The ship runs with no database service.** With no `DATABASE_URL` it keeps a small file inside its one instance and reloads the demo morning at every start. That removes the allowlist problem and the risk that a new revision cannot start against old tables. If the deployment owner prefers to keep Postgres, the tables made before 14 November 22:03 must be dropped once first.

**H3. One instance, processor always on, until judging is over.** About 1.64 to 1.97 US dollars a day. It is turned off when judging ends.

**H4. One shared ship is accepted, and said.** A visitor's restart or dial move changes what another visitor sees. For a handful of judges this is tolerable, and the story now restarts cleanly (backend finish plan, Task 1). The project page says in one line that the site is one live demo ship shared by everyone who opens it, and that "Restart demo" brings it back to the start.

**H5. With no ship, the Earth page speaks to a visitor.** Its message becomes: this copy is running the built-in demo, and the Earth console needs the live ship. The developer instructions move to the README.

**H6. The fallback is the built-in demo plus the video.** If `/api/base/health` does not answer through the site by 13:00, stop, leave the site as it is, and let the demo link carry the story. A half-live site is worse than an honest built-in one.

**H7. Nothing is merged to the backend's `main` between the last check and the end of the pitch.** Every merge redeploys the ship and puts its clock back to 06:30.

## 6. Requirements

**HR1. The ship is one always-on instance on the demo morning.** Plan Task 1.
- [ ] Given the service is described, then it shows one instance, processor not throttled, `LIGHTTIME_MORNING=1` and no `DATABASE_URL`.
- [ ] Given its newest revision is listed, then that revision is the one serving.

**HR2. The browser can reach the ship at the site's own address.** Plan Task 2.
- [ ] Given `https://lighttime.health/api/base/health` is asked, then it answers 200 with JSON.
- [ ] Given `/api/base/state` is asked ten times a second apart, then it says Mars, mission day 158, and each `now` is later than the one before.
- [ ] Given `https://lighttime.health/` is asked, then it is still the console.

**HR3. The console is built with the ship's address.** Plan Task 3.
- [ ] Given the site is opened in a browser, then the header reads "Earth is 11 min 1 s away" and shows the dial.
- [ ] Given "Earth" is opened, then it shows cases or "Loading", never the words `NEXT_PUBLIC_API_URL`.

**HR4. A visitor never reads developer instructions.** Plan Task 4.
- [ ] Given a console built with no ship address, when `/command-center` is opened, then it says the copy is the built-in demo and links back to the crew console.

**HR5. The whole loop works on the hosted site.** Plan Task 5.
- [ ] Given a laptop and a phone on different networks, then both show the same ship, the story plays with its early warning, a reply from the Earth page reaches the ship's thread, and "Restart demo" returns to 06:30.

## 7. Risks

| Risk | Sign | What to do |
|---|---|---|
| The ship's newest revision failed to start and the old one is serving | New fields missing, for example no `now` in `/api/base/state` | List revisions. Remove `DATABASE_URL` (H2) and deploy again |
| Two instances for a moment after a deploy | `now` goes backwards once, or the demo resets by itself | Wait a minute and check again. Do not deploy during the pitch (H7) |
| The load balancer is regional, not global | The global commands fail with "not found" | Use the regional forms in section 7.8 of the command sheet |
| The console's trigger ignores the new build file | The site still shows the built-in demo after a merge | Read the trigger with `gcloud builds triggers describe`. Build and deploy by hand once (plan Task 3, Step 4) |
| Several visitors at once | The dial moves by itself, the story restarts | Accepted (H4). It is one ship |
| Each open page asks the ship eight times a second | The ship's log scrolls fast; many open tabs slow it | One instance handles it for a few visitors. Close tabs left open on the pitch machine |

## 8. Open questions

- Deployment owner: is the load balancer global or regional, and what are the names of its URL map and of the console's backend service? Task 2 starts by finding out.
- Deployment owner: is the existing database a Cloud SQL instance, and do you want to keep it? H2 recommends not using one.
- Frontend owner: the console's `main` has changed since `05ac88c`. Is the Earth page's no-ship message yours to reword (HR4), or shall the backend owner send a change?

## 9. Time

Now is 07:10. Mentor hours are at 10:00 and 13:00, the pitch at 15:30, the submission closes at 23:59. Tasks 1 to 3 are about an hour for someone who knows the project's Google Cloud setup. H6 sets 13:00 as the point to stop and fall back. The site can also be made live after the pitch and before the submission, since judges open the link later.
