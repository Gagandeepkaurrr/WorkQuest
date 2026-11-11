# Known limitations and remaining release gates

The three mission application is implemented and locally verified. It is not a verified public production deployment.

- **Render/Vercel proxy identity is a launch blocker.** Configure and verify the actual trusted client-IP chain before multi-user signup. The conservative Blueprint default can aggregate authentication throttling at the ingress IP. Do not use wildcard proxy trust. The single-origin production Compose reference has an explicit trust chain, but public TLS/deployment remains untested.
- Gemini adapter and guardrails are tested with fixtures/mock responses. No billable live probe, actual model latency or real-model adversarial evaluation has run. Real provider keys, model access and budget are needed.
- External SMTP delivery, sender DNS, provider edge logs/redaction, TLS/cookies, hosted streaming/cache behavior, external alert delivery, encrypted offsite backup and production RPO/RTO remain unverified.
- PostgreSQL job fencing ensures one valid publication, not exactly-once external billing. A worker crash after a provider response can cause another paid attempt; all attempts reserve quota.
- Single-host Compose is not highly available. The 20-learner benchmark is on a local Apple M5/16GB with mock AI; it does not establish Render instance capacity or production model latency.
- Delivery encryption uses one active key. Drain pending secret payloads before rotation; an emergency rotation invalidates pending links. A multi-key migration/keyring is not implemented.
- Browser checks cover representative desktop/mobile Chromium and keyboard/axe flows, not every browser or screen-reader combination. AI transcripts are intentionally plain text. Scenario administration is a structured JSON editor restricted to the three supported mechanics, not an arbitrary-code/plugin authoring system.
- Public reports deliberately omit explanations, notes, chats, private IDs, email and AI coaching. Secret share URLs can only be recovered within the encrypted 30-minute idempotency window; later recovery requires a new explicitly created link.
- Account deletion removes live records immediately; encrypted backups can retain previous records until the documented 30-day retention expires. Operators must configure log/backup retention and reapply deletions after restoring old backups.
- Package and image scans are point-in-time evidence with a stated scope. The credential scan checks known token/private-key patterns and is not exhaustive. No independent penetration test was commissioned.
