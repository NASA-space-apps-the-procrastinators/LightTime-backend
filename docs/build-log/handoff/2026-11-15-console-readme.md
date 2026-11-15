# Console README: tasks for the console owner

Date: 15 November 2026. From the backend's documentation lane (Plan C, Task C10). Nothing here has been changed in the console repository; each item is for the console owner to do or decline.

The console's README today has two sections, "Code Organization" and Docker and Cloud Run instructions. A judge or a new developer who opens the repository needs more than that. Below is what the README should say, with the facts checked against the backend and against the console files the backend team had a copy of (`Dockerfile`, `package.json`, `src/components/shared/tour.tsx`, `src/components/base-station/app-header.tsx`, `src/lib/ship-api.ts`). Check each against the console's current `main` before pasting.

## 1. What the README should contain

**What it is.** One sentence, the same as the backend's: LIGHT-TIME is crew health monitoring software that knows how far away Earth is. Then: this repository is the crew console and the Earth console, a Next.js app that reads the ship's API in the `LightTime-backend` repository once a second. Link the live site (https://lighttime.health) and the backend repository.

**The two sides.**

| Route | Who it is for | What it shows |
|---|---|---|
| `/base-station` | the crew | The dial, the crew cards, alerts and their round trip, the check-in, the health log, the cabin |
| `/command-center` | the flight surgeon on Earth | Only what the delayed link has delivered: cases, threads, the vitals feed, the reply box |

`/` redirects to `/base-station`.

**Run it against a ship on your laptop.** Start the backend (`LIGHTTIME_MORNING=1 python app.py` in `LightTime-backend`), then in this repository:

    echo NEXT_PUBLIC_API_URL=http://localhost:5000 > .env.local
    corepack pnpm install
    corepack pnpm dev

Open http://localhost:3000. The header should read "Earth is 11 min 1 s away". The address is read when the console starts, so restart `pnpm dev` after changing it. On a Mac, port 5000 belongs to AirPlay: run the ship on another port and use that port here.

**Run it against the live ship.** Put `NEXT_PUBLIC_API_URL=https://lighttime.health` in `.env.local` instead. Everyone who opens the live site shares one demo ship, so a reset from your laptop resets it for the judges too.

**With no ship.** With no `NEXT_PUBLIC_API_URL` the console runs its built-in demo and never asks for a ship. The header then says "Ship unreachable: built-in demo".

**The build argument.** The ship's address is read when the console is built, not when it runs, so the `Dockerfile` takes it as a build argument:

| `NEXT_PUBLIC_API_URL` at build time | The built console |
|---|---|
| empty | the built-in demo |
| `/` | asks for the ship at its own address (the hosted site, where the load balancer sends `/api/*` to the ship) |
| a full address | asks for the ship there |

The copy of the `Dockerfile` the backend team saw defaults to `https://lighttime.health`. Say which default `main` uses, and how the Cloud Build trigger passes the argument (the hosted-site plan adds a `cloudbuild.yaml` for this).

**The tour.** The Start story button in the header (`src/components/base-station/app-header.tsx`) opens a click-through tour of the screens (`src/components/shared/tour.tsx`) that ends with a live emergency at Mars distance. Its stops run from "How far away is Earth?" to "Now see why it matters". Say how to add or change a stop.

**The vitals feed.** If the console has a Start suits control, say that it calls `POST /api/earth/feed/start` on the ship, which sends one reading per crew member to Earth every 120 seconds by default, labelled simulated, and that `POST /api/earth/feed/stop` stops it. The backend team could not find this control in its copy of the console.

**Who is looking.** The ship has role-based views: a request that names a crew member in the `X-LightTime-Viewer` header gets that person's record in full and name cards for the others, and the crew medical officer (C2) gets everything. The copy of `src/lib/ship-api.ts` the backend team saw never sends the header, so every screen gets the medical station's view. Either send it from a "who is looking" picker, or say in the README that the console shows the medical station's view. Do not call it a login: nothing proves who is at the screen ([security and privacy](../../tech/security-privacy.md)).

**Tests and checks.** From `package.json`:

    corepack pnpm typecheck
    corepack pnpm lint
    corepack pnpm test        # Vitest
    corepack pnpm e2e         # Playwright

Give the current test count, as the backend's README does.

**AI use and licence.** Say how AI assistants were used on the console, as the backend's `AI_USE.md` does. Add the licence the team chooses as a `LICENSE` file before the repository is made public.

## 2. Being found (technical SEO)

Checked on the live site on 15 November 2026, with `curl`. Lighthouse was not run.

| # | What was found | What to do |
|---|---|---|
| 1 | `/`, `/base-station` and `/command-center` all have the same `<title>` ("Light Time") and the same meta description ("Health monitoring for astronauts: body suit, dashboard, flight surgeon.") | Give each page its own title and description through Next.js `metadata`, for example "Crew console, LIGHT-TIME" and "Earth console, LIGHT-TIME". Use the project's own words: a smart shirt, not a body suit |
| 2 | The site calls itself "Light Time"; the submission and the backend say "LIGHT-TIME" | Pick one spelling for titles, `og:site_name` and the manifest |
| 3 | `og:title`, `og:description`, a 1200 by 630 `og:image` and a Twitter card are present | Update `og:description` with item 1. The `og:image:alt` text contains an em dash; the team's documents avoid them |
| 4 | A favicon and an Apple touch icon are present | Nothing to do |
| 5 | `/robots.txt` answers 404 | Add `robots.ts` in the app folder that allows crawling and names the sitemap |
| 6 | `/sitemap.xml` answers 404 | Add `sitemap.ts` in the app folder, listing `/base-station` and `/command-center` |
| 7 | `/` answers with a temporary redirect (307) to `/base-station` | Make it permanent (`permanent: true` in the redirect) or serve the crew console at `/` |
| 8 | No canonical link on any page | Set `metadataBase` to `https://lighttime.health` and a canonical URL per page |
| 9 | `<html lang="en">` and a viewport tag are present | Nothing to do |
| 10 | No structured data | Optional: a `SoftwareApplication` JSON-LD block on the crew console |
| 11 | Lighthouse not run | Run Lighthouse's SEO audit in Chrome DevTools on https://lighttime.health/base-station and add the score to this list |

For both repositories on GitHub: set the description to the README's first sentence, add the topics `nasa-space-apps`, `space-medicine`, `health-monitoring`, `flask`, `nextjs` and `light-time`, and upload the logo as the social preview image (1280 by 640).

## Found while writing the concept document

These come from reading the console code against the backend on 15 November. The backend is unchanged.

| # | What the console does | What to change |
|---|---|---|
| 12 | `src/data/crew-seed.json` sets `"mars_light_time_min": [4, 24]` | The submission and the concept document say about 3 to 22 minutes one way. Use the same range |
| 13 | The click-through tour (`src/components/shared/tour.tsx`, the flight surgeon step) says "The ship has already sent 7 days of readings" | The ship sends reports at each early warning and SOS, the routine vitals feed every two minutes once started, and a daily summary. Say that, or drop the number |
| 14 | The tour's live mode polls `GET /api/base/tour` | The backend no longer serves that route (the guided tour was reverted in 3c80901). Remove the live mode or the call |
| 15 | The console's API client sends no `X-LightTime-Viewer` header | Every screen gets the medical station's view. To show the role-based views, send the header for the person at the screen |
