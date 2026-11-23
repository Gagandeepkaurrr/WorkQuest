SHELL := /bin/bash
.PHONY: setup deps migrate seed dev api worker dispatcher verify contracts e2e test-db build containers stop cleanup admin audit backup-restore load
setup:
	mkdir -p artifacts
	python3 scripts/local-env.py
	docker compose up -d --wait
	uv sync --project backend --frozen
	pnpm install --frozen-lockfile
	$(MAKE) migrate seed test-db
	pnpm --filter @workquest/web exec playwright install chromium
deps:
	docker compose up -d --wait
migrate:
	cd backend && uv run alembic upgrade head
seed:
	cd backend && uv run python -m app.cli.seed
test-db:
	uv run --project backend python scripts/create-test-db.py
	uv run --project backend python scripts/test-db.py
dev:
	uv run --project backend python scripts/dev.py
api:
	cd backend && uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log --reload
worker:
	cd backend && uv run celery -A app.jobs.celery_app:celery worker --pool=solo --loglevel=WARNING --without-gossip --without-mingle
dispatcher:
	cd backend && uv run python -m app.jobs.dispatcher
verify: test-db
	cd backend && uv run ruff check app tests && uv run ruff format --check app tests migrations
	cd backend && uv run mypy app
	cd backend && uv run pytest -q
	cd backend && uv run python -m app.cli.validate_scenarios
	python3 scripts/contracts.py --check
	pnpm lint
	pnpm test
	pnpm build
contracts:
	python3 scripts/contracts.py
e2e:
	pnpm e2e
build:
	pnpm build
containers:
	docker compose -f compose.yaml -f compose.app.yaml build
	$(MAKE) migrate seed
	docker compose -f compose.yaml -f compose.app.yaml up -d --wait
stop:
	docker compose -f compose.yaml -f compose.app.yaml down
cleanup:
	cd backend && uv run python -m app.cli.cleanup
admin:
	cd backend && uv run python -m app.cli.create_admin
audit:
	uv run --project backend python scripts/security-audit.py
backup-restore:
	uv run --project backend python scripts/restore-rehearsal.py
load:
	uv run --project backend python scripts/load-test.py --seconds 300 --learners 20
