# Hosted Site Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make https://lighttime.health/ the real app: the console on the live ship, at one address, with one clock.

**Architecture:** Settings on Google Cloud and one build file, no change to the ship's code. The load balancer sends `/api/*` to the backend's Cloud Run service and the rest to the console's, and the console is built with the ship's address `/`. The spec is `docs/specs/2026-11-15-hosted-site-design.md`.

**Tech Stack:** Google Cloud Run, Cloud Build, an external Application Load Balancer, `gcloud` in Cloud Shell. Next.js for Task 4.

---

## Who does what

Tasks 1, 2 and 3 Steps 3 to 5 need access to the team's Google Cloud project: they are the deployment owner's. Task 3 Steps 1 and 2 and Task 4 are changes in the console repository. Task 5 is anyone with a browser and a phone.

Run every `gcloud` command in Cloud Shell. Replace the words in capitals: `PROJECT_ID`, `REGION`, `BACKEND_SERVICE`, `FRONTEND_SERVICE`, and the names Task 2 finds. Never paste a password or a database address into a command, a chat or a document.

Stop rule: if `https://lighttime.health/api/base/health` does not answer by 13:00, stop, undo nothing, and leave the site as the built-in demo (spec, decision H6).

Each command below is taken from `docs/deployment-commands.md`, where it sits beside the Google page it was checked against. None has been run on this project.

---

### Task 0: See what is serving now

- [ ] **Step 1: Ask the site three things, from any PowerShell**

```powershell
(iwr https://lighttime.health/ -UseBasicParsing).StatusCode
try { irm https://lighttime.health/api/base/health } catch { $_.Exception.Message }
(iwr https://lighttime.health/command-center -UseBasicParsing).Content -match 'NEXT_PUBLIC_API_URL'
```

Expected today: `200`, then an error (the ship is not reachable), then `True` (the console was built with no ship address). When this plan is done the three answers are `200`, a JSON answer, and `False`.

---

### Task 1: The ship is one always-on instance on the demo morning

- [ ] **Step 1: Set the project and look at the service**

```bash
gcloud config set project PROJECT_ID
gcloud run services list
gcloud run services describe BACKEND_SERVICE --region=REGION
```

Note the service names and the region. In the description, look for the scaling settings, "CPU Allocation" or "cpu-throttling", and the environment variables.

- [ ] **Step 2: One instance, processor always on, the demo morning**

```bash
gcloud run services update BACKEND_SERVICE --region=REGION \
  --scaling=1 --no-cpu-throttling --cpu=1 --memory=512Mi \
  --update-env-vars=LIGHTTIME_MORNING=1
```

- [ ] **Step 3: No database service**

If the description in Step 1 shows `DATABASE_URL` as a plain variable:

```bash
gcloud run services update BACKEND_SERVICE --region=REGION --remove-env-vars=DATABASE_URL
```

If it shows it as a secret:

```bash
gcloud run services update BACKEND_SERVICE --region=REGION --remove-secrets=DATABASE_URL
```

If the deployment owner keeps Postgres instead, skip this step and drop the demo tables once from an allowed address before going on (the SQL is in `docs/plans/2026-11-15-backend-polish.md`, Task 4).

- [ ] **Step 4: Check the newest revision is the one serving**

```bash
gcloud run revisions list --service BACKEND_SERVICE --region=REGION --limit=3
gcloud run services logs read BACKEND_SERVICE --region=REGION --limit=30
```

Expected: the top revision is marked active with 100 percent of traffic, and the log shows gunicorn "Booting worker" once, with no traceback. If the top revision is not serving, read the log for the reason before changing anything else.

---

### Task 2: Send `/api/*` to the ship

- [ ] **Step 1: Find the parts of the load balancer**

```bash
gcloud compute forwarding-rules list
gcloud compute url-maps list
gcloud compute backend-services list
gcloud compute backend-services describe FRONTEND_BACKEND_SERVICE --global --format="value(loadBalancingScheme)"
```

Write down the URL map's name (`URL_MAP_NAME`) and the name of the backend service that points at the console (`FRONTEND_BACKEND_SERVICE`). If the last command prints `EXTERNAL_MANAGED`, go on. If it prints `EXTERNAL`, use `--load-balancing-scheme=EXTERNAL` in Step 3. If it fails with "not found", the load balancer is regional: use the forms in section 7.8 of `docs/deployment-commands.md`.

- [ ] **Step 2: Let the load balancer reach the ship, without sign-in**

