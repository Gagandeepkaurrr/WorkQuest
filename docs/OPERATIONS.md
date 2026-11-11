# Operations and data handling

**Current cost policy:** operate the full app locally with `make setup` / `make dev`. No external AI providers or paid hosting are authorized. The single-host production reference below is for already-owned hardware; it is not an instruction to provision paid infrastructure. See [COST_POLICY.md](COST_POLICY.md).

This is a small deployment reference, not a high-availability design. See [Render + Vercel](DEPLOY_RENDER_VERCEL.md) for the requested managed-hosting commands and its unverified proxy gate.

## Single-origin deployment

Use `infra/compose.production.yaml` on a dedicated host with Docker Compose and an application domain. It keeps PostgreSQL/Redis private, places Caddy in front of Nginx, and uses explicit trusted addresses: Caddy `172.30.0.5` → Nginx `172.30.0.4` → API. Ensure that subnet does not conflict with the host network. Nginx overwrites forwarded client headers; Uvicorn trusts only Nginx. Public TLS has not been exercised here.

Prepare a root-readable private environment file outside Git with production values from `.env.example`: `APP_ENV=production`, exact HTTPS `APP_ORIGIN`, private database/Redis URLs, random session secret, Fernet delivery key, metrics token, TLS SMTP, `DEMO_ENABLED=false`, and verified email. Use `AI_PROVIDER=local`; no external model credentials are supported. Share the same file with API/worker/dispatcher/maintenance. Restrict the Docker socket and host administrator access.

Build and push images to your chosen private/trusted registry, scan them, and set `API_IMAGE` and `WEB_IMAGE` to immutable `name@sha256:...` digests. Also set `APP_ENV_FILE` to the absolute private file path, `APP_DOMAIN`, and `POSTGRES_PASSWORD` in the operator's environment. The registry and domain are not provisioned by this repository.

```sh
docker build -f apps/api/Dockerfile -t YOUR_REGISTRY/workquest-api:RELEASE .
docker build -f apps/web/Dockerfile -t YOUR_REGISTRY/workquest-web:RELEASE .
docker scout cves --only-severity critical,high YOUR_REGISTRY/workquest-api:RELEASE
docker scout cves --only-severity critical,high YOUR_REGISTRY/workquest-web:RELEASE
# Push the two reviewed images, resolve their registry digests, and configure the variables above.
docker compose -f infra/compose.production.yaml up -d db redis
# Take and verify a pre-migration backup before upgrading an existing database.
docker compose -f infra/compose.production.yaml run --rm migrate
docker compose -f infra/compose.production.yaml run --rm migrate python -m app.cli.seed
docker compose -f infra/compose.production.yaml up -d api worker dispatcher web edge
docker compose -f infra/compose.production.yaml exec api python -m app.cli.create_admin
```

Schedule `docker compose -f infra/compose.production.yaml run --rm cleanup` hourly through the host scheduler. Run the complete hosted smoke checklist before opening traffic. Managed PostgreSQL/Redis can replace the two datastore services by changing private connection URLs and enabling provider-required TLS; never expose a Redis broker to the internet.

## Monitoring and incident steps

`/health/live` checks process liveness; `/health/ready` checks PostgreSQL and Redis. `/metrics` requires `Authorization: Bearer <METRICS_TOKEN>`. Keep its scrape target private. Structured API logs use request IDs and route templates, never raw secret-bearing URLs or request bodies. Provider job records contain correlation IDs, sanitized outcomes and token counts; no prompts or model response bodies are logged. Disable provider access-log collection of verification/reset/share paths or configure redaction at the edge; application redaction cannot control a hosting provider's logs.

Track HTTP latency/error counters, database pool checked-out connections, active SSE streams, job status and oldest queued age, local reply outcomes/request totals, quota-limited jobs and failed email counts. Administrator Operations exposes aggregate job health.

- **Oldest queued job >120s for five minutes:** check dispatcher and worker processes, database readiness and Redis connectivity. Restart the failed process; let the dispatcher redispatch durable IDs. Do not manually republish prompts or clear database job records.
- **Repeated expired leases or failed jobs:** inspect sanitized error codes, deployment compatibility, timeout settings and provider health. A stale worker cannot publish after lease rotation. Retries are counted as local requests and cannot create model API charges.
- **Database/Redis loss:** close registration, restore connectivity, inspect readiness and quota/job recovery, then run a bounded mission smoke test. Never bypass rate/quota checks to conceal an outage.
- **Local teammate failures:** inspect sanitized job errors and restart the worker/dispatcher consistently. There is no external provider or billable token usage. Deterministic missions and existing scores remain usable while conversation is unavailable.
- **Email failures:** check SMTP TLS, credentials, verified sender and encrypted payload expiry. Restore delivery and request a fresh verification/reset link when the old one has expired. Do not log or paste the payload/token.

Configure alerts in your monitoring provider; alert delivery is not configured or verified here. Logs should rotate after 30 days; sanitized operational job metadata after 90 days. The CLI handles database retention, while hosting/log-storage retention must be configured separately.

## Backups, restoration and rollback

Default operating targets: **RPO 24 hours, RTO four hours**, both **unverified in production**. Take daily PostgreSQL custom-format backups and a pre-migration backup. Encrypt before upload using your organization's backup encryption system (for example age/KMS), store in a private bucket with least-privilege credentials, retain 30 days, and monitor upload failures. Keep encryption keys separate from backups. Managed PITR is optional and must be rehearsed.

`make backup-restore` is the tested local rehearsal: it uses a generated disposable database, restores a temporary dump, checks schema/row counts/pinned scenario hashes/checkpoints/replay hashes, also upgrades a seeded previous-migration fixture, and drops only those generated databases. It never overwrites the live database. The temporary dump is deleted afterward. It requires existing local practice data (the browser journeys supply it).

For a real recovery, choose an explicit new database, decrypt the selected backup privately, restore with `pg_restore --no-owner --exit-on-error --dbname=NEW_DATABASE`, run schema/hash/replay checks, then switch application connection settings only after validation and authorization. Restrict restoration credentials and record backup timestamp, recovery duration and the measured RPO. Never restore into an unspecified or live target.

Application rollback means redeploying the previous image digest only if compatible with the current schema. Prefer expand/contract migrations. Do not automatically downgrade or destructively restore a database to roll back code. A schema-incompatible rollback requires a reviewed data recovery plan.

## Retention and keys

Expired demo accounts are removed after their two-hour lifetime. Single-use token records and encrypted email/share-replay payloads are deleted after use/expiry; public share replay is recoverable for 30 minutes. AI context is purged once a terminal job is older than seven days; terminal AI job metadata/outbox records after 90 days. Learner notes/activity remain until account deletion. Account deletion revokes access and removes related data immediately; earlier encrypted backups can retain deleted records until the 30-day backup retention expires. Reapply deletion records if restoring an older backup before serving traffic.

Key rotation is operational: drain outstanding email/share-replay payloads before replacing the one active delivery encryption key and increment `DELIVERY_KEY_VERSION` consistently on all processes. A multi-key decrypting keyring is not implemented; emergency rotation invalidates pending payloads and requires fresh links. Rotate session secrets/SMTP credentials through the secret manager, restart consistently, and revoke sessions when compromise is suspected. Never expose keys through frontend variables, process arguments, logs or commits.
