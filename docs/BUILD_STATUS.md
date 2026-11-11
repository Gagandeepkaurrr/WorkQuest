# WorkQuest build status

Updated: 2026-11-12, Asia/Kolkata. Repository: `/Users/gaggu/WorkQuest`. Authorized GitHub destination: **Gagandeepkaurrr/WorkQuest only**.

**Local release candidate verified; Git publication in progress. Hosted release remains gated.** The complete 1,617-line supplied specification is preserved in PROJECT_SPECIFICATION.txt. The repository was initially empty; no applicable AGENTS.md existed. User styling instructions supersede the dark-default specification.

## Milestones

| Milestone | Status | Implemented and verified evidence |
|---|---|---|
| 1. Foundation, contracts, accounts | Implemented | Locked React/FastAPI/PostgreSQL stack; migrations; Argon2, opaque sessions, CSRF/origin, encrypted single-use email/reset; account preferences/export/deletion; PostgreSQL auth tests |
| 2. First deterministic mission | Implemented | Checkout reference t=10, 30 failed purchases, score=100; negative/cap/property/fingerprint/replay tests |
| 3. Persistent workspace | Implemented | Seven panels, PostgreSQL commands/events, exact idempotency and revision conflicts, atomic rollback, evidence/notes; browser completion and reload |
| 4. Teammates and durable work | Implemented locally | Mock and Gemini adapters; server-filtered context; PostgreSQL jobs/outbox, Celery, quota reservations, fenced leases, retries/cancellation, SSE; mock/fault tests pass; real Gemini unverified |
| 5. Branches, debrief, progress | Implemented | Immutable checkpoints, independent forks/notes/transcripts, deterministic debrief, replay/comparison, first/latest/best progress, sanitized expiring/revocable shares |
| 6. Remaining missions and admin | Implemented | Inventory t=11/zero new oversells/100; analytics t=10/90 orders/$9,000/100; draft import/edit/hash validation/copied preview/publish/archive/audit; DB immutability triggers |
| 7. Product and operations | Implemented locally | White/glass/pegboard responsive UI; keyboard/mobile checks; metrics, cleanup, non-root images, CI, production Compose, Render/Vercel setup, local restore and load exercise |
| 8. Release review | Local checks complete | Full verification, 8 browser journeys, independent review and corrected findings, image scans, container smoke and documentation completed. Git push/hosted CI pending. |

## Executed verification

- `make setup`: PASS with existing `.env` preserved; locked install, PostgreSQL/Redis/Mailpit readiness, migrations/seed, disposable test database and Chromium.
- `make verify`: PASS — Ruff lint/format; mypy **85 source files**; **45 backend tests** on PostgreSQL 18.6/Redis; three exact scenario vectors; generated OpenAPI/TypeScript drift check; ESLint; **9 frontend tests**; production TypeScript/Vite build.
- Browser suite: **8/8** desktop/mobile keyboard journeys passed (47.1s), all three missions including checkout chat/notes/replay/share/revoke/fork/compare; debrief axe had zero violations in the tested views. Settings/theme/reduced-motion persistence, run archive/restart and account deletion also passed.
- `make load`: PASS — **20 learners, 301.41 seconds, 6,045 requests, zero unexpected errors**. Read p95 **28.34ms**, command p95 **91.14ms**. Apple M5/16GB/macOS26.6, local PostgreSQL18.6/Redis8.4, mock AI. Dataset 160 runs/branches, 3,582 events, 140 scorecards, 20 jobs. Real model latency/hosted capacity excluded. [Measured report](verification/load-report.json).
- `make backup-restore`: PASS — disposable restore, prior seeded migration upgrade, pinned scenario/checkpoint/replay hash verification. [Report](verification/restore-report.json). Production remote backup/RPO/RTO unverified.
- Package audits: pnpm production audit and pip-audit passed with zero reported vulnerabilities; bounded source scan found zero known credential patterns. Not an exhaustive entropy/security audit. [Summary](verification/package-audit-summary.json).
- Production API/web images built locally. Latest API and frontend high/critical Docker Scout scans: zero on local arm64 images. Final non-root/read-only container smoke passed: readiness, SPA/API/auth/run, inherited CSP, no-store, report noindex, restricted metrics. Scans are time-, architecture- and severity-specific, not a guarantee of no vulnerabilities.
- Render file passes the official published JSON schema locally. Actual `render blueprints validate` in an account, paid provisioning and Vercel build/deploy are not performed.

## Independent review and corrections

A fresh-context reviewer inspected the complete working tree. Corrected: reset/login race via owner-first locks; uncertain writes retain idempotency keys after 401/403/429; library provides archive controls and pagination for learner/demo/preview runs; workspace explains skipped automatic checkpoints; uncertain shares retain the previously approved alias/expiry. Targeted auth/config/release-boundary tests: 17 passed. Hosted proxy identity was retained as an explicit launch blocker, not hidden by wildcard proxy trust.

## Live and deployment gates — NOT VERIFIED

- Gemini: no live key/billable probe or real-model adversarial evaluation.
- External SMTP: only local Mailpit delivery verified; real sender/DNS/TLS/delivery required.
- Render/Vercel: no account provisioning, hosted build, TLS/secure-cookie/streaming/cache/log-redaction smoke test or real capacity measurement.
- Trusted proxy identity: Render/Vercel forwarded client-IP chain must be verified/configured before multi-user signup. Default conservative trust can group clients under ingress authentication limits. Single-origin Compose has an exact configured trust chain; its public deployment is also unverified.
- Offsite encrypted backups, alert delivery, measured production RPO24h/RTO4h: not configured or rehearsed.
- GitHub-hosted CI: pending first push; local equivalent checks have run.

Next: commit and push only to WorkQuest, then inspect GitHub CI. See [deployment commands](DEPLOY_RENDER_VERCEL.md), [operations](OPERATIONS.md), [limitations](KNOWN_LIMITATIONS.md), and [acceptance mapping](REQUIREMENTS_MATRIX.md).
