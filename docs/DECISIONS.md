# Architecture decisions

- 2026-11-11: Empty folder, no repository instructions or unrelated files. Initialize a dedicated `workquest/build` branch in the requested location; no second worktree is needed for an empty project.
- The full attached specification defines the scope. Its request to resolve ordinary choices and continue implementation authorizes proceeding without a second design approval.
- User visual steering supersedes the dark-default requirement: white glass surfaces, cobalt/mint accents, bold bundled sans-serif, pegboard mission presentation; retain a functional alternate dark theme.
- Keep private content and deterministic mechanics entirely on the backend. JSONB carries typed domain state; relational ownership, constraints and locks protect transactions.
- Native implementation with one independent final review avoids simultaneous schema ownership. Build checkout end-to-end before implementing the other mechanics.
- 2026-11-12: Git destination was explicitly clarified as `Gagandeepkaurrr/WorkQuest only`; never publish to portfolio_.
- Keep the Render/Vercel hosted proxy trust check as a visible release gate. Avoid blanket trust of client-supplied forwarding headers; single-origin Compose pins both proxy hops.
- Retry recovery retains original idempotency keys after authentication/rate-limit failures because these can occur before the server retrieves a previously committed response.
- Password reset, login and password change serialize on the account row; token consumption locks owner before token to prevent reset interleavings/deadlocks.
- Frontend Nginx runtime uses patched Debian Trixie rather than Alpine after a high-severity musl finding; scan the final runtime again and record its digest.

- 2026-11-12 cost override: user explicitly selected no AI and no hosting charges. Built-in authored replies are the sole provider; reject paid provider selections, remove remote adapter/SDK/keys, keep all services local, and disable paid Render provisioning. Vercel configuration remains frontend-only and is not presented as a free full backend.