```bash
gcloud run services update BACKEND_SERVICE --region=REGION --ingress=internal-and-cloud-load-balancing
gcloud run services add-iam-policy-binding BACKEND_SERVICE --region=REGION \
  --member="allUsers" --role="roles/run.invoker"
```

- [ ] **Step 3: An endpoint group and a backend service for the ship**

```bash
gcloud compute network-endpoint-groups create lighttime-api-neg \
  --region=REGION --network-endpoint-type=serverless --cloud-run-service=BACKEND_SERVICE
gcloud compute backend-services create lighttime-api-bs \
  --load-balancing-scheme=EXTERNAL_MANAGED --global
gcloud compute backend-services add-backend lighttime-api-bs --global \
  --network-endpoint-group=lighttime-api-neg --network-endpoint-group-region=REGION
```

- [ ] **Step 4: Keep a copy of the URL map, then add the rule**

```bash
gcloud compute url-maps export URL_MAP_NAME --destination=urlmap-before.yaml --global
gcloud compute url-maps add-path-matcher URL_MAP_NAME \
  --path-matcher-name=lighttime-paths \
  --default-service=FRONTEND_BACKEND_SERVICE \
  --path-rules="/api/*=lighttime-api-bs" \
  --new-hosts="*" --global
```

If the second command says a host rule for `*` already exists, the map already has a path matcher: add the line `/api/*` to it by editing the exported file as section 7.4 of the command sheet shows, then `gcloud compute url-maps import URL_MAP_NAME --source=urlmap.yaml --global`.

To undo this step at any time: `gcloud compute url-maps import URL_MAP_NAME --source=urlmap-before.yaml --global`.

- [ ] **Step 5: Check it, allowing a few minutes for the change to spread**

```bash
curl -s -o /dev/null -w "%{http_code}\n" https://lighttime.health/
curl -s https://lighttime.health/api/base/health
for i in 1 2 3 4 5 6 7 8 9 10; do curl -s https://lighttime.health/api/base/state | grep -o '"now":"[^"]*"'; sleep 1; done
curl -s https://lighttime.health/api/base/state | grep -o '"stop":"[^"]*"\|"mission_day":[0-9]*'
```

Expected: `200`; a JSON answer; ten `now` values, each later than the one before; `"stop":"mars"` and `"mission_day":158`. A `now` that goes backwards means two instances or two workers: recheck Task 1 and that the image starts one worker.

---

### Task 3: Build the console with the ship's address

The console reads the ship's address when it is built. The click-through deploy builds the Dockerfile with no build arguments, so the trigger needs a build file that passes one.

- [ ] **Step 1: Fetch the console's `main` and branch from it**

In `LightTime-frontend`:

```powershell
git fetch origin
git checkout -b build/ship-address origin/main
```

- [ ] **Step 2: Add `cloudbuild.yaml` to the root of the console repository**

```yaml
# Builds the console with the ship's address and deploys it to Cloud Run.
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'build'
      - '--build-arg'
      - 'NEXT_PUBLIC_API_URL=${_NEXT_PUBLIC_API_URL}'
      - '-t'
      - '${_REGION}-docker.pkg.dev/$PROJECT_ID/${_REPOSITORY}/${_SERVICE}:$COMMIT_SHA'
      - '.'
  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'push'
      - '${_REGION}-docker.pkg.dev/$PROJECT_ID/${_REPOSITORY}/${_SERVICE}:$COMMIT_SHA'
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
      - 'run'
      - 'deploy'
      - '${_SERVICE}'
      - '--image'
      - '${_REGION}-docker.pkg.dev/$PROJECT_ID/${_REPOSITORY}/${_SERVICE}:$COMMIT_SHA'
      - '--region'
      - '${_REGION}'
substitutions:
  _NEXT_PUBLIC_API_URL: '/'              # "/" means: the ship answers at this site's own address
  _REGION: 'REGION'                      # replace with the Cloud Run region
  _REPOSITORY: 'cloud-run-source-deploy' # an existing Artifact Registry Docker repository
  _SERVICE: 'FRONTEND_SERVICE'           # replace with the console's Cloud Run service name
images:
  - '${_REGION}-docker.pkg.dev/$PROJECT_ID/${_REPOSITORY}/${_SERVICE}:$COMMIT_SHA'
options:
  logging: CLOUD_LOGGING_ONLY
```

Replace `REGION` and `FRONTEND_SERVICE` with the real values (ask the deployment owner; `gcloud artifacts repositories list` shows the repository name). Then:

```powershell
git add cloudbuild.yaml
git commit -m "build: the hosted console is built with the ship's address"
git push origin build/ship-address
```

