# Deployment tutorial

How to run LIGHT-TIME in three places: on a laptop, in Docker, and on Google Cloud Run. Part A is what the pitch uses. Part C is for the hosted copy that the project page links to.

Every Google Cloud command in part C comes from `docs/deployment-commands.md`, where each one sits beside the Google documentation page it was checked against, with a list of what could not be confirmed. Nothing in part C was run against the team's real project: the deployment owner runs it.

Two rules hold everywhere, and both come from how the ship is built.

1. **One process.** The mission clock and the story live in the memory of one Python process. Two processes means two clocks.
2. **Never put a secret in a command, a file in git, or a document.** The database address goes in a git-ignored `.env` on a laptop and in Secret Manager on Google Cloud.

## Part A. On a laptop

You need Python 3.12 or newer, Node.js 22 or newer, and git. The two repositories sit side by side.

### A1. The ship

Windows PowerShell, in `LightTime-backend`:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
$env:DATABASE_URL = 'sqlite:///lighttime.db'; $env:LIGHTTIME_MORNING = '1'; python app.py
```

macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
DATABASE_URL=sqlite:///lighttime.db LIGHTTIME_MORNING=1 python app.py
```

Setting `DATABASE_URL` on the command line matters. The app also reads `.env`, and a value given on the command line wins, so a `.env` that still points at the hosted database cannot send a local run there.

Check it in a second window:

```powershell
irm http://localhost:5000/api/base/state | Select-Object stop, delay_s, mission_day, now
```

Expected: `mars`, `660.86`, `158`, and a `now` that starts `2026-11-14T06:30`. If the delay's source reads "read on 2026-11-13", the laptop could not reach NASA JPL and is using the stored figure for the day, which is the same number.

### A2. The console

In `LightTime-frontend`, create a file named `.env.local` holding one line:

```
NEXT_PUBLIC_API_URL=http://localhost:5000
```

Then:

```powershell
corepack pnpm install
corepack pnpm dev
```

Open http://localhost:3000. The header should read "Earth is 11 min 1 s away". If it reads "Ship unreachable: built-in demo", the ship is not running or the address in `.env.local` is wrong. With no `.env.local` at all the console runs on its built-in demo data and never asks for a ship.

### A3. Check everything

```powershell
# in LightTime-backend
$env:DATABASE_URL = 'sqlite:///:memory:'; python -m pytest -q
# in LightTime-frontend
corepack pnpm typecheck; corepack pnpm lint; corepack pnpm test
```

Expected: `192 passed` for the backend (196 after the backend finish plan), and no errors from the three console checks.

### A4. Driving the demo

1. Press "Restart demo", then "Sound on". Speech is blocked by browsers until a click, and that click is it.
2. Move the dial across its four stops and back to Mars.
3. Open the first alert, acknowledge it, send it. Open "Earth" in a second window, wait 11 seconds, reply. Back on the ship, accept the plan.
4. Press "Start story". The early warning is spoken after about half a minute and the SOS about 13 seconds later.
5. Before a second run, reload the tab and press "Restart demo" (not needed once both finish plans are in).

To let a phone or a suit sensor on the same Wi-Fi reach the ship, use the laptop's network address in place of `localhost` (the ship prints it when it starts) and allow Python through the firewall when Windows asks.

## Part B. In Docker

Docker shows that the images the host will build do start. Build and run each from its own repository.

```bash
# in LightTime-backend
docker build -t lighttime-backend .
docker run --rm -p 8080:8080 -e LIGHTTIME_MORNING=1 lighttime-backend
```

With no `DATABASE_URL` the ship keeps its data in a SQLite file inside the container, which is all the demo needs: it reloads the demo morning at every start. Check it at http://localhost:8080/api/base/state.

```bash
# in LightTime-frontend
docker build --build-arg NEXT_PUBLIC_API_URL=http://localhost:8080 -t lighttime-console .
docker run --rm -p 3000:8080 lighttime-console
```

Open http://localhost:3000. The ship's address is read when the console is **built**, not when it runs, so it is a build argument. Built with no argument, the image is the built-in demo. Built with `/`, the console asks for the ship at its own address, which is what part C sets up.

## Part C. On Google Cloud Run

The team's project already has both services, a load balancer with a fixed address that points at the console, and automatic deploys on every merge to `main`. What is missing for a live hosted copy is four settings. Until they are made, the hosted console shows its built-in demo, which is a safe thing to link from the project page.

Run the commands in Cloud Shell, which avoids quoting differences between PowerShell and bash. Replace the words in capitals. The full version of every step, with alternatives, is in `docs/deployment-commands.md` under the section number given.

### C1. One always-on instance for the ship (section 4)

```bash
gcloud run services update BACKEND_SERVICE --region=REGION \
  --scaling=1 --no-cpu-throttling --cpu=1 --memory=512Mi \
  --update-env-vars=LIGHTTIME_MORNING=1
```

`--scaling=1` keeps exactly one instance, so there is one clock. `--no-cpu-throttling` is instance-based billing: the story's thread sends a reading every second whether or not a page is open, and with the default billing the processor is taken away between requests and the story stalls. The image must also start one worker, which is pull request #7.

Three things one instance does not promise: a deploy runs a second instance for a moment, the instance can be restarted at any time, and each restart puts the mission clock back to 06:30. So do not merge to the backend's `main` during the pitch.

### C2. The database: use none (section 6)

The simplest setup that works is no database service. With no `DATABASE_URL` the ship writes a small SQLite file inside its instance. Cloud Run's file system is writable and held in memory; the file is about 0.1 MB after the morning loads and grows about 1.5 MB an hour while a story runs. Losing it on a restart changes nothing, because the ship reloads the demo morning at every start on any database.

