"""Root Makefile with common developer commands."""

SHELL := /bin/bash

.PHONY: help up down migrate seed test lint fmt check

help:
	@echo "up       - start dev stack (docker compose)"
	@echo "down     - stop dev stack and remove volumes"
	@echo "migrate  - apply alembic migrations locally"
	@echo "seed     - seed demo data"
	@echo "test     - run backend tests"
	@echo "lint     - lint backend and frontend"
	@echo "fmt      - format backend code"

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

lint:
	cd backend && uv run ruff check .
	cd backend && uv run ruff format --check .
	cd frontend && npm run lint

fmt:
	cd backend && uv run ruff format .
	cd backend && uv run ruff check --fix .

check: lint test
