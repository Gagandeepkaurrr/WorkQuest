# Requirements and acceptance evidence

Source: PROJECT_SPECIFICATION.txt, with the user's white/glass/pegboard visual override and 2026-11-12 no-AI/no-hosting-charge requirement. The latter replaces the live AI adapter with built-in authored replies and disables managed paid deployment. Implementation evidence below is local; external gates are separate in RELEASE_CHECKLIST.md. Tests use real PostgreSQL, not SQLite.

| Requirement | Implementation | Local evidence |
|---|---|---|
| F01 Accounts/onboarding | modules/auth, modules/users; web auth/settings/orientation | auth integration tests; actual UI signup/Mailpit verification; settings browser flow |
| F02–F03 Library/briefing | public scenario projections, filters, saved run archive/pagination, version-pinned start | ownership/draft tests; three browser mission starts |
| F04 Workspace | seven responsive panels, keyboard navigation, evidence/action dialogs, durable drafts | desktop/mobile keyboard journeys; axe tested debrief views |
| F05 AI teammates | ai/context/validation/providers; durable conversations/jobs/SSE | unit AI tests; lease/quota/recovery tests; mock browser reply; external models removed by user request |
| F06–F08 Evidence/tasks/operations | pure engine + three private scenario packages, structured commands | exact golden/negative vectors, cap/property/fingerprint tests |
| F09 Persistence | atomic PostgreSQL transactions, idempotency records, notes revision, reload recovery | parallel command and rollback tests; browser notes/replay; frontend timeout recovery |
| F10 Branches/replay | immutable snapshots, branch baselines, permitted transcript, pure replay | branch isolation and replay side-effect tests; browser fork/compare |
| F11–F12 Debrief/progress | exact rubric and hash; separate optional coaching; first/latest/best personal history | all three 100-point vectors; coaching immutability; concurrent first attempt test |
| F13 Sharing/export | explicit public allowlist, hashed tokens, encrypted replay window, expiry/revocation | private-field tests; share/revoke browser journey; export endpoints |
| F14 Administration | secure admin CLI; draft import/edit/export/validate/preview/publish/archive/audit | admin hash-bound lifecycle and DB trigger tests; immutable copied preview |
| F15 Reliability/limits | owner/branch locks, durable outbox, leases, Redis quotas/rates, cursor SSE, bounded payloads | concurrency/fault/atomicity/SSE/quotas tests; local load exercise |
| F16 Delivery/operations | locked setup, non-root images, CI, metrics/cleanup, restore/load scripts, Compose/Render/Vercel docs | make setup/verify, build/audit/load/restore; hosted gates unverified |

## Mandatory acceptance cases

Paths are relative to `apps/api/tests` unless noted. Each named test was included in the passing local suite; these establish the described boundary, not every possible adversarial interleaving.

| ID | Named executable evidence |
|---|---|
| T01 Fresh/previous migration and seed | `scripts/restore-rehearsal.py`; `integration/test_acceptance.py::test_first_attempt_simultaneous_roots_and_seed_idempotence`; admin reseed after v2 publication |
| T02 Accounts/session lifecycle | `integration/test_auth.py` including concurrent password reset/login revocation |
| T03 Origin/CSRF/ownership | `test_auth.py::test_origin_reset_revokes_sessions_and_token_secrets`; `test_acceptance.py::test_ownership_for_nested_resources_and_draft_rules` |
| T04 Published/nonarchived/draft rules | `test_acceptance.py::test_ownership_for_nested_resources_and_draft_rules` |
| T05 All successful/negative vectors | `unit/test_checkout.py`; `unit/test_other_scenarios.py`; `python -m app.cli.validate_scenarios` |
| T06 Clock/cap/rejections/free reopens | `unit/test_checkout.py::test_cap_and_rejected_command_does_not_mutate` and `test_relevant_fingerprint_and_free_reopens` |
| T07 Score/fingerprint | exact three-vector tests and stale verification/report negative cases |
| T08 Parallel same key | `integration/test_runs.py::test_parallel_idempotency_and_revision_conflict` |
| T09 Competing revisions | same test explicitly asserts one committed effect and one stale conflict |
| T10 Atomic rollback | `test_runs.py::test_rejected_transition_rolls_back_and_finalize`; `test_release_boundaries.py::test_message_failure_rolls_back_event_quota_and_outbox` |
| T11 Lease/late/cancel/stale | `integration/test_jobs.py`; preloaded branch refresh regression in `test_release_boundaries.py` |
| T12 Broker acknowledgement loss | `test_acceptance.py::test_broker_ack_is_not_completion_and_payload_is_id_only` |
| T13 Fork snapshot/notes/transcript | `test_branches.py::test_checkpoint_fork_preserves_parent_notes_and_context` |
| T14 Replay no external side effects | `test_acceptance.py::test_replay_has_no_external_dispatch_and_share_expiry` |
| T15 SSE reconnect/privacy/revocation | `test_acceptance.py::test_sse_private_cursor_reconnect_and_revocation` with real PostgreSQL/Redis and the streaming generator |
| T16 Injection/private facts/schema/markup | `unit/test_ai.py`, `unit/test_scenario_validation.py`; frontend `report-safety.test.tsx`; local authored replies; no external model |
| T17 Every attempted call counted | `test_acceptance.py::test_every_retry_and_coaching_reserves_quota` |
| T18 Coaching cannot alter score hash | `test_release_boundaries.py::test_failed_coaching_is_terminal_without_score_mutation` |
| T19 Immutable preview | `test_admin.py::test_admin_hash_bound_validation_preview_and_immutable_publish` |
| T20 Sanitized, expired, revoked shares | branch/acceptance tests; checkout browser share and immediate revocation |
| T21 Encrypted token/broker payload | auth/branch tests; ID-only broker assertion; structured logging source review and bounded credential scan (hosting-provider logs unverified) |
| T22 Concurrent first root | `test_acceptance.py::test_first_attempt_simultaneous_roots_and_seed_idempotence` |
| T23 Deletion/late publication | `test_release_boundaries.py::test_deletion_destroys_secrets_and_blocks_late_publication`; auth deletion test |
| T24 Mobile/keyboard | `apps/web/e2e/checkout.spec.ts`, `scenarios.spec.ts` on desktop and mobile Chromium; dialogs, evidence and keyboard operations |
| T25 AI outage independent of engine | `test_jobs.py::test_quota_and_schema_failure_preserve_work`; failed-coaching test and deterministic replay/engine tests |

Frontend recovery tests additionally cover exact request/key replay after a lost response, rejections before idempotency lookup, share preview consistency and safe plain-text alias rendering. Accessibility evidence is representative Chromium/axe coverage; no claim of exhaustive assistive-technology certification.
