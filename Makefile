"""Root Makefile with common developer commands."""

SHELL := /bin/bash

.PHONY: help up down migrate seed test test-e2e lint fmt check audit backup restore smoke

help:
	@echo "up        - start dev stack (docker compose)"
	@echo "down      - stop dev stack and remove volumes"
	@echo "migrate   - apply alembic migrations locally"
	@echo "seed      - seed demo data"
	@echo "test      - run backend tests"
	@echo "test-e2e  - run Playwright scenarios (stack must be running + seeded)"
	@echo "lint      - lint backend and frontend"
	@echo "fmt       - format backend code"
	@echo "audit     - dependency audits (pip-audit, npm audit)"
	@echo "backup    - prod Postgres + media backup"
	@echo "restore   - restore prod backup (DUMP=path)"
	@echo "smoke     - post-deploy smoke test (BASE_URL=...)"

up:
	cd deploy && docker compose up --build

down:
	cd deploy && docker compose down -v

migrate:
	cd backend && uv run alembic upgrade head

seed:
	cd backend && uv run python -m app.db.seed --dev

test:
	cd backend && uv run pytest

test-e2e:
	cd frontend && npx playwright test

audit:
	cd backend && uv run --with pip-audit pip-audit
	cd frontend && npm audit --audit-level=high

backup:
	./deploy/scripts/backup.sh

restore:
	./deploy/scripts/restore.sh "$(DUMP)"

smoke:
	./deploy/scripts/smoke.sh

lint:
	cd backend && uv run ruff check .
	cd backend && uv run ruff format --check .
	cd frontend && npm run lint

fmt:
	cd backend && uv run ruff format .
	cd backend && uv run ruff check --fix .

check: lint test
