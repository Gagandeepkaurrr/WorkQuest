# WorkQuest

A workplace practice app: investigate an incident, talk with a simulated team, make decisions, and compare the consequences. Three complete missions cover a checkout outage, inventory overselling, and an analytics timezone error. A white glass interface, bold Inter typography, sage/cobalt accents, and a pegboard mission board give it a calm, tactile feel.

React + TypeScript + Vite · FastAPI + SQLAlchemy · PostgreSQL 18 · Redis + Celery. The deterministic engine owns state, logical time, verification and scores. Built-in authored teammates provide evidence-based conversation and optional coaching. They use no external model, API key, tokens or credits, and cannot execute actions or assign points.

![WorkQuest white glass interface with a pegboard mission preview](docs/screenshots/landing.png)

## Run locally

Prerequisites: Docker Desktop/Engine with Compose, Node **24.22.1**, pnpm **11.25.0**, Python **3.14.10**, and uv **0.13.6**. uv can install the pinned Python automatically. Start Docker first.

```sh
git clone https://github.com/Gagandeepkaurrr/WorkQuest.git
cd WorkQuest
make setup
make dev
```

For this existing checkout, use `cd /Users/gaggu/WorkQuest` and run the last two commands. `make setup` preserves an existing `.env`, generates random local secrets when absent, installs locked dependencies, starts PostgreSQL/Redis/Mailpit, migrates, seeds the three missions, and prepares Chromium. `make dev` runs the API, React app, worker and dispatcher; Ctrl-C stops those four processes.

- App: **http://localhost:5173**
- Local email inbox: **http://localhost:8025** — sign up in the app and follow the verification email here.
- API documentation: **http://localhost:8000/docs** (local only).
- `Try the demo` creates an isolated two-hour local practice account. No default learner or administrator credentials exist.

```sh
make admin       # prompts privately for email, display name and password
make verify      # backend lint/types/tests, scenario checks, contract drift, frontend lint/tests/build
make e2e         # desktop + mobile browser journeys; keep make dev running
make audit       # package audits and redacted source credential scan
make backup-restore
make load        # isolated 20-learner, five-minute local exercise
```

Admin creation is explicit. Promoting an existing account requires its current password. Sign in afterward and use Administration. No HTTP role-promotion endpoint exists.

A production-style local container preview is available with `make containers` at **http://localhost:8080**. Stop `make dev` before using that mode: the workers must share one consistent origin configuration. Stop containers with `make stop`; this preserves database volumes. Do not run `docker compose down -v` unless you intend to delete local data.

## Free runtime and hosting policy

The complete supported setup runs on your existing computer with **no AI API credits and no cloud hosting fees**. PostgreSQL, Redis and the Mailpit email inbox run locally. `AI_PROVIDER=local` is enforced; the old `mock` value remains a compatible alias. External model adapters and SDKs have been removed, and paid provider settings are rejected.

Teammates use authored scenario facts and rule-based replies, not a general-purpose language model. Coaching also runs locally. Check it without any billable request:

```sh
cd apps/api
uv run python -m app.cli.validate_provider
```

The previous paid Render deployment is disabled: `render.yaml` provisions no resources. `vercel.json` is retained for optional frontend hosting, but a frontend alone does not host the complete backend. No cloud services have been deployed. See [cost policy](docs/COST_POLICY.md) and [hosting notes](docs/DEPLOY_RENDER_VERCEL.md). Do not apply the older paid deployment instructions from Git history.

## Where things live

- `apps/web/src`: routes, accessible dialogs, evidence/actions/workspace, branch comparisons, debrief, admin and settings.
- `apps/api/app/engine`: pure mechanics, visibility, scoring and replay.
- `apps/api/content/scenarios`: backend-only authored definitions, golden and negative vectors.
- `apps/api/app/modules`: accounts, persistent runs, checkpoints, conversations, reports and administration.
- `apps/api/app/jobs`: PostgreSQL-backed durable work, quota reservations, fenced leases and recovery.
- `packages/contracts`: exported OpenAPI and scenario schema. `make contracts` regenerates frontend types.
- `infra`: non-root production images/proxy and vendor-neutral Compose reference.

Read [build status](docs/BUILD_STATUS.md), [release checks](docs/RELEASE_CHECKLIST.md), [requirements evidence](docs/REQUIREMENTS_MATRIX.md), [operations](docs/OPERATIONS.md), and [limitations](docs/KNOWN_LIMITATIONS.md) before a release. Local success is not evidence of a verified public deployment.
