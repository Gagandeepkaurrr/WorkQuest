# WorkQuest implementation plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task. Update BUILD_STATUS.md with observed evidence after each milestone.

**Goal:** Build a persistent incident-practice application, three deterministic missions, safe AI teammates, independent branches, and an evidence-backed release review.

**Architecture:** A modular FastAPI monolith owns PostgreSQL state, opaque sessions, commands, scorecards and visibility. Pure mechanics execute deterministic commands. PostgreSQL jobs/outbox drive Celery workers; Redis is transport and rate limiting. A React SPA uses a same-origin API and resumable SSE.

**Tech stack:** React/TypeScript/Vite, React Router, TanStack Query, Tailwind, Radix/shadcn-style accessible UI, RHF/Zod, Zustand, Recharts; FastAPI/Pydantic, SQLAlchemy 2/psycopg 3, Alembic, PostgreSQL 18, Redis, Celery, uv/pnpm.

**Spec:** docs/PROJECT_SPECIFICATION.txt (read completely). User steering: white backgrounds, translucent glass surfaces, minimal bold typography, creative pegboard area, restrained colors. This supersedes the spec's dark-default visual direction.

## Global constraints

- PostgreSQL is authoritative. Never substitute SQLite for integration gates.
- All operations are simulated. No arbitrary code execution, public deployment, paid/live calls or real third-party messages without separate authorization.
- Cap is 20 logical minutes. Effects precede ticks. Reading speed never affects scores.
- Every first artifact open costs one minute; repeats, chat and notes cost zero.
- Scores are exactly diagnosis 20, outcome 40, verification 20, communication 10, judgment 10.
- User-authorized implementation proceeds without further design approval; ordinary decisions are documented.
- Private definitions and solutions stay backend-only. Public projection, ownership and context filtering are server concerns.
- Milestone acceptance is based on executed checks, never inferred from implementation.

## Review focus

- Network timeout followed by duplicate command: same response/effect, including secrets replay expiry.
- World changes while AI is running: stale response cannot publish.
- Fork after parent learns new facts: child sees only checkpoint context and saved notes.
- Concurrent roots, commands and quota requests: transactional limits and first-attempt identity remain correct.
- Keyboard/mobile dialogs and glass contrast: the full task remains operable and readable.

## Contracts

Types live in app/engine/types.py and feature schemas. JSON uses snake_case; UUIDs serialize as strings. Public world state contains simulation_time, metrics, artifacts (metadata only), allowed actions, tasks, communication values, diagnosis choices and verification summaries. It never contains private facts, rubric predicate metadata or unopened bodies.

- `apply_command(state: WorldState, command: Command, scenario: Scenario) -> TransitionResult`; no I/O.
- `project_visible_state(state: WorldState, scenario: Scenario) -> VisibleWorldState`.
- `execute_world_command(owner_id: UUID, branch_id: UUID, idempotency_key: UUID, request: CommandRequest) -> CommandResponse`; owns transaction, branch lock, atomic events/response.
- `create_checkpoint(owner_id, branch_id, expected_state_revision, label, key) -> CheckpointSummary`; settled immutable snapshot.
- `fork_checkpoint(owner_id, checkpoint_id, label, key) -> BranchSummary`; fresh counters, no copied jobs.
- `build_character_context(state, scenario, teammate_id, transcript, message) -> CharacterContext`; immutable authorized facts.
- `claim_ai_job(job_id) -> Lease | None`; `publish_ai_result(job_id, lease_token, result) -> bool`.
- `calculate_scorecard(final_state, inherited_ledger, new_events, scenario) -> Scorecard`; canonical deterministic hash.
- `build_public_report_snapshot(scorecard, share_options) -> PublicReport`; explicit field allowlist.

