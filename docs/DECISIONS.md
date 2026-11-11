# Architecture decisions

- 2026-11-11: Empty folder, no repository instructions or unrelated files. Initialize a dedicated `workquest/build` branch in the requested location; no second worktree is needed for an empty project.
- The full attached specification defines the scope. Its request to resolve ordinary choices and continue implementation authorizes proceeding without a second design approval.
- User visual steering supersedes the dark-default requirement: white glass surfaces, cobalt/mint accents, bold bundled sans-serif, pegboard mission presentation; retain a functional alternate dark theme.
- Keep private content and deterministic mechanics entirely on the backend. JSONB carries typed domain state; relational ownership, constraints and locks protect transactions.
- Native implementation with one independent final review avoids simultaneous schema ownership. Build checkout end-to-end before implementing the other mechanics.
