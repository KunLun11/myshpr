# Индивидуальный проект

Платформа для школьных индивидуальных проектов: ученик вовремя формулирует
тему и определяет продукт, учитель видит, кто застрял, — в сентябре, а не в
апреле.

MVP покрывает четыре функции:

1. мастер темы с проверкой на повтор и «слишком широко»;
2. помощник в выборе продукта;
3. дашборд учителя «кто застрял»;
4. работа над проектом: файлы, односторонние комментарии учителя и чек-листы.

Подробный план, доменная модель и ADR — в `TASKS.md` и `docs/`.

## Стек

| Слой | Технологии |
| --- | --- |
| Backend | Python 3.13, FastAPI, SQLAlchemy 2.0 async, Alembic, asyncpg, ARQ |
| Frontend | Next.js 16 (App Router, Cache Components), React 19, Tailwind 4 |
| Данные | PostgreSQL 16, Redis 7 |
| Доставка | Docker Compose, Caddy (TLS), GitHub Actions |

## Быстрый старт (Docker)

```bash
cp backend/.env.example backend/.env     # dev values, safe for local use
cp deploy/.env.example deploy/.env       # compose needs the password vars
make up                                  # docker compose up --build
```

Первый запуск: примените миграции и демо-данные.

```bash
docker compose -f deploy/docker-compose.yml exec backend uv run alembic upgrade head
docker compose -f deploy/docker-compose.yml exec backend uv run python -m app.db.seed --dev
```

Откройте <http://localhost:3000>.

| Роль | Логин | Пароль |
| --- | --- | --- |
| Учитель | `teacher@example.com` | `student123` |
| Ученик | `student1@example.com` | `student123` |
| Код класса | `DEMO2026` | — |

> Демо-данные только для разработки. `seed` отказывается работать без `--dev`.

## Локальная разработка без Docker

Нужны PostgreSQL 16 и Redis 7 (или контейнеры на нестандартных портах).

```bash
cd backend
uv sync
uv run alembic upgrade head
uv run python -m app.db.seed --dev
uv run uvicorn app.main:app --reload --port 8000
```

```bash
cd frontend
npm ci
BACKEND_URL=http://localhost:8000 npm run dev
```

`backend/.env` — источник настроек backend при локальном запуске и dev compose.
В prod-стеке настройки живут в `deploy/.env` (backend читает их из окружения,
файл `backend/.env` на сервере не обязателен). Шаблоны и полный справочник
переменных — `backend/.env.example`, `deploy/.env.example` и `docs/env.md`.

## Тесты и проверки

```bash
make lint       # ruff (backend) + eslint (frontend)
make test       # pytest; нужен Postgres (TEST_DATABASE_URL)
make audit      # pip-audit + npm audit
make test-e2e   # Playwright; стек должен быть запущен и засеян
make check      # lint + test
```

E2E-сценарии: `frontend/e2e/journey.spec.ts` — пять P0-сценариев из `TASKS.md`
(регистрация и мастер темы, проверка учителем, продукт, файл/чек-лист/комментарий,
дашборд). По умолчанию идут против `http://localhost:3000`; переопределяется
через `E2E_BASE_URL`.

## Структура

```text
backend/    FastAPI, SQLAlchemy-модели, сервисы, репозитории, Alembic, ARQ
frontend/   Next.js App Router, дизайн-система, Playwright
deploy/     compose dev/prod, Caddyfile, скрипты бэкапа и smoke-теста
docs/       ADR, доменная модель, runbook, инструкции
openspec/   спецификации изменений
```

## Безопасность и эксплуатация

- Токены — только в `httpOnly` cookies; refresh-токены хранятся в виде хеша и
  ротируются. Все мутации дополнительно проверяют `Origin`/`Referer`.
- Rate limit на вход, регистрацию, проверку темы и загрузку файлов. В prod —
  общий счётчик в Redis (`RATE_LIMIT_BACKEND=redis`), потому что backend
  запускается в несколько воркеров.
- Файлы — приватное хранилище, проверка размера, расширения, MIME и сигнатуры.
- Логи — JSON с `request_id`, `user_id` (без ПДн), маршрутом, статусом и
  длительностью. Метрики — Prometheus-формат на `/api/v1/metrics` (только из
  приватной сети).
- Деплой, TLS, бэкапы и восстановление — `docs/runbook.md`.
- Чек-лист релиза — `docs/release-checklist.md`.

## Документация

| Документ | О чём |
| --- | --- |
| `TASKS.md` | продукт, доменная модель, этапы и критерии приёмки |
| `docs/domain.md` | сущности и правила |
| `docs/design.md` | дизайн-система и бриф |
| `docs/runbook.md` | эксплуатация: деплой, бэкапы, инциденты |
| `docs/env.md` | все переменные окружения для dev и сервера |
| `docs/guides/student.md` | инструкция ученика |
| `docs/guides/teacher.md` | инструкция учителя |
| `docs/adr/` | архитектурные решения |
| `docs/release-checklist.md` | чек-лист релиза |
| `CHANGELOG.md` | история версий |
