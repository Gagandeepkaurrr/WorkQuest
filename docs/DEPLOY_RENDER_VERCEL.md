# Deploy WorkQuest with Render and Vercel

Prepared on 2026-11-12. The configuration is supplied and locally schema-checked; **no Render or Vercel deployment has been performed**. Render resources in this Blueprint are paid. Review the plans before applying it.

Vercel serves the React SPA and forwards `/api/*` to Render. Browser cookies and CSRF remain under the Vercel origin. Render runs FastAPI, a Celery worker, the durable dispatcher, hourly cleanup, PostgreSQL 18, and private Key Value. Workers and API must use identical secrets and database settings.

## 1. Install the deployment CLIs and link the frontend

From the repository root on macOS:

```sh
brew install render
render login
pnpm dlx vercel@65.14.0 login
pnpm dlx vercel@65.14.0 link
```

Create/select a Vercel project named `workquest` (or your own available name). Keep **Root Directory at the repository root**, use Node 24.x, and retain the build/output overrides from `vercel.json`. Find the final production domain in Project Settings → Domains. It might differ from `workquest.vercel.app`; use your actual domain throughout. `.vercel/` is gitignored.

## 2. Create the Render backend

```sh
render blueprints validate render.yaml
```

The CLI validation requires your Render workspace. It has **not** been run against an account. The local JSON-schema validation does not prove account quotas, region availability, secret setup, billing or runtime health.

In the [Render dashboard](https://dashboard.render.com/), choose **New → Blueprint**, connect **Gagandeepkaurrr/WorkQuest**, select `main` and `render.yaml`, review the proposed services, and apply. Initial Blueprint creation is a dashboard step; there is no fabricated one-command deploy in this guide.

Supply the prompted settings in the shared `workquest-shared` environment group:

| Setting | Value |
|---|---|
| `APP_ORIGIN` | Exact final Vercel origin, e.g. `https://your-workquest.vercel.app`, without a trailing slash |
| `DELIVERY_PAYLOAD_ENCRYPTION_KEY` | A new Fernet key, identical across all backend processes |
| `SMTP_HOST`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM` | Your actual transactional email service and verified sender |
| `SMTP_PORT`, `SMTP_TLS` | Default 587 / `starttls`; use the provider's actual settings |
| `SESSION_SECRET`, `METRICS_TOKEN` | Generated once by the shared environment group |

Generate a Fernet key into a private local file, copy its value into Render's secret field, then remove the temporary file after recording it in your password manager:

```sh
umask 077
uv run --project apps/api python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())' > .delivery-key
```

Do not commit `.delivery-key`, environment files or credentials. Prefer your password manager's private scratch area; `.delivery-key` is ignored by this repository. PostgreSQL and Redis URLs are injected from Render resources. Standard `postgresql://` URLs are normalized to psycopg by the backend. `RENDER_EXTERNAL_HOSTNAME` is recognized automatically as an exact allowed backend host.

The Blueprint deliberately enables a visibly labelled public **mock AI** mode (`AI_PROVIDER=mock`, `PUBLIC_MOCK_DEMO=true`) and disables guest accounts in production. For real AI, set `AI_PROVIDER=gemini`, an available `AI_MODEL`, and `GEMINI_API_KEY` in the shared group, then restart API, worker and dispatcher. Keep credentials out of Vercel/frontend environment variables.

The API pre-deploy command runs migrations and an idempotent seed. Take a backup before later migrations. Existing administrator-published scenario versions remain selected when seeding again.

## 3. Connect Vercel to the Render API and deploy

Find the Render API URL (for example `https://workquest-api-xxxx.onrender.com`), then:

```sh
python3 scripts/configure-vercel.py --api-origin https://YOUR-API.onrender.com
pnpm dlx vercel@65.14.0 deploy --prod
```

The helper edits the public backend destination in `vercel.json`; it does not accept credentials or deploy anything. Commit that hostname change if using future Git deployments. No browser `VITE_API_URL` or cross-origin cookie configuration is required. Preview domains are intentionally rejected by the production `APP_ORIGIN`; use a separate staging backend for preview testing.

## 4. Resolve the proxy identity gate before opening registration

**Hosted release blocker: the Render → Vercel proxy chain is not verified.** The Blueprint initially trusts only `127.0.0.1` for forwarded client addresses. Until you configure and verify the exact trusted proxy addresses/chain, requests can share the ingress IP's authentication limit (30 requests/minute), preventing a multi-user launch.

Set the API service's `FORWARDED_ALLOW_IPS` to the platform's verified proxy IPs/CIDRs. Test the actual two-provider chain with two separate clients and a forged `X-Forwarded-For` request: clients must have separate rate-limit buckets, and a client-supplied header must not control its identity. Do **not** set `*` merely to make throttling disappear. If the provider cannot supply a verifiable chain, use a trusted gateway with authenticated client-address forwarding, or use the documented single-origin Compose deployment, whose exact proxy trust is configured. This gate cannot be resolved by local mock tests.

## 5. Admin setup, updates and hosted smoke checks

```sh
render services
# Replace each service ID with the actual ID returned by Render.
render deploys create srv-API --wait
render deploys create srv-WORKER --wait
render deploys create srv-DISPATCHER --wait
render ssh srv-API
# In the Render shell:
python -m app.cli.create_admin
# Optional, intentionally billable real-provider probe after configuring Gemini:
python -m app.cli.validate_provider --live
```

Render SSH requires an SSH key on your account. If SSH is unavailable, use the service's interactive dashboard shell. Never put the admin password in a command argument.

After deployment, check:

```sh
curl --fail https://YOUR-API.onrender.com/health/live
curl --fail https://YOUR-API.onrender.com/health/ready
curl --fail --head https://YOUR-FRONTEND.vercel.app/
```

Then use the public browser UI to sign up, receive a real verification email, log in, finish a mission, receive a teammate reply, reload, fork, create/revoke a report, reset the password, and sign out. Inspect `__Host-wq_session` for Secure/HttpOnly/SameSite=Lax/Path=/ with no Domain attribute. Verify CSRF rejects another origin, SSE reconnects through Vercel, API/report responses are never cached, and secret URLs are excluded/redacted in provider logs. Test proxy identity as above, worker/dispatcher recovery, and an encrypted offsite restore. Keep public signup closed (`PUBLIC_SIGNUP_ENABLED=false`) until these gates pass.

A Vercel deployment is not a database rollback. Redeploy a previous application commit only when it is compatible with the current database schema; see [operations](OPERATIONS.md). Hosted streaming duration, SMTP delivery, Gemini evaluation, custom domain/TLS, billing limits, backup RPO/RTO and this entire hosted smoke flow remain **NOT VERIFIED**.

Official references checked for these commands/configuration: [Render CLI](https://render.com/docs/cli), [CLI reference](https://render.com/docs/cli-reference), [Blueprint specification](https://render.com/docs/blueprint-spec), [Docker services](https://render.com/docs/docker), [Vercel CLI deployment](https://vercel.com/docs/projects/deploy-from-cli), [external rewrites](https://vercel.com/docs/routing/rewrites), [Vercel forwarded headers](https://vercel.com/docs/headers/request-headers).
