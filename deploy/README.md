# Запуск контейнеров

Все команды выполняются из папки `deploy/`.

## Dev

```bash
docker compose up --build
```

- `docker-compose.yml` использует `target: dev`: uvicorn с `--reload`, `next dev`.
- Исходники монтируются из хоста — правки применяются без пересборки.
- Frontend: <http://localhost:3000> · Backend: <http://localhost:8000> ·
  Swagger: <http://localhost:8000/docs> · Postgres: `localhost:5432`.

После изменения `package.json` / `uv.lock` зависимости надо переустановить (они лежат в named volume'ах):

```bash
docker compose down
docker volume rm deploy_backend_venv deploy_frontend_node_modules
docker compose up --build
```

Пересобрать один сервис: `docker compose up --build frontend`.

## Prod

Все настройки берутся из `deploy/.env` (шаблон — `.env.example`, полный
справочник — `docs/env.md`). Файл `backend/.env` на сервере не нужен.

```bash
cp .env.example .env
$EDITOR .env                       # DOMAIN, пароли БД/Redis, JWT_SECRET, CORS/CSRF
docker compose -f docker-compose.prod.yml config >/dev/null   # проверка
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml logs -f
docker compose -f docker-compose.prod.yml down
```

- `docker-compose.prod.yml` — отдельный файл (не override), использует `target: prod` и без bind-mount'ов.
- Frontend собирается в `next build` и запускается через `node server.js` (standalone), backend — uvicorn с 2 воркерами.
- Одноразовый сервис `migrate` применяет Alembic до старта backend и worker.
- Postgres, Redis и FastAPI наружу не публикуются; порты 80/443 держит только Caddy.
- `CORS_ORIGINS` и `CSRF_TRUSTED_ORIGINS` должны содержать публичный HTTPS-origin.
  Без них браузерные POST/PATCH/DELETE отклоняются origin-проверкой (fail closed).
- Админка живёт на том же домене под `/admin/**`, закрыта от индексации и
  требует обычного входа с ролью `school_admin`/`super_admin`.
- После деплоя: `BASE_URL=https://<домен> ./scripts/smoke.sh`.

Требуется Docker Compose ≥ 2.24.

## Общее

```bash
docker compose down        # остановить
docker compose down -v     # остановить + удалить данные БД и volume'ы
docker compose ps          # статус
```
