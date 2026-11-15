# LIGHT-TIME on Google Cloud: verified deployment command sheet

Checked on 15 November 2026. Every command below was read on the official Google Cloud documentation page named beside it (pages fetched that day, each showing "Last updated" between 10 and 15 November 2026). The flags were also parsed by a local Google Cloud CLI, version 570.0.0, with no account signed in, so nothing was created or changed anywhere. `cloud.google.com/...` documentation addresses now redirect to `docs.cloud.google.com/...`; the addresses below are the ones the pages resolve to.

Nothing here was run against a real project. Anything I could not confirm on a Google page is marked "Not confirmed" where it appears and listed again at the end.

## Placeholders

| Placeholder | Meaning |
|---|---|
| `PROJECT_ID`, `PROJECT_NUMBER` | The Google Cloud project's id and its number |
| `REGION` | The region both Cloud Run services run in, for example `us-central1` |
| `BACKEND_SERVICE` | The Cloud Run service that runs the Flask backend (the backend README uses `lighttime-api` as its example) |
| `FRONTEND_SERVICE` | The Cloud Run service that runs the Next.js console (the frontend README uses `light-time-frontend`) |
| `REPOSITORY` | An Artifact Registry Docker repository, for example `cloud-run-source-deploy` |
| `RUNTIME_SA` | The service account the backend service runs as. If none was chosen it is `PROJECT_NUMBER-compute@developer.gserviceaccount.com` |
| `BUILD_SA` | The service account the Cloud Build trigger runs as |
| `INSTANCE_NAME`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` | Cloud SQL instance, database, user and password. Never write the real password in a file that is committed |
| `URL_MAP_NAME` | The existing load balancer's URL map |

Run the commands in Cloud Shell or any bash shell. In PowerShell the line continuation is a backtick, not a backslash, and quoting differs.

## The recommended path, in order

1. Section 1: sign in, set the project and region, enable the APIs.
2. Section 4: fix the backend at one instance with instance-based billing (4.1), and set the start-up check (4.6).
3. Section 5 and section 6: decide the database. Simplest: no database service, the SQLite file (6.5). If Postgres is kept and it is Cloud SQL: the built-in connection (6.2) with `DATABASE_URL` in Secret Manager (5.2 to 5.4).
4. Section 7: open both services to the load balancer only (7.1), add a serverless NEG and backend service for the API (7.3), add the `/api/*` rule to the existing URL map (7.4), check it with `curl` (7.5).
5. Section 3: add `cloudbuild.yaml` to the frontend repository and point its trigger at it, so the console is built with `NEXT_PUBLIC_API_URL=/`.
6. Section 8: after every deploy, check the newest revision is serving and the clock only moves forward. Do not merge to the backend's `main` during the demo.

## 1. One-time setup

```bash
gcloud init
```

Signs in and picks a project the first time the CLI is used. Cloud Shell is already signed in. https://docs.cloud.google.com/run/docs/quickstarts/build-and-deploy/deploy-python-service

```bash
gcloud config set project PROJECT_ID
```

Makes this project the default for every later command. https://docs.cloud.google.com/sdk/docs/properties

```bash
gcloud config set run/region REGION
```

Makes this region the default for Cloud Run commands, so `--region` can be left out. Use the region the two services already run in. https://docs.cloud.google.com/run/docs/setup

```bash
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  sqladmin.googleapis.com \
  compute.googleapis.com
```

Turns on Cloud Run, Cloud Build, Artifact Registry, Secret Manager, Cloud SQL Admin and Compute Engine (the load balancer and VPC live under Compute Engine). Enabling an API that is already on does nothing. Command: https://docs.cloud.google.com/service-usage/docs/enable-disable. Five of the six names appear together in Google's Cloud SQL and Cloud Run quickstart (https://docs.cloud.google.com/sql/docs/postgres/connect-instance-cloud-run); `secretmanager.googleapis.com` is on https://docs.cloud.google.com/secret-manager/docs/configuring-secret-manager.

Only for the paths in section 6 that use them: `servicenetworking.googleapis.com` (a private address for Cloud SQL) and `vpcaccess.googleapis.com` (a Serverless VPC Access connector).

"To enable APIs, you need the serviceusage.services.enable permission", which the project's Owner has.

The project number, needed for the default service account's name:

```bash
gcloud projects describe PROJECT_ID --format="value(projectNumber)"
```

Prints `PROJECT_NUMBER`. This command parsed locally; I did not look it up on a documentation page.

## 2. Deploy a service from source, or from a prebuilt image

### 2.1 From source with the repository's Dockerfile

```bash
cd PATH_TO_REPO
gcloud run deploy SERVICE --source . --region REGION
```

Uploads the folder, builds it with Cloud Build and deploys the result. "If a Dockerfile is present in the source code directory, the uploaded source code is built using that Dockerfile." https://docs.cloud.google.com/run/docs/deploying-source-code

- **Where the image goes:** an Artifact Registry repository named `cloud-run-source-deploy` in the region of the deploy. The command creates it if it is missing. Same page.
- **What is uploaded:** `gcloud run deploy` obeys `.gcloudignore`, not `.dockerignore`. With no `.gcloudignore`, the generated one leaves out `.git` and everything `.gitignore` leaves out, so a local `.env` is not uploaded. https://docs.cloud.google.com/sdk/gcloud/reference/topic/gcloudignore
- **Public or not:** without `--allow-unauthenticated` or `--no-allow-unauthenticated` "you are prompted to confirm when the deploy command runs". https://docs.cloud.google.com/run/docs/deploying
- **No build arguments:** "Deploying from source is a convenience feature, and does not allow full customization of the build. For more control, build the container image using Cloud Build". So the frontend, which needs `--build-arg`, should not be deployed this way once it must reach the ship (section 3).

Roles, from the same page. The person deploying needs Cloud Run Source Developer (`roles/run.sourceDeveloper`), Service Usage Consumer (`roles/serviceusage.serviceUsageConsumer`) and Service Account User (`roles/iam.serviceAccountUser`) on the service's identity. The account that builds is the Compute Engine default service account unless changed, and it needs Cloud Run Builder:

```bash
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member=serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com \
  --role=roles/run.builder
```

Lets the default build account build and deploy source. https://docs.cloud.google.com/run/docs/deploying-source-code

The backend in one command, with everything from sections 4, 5, 6 and 7:

```bash
gcloud run deploy BACKEND_SERVICE --source . --region=REGION \
  --scaling=1 --no-cpu-throttling --cpu=1 --memory=512Mi \
  --set-env-vars=LIGHTTIME_MORNING=1 \
  --set-secrets=DATABASE_URL=database-url:latest \
  --add-cloudsql-instances=PROJECT_ID:REGION:INSTANCE_NAME \
  --ingress=internal-and-cloud-load-balancing \
  --allow-unauthenticated
```

Every flag here is explained in its own section. Leave out `--set-secrets` and `--add-cloudsql-instances` to run on the SQLite file (section 6.5). The combination parsed in the CLI but was not run against a project.

### 2.2 From a prebuilt image

```bash
gcloud artifacts repositories create REPOSITORY \
  --repository-format=docker \
  --location=REGION \
  --description="Docker repository"
```

Creates a Docker repository to hold images. Skip it to reuse `cloud-run-source-deploy`. https://docs.cloud.google.com/artifact-registry/docs/docker/store-docker-container-images

```bash
gcloud builds submit --tag REGION-docker.pkg.dev/PROJECT_ID/REPOSITORY/IMAGE_NAME
```

Builds the Dockerfile in the current folder on Cloud Build and pushes the image. It cannot pass build arguments, so use it for the backend only. https://docs.cloud.google.com/build/docs/building/build-containers

```bash
gcloud run deploy SERVICE --image REGION-docker.pkg.dev/PROJECT_ID/REPOSITORY/IMAGE_NAME --region REGION
```

Deploys that image as a new revision. The image address has the form `LOCATION-docker.pkg.dev/PROJECT_ID/REPO_NAME/PATH:TAG` and "the repository REPO_NAME must already be created". https://docs.cloud.google.com/run/docs/deploying

Building on a laptop instead (needs Docker):

```bash
gcloud auth configure-docker REGION-docker.pkg.dev
docker build --build-arg NEXT_PUBLIC_API_URL=/ \
  -t REGION-docker.pkg.dev/PROJECT_ID/REPOSITORY/console:TAG .
docker push REGION-docker.pkg.dev/PROJECT_ID/REPOSITORY/console:TAG
```

Signs Docker in to Artifact Registry, builds the console with the ship at the same address, and pushes it. `configure-docker`: https://docs.cloud.google.com/run/docs/setup. Push: https://docs.cloud.google.com/artifact-registry/docs/docker/store-docker-container-images. `docker build --build-arg` is Docker's own flag, not a Google one; Google shows it inside a build step in section 3.

Two cautions. Cloud Run needs a Linux x86_64 image, and the troubleshooting page warns that an image built "on a ARM based machine ... might not work as expected", with the fix "build your image using Cloud Build" (https://docs.cloud.google.com/run/docs/troubleshooting). And in Git Bash on Windows a bare `/` argument can be rewritten into a Windows path; this is not confirmed here and is not from a Google page, so check the built console or build on Cloud Build.

## 3. Continuous deployment from GitHub on every push to `main`

### 3.1 What the click-through flow does

In the console: Cloud Run, open the service, **Source** tab, **Connect to repo**, **Set up with Cloud Build**, pick the repository, then in **Build Configuration** choose the branch (a regular expression such as `^main$`) and the build type **Dockerfile** with its location. https://docs.cloud.google.com/run/docs/continuous-deployment

- "Cloud Run uses a Cloud Build trigger, to automatically build and deploy your code whenever new commits are pushed to a given branch".
- The connection uses the Cloud Build GitHub app.
- The form asks for a branch, a build type and the Dockerfile's location. The page shows no field for Docker build arguments. That is why the hosted console is the built-in demo today.
- Afterwards, **Edit repo settings** on the service opens the trigger in Cloud Build. This is the way in for 3.3.
- An existing trigger can be tied to a service by putting the label `gcb-trigger-id` (the trigger's id, not its name) on the service.

Not confirmed: the exact build steps inside the trigger that this flow creates. The page does not print them. Look at yours before changing it:

```bash
gcloud builds triggers list --region=REGION
gcloud builds triggers describe TRIGGER_NAME --region=REGION
```

Lists the triggers and prints one in full, including its build steps, substitutions and service account. If the list is empty, run it again without `--region`, which shows the global ones. https://docs.cloud.google.com/sdk/gcloud/reference/builds/triggers/list and https://docs.cloud.google.com/sdk/gcloud/reference/builds/triggers/describe

### 3.2 A `cloudbuild.yaml` for the frontend that passes the build argument

Put this file in the root of the frontend repository. It follows Google's own example (build, push, `gcloud run deploy`) from https://docs.cloud.google.com/build/docs/deploying-builds/deploy-cloud-run, with the `--build-arg` pattern from https://docs.cloud.google.com/build/docs/configuring-builds/substitute-variable-values.

```yaml
# cloudbuild.yaml, in the root of the frontend repository
steps:
  # 1. Build the image. The Dockerfile's "ARG NEXT_PUBLIC_API_URL" receives the value,
  #    and "pnpm build" bakes it into the console.
  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'build'
      - '--build-arg'
      - 'NEXT_PUBLIC_API_URL=${_NEXT_PUBLIC_API_URL}'
      - '-t'
      - '${_REGION}-docker.pkg.dev/$PROJECT_ID/${_REPOSITORY}/${_SERVICE}:$COMMIT_SHA'
      - '.'
  # 2. Push the image to Artifact Registry.
  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'push'
      - '${_REGION}-docker.pkg.dev/$PROJECT_ID/${_REPOSITORY}/${_SERVICE}:$COMMIT_SHA'
  # 3. Deploy the image to Cloud Run as a new revision.
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
  _REGION: 'REGION'                      # replace, for example us-central1
  _REPOSITORY: 'cloud-run-source-deploy' # an existing Artifact Registry Docker repository
  _SERVICE: 'FRONTEND_SERVICE'           # replace with the Cloud Run service name
images:
  - '${_REGION}-docker.pkg.dev/$PROJECT_ID/${_REPOSITORY}/${_SERVICE}:$COMMIT_SHA'
options:
  logging: CLOUD_LOGGING_ONLY
```

How it was checked: the file parses as YAML, and `gcloud builds submit --config` accepted it as a build config (a copy with one misspelt key was rejected, so the check is real). It has not been run on Cloud Build.

Notes on the file:

- `$PROJECT_ID` and `$COMMIT_SHA` are filled in by Cloud Build; `$COMMIT_SHA` only for builds started by a trigger. Names you define must start with an underscore and use capitals, digits and underscores.
- The deploy step names only the image and the region, so the service keeps its other settings (ingress, scaling, variables).
- `options: logging: CLOUD_LOGGING_ONLY` is there because "When you specify your own service account for builds, you must store your build logs" in Cloud Logging or in your own bucket, and a trigger now has to name a service account "unless the default service account for your project is the Cloud Build legacy service account". https://docs.cloud.google.com/build/docs/securing-builds/configure-user-specified-service-accounts and https://docs.cloud.google.com/build/docs/cloud-build-service-account-updates
- The backend needs no build argument, so its existing trigger can stay as it is.

To try it by hand before any trigger uses it:

```bash
gcloud builds submit --region=REGION --config=cloudbuild.yaml --substitutions=COMMIT_SHA=manual-1 .
```

Runs the same three steps from the current folder. `COMMIT_SHA` has to be given by hand here because no commit started the build. https://docs.cloud.google.com/build/docs/configuring-builds/substitute-variable-values

### 3.3 Make the frontend's trigger use it

Either edit the existing trigger or create a new one. Do not keep two triggers on the same branch of the same repository, or every merge deploys twice.

**In the console (documented step by step):** Cloud Run, the frontend service, **Edit repo settings**. In the trigger, under **Configuration**, choose **Cloud Build configuration file (yaml or json)**, location **Repository**, file `cloudbuild.yaml`, and save. The **Inline** choice with **Open Editor** lets you instead add the two `--build-arg` lines to a build config kept in the trigger. https://docs.cloud.google.com/build/docs/automating-builds/create-manage-triggers

**The same from the command line:**

```bash
gcloud builds triggers update github TRIGGER_NAME --region=REGION --build-config=cloudbuild.yaml
```

Points an existing GitHub trigger at the file in the repository. The flags are on the reference page; I did not run it against a trigger made by the Cloud Run flow. https://docs.cloud.google.com/sdk/gcloud/reference/builds/triggers/update/github

**A new trigger:**

```bash
gcloud builds triggers create github \
  --name=console-main \
  --region=REGION \
  --repo-owner=GITHUB_OWNER \
  --repo-name=GITHUB_REPO \
  --branch-pattern='^main$' \
  --build-config=cloudbuild.yaml \
  --service-account=projects/PROJECT_ID/serviceAccounts/BUILD_SA
```

Builds and deploys on every push to `main`. The repository must already be connected to Cloud Build (the Cloud Run flow did that). `--repo-owner` and `--repo-name` are for a repository connected through the Cloud Build GitHub app; one connected the newer way is named with `--repository=projects/PROJECT_ID/locations/REGION/connections/CONNECTION/repositories/REPO` instead. "The region for your trigger must match the region of the Cloud Run service you're deploying to." https://docs.cloud.google.com/build/docs/automating-builds/create-manage-triggers and https://docs.cloud.google.com/build/docs/deploying-builds/deploy-cloud-run

```bash
gcloud builds triggers run TRIGGER_NAME --region=REGION --branch=main
```

Starts the trigger once without a push. https://docs.cloud.google.com/sdk/gcloud/reference/builds/triggers/run

A commit whose message contains `[skip ci]` or `[ci skip]` does not start a build. Same triggers page. Useful on demo day, because a merge to the backend's `main` restarts the mission clock.

### 3.4 The service account the trigger runs as, and its roles

"Only the service account specified on your trigger will be used for builds executed by triggers." A `serviceAccount` line in the YAML is ignored for triggered builds. https://docs.cloud.google.com/build/docs/automating-builds/create-manage-triggers

The Cloud Run page lists what that account needs (https://docs.cloud.google.com/run/docs/continuous-deployment):

| Role | Why |
|---|---|
| Cloud Build Service Account, `roles/cloudbuild.builds.builder` | Run the build, push to Artifact Registry, write logs |
| Cloud Run Admin, `roles/run.admin` | Deploy the new revision |
| Service Account User, `roles/iam.serviceAccountUser`, on `RUNTIME_SA` | Deploy a service that runs as that account |

Cloud Build's own page names a longer list for the same job: Cloud Run Admin, Service Account User, Storage Admin, Artifact Registry Writer (`roles/artifactregistry.writer`), Logs Writer (`roles/logging.logWriter`) and Cloud Build Editor. https://docs.cloud.google.com/build/docs/deploying-builds/deploy-cloud-run If a build fails on permissions, compare against that list.

Both existing triggers already deploy, so their account has these roles. For a new, separate account:

```bash
gcloud iam service-accounts create lighttime-build --display-name="LIGHT-TIME build and deploy"
```

Creates the account `lighttime-build@PROJECT_ID.iam.gserviceaccount.com` (this is `BUILD_SA`). https://docs.cloud.google.com/iam/docs/service-accounts-create

```bash
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:BUILD_SA" --role="roles/cloudbuild.builds.builder"
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:BUILD_SA" --role="roles/run.admin"
```

Grants the two project roles. The command form is the one Google uses for the build account at https://docs.cloud.google.com/run/docs/deploying-source-code; the role names are from the table above.

```bash
gcloud iam service-accounts add-iam-policy-binding RUNTIME_SA \
  --member="serviceAccount:BUILD_SA" --role="roles/iam.serviceAccountUser"
```

Lets the build account deploy services that run as `RUNTIME_SA`. https://docs.cloud.google.com/run/docs/reference/iam/roles

### 3.5 What does not pass a Dockerfile build argument

`gcloud run deploy --source . --set-build-env-vars KEY=VALUE` exists, but its page says build environment variables "let you pass configuration information to buildpacks". It says nothing about a Dockerfile's `ARG`. Not confirmed either way, so do not rely on it for `NEXT_PUBLIC_API_URL`. https://docs.cloud.google.com/run/docs/configuring/services/build-environment-variables

## 4. Pin the backend to one always-on instance with CPU outside requests

What the current pages say, in short:

- Scaling settings now exist at two levels. The service-level flags are `--min` and `--max`, and they take effect at once without a new revision. The older revision-level flags `--min-instances` and `--max-instances` still exist, but both pages now say "Revision-level scaling is only available for services that previously had the feature configured", and Google recommends the service-level ones.
- There is a third choice that fits this backend best: manual scaling, `--scaling=N`, which fixes the instance count "regardless of traffic or utilization". The autoscaling page points to it for "a fixed instance count".
- The setting that keeps CPU available between requests is now called **instance-based billing** (it "was previously called CPU always allocated"). The default is **request-based billing** ("previously called CPU only allocated during request processing"). The flag did not change: `--no-cpu-throttling`.

### 4.1 Recommended: one command for the backend

```bash
gcloud run services update BACKEND_SERVICE \
  --region=REGION \
  --scaling=1 \
  --no-cpu-throttling \
  --cpu=1 \
  --memory=512Mi \
  --concurrency=80 \
  --timeout=300
```

Fixes the backend at exactly one instance, gives it CPU for its whole life, and sets the smallest size that instance-based billing allows.

- `--scaling=1`: https://docs.cloud.google.com/run/docs/configuring/services/manual-scaling ("Changing scaling mode from automatic to manual or vice-versa, or changing the manual instance count does not create a new revision.")
- `--no-cpu-throttling`: https://docs.cloud.google.com/run/docs/configuring/billing-settings
- `--cpu`: https://docs.cloud.google.com/run/docs/configuring/services/cpu
- `--memory`: https://docs.cloud.google.com/run/docs/configuring/services/memory-limits
- `--concurrency`: https://docs.cloud.google.com/run/docs/configuring/concurrency
- `--timeout`: https://docs.cloud.google.com/run/docs/configuring/request-timeout

Why each value:

- `--cpu=1`. Less than 1 vCPU is not allowed here: below 1 vCPU the CPU page requires concurrency 1, request-based billing and the first generation environment.
- `--memory=512Mi`. The billing page says "If you select instance-based billing, you must specify at least 512MiB of memory." 512 MiB is also the default. Raise it to `1Gi` if the backend uses the SQLite file (section 6.5) or the logs show the instance was ended for exceeding memory.
- `--concurrency=80`. This is the default. The container runs one gunicorn worker with 8 threads, so extra requests wait inside gunicorn. Lowering concurrency to 8 would instead make Cloud Run hold them (for 10 seconds, or longer if the container is slow to start) and then answer 429, because there is no second instance to send them to (https://docs.cloud.google.com/run/docs/about-instance-autoscaling). Keeping 80 is my recommendation, not a Google statement.
- `--timeout=300`. The default (5 minutes, up to 60). Nothing in this API needs more.
- `--port` is not needed. Requests go to port 8080 by default and Cloud Run sets `PORT` for the container; both Dockerfiles already listen on `$PORT` with 8080 as the fallback. To set it anyway: `gcloud run services update SERVICE --port 8080` (https://docs.cloud.google.com/run/docs/configuring/services/containers).

### 4.2 The same thing with minimum and maximum instances

```bash
gcloud run services update BACKEND_SERVICE --region=REGION --min 1 --max 1 --no-cpu-throttling
```

Service-level minimum and maximum of one, with autoscaling still switched on. https://docs.cloud.google.com/run/docs/configuring/min-instances and https://docs.cloud.google.com/run/docs/configuring/max-instances

```bash
gcloud run services update BACKEND_SERVICE --region=REGION --min-instances 1 --max-instances 1
```

The older revision-level form, kept on the same two pages. Use it only if the service already has revision-level scaling set. If the service is on manual scaling, "any revision-level minimum and maximum instance settings are ignored".

### 4.3 Check what is set

```bash
gcloud run services describe BACKEND_SERVICE --region=REGION
```

Look for `Scaling: Manual (Instances: 1)` or `Scaling: Auto (Min: 1, Max: 1)` near the top. https://docs.cloud.google.com/run/docs/configuring/services/manual-scaling

### 4.4 Optional: faster starts

```bash
gcloud run services update BACKEND_SERVICE --region=REGION --cpu-boost
```

Gives extra CPU while the container starts, which is when the backend loads the demo morning. https://docs.cloud.google.com/run/docs/configuring/services/cpu

### 4.5 What "one instance" does not promise (read this)

All four statements are on Google pages:

1. **A deploy runs two instances for a short time.** "When you deploy a new revision to serve 100% of the traffic, Cloud Run starts enough instances of the new revision before directing traffic to it", and the maximum is "a limit for each revision", so "during a deployment, the total number of instances for the service can exceed the maximum". https://docs.cloud.google.com/run/docs/about-instance-autoscaling For this backend that means: the new instance starts its own clock and reloads the morning, which empties the demo tables, while the old instance is still answering. Do not merge to the backend's `main` during the demo.
2. **With autoscaling, the maximum can be passed without a deploy.** "The maximum instance limit can be exceeded under normal operation a few times per week", for example during "system maintenance". Same page. The manual scaling page does not repeat this warning, which is one reason 4.1 uses manual scaling. Not confirmed: whether manual scaling removes the overlap during a deploy or during maintenance.
3. **The one instance can be restarted.** "Minimum instances can be restarted at any time." https://docs.cloud.google.com/run/docs/configuring/min-instances Each restart puts the mission clock back to 06:30.
4. **A background thread needs both settings.** With request-based billing "CPU is only allocated during request processing". The autoscaling page adds: if a service runs "background threads", "set minimum instances to at least 1". Instance-based billing alone is not enough, because a service with no minimum scales to zero after at most 15 minutes idle.

### 4.6 Make "started" mean "the app answers"

```bash
gcloud run services update BACKEND_SERVICE --region=REGION \
  --startup-probe=httpGet.path=/api/base/health,periodSeconds=5,timeoutSeconds=3,failureThreshold=24
```

Replaces the default start-up check with an HTTP request to the backend's own health route, tried every 5 seconds for up to 2 minutes. "Any 2XX or 3XX response is a success". https://docs.cloud.google.com/run/docs/configuring/healthchecks

Why: the default is "a TCP startup probe" that only makes "a TCP connection" to the port. Gunicorn opens the port before its worker has built the app, loaded the demo morning and reached the database. I checked this on a copy: with a database that never answered, a TCP connection to the port succeeded while `GET /api/base/health` got no reply. With the default check, Cloud Run can therefore count a new revision as started, and move traffic to it, before the backend can answer anything. With the HTTP check a revision that cannot finish starting is ended and the previous one keeps serving. Not confirmed on Cloud Run itself: this follows from the two pages and the local test.

Not for this weekend: the billing page now suggests a new resource type, a "Cloud Run instance", for "a single, long-lived instance". It is in Preview, is created with `gcloud beta run instances create`, is not offered in `us-central1`, `us-east1` or `europe-west1`, and I did not confirm that a load balancer can route to one. https://docs.cloud.google.com/run/docs/instances/create-and-manage-instances

## 5. Environment variables and secrets

### 5.1 Plain environment variables

```bash
gcloud run services update BACKEND_SERVICE --region=REGION --update-env-vars=LIGHTTIME_MORNING=1
```

Adds or changes one variable and keeps the others ("a non-destructive approach"). https://docs.cloud.google.com/run/docs/configuring/services/environment-variables

```bash
gcloud run deploy SERVICE --image IMAGE_URL --set-env-vars KEY1=VALUE1,KEY2=VALUE2
```

Sets the whole list at deploy time. Careful: "the --set-env-vars flag is a destructive action that deletes previously set environment variables not included in the new list". https://docs.cloud.google.com/run/docs/configuring/services/environment-variables

A value set on the service wins over an `ENV` line in the Dockerfile. Same page. Google says not to keep database credentials in plain variables, which is why `DATABASE_URL` goes in a secret.

### 5.2 Put DATABASE_URL in Secret Manager

```bash
gcloud services enable secretmanager.googleapis.com
```

Turns the API on. https://docs.cloud.google.com/secret-manager/docs/configuring-secret-manager

```bash
gcloud secrets create database-url --replication-policy="automatic"
```

Creates an empty secret named `database-url`. https://docs.cloud.google.com/secret-manager/docs/creating-and-accessing-secrets

```bash
gcloud secrets versions add database-url --data-file="FILE_PATH"
```

Stores the file's contents as the secret's first version. The file must hold the URL and nothing else, with no line break at the end, and must not be committed. https://docs.cloud.google.com/secret-manager/docs/add-secret-version

```bash
echo -n "postgresql+psycopg://DB_USER:DB_PASSWORD@/DB_NAME?host=/cloudsql/PROJECT_ID:REGION:INSTANCE_NAME" | \
  gcloud secrets versions add database-url --data-file=-
```

The same without a file. Google shows this form but discourages it, because the value "appears as plaintext in the list of processes" and stays in the shell history. Same page. Use bash for it: `echo -n` is a bash form, and a trailing line break would become part of the URL. The URL's shape is explained in section 6.

### 5.3 Let the backend's service account read it

```bash
gcloud run services describe BACKEND_SERVICE --region REGION \
  --format="value(spec.template.spec.serviceAccountName)"
```

Prints the service account the backend runs as (`RUNTIME_SA`). https://docs.cloud.google.com/sql/docs/postgres/connect-run If none was chosen it is `PROJECT_NUMBER-compute@developer.gserviceaccount.com` (https://docs.cloud.google.com/run/docs/securing/service-identity).

```bash
gcloud secrets add-iam-policy-binding database-url \
  --member="serviceAccount:RUNTIME_SA" \
  --role="roles/secretmanager.secretAccessor"
```

Gives that account read access to this one secret. https://docs.cloud.google.com/secret-manager/docs/manage-access-to-secrets

### 5.4 Hand the secret to the service as DATABASE_URL

```bash
gcloud run services update BACKEND_SERVICE --region=REGION \
  --set-secrets="DATABASE_URL=database-url:latest"
```

Makes the secret the value of `DATABASE_URL`. `--set-secrets` clears any other secrets on the service; `--update-secrets=DATABASE_URL=database-url:latest` adds this one and keeps the rest. https://docs.cloud.google.com/run/docs/configuring/services/secrets

Three things from that page:

- A secret passed as a variable is read "at instance startup time". After adding a new version, deploy again or the running instance keeps the old value.
- Google recommends pinning a version (`database-url:1`) instead of `latest`.
- "If the secret retrieval process fails, the instance doesn't start." A missing role in 5.3 shows up as a revision that never becomes ready.

To go back to the SQLite file, remove it: `gcloud run services update BACKEND_SERVICE --region=REGION --remove-secrets=DATABASE_URL`. Same page.

## 6. The database: Cloud SQL for PostgreSQL, three ways in, and the no-database option

First find out what the existing database is:

```bash
gcloud sql instances list
```

Lists Cloud SQL instances in the project. If the "allowlisted addresses" database is in this list, use 6.2. If it is not a Cloud SQL instance, only 6.3 applies to it. (Command parsed locally; the instance pages use `gcloud sql instances describe`.)

### 6.1 Create a small instance, a database and a user

```bash
gcloud services enable sqladmin.googleapis.com
```

Turns on the Cloud SQL Admin API, which the Cloud Run connection needs. https://docs.cloud.google.com/sql/docs/postgres/connect-run

```bash
gcloud sql instances create INSTANCE_NAME \
  --database-version=POSTGRES_16 \
  --edition=ENTERPRISE \
  --tier=db-f1-micro \
  --region=REGION \
  --storage-size=10
```

Creates the smallest instance: a shared-core machine with 10 GB of disk, in the same region as Cloud Run. https://docs.cloud.google.com/sql/docs/postgres/create-instance

- `--edition=ENTERPRISE` matters. The page warns: "If the database version for your instance is PostgreSQL 16 or later, then the default edition is Cloud SQL Enterprise Plus edition", and the shared-core machines (`db-f1-micro`, `db-g1-small`) are the cheap ones, set with `--tier`. The local CLI lists the values as `enterprise` and `enterprise-plus` and accepted both spellings.
- The backend was tested on PostgreSQL 16. Allow several minutes for the instance to be created (from experience, not from the page).
- A new instance gets a public address by default ("By default, Cloud SQL assigns a public IP address to a new instance"), with nothing authorized to connect to it directly.

```bash
gcloud sql databases create DB_NAME --instance=INSTANCE_NAME
```

Creates the database. https://docs.cloud.google.com/sql/docs/postgres/create-manage-databases

```bash
gcloud sql users create DB_USER --instance=INSTANCE_NAME --password=DB_PASSWORD
```

Creates the login the backend uses. The page says a user made this way "is granted the cloudsqlsuperuser role automatically". The backend creates its own tables at start; I did not test that on a real Cloud SQL instance. https://docs.cloud.google.com/sql/docs/postgres/create-manage-users Use letters and digits in the password, or percent-encode it in the URL (`@` becomes `%40`).

```bash
gcloud sql instances describe INSTANCE_NAME --format="value(connectionName)"
```

Prints the instance connection name, `PROJECT_ID:REGION:INSTANCE_NAME`, used below. https://docs.cloud.google.com/sql/docs/postgres/connect-run

### 6.2 Way (a): Cloud Run's built-in Cloud SQL connection (recommended if you keep Postgres)

What it needs: the Cloud SQL Admin API on, a public address on the instance, the Cloud SQL Client role on the backend's service account. It does **not** need authorized networks or a VPC: Cloud Run uses "an embedded Cloud SQL Auth Proxy", and a connector is the documented answer for "a client or application that uses a dynamically assigned or ephemeral IP address". https://docs.cloud.google.com/sql/docs/postgres/connection-options

```bash
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:RUNTIME_SA" \
  --role="roles/cloudsql.client"
```

Lets the backend's service account open connections to Cloud SQL. https://docs.cloud.google.com/sql/docs/postgres/connect-instance-cloud-run

```bash
gcloud run services update BACKEND_SERVICE --region=REGION \
  --add-cloudsql-instances=PROJECT_ID:REGION:INSTANCE_NAME
```

Mounts a Unix socket for the instance inside the container at `/cloudsql/PROJECT_ID:REGION:INSTANCE_NAME`. https://docs.cloud.google.com/sql/docs/postgres/connect-run

The value to store as `DATABASE_URL` (section 5):

```text
postgresql+psycopg://DB_USER:DB_PASSWORD@/DB_NAME?host=/cloudsql/PROJECT_ID:REGION:INSTANCE_NAME
```

Nothing between `@` and `/`: the host is the socket folder, given in the `host` parameter.

How this URL was confirmed, since Google's page does not show psycopg 3:

- Google's sample uses the `pg8000` driver with `unix_sock=.../.s.PGSQL.5432` and adds: "Some drivers require the `unix_sock` query parameter to use a different key. For example, 'psycopg2' uses the path set to `host`". It also says the PostgreSQL socket file is `.s.PGSQL.5432` inside that folder and that "Some libraries apply this suffix automatically".
- I tested it. With SQLAlchemy 2.1.8 and psycopg 3.3.9 (what `requirements.txt` installs today), I started a throwaway PostgreSQL 16 that listened only on a Unix socket in a folder named `placeholder-project:us-central1:lighttime-db`, and started a copy of the backend with a URL of exactly this shape. It connected, created its tables, loaded the demo morning and answered `/api/base/health` with 200. psycopg 3 adds `.s.PGSQL.5432` by itself. That was a local socket, not a real Cloud SQL instance.
- The whole socket path must stay under 108 characters (same Google page). With long project and instance names, count it.

### 6.3 Way (b): public address with authorized networks

```bash
gcloud sql instances patch INSTANCE_NAME --authorized-networks=ADDRESS_1/32,ADDRESS_2/32
```

Allows direct connections from the listed addresses. Careful: "Configuring authorized networks replaces the existing authorized networks list", so repeat the addresses already there. https://docs.cloud.google.com/sql/docs/postgres/authorize-networks

Why this does not work for Cloud Run as it stands: "By default, Cloud Run workloads connect to external endpoints on the internet using a regional pool of dynamic IP addresses shared across all serverless workloads." There is no single address to put on the list. To get one, send all of the service's outbound traffic through the VPC and give the VPC a NAT gateway with a reserved address. All four commands are from https://docs.cloud.google.com/run/docs/configuring/static-outbound-ip:

```bash
gcloud compute routers create lighttime-router --network=VPC_NETWORK --region=REGION
gcloud compute addresses create lighttime-egress-ip --region=REGION
gcloud compute routers nats create lighttime-nat \
  --router=lighttime-router \
  --region=REGION \
  --nat-custom-subnet-ip-ranges=SUBNET \
  --nat-external-ip-pool=lighttime-egress-ip
gcloud run services update BACKEND_SERVICE --region=REGION \
  --network=VPC_NETWORK --subnet=SUBNET --vpc-egress=all-traffic
```

A router, a reserved address, a NAT gateway that uses it for one subnet, and the backend's outbound traffic sent through that subnet. The page shows the last one as `gcloud run deploy ... --network --subnet --vpc-egress=all-traffic`; the same flags parsed on `services update`. Then put the reserved address on the database's list. The URL is the ordinary one:

```text
postgresql+psycopg://DB_USER:DB_PASSWORD@DATABASE_ADDRESS:5432/DB_NAME
```

This is the only way that fits a database that is **not** Cloud SQL. For a direct connection "you're responsible for configuring the SSL/TLS settings"; adding `?sslmode=require` to the URL is the usual way with this driver, not confirmed on a Google page. The subnet must be `/26` or larger, and the Direct VPC page warns of "cold start delays of 30s or more" with Cloud NAT. https://docs.cloud.google.com/run/docs/configuring/vpc-direct-vpc

### 6.4 Way (c): private address, reached through the VPC

What it needs: private services access on the VPC (an address range and a peering), a private address on the instance, and the backend attached to the VPC. Commands from https://docs.cloud.google.com/sql/docs/postgres/configure-private-services-access:

```bash
gcloud services enable sqladmin.googleapis.com compute.googleapis.com servicenetworking.googleapis.com
gcloud compute addresses create google-managed-services-VPC_NETWORK \
  --global --purpose=VPC_PEERING --prefix-length=16 \
  --network=projects/PROJECT_ID/global/networks/VPC_NETWORK
gcloud services vpc-peerings connect \
  --service=servicenetworking.googleapis.com \
  --ranges=google-managed-services-VPC_NETWORK \
  --network=VPC_NETWORK
gcloud beta sql instances patch INSTANCE_NAME \
  --network=projects/PROJECT_ID/global/networks/VPC_NETWORK --no-assign-ip
```

The APIs, a reserved range for Google's services, the peering, and the instance moved onto the VPC with its public address removed (leave out `--no-assign-ip` to keep both). The last command is `gcloud beta` on Google's page; the beta component was not installed where I checked, so that one was not parsed locally.

Then attach the backend, one of two ways:

```bash
gcloud run services update BACKEND_SERVICE --region=REGION \
  --network=VPC_NETWORK --subnet=SUBNET --vpc-egress=private-ranges-only
```

Direct VPC egress, which Google marks "recommended". `private-ranges-only` "Sends only traffic to internal addresses through the VPC network", so the backend's call to NASA JPL still goes straight out. https://docs.cloud.google.com/run/docs/configuring/vpc-direct-vpc

```bash
gcloud services enable vpcaccess.googleapis.com
gcloud compute networks vpc-access connectors create lighttime-conn \
  --region=REGION --network=VPC_NETWORK --range=10.8.0.0/28
gcloud run services update BACKEND_SERVICE --region=REGION --vpc-connector=lighttime-conn
```

The older way, a Serverless VPC Access connector. It needs its own unused `/28` range and "Connectors continue to incur charges even if they have no traffic". https://docs.cloud.google.com/run/docs/configuring/vpc-connectors

The URL uses the private address: `postgresql+psycopg://DB_USER:DB_PASSWORD@PRIVATE_ADDRESS:5432/DB_NAME` ("Connect using your instance's private IP address and port 5432").

A risk for this backend with Direct VPC egress: "You might experience connection establishment delays of a minute or more on instance startup", and the backend opens its database connection the moment it starts. A first start can fail for that reason.

### 6.5 No database service at all: the SQLite file

Without `DATABASE_URL` the backend uses `sqlite:///lighttime.db`, which Flask-SQLAlchemy places at `/app/instance/lighttime.db`. The Dockerfile gives `/app` to the user the container runs as, so the folder can be created.

Does a writable local file work on Cloud Run? Yes. "Each container's file system is writable", with two conditions from the same page (https://docs.cloud.google.com/run/docs/container-contract):

- "It is an in-memory file system, so writing to it uses the instance's memory."
- "Data written to the file system doesn't persist when the instance stops."

There is no separate size limit: a file that grows without end would use up the instance's memory and "crash the instance".

What it costs in memory, measured on a copy of the backend run with the Dockerfile's own gunicorn command:

| Measure | Value |
|---|---|
| SQLite file right after the demo morning loads | 0.1 MB (102,400 bytes) |
| Growth while a story runs (3 readings a second) | about 137 bytes a reading, about 1.5 MB an hour |
| Memory of the gunicorn master and its one worker together | about 97 MiB |

So the file is a rounding error against the 512 MiB minimum. A device posting one reading a second around the clock would add roughly 12 MB a day at the same size per row, still small, and every restart starts again from the demo morning.

What losing the file on restart means here: nothing new. In morning mode the backend empties its tables and reloads the demo at every start, on Postgres too.

One real advantage for this app: each instance has its own file. During a deploy (section 4.5) the new instance cannot empty the tables the old one is still serving from, which it does when both share one Postgres database. The two instances still have two clocks for the moment they overlap.

Limits: one instance only (already required), no data kept between restarts, and SQLite allows one writer at a time, so heavy simultaneous writes can wait or fail where Postgres would not. The backend's own notes record one behaviour difference between the two (a reading for an unknown crew member is stored on SQLite and rejected on Postgres).

### 6.6 Recommendation

For the demo weekend, in this order:

1. **No database service (6.5).** It is the simplest thing that works: nothing to create, allowlist, pay for or wait on, and the backend throws its data away at every start anyway. Remove `DATABASE_URL` from the backend service and it is done.
2. **If Postgres is wanted and it is Cloud SQL, way (a) (6.2).** Two commands and one URL, no addresses to list, no VPC work, and it is the path Google documents for Cloud Run.
3. **Way (b) only if the database is not Cloud SQL**, and way (c) only if a private address is a requirement. Both add network pieces that can fail at start for reasons unrelated to the app.

Whichever is chosen, if the existing hosted database was created before the backend's tables changed, the backend's own plan applies: it "creates missing tables and never changes one", so the old tables have to be dropped once.

## 7. Ingress and the load balancer: one address, `/api/*` to the backend

The target: the browser asks `http://ADDRESS/api/base/...`; the load balancer sends every path under `/api/` to the backend service and everything else to the frontend. The URL map does not change the path, which is what the backend wants: its routes are registered at `/api/base` and `/api/earth`.

### 7.1 Let the load balancer, and only the load balancer, reach both services

```bash
gcloud run services update BACKEND_SERVICE --region=REGION --ingress=internal-and-cloud-load-balancing
gcloud run services update FRONTEND_SERVICE --region=REGION --ingress=internal-and-cloud-load-balancing
```

Accepts requests that come through the external Application Load Balancer and refuses direct requests from the internet to the `run.app` address. The other values are `all` and `internal`. https://docs.cloud.google.com/run/docs/securing/ingress

Ingress is only the network half. The same page says "IAM authentication still applies to requests reaching the service", so a browser also needs the service to be public. There are two documented ways (https://docs.cloud.google.com/run/docs/authenticating/public):

```bash
gcloud run services update BACKEND_SERVICE --region=REGION --no-invoker-iam-check
```

Switches off the Cloud Run Invoker check. This is the way Google now recommends, and it works where an organization policy forbids granting roles to `allUsers`.

```bash
gcloud run services add-iam-policy-binding BACKEND_SERVICE --region=REGION \
  --member="allUsers" --role="roles/run.invoker"
```

The older way: gives everyone the Invoker role. `gcloud run deploy SERVICE ... --allow-unauthenticated` does the same at deploy time.

Anyone who can reach the load balancer can then call the API, including `POST /api/base/reset`. That is the design the team chose for the demo.

### 7.2 Find the parts of the existing load balancer

```bash
gcloud compute forwarding-rules list
gcloud compute target-http-proxies list
gcloud compute target-https-proxies list
gcloud compute url-maps list
gcloud compute backend-services list
```

Shows the address and port (forwarding rule), which proxy it points at, which URL map the proxy uses, and the backend service the URL map sends traffic to today. "If you originally set up your load balancer in the Google Cloud console, the URL map's name is the same as your load balancer's name." https://docs.cloud.google.com/load-balancing/docs/url-map

```bash
gcloud compute backend-services describe FRONTEND_BACKEND_SERVICE --global \
  --format="value(loadBalancingScheme)"
gcloud compute url-maps describe URL_MAP_NAME --global
```

Prints the scheme of the existing backend service and the URL map as it stands (note whether it already has `hostRules`). `EXTERNAL_MANAGED` is a global external Application Load Balancer; `EXTERNAL` is the classic one. If these fail with "not found", the load balancer is regional: use `--region=REGION` in place of `--global` here and in every command below (see 7.7). The new backend service must have the same scheme and the same scope as the existing one.

### 7.3 A serverless NEG and a backend service for the API

```bash
gcloud compute network-endpoint-groups create lighttime-api-neg \
  --region=REGION \
  --network-endpoint-type=serverless \
  --cloud-run-service=BACKEND_SERVICE
```

Creates a serverless network endpoint group that points at the backend Cloud Run service. It must be in the same region and project as the service.

```bash
gcloud compute backend-services create lighttime-api-bs \
  --load-balancing-scheme=EXTERNAL_MANAGED \
  --global
```

Creates the load balancer's backend service for the API. Use `EXTERNAL` here if 7.2 printed `EXTERNAL`.

```bash
gcloud compute backend-services add-backend lighttime-api-bs \
  --global \
  --network-endpoint-group=lighttime-api-neg \
  --network-endpoint-group-region=REGION
```

Puts the NEG behind that backend service. All three: https://docs.cloud.google.com/load-balancing/docs/https/setup-global-ext-https-serverless

No health check and no firewall rule are needed: "health checks are not supported for backend services with serverless NEG backends". The price of that, from https://docs.cloud.google.com/load-balancing/docs/negs/serverless-neg-concepts: "even if your resource is returning errors, the load balancer continues to direct traffic to it".

The frontend already has its own NEG and backend service (the existing ones). If it did not, repeat the three commands with `--cloud-run-service=FRONTEND_SERVICE` and other names.

### 7.4 Add the `/api/*` rule to the existing URL map

```bash
gcloud compute url-maps add-path-matcher URL_MAP_NAME \
  --path-matcher-name=lighttime-paths \
  --default-service=FRONTEND_BACKEND_SERVICE \
  --path-rules="/api/*=lighttime-api-bs" \
  --new-hosts="*" \
  --global
```

Adds a path matcher that sends `/api/...` to the API's backend service and everything else to the frontend's, for every host name. Command and `--path-rules` form: https://docs.cloud.google.com/load-balancing/docs/url-map. Host and path rules: https://docs.cloud.google.com/load-balancing/docs/url-map-concepts. Flags: https://docs.cloud.google.com/sdk/gcloud/reference/compute/url-maps/add-path-matcher

What the pages say about this rule:

- "A --path-rule for /video/* matches URIs such as /video/test1 and /video/test2. However, this path rule doesn't match the path /video." So `/api/*` covers every route the backend has; a bare `/api` goes to the frontend, which is fine.
- The host must be `*`. A host rule cannot be an IP address, and "It is possible to match all hostnames by specifying the wildcard character * in the host rule". Without a host rule that matches, a request goes to the URL map's default service and never sees the path rule. This matters because the demo is opened by IP address.
- If 7.2 showed that the URL map already has a host rule for `*`, the command above will probably be refused, because one host cannot sit in two host rules (not confirmed). Use `--existing-host="*" --delete-orphaned-path-matcher` in place of `--new-hosts="*"`, or use the file method below. This variant parsed in the CLI but I did not run it.

The file method, which lets you test before anything changes:

```bash
gcloud compute url-maps export URL_MAP_NAME --destination=urlmap.yaml --global
```

Saves the current URL map to a file. Keep a copy: it is also the way back.

Edit the file so it has these parts (keep the other lines as exported):

```yaml
defaultService: https://www.googleapis.com/compute/v1/projects/PROJECT_ID/global/backendServices/FRONTEND_BACKEND_SERVICE
hostRules:
- hosts:
  - '*'
  pathMatcher: lighttime-paths
pathMatchers:
- name: lighttime-paths
  defaultService: https://www.googleapis.com/compute/v1/projects/PROJECT_ID/global/backendServices/FRONTEND_BACKEND_SERVICE
  pathRules:
  - paths:
    - /api/*
    service: https://www.googleapis.com/compute/v1/projects/PROJECT_ID/global/backendServices/lighttime-api-bs
tests:
- description: the console
  host: example.com
  path: /
  service: https://www.googleapis.com/compute/v1/projects/PROJECT_ID/global/backendServices/FRONTEND_BACKEND_SERVICE
- description: the ship
  host: example.com
  path: /api/base/health
  service: https://www.googleapis.com/compute/v1/projects/PROJECT_ID/global/backendServices/lighttime-api-bs
```

```bash
gcloud compute url-maps validate --source=urlmap.yaml --load-balancing-scheme=EXTERNAL_MANAGED --global
gcloud compute url-maps import URL_MAP_NAME --source=urlmap.yaml --global
```

The first runs the tests and changes nothing. The second replaces the live URL map. Both, with the file layout: https://docs.cloud.google.com/load-balancing/docs/url-map (validate is not offered for regional load balancers).

### 7.5 Check it

```bash
curl -i http://LOAD_BALANCER_IP/api/base/health
curl -i http://LOAD_BALANCER_IP/
```

The first must be answered by the backend (JSON), the second by the console. `curl` is not a Google command. Not confirmed: how long a URL map change takes to reach every Google front end; allow a few minutes before deciding it failed. A `404` in JSON form (`{"error": "not found"}`) means the backend answered, which proves the route.

After this works, rebuild the console with `NEXT_PUBLIC_API_URL=/` (section 3).

### 7.6 If the load balancer had to be built from nothing (plain HTTP on an address)

Google's page states that HTTP is enough for a test: "If you want to test this process without setting up an SSL certificate resource (or a domain as required by Google-managed certificates), you can set up an HTTP load balancer." All commands in this subsection are from https://docs.cloud.google.com/load-balancing/docs/https/setup-global-ext-https-serverless, in the page's order.

```bash
gcloud compute addresses create lighttime-ip --network-tier=PREMIUM --ip-version=IPV4 --global
gcloud compute addresses describe lighttime-ip --format="get(address)" --global
```

Reserves a fixed public address and prints it.

```bash
gcloud compute network-endpoint-groups create lighttime-web-neg \
  --region=REGION --network-endpoint-type=serverless --cloud-run-service=FRONTEND_SERVICE
gcloud compute backend-services create lighttime-web-bs --load-balancing-scheme=EXTERNAL_MANAGED --global
gcloud compute backend-services add-backend lighttime-web-bs --global \
  --network-endpoint-group=lighttime-web-neg --network-endpoint-group-region=REGION
```

The frontend's NEG and backend service. Do 7.3 for the API as well.

```bash
gcloud compute url-maps create lighttime-map --default-service lighttime-web-bs
```

A URL map whose default is the frontend. Then add the `/api/*` rule with the command in 7.4.

```bash
gcloud compute target-http-proxies create lighttime-http-proxy --url-map=lighttime-map
```

An HTTP proxy that uses the URL map.

```bash
gcloud compute forwarding-rules create lighttime-http-rule \
  --load-balancing-scheme=EXTERNAL_MANAGED \
  --network-tier=PREMIUM \
  --address=lighttime-ip \
  --target-http-proxy=lighttime-http-proxy \
  --global \
  --ports=80
```

Opens port 80 on the reserved address and sends it to the proxy.

### 7.7 HTTPS with a Google-managed certificate (needs a domain)

"To create a Google-managed certificate, you must have a domain." Point the domain's A record at the load balancer's address first.

```bash
gcloud compute ssl-certificates create lighttime-cert --domains=DOMAIN --global
```

Asks Google for a certificate for the domain. https://docs.cloud.google.com/load-balancing/docs/ssl-certificates/google-managed-certs

```bash
gcloud compute target-https-proxies create lighttime-https-proxy \
  --ssl-certificates=lighttime-cert \
  --url-map=URL_MAP_NAME
gcloud compute forwarding-rules create lighttime-https-rule \
  --load-balancing-scheme=EXTERNAL_MANAGED \
  --network-tier=PREMIUM \
  --address=lighttime-ip \
  --target-https-proxy=lighttime-https-proxy \
  --global \
  --ports=443
```

An HTTPS proxy on the same URL map and a rule for port 443 on the same address. https://docs.cloud.google.com/load-balancing/docs/https/setup-global-ext-https-serverless

```bash
gcloud compute ssl-certificates describe lighttime-cert --global \
  --format="get(name,managed.status, managed.domainStatus)"
```

Shows `PROVISIONING` until the certificate is issued, then `ACTIVE`. From the certificate page: issuing "might take up to 60 minutes" after DNS has spread, the forwarding rule "must use TCP port 443", and after `ACTIVE` "it can take up to 30 minutes" before the load balancer serves it. For a demo on the same day, plain HTTP on the address is the safe choice, with HTTPS added only if there is an hour to spare.

Regional load balancers cannot use this kind of certificate: "Compute Engine Google-managed SSL certificates aren't supported for regional external Application Load Balancers".

### 7.8 If the existing load balancer is regional

A regional external Application Load Balancer lives in a VPC network with a proxy-only subnet, which may be why the project has a VPC. The commands are the same with `--region=REGION` in place of `--global`, and the backend service needs a protocol:

```bash
gcloud compute backend-services create lighttime-api-bs \
  --load-balancing-scheme=EXTERNAL_MANAGED \
  --protocol=HTTP \
  --region=REGION
gcloud compute backend-services add-backend lighttime-api-bs \
  --region=REGION \
  --network-endpoint-group=lighttime-api-neg \
  --network-endpoint-group-region=REGION
```

"Set the --protocol to HTTP. This parameter is ignored but it is required". https://docs.cloud.google.com/load-balancing/docs/https/setting-up-reg-ext-https-serverless Then run the 7.4 command with `--region=REGION`. A regional backend service "can only have one serverless NEG attached to it".

## 8. Operating it: logs, revisions, rollback, and a revision that will not start

### 8.1 Logs

```bash
gcloud run services logs read BACKEND_SERVICE --region=REGION --limit=50
```

Prints the newest log lines of the service in a readable form. Gunicorn writes its access and error logs to standard output, so every request and every Python traceback is here. https://docs.cloud.google.com/run/docs/logging

```bash
gcloud beta run services logs tail BACKEND_SERVICE --region=REGION
```

Follows the log live. It is a `beta` command on Google's page; the beta component was not installed where I checked, so it was not parsed locally. Same page.

```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=BACKEND_SERVICE" --limit 10
```

Reads the same entries straight from Cloud Logging. The quoted filter is also what to paste into Logs Explorer in the console, which "provides more details and more filtering capabilities". Same page.

For a build that failed rather than a service:

```bash
gcloud builds list --region=REGION --limit=5
gcloud builds describe BUILD_ID --region=REGION
```

Lists recent builds with their status, and shows one in detail, step by step. https://docs.cloud.google.com/build/docs/view-build-results (`--region` and `--limit` parsed locally; the page shows the commands without them.)

### 8.2 Revisions

```bash
gcloud run revisions list --service BACKEND_SERVICE --region REGION
```

Lists the service's revisions. Revision names look like `BACKEND_SERVICE-00012-abc`. https://docs.cloud.google.com/run/docs/managing/revisions

```bash
gcloud run revisions describe REVISION --region REGION
```

Shows one revision in detail. Same page.

### 8.3 Roll back, and go forward again

```bash
gcloud run services update-traffic BACKEND_SERVICE --region=REGION --to-revisions REVISION=100
```

Sends all traffic to the named older revision. The page warns that this "updates the routing configuration immediately; Cloud Run does not re-run deployment health checks". https://docs.cloud.google.com/run/docs/rollouts-rollbacks-traffic-migration

```bash
gcloud run services update-traffic BACKEND_SERVICE --region=REGION --to-latest
```

Returns to "always serve the newest revision". Same page.

Do not skip the second command. "If you ... assigned traffic to a previous revision, all subsequent deployments use that traffic split pattern going forward." After a rollback, every later merge still builds and deploys, but the new revisions get no traffic until `--to-latest` is run. With automatic deploys this looks exactly like "my change did not go out".

For the backend, a rollback starts an instance of the old revision, so the mission clock goes back to 06:30 and, on a shared Postgres database, the demo tables are reloaded.

### 8.4 What happens when a new revision fails to start

- "By default, Cloud Run checks that your deployment is healthy by starting an instance and waiting for its startup probe to pass. If the health check fails, the revision will be marked as unhealthy and the traffic won't be routed to it." https://docs.cloud.google.com/run/docs/deploying
- "Cloud Run automatically routes requests as soon as possible to the latest healthy service revision." https://docs.cloud.google.com/run/docs/resource-model
- The instance has 4 minutes: "your instances must listen for requests within 4 minutes after being started". https://docs.cloud.google.com/run/docs/container-contract

So the site keeps working on the previous revision and shows no error. The failure is visible in three places: the deploy command or the build fails with "Container failed to start. Failed to start and then listen on the port defined by the PORT environment variable", the console marks the newest revision as failed, and the logs hold the reason. Google's checklist for that error: the container must run locally, listen on `PORT`, listen on `0.0.0.0`, be a 64-bit Linux image, and the logs must be read for application errors. https://docs.cloud.google.com/run/docs/troubleshooting

What this backend's own failures look like (observed on a copy run with the Dockerfile's gunicorn command, not on Cloud Run):

- **The database refuses or closes the connection.** Gunicorn logs a Python `OperationalError`, then "Worker failed to boot", and the container exits with code 3 within a second or two.
- **The database accepts the connection and never answers** (what an address that is not on the allowlist can look like). The worker stays in start-up for as long as I watched, the port is already open, and requests get no answer. Gunicorn's worker timeout did not end it.

The second case is why section 4.6 matters: the default check only asks whether the port is open, and gunicorn opens the port before the app is built. Either way the cure is in section 6, not in the container.

Because a load balancer with a serverless NEG cannot tell a broken backend from a working one (section 7.3), check after every deploy that the newest revision is the one serving, then call `/api/base/state` a few times and confirm the time only moves forward.

## 9. Cost notes

One always-on backend instance at the smallest size instance-based billing allows (1 vCPU and 512 MiB) costs 86,400 seconds times ($0.000018 per vCPU-second plus half of $0.000002 per GiB-second), which is about **$1.64 a day** in a Tier 1 region such as `us-central1`, and about **$1.97 a day** in a Tier 2 region such as Toronto or Montreal, where the rates are $0.0000216 and $0.0000024. Both figures are before the monthly free allowance for instance-based billing, 240,000 vCPU-seconds and 450,000 GiB-seconds, which covers about 2.8 days of this instance's CPU if nothing else on the billing account uses it. The frontend can stay on the default request-based billing with no minimum, where it is charged only while it answers requests. The smallest Cloud SQL tier, `db-f1-micro` (shared core, 0.6 GiB of memory, Enterprise edition, not covered by the Cloud SQL SLA), is $0.0105 an hour in `us-central1`, about **$0.25 a day**, plus SSD storage at $0.000232877 per GiB-hour, about $0.06 a day for 10 GB; stopping the instance with `gcloud sql instances patch INSTANCE_NAME --activation-policy=NEVER` "suspends instance charges" but "charges for storage and IP addresses continue to apply". Sources: https://cloud.google.com/run/pricing, https://cloud.google.com/sql/pricing and https://docs.cloud.google.com/sql/docs/postgres/start-stop-restart-instance. Not looked up: the load balancer's own charges, Artifact Registry storage, Cloud Build minutes, and a NAT gateway or VPC connector if section 6.3 or 6.4 is used.

## 10. The two Dockerfiles on Cloud Run

Read from the `Dockerfile` of each repository (backend `Tj-Backend` at `3d679f8`, console `feat/live-ship` at `05ac88c`). Docker was not running where I worked, so neither image was built. The backend was instead run from a copy with the Dockerfile's exact gunicorn command.

### 10.1 Backend: nothing that breaks, four things to know

| Point | Finding |
|---|---|
| Port | Good. Gunicorn binds `0.0.0.0:${PORT}` and `PORT` defaults to 8080. Cloud Run requires listening "on 0.0.0.0 on the port to which requests are sent" and sets `PORT` itself. |
| User | Good. It runs as `appuser` (uid 10001) and `/app` belongs to that user. Google's advice is "Prefer containers that don't use or rely on the root user". |
| One process | Good. `--workers 1 --threads 8`. Run that way, a story's thread stored 3 readings a second and `/api/base/health` answered 200. |
| Files | Good. Everything the code opens at run time (`data/processed/...`, `data/clean/...`, `base_station/limits.json`) is in the image. `.dockerignore` leaves out only `tests`, `.env`, `instance`, `*.db`, `data/cache` and caches, and `.gitignore` leaves out only generated `packets.csv` files, which no route reads. |
| Logs | Good. Access and error logs go to standard output, where Cloud Logging collects them. |

To know:

1. **Start-up does real work.** `create_app()` runs inside the worker as it boots: it creates tables, loads the demo morning and asks NASA JPL twice with a 5 second limit each. On a local socket database this took 1.1 seconds. If outbound internet is blocked, add up to 10 seconds and expect `light_time_source` to say "read on 2026-11-13". If the database refuses the connection the container exits with code 3; if it never answers, start-up hangs with the port open (section 8.4). Set the start-up check in section 4.6.
2. **Unpinned versions.** `requirements.txt` uses `>=` for every package, so each build installs whatever is newest that day (today: gunicorn 27.0.1, SQLAlchemy 2.1.8, psycopg 3.3.9, Flask 3.1.3). A rebuild on demo day could pick up a release nobody has tested. Pinning is the team's decision.
3. **The SQLite fallback works but lives in memory** (section 6.5).
4. **`pytest` is installed in the image** and `EXPOSE 8080` is only a label. Neither matters to Cloud Run.

### 10.2 Frontend: correct, and the build argument is wired correctly

| Point | Finding |
|---|---|
| Port and host | Good. `ENV PORT=8080`, `ENV HOSTNAME=0.0.0.0`, `CMD ["node", "server.js"]`. Next.js says the standalone server reads both: "run `PORT=8080 HOSTNAME=0.0.0.0 node server.js`". Cloud Run's own `PORT` replaces the default. |
| User | Good. Runs as `nextjs` (uid 1001); the copied files belong to it. |
| Files | Good for this repository. The image copies `.next/standalone` and `.next/static`. Next.js "does not copy the `public` or `.next/static` folders by default", and the Dockerfile handles `static`. There is no `public` folder in the repository, so nothing is missing. If one is ever added, the Dockerfile needs a `COPY` line for it. |
| Config | Good. `next.config.ts` has `output: "standalone"`, which the Dockerfile depends on. |
| No clash with `/api/*` | Good. The app has no route, rewrite or middleware under `/api`, and every request the console makes goes to `/api/base/...` or `/api/earth/...`, so the load balancer rule in section 7 takes nothing away from the frontend. |

The build argument:

```dockerfile
ARG NEXT_PUBLIC_API_URL=""
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

RUN pnpm build
```

This is right. The `ARG` and `ENV` lines sit in the `builder` stage before `pnpm build`, so the value is in the environment of the build, which is when Next.js reads it: it replaces `process.env.NEXT_PUBLIC_...` "with the value from the environment in which you run `next build`". The code reads it by its full literal name in one place (`src/lib/ship-api.ts`), which matters because "dynamic lookups will not be inlined". `.dockerignore` keeps every `.env*` file out, so nothing can override the argument.

What follows from that:

- With no argument the default is the empty string and the console is the built-in demo. With `--build-arg NEXT_PUBLIC_API_URL=/` the code turns `/` into an empty base, so the browser asks `/api/base/...` and `/api/earth/...` at the address the page came from.
- **Setting `NEXT_PUBLIC_API_URL` on the Cloud Run service does nothing.** "After being built, your app will no longer respond to changes to these environment variables." The value has to be given to the build (section 3).
- The build needs the network: `corepack enable` downloads pnpm 10.24.0 and `pnpm install --frozen-lockfile` downloads the packages. Cloud Build has it.

Next.js sources: https://nextjs.org/docs/pages/api-reference/config/next-config-js/output and https://nextjs.org/docs/pages/guides/environment-variables. These are the public Next.js pages, not the copy shipped inside this project's `next` 16.4.6 package, which the repository's `AGENTS.md` says to prefer; I could not read that copy because `node_modules` is not in the audit folder. Not confirmed by a real build: I did not run `pnpm build` or `docker build`.

## Not confirmed

About the method:

1. Nothing was run against a real Google Cloud project. Each command was read on the page named beside it and its flags were parsed by a local CLI (version 570.0.0) with no account. A command can parse and still fail on a real project for reasons of permissions, quotas or organization policy.
2. Three `gcloud beta` commands (`beta run services logs tail`, `beta sql instances patch`, `beta run instances create`) are on Google's pages but could not be parsed locally, because the beta component was not installed.
3. These were parsed locally but not looked up on a documentation page: `gcloud projects describe PROJECT_ID --format="value(projectNumber)"`, `gcloud sql instances list`, the `--format="value(connectionName)"` shortcut, and `--region` and `--limit` on `gcloud builds list`.
4. No container image was built (no Docker daemon) and `pnpm build` was not run. The frontend findings come from reading the Dockerfile, the code and the public Next.js pages, not the Next.js 16 documents inside the project's own packages.

About the existing setup (only the team can answer):

5. Which kind the existing load balancer is (global, classic or regional) and the names of its URL map and backend service. Section 7.2 finds out.
6. Whether the existing "allowlisted" database is a Cloud SQL instance. Section 6 depends on it.
7. The exact build steps inside the triggers that the Cloud Run click-through created. The page does not print them. `gcloud builds triggers describe` shows them.

About Google Cloud behaviour:

8. Whether manual scaling (`--scaling=1`) avoids the short second instance during a deploy or during maintenance. The pages state the overlap for the per-revision maximum and say nothing either way for manual scaling.
9. What `--min-instances` and `--max-instances` do on a service that never used them. The pages only say revision-level scaling is "only available for services that previously had the feature configured".
10. Whether a build environment variable (`--set-build-env-vars`) reaches a Dockerfile `ARG`. The page speaks only of buildpacks.
11. `gcloud builds triggers update github TRIGGER_NAME --build-config=cloudbuild.yaml` on a trigger made by the Cloud Run flow. The flags are documented; the result on such a trigger was not seen.
12. `add-path-matcher` when the URL map already has a host rule for `*`, and the `--existing-host` variant. Also how long a URL map change takes to take effect.
13. Whether a load balancer can route to the new "Cloud Run instance" resource (Preview).
14. The start-up reasoning in 4.6 and 8.4 on Cloud Run itself: that the default TCP check can pass while gunicorn's worker is still starting, and in which order Cloud Run sees "port open" and "container exited" when the worker fails within a second.
15. The time needed to create a Cloud SQL instance, and whether a user made with `gcloud sql users create` can create tables in a database made with `gcloud sql databases create` (expected, since it is given `cloudsqlsuperuser`, but not tested on Cloud SQL).

About the database URL:

16. The psycopg 3 form `postgresql+psycopg://DB_USER:DB_PASSWORD@/DB_NAME?host=/cloudsql/PROJECT_ID:REGION:INSTANCE_NAME` is not printed on a Google page. Google shows `pg8000` and describes psycopg2's `host` form. It was confirmed against a local PostgreSQL 16 socket in a folder named like a connection name, not against a real Cloud SQL socket.
17. `?sslmode=require` for a direct connection to a public or private address is not from a Google page.

About cost:

18. The Tier 2 rates ($0.0000216 and $0.0000024) were read from the data inside the Cloud Run pricing page for Toronto and Montreal, not from the table as displayed. The Cloud SQL prices are the ones shown for `us-central1`; other regions differ. Load balancer, NAT, connector, Artifact Registry and Cloud Build charges were not looked up.

About things outside Google's pages:

19. Git Bash on Windows rewriting the `/` in `--build-arg NEXT_PUBLIC_API_URL=/`, and PowerShell's handling of `echo -n` and quotes. Not tested; no Windows machine here. Cloud Shell avoids both.
20. Memory on Cloud Run. The 97 MiB figure was measured locally with Python 3.13 and gunicorn 27.0.1; the image uses Python 3.12. The 512 MiB setting was not tested under load.
21. Keeping `--concurrency=80` is my recommendation, reasoned from the pages, not a Google statement.
