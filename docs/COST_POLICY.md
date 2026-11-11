# No API credits and no hosting charges

Updated 2026-11-12. The user's latest instruction overrides the original specification's live-model adapter and managed-hosting requirements.

The supported complete deployment is **local on your existing computer**:

```sh
make setup
make dev
```

PostgreSQL, Redis and Mailpit run locally in Docker. React, FastAPI, the worker and dispatcher run locally. No cloud account, model download, payment card, SMTP subscription, OpenAI/GPT credit, Gemini token or other AI API key is needed. Normal use does not call an external language model.

## Enforced in code

- `AI_PROVIDER=local` is the only supported provider. The former `mock` value maps to `local` for existing installations. Paid provider selections fail configuration validation, even if credentials are present.
- The Gemini adapter and Google GenAI SDK are removed. There is no OpenAI, Anthropic or other live-model adapter, fallback, credential setting or billable probe.
- The job worker always uses the authored local provider. Old job metadata cannot select a remote provider.
- Replies cite only permitted scenario facts; coaching is authored guidance. This is a built-in simulation, not a general-purpose language model.
- Provider results require zero model tokens. New completed reply attempts record known zero API cost. Request/retry limits remain to protect local resources, not as paid credits.
- No analytics, model API or remote font service is required by the application. Package installation and container pulls use the network during setup; the application stack and teammate engine run locally afterward.

Verify the cost boundary with `uv run --project apps/api pytest apps/api/tests/unit/test_free_runtime.py apps/api/tests/unit/test_config.py`. The tests block sockets during dialogue/coaching and the worker path, reject paid provider settings, and prove zero token usage. `cd apps/api && uv run python -m app.cli.validate_provider` is an offline check, with no `--live` mode.

## Hosting boundary

The default `render.yaml` intentionally declares **no resources**. The former paid API/worker/dispatcher/cron/database/Key Value stack is disabled. No managed services were provisioned by this work, and no paid deployment is authorized.

Render's full previous architecture cannot be truthfully called free: background workers/cron have no free compute instances, and free Render PostgreSQL expires after 30 days. Its free web tier also has sleep, usage and SMTP restrictions. [Render free services](https://render.com/docs/free), [service availability](https://render.com/docs/your-first-deploy).

`vercel.json` is retained for a possible frontend-only deployment. Vercel Hobby is currently free for eligible personal/non-commercial use within its limits, but does not host this application's PostgreSQL/Redis/worker backend. No Vercel deployment was performed. Never upgrade to a paid plan or add billable infrastructure on behalf of this project without a new user decision. [Vercel Hobby](https://vercel.com/docs/plans/hobby).

Free public hosting for the complete persistent application is **not provided or verified** by this change. The full supported no-service-fee setup is local. This policy covers WorkQuest runtime and infrastructure; it does not change the billing or usage limits of the coding/chat tool used to develop it, or unrelated existing hosting resources.