```bash
gcloud run services update BACKEND_SERVICE --region=REGION --remove-env-vars=DATABASE_URL
```

If `DATABASE_URL` was set as a secret, use `--remove-secrets=DATABASE_URL` instead.

If Postgres is kept, the newest revision may fail to start against tables made before 14 November 22:03, when the table shapes changed. Cloud Run then keeps serving the older revision with no error on the site. The fix is to drop the demo tables once, from an address the database allows, which only the deployment owner can do. Section 6 of the command sheet has the Cloud SQL route and the `DATABASE_URL` form for it.

### C3. One address for both: `/api/*` to the ship (section 7)

A browser cannot reach the ship today. The clean fix keeps one address: the load balancer sends `/api/*` to the ship and everything else to the console.

```bash
# let the load balancer, and only it, reach both services
gcloud run services update BACKEND_SERVICE  --region=REGION --ingress=internal-and-cloud-load-balancing
gcloud run services update FRONTEND_SERVICE --region=REGION --ingress=internal-and-cloud-load-balancing

# find the names of the existing parts
gcloud compute url-maps list
gcloud compute backend-services list

# a serverless endpoint group and a backend service for the ship
gcloud compute network-endpoint-groups create lighttime-api-neg \
  --region=REGION --network-endpoint-type=serverless --cloud-run-service=BACKEND_SERVICE
gcloud compute backend-services create lighttime-api-bs --load-balancing-scheme=EXTERNAL_MANAGED --global
gcloud compute backend-services add-backend lighttime-api-bs --global \
  --network-endpoint-group=lighttime-api-neg --network-endpoint-group-region=REGION

# the rule
gcloud compute url-maps add-path-matcher URL_MAP_NAME \
  --path-matcher-name=lighttime-paths \
  --default-service=FRONTEND_BACKEND_SERVICE \
  --path-rules="/api/*=lighttime-api-bs" \
  --new-hosts="*" --global
```

These commands are for a global external Application Load Balancer. If `gcloud compute backend-services describe FRONTEND_BACKEND_SERVICE --global` fails, the load balancer is regional and section 7.8 of the command sheet has the regional form. The ship must also accept requests without sign-in (section 7.1).

Check it:

```bash
curl -i http://LOAD_BALANCER_IP/api/base/health
curl -s http://LOAD_BALANCER_IP/api/base/state | head -c 300
```

### C4. Build the console with the ship's address (section 3)

The console reads the ship's address at build time, and the click-through deploy builds the Dockerfile with no build arguments. So the console's trigger needs a `cloudbuild.yaml` that passes one. The complete file is in section 3.2 of the command sheet; its heart is one line:

```yaml
      - '--build-arg'
      - 'NEXT_PUBLIC_API_URL=${_NEXT_PUBLIC_API_URL}'   # set to '/' in substitutions
```

Add the file to the root of `LightTime-frontend`, point the existing trigger at it (section 3.3), and run the trigger once.

### C5. Check the hosted copy

```bash
for i in 1 2 3 4 5 6 7 8 9 10; do curl -s http://LOAD_BALANCER_IP/api/base/state | grep -o '"now":"[^"]*"'; sleep 1; done
```

Each `now` must be later than the one before. If one goes backwards, two instances or two workers are answering: recheck C1 and that pull request #7 is merged. Then open the site: the header must show "Earth is 11 min 1 s away" and the dial.

A hosted ship is one ship. Everyone who opens the site shares the same dial and the same story, and each open page asks the ship eight times a second. For judging, either leave the hosted console as the built-in demo, or accept that visitors share one ship.

### C6. Logs and going back (section 8)

```bash
gcloud run services logs read BACKEND_SERVICE --region=REGION --limit=50
gcloud run revisions list --service BACKEND_SERVICE --region=REGION
gcloud run services update-traffic BACKEND_SERVICE --region=REGION --to-revisions REVISION=100
```

A revision that fails to start gets no traffic and the one before it keeps serving, so a site that looks fine can be a version behind. After every deploy, read the revision list and check the newest is the one serving.

### C7. What it costs (section 9)

One always-on instance at 1 vCPU and 512 MiB is about 1.64 US dollars a day in a Tier 1 region such as `us-central1` and about 1.97 in Toronto or Montreal, before the free allowance. The console can stay on default billing and costs nothing while idle. With no database service there is no database charge. Turn `--no-cpu-throttling` off, or delete the service, when judging is over.

## When something is wrong

| What you see | Likely cause | What to do |
|---|---|---|
| "Ship unreachable: built-in demo" on a laptop | The ship is not running, or `.env.local` has the wrong address | Start the ship; check the address; restart `pnpm dev` after changing `.env.local` |
| `python app.py` fails at start with a database error | `.env` holds the hosted database's address | Start with `$env:DATABASE_URL='sqlite:///lighttime.db'` as in A1 |
| Nothing is spoken | Sound is off, or the tab already spoke for this alert | Press "Sound on"; reload the tab before a second run |
| A second story raises no alert | The first story's SOS is still open | Press "Restart demo" first (fixed by the backend finish plan) |
| The story stalls on the host when no page is open | Default billing takes the processor away between requests | C1: `--no-cpu-throttling` |
| `now` goes backwards between two requests, or the demo empties itself | Two workers or two instances | Merge pull request #7; C1: `--scaling=1` |
| The hosted site works but new fields are missing | The newest revision failed to start and the old one is serving | C6: list revisions; C2: remove `DATABASE_URL` or drop the old tables |
| The hosted console shows the built-in demo | It was built with no ship address, or `/api/*` is not routed | C3 and C4 |
| The light time's source says "read on 2026-11-13" | The host has no way out to the internet | Nothing: the stored NASA figure for the day is used and labelled |
