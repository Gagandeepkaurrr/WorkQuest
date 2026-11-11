# Dependency decisions

Checked 2026-11-11. Exact resolved JavaScript packages are in pnpm-lock.yaml and apps/web/package.json. Exact Python resolution is in apps/api/uv.lock (Python 3.14.10). Container digests are recorded in Compose/build definitions.

- Python 3.14.10 installs the required stack on Apple Silicon without a fallback.
- SQLAlchemy 2.0.57, psycopg 3.3.8, FastAPI 0.162.4, Celery 5.7.0, Google GenAI 3.1.0 resolved successfully.
- PostgreSQL 18.6 is the supported current minor checked at https://www.postgresql.org/support/versioning/ . Redis 8.4.0 and Mailpit 1.27.10 run locally.
- Node 24.22.1 is the pinned container baseline. The host shell additionally has Node 26.13.0; the bundled pnpm runtime is Node 24.22.1. Both series are supported LTS according to https://nodejs.org/en/about/previous-releases . Record actual container build verification separately.
- pnpm 11.25.0 is pinned. React/Vite/Tailwind use current stable packages and Tailwind's Vite plugin (https://vite.dev/guide/ and https://tailwindcss.com/docs/installation/using-vite).
- TypeScript 7.0.2 resolved initially but openapi-typescript 7.13.0 failed because its compiler API `ts.factory` was unavailable. Pin TypeScript 6.0.3; type generation and builds then succeeded. This is a verified compatibility decision, not an unexplained version downgrade.
- Official Gemini model page identifies `gemini-3.8-flash` as stable and structured-output capable: https://aistudio.google.com/docs/models/gemini-3.8-flash . Structured output docs: https://aistudio.google.com/docs/structured-output . SDK 3.1.0 exposes the typed generate_content/config interface used by the adapter. No live model call has been made.
