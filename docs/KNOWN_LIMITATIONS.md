# Known limitations and remaining verification

Updated 2026-11-12. The latest user requirement is **no AI or hosting charges**. See [COST_POLICY.md](COST_POLICY.md).

- The full supported deployment is local on existing hardware. The paid Render Blueprint is disabled and no managed resources were provisioned. A free public backend is not provided or verified; Vercel frontend hosting alone does not run PostgreSQL, Redis or durable workers.
- Teammates and coaching use authored rules and permitted scenario facts. They are not a general-purpose language model and may respond with a fallback to questions outside the scenario. External model adapters, keys and SDKs are removed; there are no billable AI calls or token credits.
- Single-host/local Compose is not highly available. Keep the computer and worker/dispatcher running for email and teammate jobs. PostgreSQL-backed work survives process restarts; job recovery remains bounded and fenced.
- The historical 20-learner benchmark ran locally on an Apple M5/16GB using the same authored reply engine. It is not a public hosting capacity result.
- Delivery encryption uses one active key. Drain pending email/share-replay payloads before rotation. Emergency rotation invalidates pending links; a multi-key migration/keyring is not implemented.
- Browser checks cover desktop/mobile Chromium and keyboard/axe flows, not every browser or screen reader. Scenario authoring is a structured JSON editor limited to the three supported mechanics.
- Public report secret URLs can be recovered only within the encrypted 30-minute replay window. New links require explicit creation after that period.
- Account deletion removes live records; operator-created backups can retain earlier data until their retention expires. Configure retention on any storage you manage.
- Public TLS/cookies/proxy identity/streaming, external SMTP, offsite backups and alert delivery remain unverified. These are not needed for the supported local setup. No live-model integration remains to enable or verify.
- Historical package/image scans are point-in-time evidence. Rebuild/re-scan changed images before distributing them; no penetration test was commissioned.
