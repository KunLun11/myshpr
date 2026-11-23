# Переменные окружения

Справочник по всем переменным backend и инфраструктуры. Шаблоны:

- `backend/.env.example` — локальная разработка (backend читает `backend/.env`);
- `deploy/.env.example` — prod-стек (docker compose читает `deploy/.env`).

Ни один `.env` не коммитится. Реальные секреты — только на сервере или в
secret manager.

## 1. Как загружаются настройки

| Запуск | Файл | Приоритет |
| --- | --- | --- |
| Локально (`uv run uvicorn`) | `backend/.env` | реальные env-переменные > `.env` |
| Dev compose | `backend/.env` (обязателен) | — |
| Prod compose | `deploy/.env` (обязателен) | `environment:` в compose > `backend/.env` (необязателен) |

В prod compose все рабочие переменные прокидываются из `deploy/.env` через
anchor `x-backend-env`. Файл `backend/.env` на сервере **не нужен**; если он
существует, его значения перекрываются `deploy/.env`.

Prod-валидатор `app/core/config.py` не даст приложению стартовать, если:

- `JWT_SECRET` отсутствует, короче 32 символов или содержит заглушку `CHANGE-ME`;
- пароль в `DATABASE_URL` пустой, равен демо-паролю `myschoolproject` или
  содержит `CHANGE-ME` (роль и имя БД могут оставаться `myschoolproject`);
- `RATE_LIMIT_BACKEND` не `redis` (backend работает в 2 воркера);
- `STORAGE_BACKEND=s3`, но не заданы `S3_ENDPOINT` и `S3_BUCKET`.

## 2. Обязательные переменные на сервере

Скопируйте `deploy/.env.example` → `deploy/.env` и заполните:

| Переменная | Пример / как получить | Зачем |
| --- | --- | --- |
| `DOMAIN` | `project.school.example` | Домен для Caddy и Let's Encrypt (A/AAAA → сервер) |
| `ACME_EMAIL` | `admin@school.example` | Контакт Let's Encrypt (можно пустым) |
| `POSTGRES_USER` | `myschoolproject` | Роль PostgreSQL |
| `POSTGRES_PASSWORD` | `openssl rand -base64 36` | Пароль PostgreSQL |
| `POSTGRES_DB` | `myschoolproject` | Имя БД |
| `REDIS_PASSWORD` | `openssl rand -base64 36` | Пароль Redis |
| `REDIS_URL` | `redis://:<pass>@redis:6379/0` | Должен совпадать с `REDIS_PASSWORD` |
| `DATABASE_URL` | `postgresql+asyncpg://<user>:<pass>@db:5432/<db>` | Должен совпадать с `POSTGRES_*` |
| `JWT_SECRET` | `openssl rand -base64 48` (≥ 32 символов) | Подпись access-токенов |
| `CORS_ORIGINS` | `https://project.school.example` | Разрешённые origins (CSV) |
| `CSRF_TRUSTED_ORIGINS` | `https://project.school.example` | Origin/Referer для мутаций (CSV) |

Важно: пароли в `REDIS_URL` и `DATABASE_URL` должны быть URL-encoded
(`@` → `%40`, `/` → `%2F`, `#` → `%23`). Проще сгенерировать пароль без
спецсимволов: `openssl rand -hex 24`.

## 3. Backend: необязательные переменные

Все значения ниже уже имеют дефолты в compose; переопределяйте только при
необходимости.

### Платформа и auth

| Переменная | По умолчанию | Описание |
| --- | --- | --- |
| `ENV` | `dev` (`prod` в compose) | Режим: `dev` / `prod` |
| `DEBUG` | `false` | Подробные ошибки |
| `BACKEND_URL` | `http://localhost:8000` | Внутренний адрес API (`http://backend:8000` в compose) |
| `ACCESS_TOKEN_TTL_MIN` | `15` | Время жизни access-токена, мин |
| `REFRESH_TOKEN_TTL_DAYS` | `30` | Время жизни refresh-токена, дней |
| `BCRYPT_ROUNDS` | `12` | Стоимость bcrypt (тесты — 4) |
| `RATE_LIMIT_BACKEND` | `memory` (`redis` в prod) | Хранилище счётчиков rate limit |
| `METRICS_ENABLED` | `true` | Отдавать `/api/v1/metrics` |
| `HSTS_ENABLED` | `false` (`true` в prod) | Заголовок `Strict-Transport-Security` |

### Пороги проверки темы

| Переменная | По умолчанию | Описание |
| --- | --- | --- |
| `TOPIC_DUPLICATE_WARN` | `0.55` | Сходство, при котором предупреждаем о повторе |
| `TOPIC_DUPLICATE_BLOCK` | `0.85` | Сходство, при котором блокируем |
| `TOPIC_BROADNESS_OK` | `70` | Балл «достаточно узкая тема» |
| `TOPIC_BROADNESS_WARN` | `40` | Балл «слишком широко» |

