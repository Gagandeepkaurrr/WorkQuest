# WorkQuest build status

Updated: 2026-11-12, Asia/Kolkata. Repository: `/Users/gaggu/WorkQuest`. Authorized GitHub destination: **Gagandeepkaurrr/WorkQuest only**.

**No-charge release verified locally; push and clean-runner CI pending. Complete supported operation is local.** The complete 1,617-line supplied specification is preserved in PROJECT_SPECIFICATION.txt. The repository was initially empty; no applicable AGENTS.md existed. User styling instructions supersede the dark-default specification.

## No-charge change — 2026-11-12

The user explicitly requires no AI/API credits **and no hosting charges**. This overrides the original live-provider and managed-hosting requirements. External model code/SDK/keys are removed; local authored teammates and coaching are the sole runtime, with zero token/cost records. Paid provider selections fail closed. The default Render Blueprint is disabled (no resources); the complete supported deployment is local. No Render/Vercel resources were provisioned. Fresh verification passed: 50 backend tests, 9 frontend tests, 8 browser journeys, lint/types/contracts/build, package audits, offline provider check, and container builds. Independent follow-up review found no actionable issues. Tests block sockets while generating replies and reject paid provider configuration.

## Milestones

| Milestone | Status | Implemented and verified evidence |
|---|---|---|
| 1. Foundation, contracts, accounts | Implemented | Locked React/FastAPI/PostgreSQL stack; migrations; Argon2, opaque sessions, CSRF/origin, encrypted single-use email/reset; account preferences/export/deletion; PostgreSQL auth tests |
| 2. First deterministic mission | Implemented | Checkout reference t=10, 30 failed purchases, score=100; negative/cap/property/fingerprint/replay tests |
| 3. Persistent workspace | Implemented | Seven panels, PostgreSQL commands/events, exact idempotency and revision conflicts, atomic rollback, evidence/notes; browser completion and reload |
| 4. Teammates and durable work | Implemented locally | Built-in local provider; server-filtered context; PostgreSQL jobs/outbox, Celery, quota reservations, fenced leases, retries/cancellation, SSE; local/fault tests pass; external providers removed by user request |
| 5. Branches, debrief, progress | Implemented | Immutable checkpoints, independent forks/notes/transcripts, deterministic debrief, replay/comparison, first/latest/best progress, sanitized expiring/revocable shares |
| 6. Remaining missions and admin | Implemented | Inventory t=11/zero new oversells/100; analytics t=10/90 orders/$9,000/100; draft import/edit/hash validation/copied preview/publish/archive/audit; DB immutability triggers |
| 7. Product and operations | Implemented locally | White/glass/pegboard responsive UI; keyboard/mobile checks; metrics, cleanup, non-root images, CI, production Compose, disabled Render Blueprint, frontend-only Vercel configuration, local restore and load exercise |
| 8. Release review | Local checks complete | Current no-charge checks and independent review complete. Earlier image scans/container smoke retained as historical evidence. Push and new clean-runner CI pending. |

## Current no-charge verification

- `make verify`: PASS — Ruff lint/format; mypy **84 source files**; **50 backend tests** on PostgreSQL 18.6/Redis; three exact scenario vectors; generated OpenAPI/TypeScript drift check; ESLint; **9 frontend tests**; production TypeScript/Vite build.
- `make e2e`: **8/8** desktop/mobile keyboard journeys passed (45.6s), all three missions including checkout chat/notes/replay/share/revoke/fork/compare; debrief axe had zero violations in the tested views. Settings/theme/reduced-motion persistence, run archive/restart and account deletion also passed.
- Free-runtime checks: paid-provider configuration rejected; legacy `mock` maps to `local`; dialogue/coaching and old-metadata worker paths pass with sockets blocked; zero token results. Offline `python -m app.cli.validate_provider`: PASS. Local readiness reports `ai_provider: local`.
- `make audit`: PASS — pnpm production audit and pip-audit report zero vulnerabilities; bounded source scan found zero known credential patterns. Not an exhaustive entropy/security audit. [Summary](verification/package-audit-summary.json).
- Production API/web images rebuilt successfully locally from the current locked dependencies. Live development API/frontend/worker/dispatcher and updated landing screenshot verified.
- Disabled Render file passes the official published JSON schema and declares zero resources. Retained Vercel configuration passes an instance check against its published schema. Account-level Blueprint validation, Vercel deployment and public application smoke tests were not performed.
- Independent source review of the no-charge update: no actionable findings.
- GitHub Actions for this update: pending push. The previous successful run below does not verify the current diff.

## Earlier release evidence (historical)

- `make setup`: PASS with existing `.env` preserved; locked install, PostgreSQL/Redis/Mailpit readiness, migrations/seed, disposable test database and Chromium. Setup will also run on the new CI commit.
- `make load`: PASS — **20 learners, 301.41 seconds, 6,045 requests, zero unexpected errors**. Read p95 **28.34ms**, command p95 **91.14ms**. Apple M5/16GB/macOS26.6, local PostgreSQL18.6/Redis8.4 and authored mock provider. Dataset 160 runs/branches, 3,582 events, 140 scorecards, 20 jobs. Hosted capacity excluded. [Measured report](verification/load-report.json).
- `make backup-restore`: PASS — disposable restore, prior seeded migration upgrade, pinned scenario/checkpoint/replay hash verification. [Report](verification/restore-report.json). Production remote backup/RPO/RTO unverified.
- Local arm64 API/frontend Docker Scout high/critical scans had zero findings. Non-root/read-only container smoke passed readiness, SPA/API/auth/run, inherited CSP, no-store, report noindex and restricted metrics. Those image scans and container smoke precede the no-charge update; current images have been rebuilt but not re-scanned. Scans are time-, architecture- and severity-specific.
- Previous GitHub Actions: PASS on `ea2c74c` — clean Ubuntu setup, complete verification/browser/restore/audit and amd64 container builds. [Run](https://github.com/Gagandeepkaurrr/WorkQuest/actions/runs/43085445643). This is CI, not a hosted deployment.

## Independent review and corrections

A fresh-context reviewer inspected the complete working tree. Corrected: reset/login race via owner-first locks; uncertain writes retain idempotency keys after 401/403/429; library provides archive controls and pagination for learner/demo/preview runs; workspace explains skipped automatic checkpoints; uncertain shares retain the previously approved alias/expiry. Targeted auth/config/release-boundary tests: 17 passed. Hosted proxy identity was retained as an explicit launch blocker, not hidden by wildcard proxy trust.

## Public deployment checks — NOT VERIFIED / outside current local scope

- Live model integration: REMOVED by user request; no key, tokens or paid probe are supported.
- External SMTP: only local Mailpit delivery verified; real sender/DNS/TLS/delivery required.
- Render/Vercel: no account provisioning, hosted build, TLS/secure-cookie/streaming/cache/log-redaction smoke test or real capacity measurement.
- Trusted proxy identity: Render/Vercel forwarded client-IP chain must be verified/configured before multi-user signup. Default conservative trust can group clients under ingress authentication limits. Single-origin Compose has an exact configured trust chain; its public deployment is also unverified.
- Offsite encrypted backups, alert delivery, measured production RPO24h/RTO4h: not configured or rehearsed.

Next action: push the no-charge update to WorkQuest `main` and verify clean-runner CI. The supported complete app runs locally; do not provision the old paid Render stack. See [deployment commands](DEPLOY_RENDER_VERCEL.md), [operations](OPERATIONS.md), [limitations](KNOWN_LIMITATIONS.md), and [acceptance mapping](REQUIREMENTS_MATRIX.md).
