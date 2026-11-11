# Build status

Updated: 2026-11-11 (Asia/Kolkata)

Status: implementation in progress. No release or integration success claimed.

## Inspection

Read all 1,617 lines of the supplied specification. Repository initially empty; no AGENTS.md found in applicable parent paths. Docker Desktop and Compose are available on Apple Silicon. Host Node is 26.13.0; pnpm 11.25.0; uv 0.13.6. Dependencies and runtime compatibility still being established.

## Milestones

1. Foundation/accounts: IN PROGRESS
2. Checkout engine: NOT STARTED
3. Persisted workspace: NOT STARTED
4. AI/jobs/events: NOT STARTED
5. Branches/reports: NOT STARTED
6. Remaining scenarios/admin: NOT STARTED
7. Product/operations: NOT STARTED
8. Release verification: NOT STARTED

## Verification evidence

- `docker version` / `docker compose version`: available, server 29.9.2 / Compose 5.6.1.
- No application tests run yet.

## External gates

Live Gemini, external SMTP, public TLS, deployed backup target and deployment smoke checks: NOT VERIFIED. No credentials or deployment authorization supplied.

Next: lock dependencies, start isolated PostgreSQL/Redis/Mailpit, write failing account tests and implement the first slice.

## First implementation evidence

- `uv run pytest tests/unit/test_config.py tests/integration/test_auth.py -q`: 5 passed against PostgreSQL 18.6.
- `uv run alembic upgrade head`: clean local and disposable test migrations passed.
- `pnpm build`: passed (TypeScript and Vite), initial bundle-size advisory remains for later splitting.
- `uv run pytest tests/unit/test_checkout.py tests/unit/test_config.py tests/integration/test_auth.py -q`: 10 passed, including exact checkout score/time/harm, negative paths, fingerprints, cap, purity, bounded-score properties.
- M1 account backend and shell implemented; local email delivery and UI walkthrough still pending. M2 checkout engine checks passed. M3 transaction services in progress.

## Milestones 3–6 progress

- `uv run pytest tests/integration/test_runs.py -q`: 3 passed on PostgreSQL: isolation, duplicate key race, revision conflict, rollback, exact persisted checkout score.
- `uv run pytest tests/unit/test_ai.py tests/integration/test_jobs.py -q`: 6 passed: authorized context, injection refusal in mock, unsafe outputs, stale/cancelled publication, expired leases and duplicate fencing.
- `uv run pytest tests/integration/test_branches.py -q`: 2 passed: snapshot/notes isolation, parent immutability, replay hash, pending-dialogue rejection, sanitized encrypted share replay and immediate revocation.
- `uv run pytest tests/unit/test_other_scenarios.py -q`: 4 passed: exact inventory t=11/zero new oversells, analytics t=10/90 orders/$9000, negative paths and isolated fixtures.
- `uv run pytest -q` at pre-admin checkpoint: 25 passed. Later additions need a fresh complete run.
- Browser checkout walkthrough reached 100-point debrief, saved/reloaded notes, mock reply, matching replay, and zero axe violations on debrief. Initial runs failed on test locator/panel assumptions; full browser gate still pending rerun, not marked PASS.
- Frontend builds pass. Route splitting and bundle-size warning remain to address.
- Admin hash-bound validation and immutable preview tests are being added. Settings/admin UI, operational scripts, broader fault/security tests, full mobile E2E, load/restore and final review remain.

Next: finish settings and admin interfaces, complete browser walkthroughs, then harden and run all release checks. No live provider, external email, TLS or public deployment has been attempted.
