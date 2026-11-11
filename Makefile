SHELL := /bin/bash
.PHONY: setup deps migrate seed dev api worker dispatcher verify contracts e2e test-db build containers stop cleanup admin audit backup-restore load
setup:
	mkdir -p artifacts
	python3 scripts/local-env.py
	docker compose up -d --wait
	uv sync --project apps/api --frozen
	pnpm install --frozen-lockfile
	$(MAKE) migrate seed test-db
	pnpm --filter @workquest/web exec playwright install chromium
deps:
	docker compose up -d --wait
migrate:
	cd apps/api && uv run alembic upgrade head
seed:
	cd apps/api && uv run python -m app.cli.seed
test-db:
	uv run --project apps/api python scripts/create-test-db.py
	uv run --project apps/api python scripts/test-db.py
dev:
	uv run --project apps/api python scripts/dev.py
api:
	cd apps/api && uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log --reload
worker:
	cd apps/api && uv run celery -A app.jobs.celery_app:celery worker --pool=solo --loglevel=WARNING --without-gossip --without-mingle
dispatcher:
	cd apps/api && uv run python -m app.jobs.dispatcher
verify: test-db
	cd apps/api && uv run ruff check app tests && uv run ruff format --check app tests migrations
	cd apps/api && uv run mypy app
	cd apps/api && uv run pytest -q
	cd apps/api && uv run python -m app.cli.validate_scenarios
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
	cd apps/api && uv run python -m app.cli.cleanup
admin:
	cd apps/api && uv run python -m app.cli.create_admin
audit:
	uv run --project apps/api python scripts/security-audit.py
backup-restore:
	uv run --project apps/api python scripts/restore-rehearsal.py
load:
	uv run --project apps/api python scripts/load-test.py --seconds 300 --learners 20