### Task 1: Foundation and secure accounts
Files: root manifests/Compose, app/core, app/db, modules/auth, modules/users, migrations, web shell/auth.
- [ ] Write account/config integration tests: registration, single-use verification, session rotation, reset revocation, CSRF/origin and ownership boundaries; observe failure.
- [ ] Implement typed settings, Argon2, opaque cookies, encrypted email delivery, session/preferences/deletion endpoints, migration and local services.
- [ ] Implement forms, route protection and functional white/glass shell.
- [ ] Run `uv run pytest tests/integration/test_auth.py tests/unit/test_config.py`; migrate empty PostgreSQL; build frontend. Commit and record results.

### Task 2: First deterministic mission
Files: engine/{types,commands,transitions,visibility,scoring,replay,registry}.py, mechanics/checkout_v1.py, private checkout content.
- [ ] Write exact reference/negative/clock/property tests, observe failure.
- [ ] Implement checkout transitions, safe projections, 100-point scoring, fingerprints and pure replay.
- [ ] Verify `uv run pytest tests/unit/test_checkout.py` with no external services. Expected reference t=10, failed_purchases=30, score=100. Commit and record results.

### Task 3: Persisted playable workspace
Files: modules/scenarios, modules/runs, frontend missions/workspace/evidence/actions/timeline.
- [ ] Test duplicate keys, revision races, rollback, hidden evidence and cross-user access on PostgreSQL.
- [ ] Implement run/start/state, command transaction, artifact reads, structured decisions, notes, lifecycle and finalization.
- [ ] Build all seven workspace panels, action review and timeout-safe client mutations.
- [ ] Verify `uv run pytest tests/integration/test_runs.py` and browser checkout completion/reload. Commit and record.

### Task 4: Teammates and durable work
Files: ai/, jobs/, modules/conversations, SSE/client transport.
- [ ] Write context/validation and job lease/quota/cancellation/stale/recovery tests first.
- [ ] Implement mock/Gemini contract, authorized context, encrypted email jobs, DB dispatcher, fenced claims and counted attempts.
- [ ] Implement queued/working/failed/stale/cancel/retry UI, persistent chat drafts, resumable branch-bound event cursors.
- [ ] Run `uv run pytest tests/unit/test_ai.py tests/integration/test_jobs.py`; bounded worker/broker fault checks. Commit and record.

### Task 5: Branches, debrief, progress and sharing
Files: modules/checkpoints, modules/reports, progress/branches/debrief/report UI.
- [ ] Test baseline/future-context separation, note independence, replay/hash, first root, sanitized secret sharing and expiry/revocation.
- [ ] Implement start/manual/automatic checkpoints, forks, replay, comparison, deterministic result, optional coaching, progress and exports.
- [ ] Run `uv run pytest tests/integration/test_branches.py`; browser fork/compare/share/revoke. Commit and record.

### Task 6: Remaining missions and administration
Files: inventory_v1.py, analytics_v1.py, private content, modules/admin and editor UI.
- [ ] Write exact vectors: inventory t=11/no new oversells, analytics t=10/90 orders/$9000; stated negative paths fail for stated reasons.
- [ ] Implement both mechanics and complete evidence, immutable draft-preview snapshots, hash-bound validation, publication/archive, import/export.
- [ ] Run engine/scenario/admin tests; complete both in browser. Commit and record.

### Task 7: Product and operations
Files: styles/UI, infra/, scripts/, docs/, CI.
- [ ] Run desktop/mobile/keyboard/axe checks and correct observed problems.
- [ ] Add restricted metrics, logs/redaction, cleanup, non-root images, backup/restore rehearsal, modest load script and deployment runbooks.
- [ ] Run frontend/backend lint/types, builds, backup/restore, secret/dependency scans and bounded performance test; record measurements and exclusions.

### Task 8: Release review
- [ ] Export OpenAPI/scenario schema and generate TypeScript; fail drift.
- [ ] Run `make verify` and `make e2e` against disposable PostgreSQL/Redis; review all T01–T25 evidence.
- [ ] Obtain independent final code review, resolve substantive findings and rerun affected checks.
- [ ] Complete requirements matrix, release gates, limitations and exact setup/admin/provider instructions. Live integrations/TLS/deployment stay NOT VERIFIED without credentials and authorization.