Open a pull request into `main`. Do not merge it before Task 2 Step 5 passes: a console built with `/` and no route to the ship shows "Ship unreachable: built-in demo" in its header.

- [ ] **Step 3: Point the console's trigger at the file**

```bash
gcloud builds triggers list --region=REGION
gcloud builds triggers update github TRIGGER_NAME --region=REGION --build-config=cloudbuild.yaml
```

- [ ] **Step 4: Merge the pull request, or build once by hand if the trigger does not pick it up**

After the merge, watch the build:

```bash
gcloud builds list --region=REGION --limit=3
```

If no build starts, or it built without the file, run it by hand from a checkout of `main` in Cloud Shell:

```bash
gcloud builds submit --region=REGION --config=cloudbuild.yaml --substitutions=COMMIT_SHA=manual-1 .
```

- [ ] **Step 5: Check it**

```bash
curl -s https://lighttime.health/command-center | grep -c "NEXT_PUBLIC_API_URL"
```

Expected: `0`. Then open https://lighttime.health/ in a browser: the header reads "Earth is 11 min 1 s away" and shows the dial.

---

### Task 4: With no ship, the Earth page speaks to a visitor

This matters only for a console built with no ship address, which is what the site is until Task 3 is done, and what it goes back to under the stop rule. The console's `main` has moved since the backend owner's copy, so this step names the block to replace instead of quoting it.

**Files:**
- Modify: `src/components/command-center/earth-console.tsx` (the block that begins `if (!LIVE)`)
- Modify: `README.md` (the developer instructions move here)

- [ ] **Step 1: Replace the whole `if (!LIVE) return ( ... );` block with**

```tsx
  if (!LIVE)
    return (
      <main className="mx-auto flex max-w-xl flex-col gap-3 p-8 text-sm">
        <h1 className="font-heading text-lg font-semibold">Earth console</h1>
        <p>
          This copy of LIGHT-TIME is running its built-in demo. The Earth
          console shows what the ship has sent across the delayed link, so it
          needs the live ship.
        </p>
        <a className="text-link" href="/base-station">
          ← Back to the crew console
        </a>
      </main>
    );
```

- [ ] **Step 2: Move the instructions to the README**

Add to the console's `README.md`:

```markdown
## Run against the ship

Put `NEXT_PUBLIC_API_URL=http://localhost:5000` in `.env.local` and restart `corepack pnpm dev`. The address is read when the console starts. On a Mac, port 5000 belongs to AirPlay: run the ship on another port and use that port here. With no address the console runs its built-in demo and never asks for a ship.
```

- [ ] **Step 3: Run the checks and commit**

```powershell
corepack pnpm typecheck; corepack pnpm lint:fix; corepack pnpm lint; corepack pnpm test
git add src/components/command-center/earth-console.tsx README.md
git commit -m "fix: with no ship the Earth page speaks to a visitor, not a developer"
```

Expected: no type or lint errors. If `text-link` or `font-heading` is reported as unknown, use the class names the file already uses for its link and its heading.

---

### Task 5: The hosted run-through

- [ ] **Step 1: On a laptop**, open https://lighttime.health/. Press "Restart demo" and "Sound on". Move the dial to the Moon and back to Mars: the header follows within two seconds. Press "Start story": the early warning is spoken after about half a minute, the SOS about 13 seconds later.
- [ ] **Step 2: On a phone, on mobile data**, open the same address while the story runs. Expected: the same alert, the same dial stop.
- [ ] **Step 3: Earth.** On the phone open "Earth", wait for the case, type a reply and send it. On the laptop, the reply appears in the alert's thread about 11 seconds later.
- [ ] **Step 4: Restart.** Press "Restart demo" on either. Both return to 06:30 with alert A1 waiting.
- [ ] **Step 5: Leave it running for ten minutes with no page open, then open it.** The time shown has moved on by ten minutes. If it has not, the processor is being taken away between requests: recheck Task 1 Step 2.
- [ ] **Step 6: Add one line to the project page**, under the link: "This is one live demo ship, shared by everyone who opens it. Restart demo brings it back to the start."

---

### Task 6: When judging is over

- [ ] Turn the always-on instance off, so it stops costing:

```bash
gcloud run services update BACKEND_SERVICE --region=REGION --cpu-throttling --min-instances=0
```

The site then falls back to starting the ship on demand. For a permanent built-in demo, set `_NEXT_PUBLIC_API_URL: ''` in `cloudbuild.yaml` and merge.
