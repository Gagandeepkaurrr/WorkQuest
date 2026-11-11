# Release checklist

Updated 2026-11-12. **No-charge follow-up:** runtime is now local-only and the paid Render stack is disabled. Fresh checks are distinguished from earlier evidence below; see BUILD_STATUS.md for details. PASS means an executed local check; NOT VERIFIED is an explicit release gate. This is a locally verified candidate, not a production-readiness certification.

| Gate | Status | Evidence |
|---|---|---|
| Secure accounts and migrations | PASS locally | PostgreSQL tests, encrypted token/reset/revocation/delete cases, reset/login race regression verified failing without lock and passing with fix |
| Three exact scenarios and negative vectors | PASS | Checkout 100/t10/30 failed purchases; inventory 100/t11/no new oversells; analytics 100/t10/90 orders/$9,000; authored negative vectors |
| PostgreSQL concurrency/atomic rollback | PASS | Parallel same-key/same-revision tests; no partial state/event/quota/outbox on rejected transaction |
| Local teammate context, quotas, leases, recovery | PASS | Typed context/markup/fact tests; counted retries/repairs/coaching; cancellation/stale/late-worker/Redis redispatch tests |
| Branch/replay/report invariants | PASS | Snapshot/notes/transcript isolation, inherited ledger, pure hash replay, allowlisted share/expiry/revocation |
| Admin immutability/publication | PASS | Hash-bound validation, copied preview, published-edit DB triggers, reseed preserves active v2 |
| Frontend/backend lint/types/tests | PASS | `make verify`: Ruff, mypy84 files, pytest50, ESLint, Vitest9, build, generated contract drift |
| Desktop/mobile/keyboard | PASS representative coverage | `make e2e`: 8/8, 45.6s, three missions, notes/chat/replay/fork/compare/sharing, preferences/archive/delete; axe zero in tested debrief views |
| Local setup | PASS earlier release; current dev verified | `make setup` and `make dev`; PostgreSQL18.6, Redis8.4, Mailpit1.27.10; pinned installs/migrations/seed/Chromium |
| Production frontend/contracts | PASS | Vite/TypeScript build; OpenAPI/scenario JSON schema and generated types drift check |
| Container build and smoke | Current build PASS; smoke historical | Non-root/read-only Compose, readiness, inherited CSP/no-store/noindex, SPA route, cookie/CSRF/run/state, restricted metrics; container-smoke.json |
| Dependency/credential scans | PASS within scope | pnpm production audit + pip-audit zero findings; known token/key patterns zero; not exhaustive |
| Runtime image scan | Historical PASS within scope | Docker Scout1.27.0, local arm64 API/web, zero high/critical after OS updates and Debian frontend switch; re-scan hosted amd64 builds |
| Local backup/restore | Historical PASS; rerun in CI | Disposable restore/previous fixture upgrade/hash/replay verification; summary JSON in docs/verification |
| 20 learners / five minutes | Historical PASS locally | 6,045 requests, 0 errors, p95 read28.34ms/command91.14ms; mock AI; Apple M5/16GB |
| Independent final code review | PASS; no-charge review found no issues | Auth serialization, retry keys, archive control, checkpoint notice fixed; hosted proxy trust remains explicit gate |
| Render/Vercel configuration schema | PASS locally | Render declares zero resources; Vercel frontend-only instance validated against published schema; account-level validation not run |
| GitHub Actions | PENDING current push | Previous release ea2c74c passed; current no-charge diff needs clean-runner verification |
| No model charges | PASS | Socket-blocked dialogue/coaching and worker tests; reject paid provider settings; zero tokens; offline provider CLI |
| Live model integration | REMOVED | User requires no AI/API charges; no adapter, SDK, key or billable probe remains |
| External SMTP | NOT VERIFIED | Need real sender credentials/DNS/TLS/delivery; only Mailpit verified |
| Public TLS/cookies/SSE/cache/log redaction | NOT VERIFIED | Need actual public domains and hosted browser smoke flow |
| Hosted trusted proxy identity | BLOCKED pending operator verification | Configure verified proxy chain; prove distinct client buckets and spoof rejection before opening signup. No wildcard proxy trust |
| Encrypted offsite backup and RPO/RTO | NOT VERIFIED | Need private backup destination/keys/retention and measured restore; targets24h/4h |
| Alert delivery and hosted load | NOT VERIFIED | Need configured monitoring destinations and actual hosting capacity test |
| Public deployment smoke | NOT PROVIDED / NOT VERIFIED | Full supported no-service-fee operation is local; no resources provisioned or deployment performed |

Follow [Render/Vercel commands](DEPLOY_RENDER_VERCEL.md) and [operations](OPERATIONS.md); keep public signup closed until hosted gates pass. Limitations and retention implications are in [KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md).
