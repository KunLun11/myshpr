# Запуск контейнеров

Все команды выполняются из папки `deploy/`.

## Dev

```bash
docker compose up --build
```

- `docker-compose.yml` использует `target: dev`: uvicorn с `--reload`, `next dev`.
- Исходники монтируются из хоста — правки применяются без пересборки.
- Frontend: http://localhost:3000 · Backend: http://localhost:8000 · Swagger: http://localhost:8000/docs · Postgres: `localhost:5432`.

После изменения `package.json` / `uv.lock` зависимости надо переустановить (они лежат в named volume'ах):

```bash
docker compose down
docker volume rm deploy_backend_venv deploy_frontend_node_modules
docker compose up --build
```

Пересобрать один сервис: `docker compose up --build frontend`.

## Prod

```bash
docker compose -f docker-compose.prod.yml up --build -d
docker compose -f docker-compose.prod.yml logs -f
docker compose -f docker-compose.prod.yml down
```

- `docker-compose.prod.yml` — отдельный файл (не override), использует `target: prod` и без bind-mount'ов.
- Frontend собирается в `next build` и запускается через `node server.js` (standalone), backend — uvicorn с 2 воркерами.
- Postgres наружу не публикуется. Пароль задаётся через переменные окружения:

```bash
POSTGRES_PASSWORD=<strong-password> docker compose -f docker-compose.prod.yml up -d --build
```

## Общее

```bash
docker compose down        # остановить
docker compose down -v     # остановить + удалить данные БД и volume'ы
docker compose ps          # статус
```