### Дашборд и напоминания

| Переменная | По умолчанию | Описание |
| --- | --- | --- |
| `INACTIVITY_YELLOW_DAYS` | `7` | Жёлтый статус после N дней без активности |
| `INACTIVITY_RED_DAYS` | `14` | Красный статус |
| `CHECKPOINT_SOON_DAYS` | `7` | «Скоро контрольная точка» |
| `CHECKLIST_SOON_DAYS` | `3` | «Срок пункта чек-листа близко» |
| `CHECKLIST_STALLED_DAYS` | `14` | «Чек-лист застрял» |
| `FINAL_FILE_DAYS_BEFORE` | `14` | Напоминание об итоговом файле |
| `REVIEW_WAIT_DAYS` | `5` | «Тема ждёт решения учителя» |

### Файлы

| Переменная | По умолчанию | Описание |
| --- | --- | --- |
| `STORAGE_BACKEND` | `local` | `local` (том `media_data`) или `s3` |
| `MEDIA_ROOT` | `media` | Каталог локального хранилища; в prod фиксирован `/app/media` |
| `MAX_UPLOAD_BYTES` | `26214400` | Максимальный размер файла (25 МиБ) |
| `MAX_FILES_PER_PROJECT` | `10` | Лимит файлов на проект |
| `ALLOWED_UPLOAD_MIME` | PDF, DOCX, PPTX, PNG, JPEG, ZIP | CSV-список MIME |
| `ALLOWED_UPLOAD_EXTENSIONS` | `.pdf,.docx,.pptx,.png,.jpg,.jpeg,.zip` | CSV-список расширений |

### S3 (только при `STORAGE_BACKEND=s3`)

Образ backend собран с extra `s3` (aioboto3), бакет должен быть приватным и
версионированным.

| Переменная | Пример |
| --- | --- |
| `S3_ENDPOINT` | `https://s3.twcstorage.ru` |
| `S3_BUCKET` | `my-school-project` |
| `S3_ACCESS_KEY` | ключ доступа |
| `S3_SECRET_KEY` | секретный ключ |
| `S3_REGION` | `ru-1` (по умолчанию `us-east-1`) |

### Почта (зарезервировано)

`EMAIL_FROM`, `SMTP_HOST`, `SMTP_PORT` (587), `SMTP_USER`, `SMTP_PASSWORD` есть
в конфиге, но приложение пока не отправляет письма — напоминания создаются
только in-app.

## 4. Инфраструктура и бэкапы (`deploy/.env`)

| Переменная | По умолчанию | Описание |
| --- | --- | --- |
| `DOMAIN`, `ACME_EMAIL` | — | Caddy / TLS |
| `POSTGRES_*`, `REDIS_PASSWORD` | — | Контейнеры БД и Redis |
| `BACKUP_DIR` | `./backups` | Куда `backup.sh` пишет дампы (лучше отдельный диск) |
| `BACKUP_KEEP_DAYS` | `30` | Срок хранения бэкапов |

## 5. Frontend

| Переменная | Где | По умолчанию | Описание |
| --- | --- | --- | --- |
| `BACKEND_URL` | build arg + runtime | `http://localhost:8000` | Адрес FastAPI для rewrites и server components |
| `NEXT_PUBLIC_API_BASE` | build time | `/api/backend` | Префикс браузерных запросов (менять не нужно) |
| `NODE_ENV` | runtime | `production` | Режим Next.js |
| `HOSTNAME` | runtime | `0.0.0.0` (задаётся в compose) | Адрес, на который биндится `server.js` |
| `E2E_BASE_URL` | тесты | `http://localhost:3000` | База для Playwright |

`BACKEND_URL` попадает в rewrites на этапе `next build`, поэтому при смене
адреса backend образ frontend надо пересобрать:
`docker compose -f deploy/docker-compose.prod.yml build frontend`.

## 6. Чек-лист перед первым запуском на сервере

```bash
cp deploy/.env.example deploy/.env
# 1) домен и почта
# 2) POSTGRES_PASSWORD, REDIS_PASSWORD -> и те же значения в DATABASE_URL / REDIS_URL
# 3) JWT_SECRET = openssl rand -base64 48
# 4) CORS_ORIGINS и CSRF_TRUSTED_ORIGINS = https://<DOMAIN>
docker compose -f deploy/docker-compose.prod.yml config >/dev/null   # проверка синтаксиса
docker compose -f deploy/docker-compose.prod.yml up -d --build
BASE_URL=https://<DOMAIN> deploy/scripts/smoke.sh
```

Требуется Docker Compose ≥ 2.24 (используется `env_file: required: false`).
