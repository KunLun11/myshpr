# Runbook: административная часть

Операционная инструкция для школьных администраторов и суперадмина. Продуктовая
часть — этапы 0–5; здесь только админка (этап 6, вариант A без Payload).

## 1. Роли и доступ

| Роль | Что может |
|---|---|
| `super_admin` | Школы, учебные годы любой школы, глобальные справочники, аудит всех школ |
| `school_admin` | Классы, приглашения, учебные годы и контрольные точки своей школы, чек-лист, ученики и импорт, аудит своей школы. Справочники — только чтение |
| `teacher` | Свои классы, проверка тем, работа с проектами, дашборд |
| `student` | Кабинет, мастер темы, продукт, работа |

Админка — это те же страницы Next.js под `/admin/**`, доступ проверяется на
сервере (`requireRole("school_admin")`) и в FastAPI (`require_roles`). Отдельного
второго приложения и второй базы пользователей нет.

## 2. Разделы админки

- `/admin` — классы и коды приглашения.
- `/admin/years` — учебные годы; у школы ровно один текущий год.
- `/admin/schools` — школы (только суперадмин).
- `/admin/references` — сферы интересов и категории продукта.
- `/admin/checklist` — шаблон чек-листа по этапам.
- `/admin/checkpoints` — контрольные точки.
- `/admin/students` — список учеников и импорт CSV.
- `/admin/audit` — журнал действий администраторов.

## 3. Защита от CSRF и origin

Все небезопасные методы (`POST`, `PATCH`, `PUT`, `DELETE`) проходят проверку
`Origin`/`Referer` в FastAPI (`app/core/csrf.py`).

- В dev при пустом allowlist запросы без `Origin` разрешены.
- В prod при пустом allowlist браузерные запросы с `Origin` отклоняются
  (fail closed), а `Sec-Fetch-Site: cross-site` отклоняется всегда.
- Настройка: `CORS_ORIGINS` и `CSRF_TRUSTED_ORIGINS` в `backend/.env`
  (comma-separated), например:
  `CSRF_TRUSTED_ORIGINS=https://project.school.example`.

Cookies остаются `httpOnly`, `SameSite=Lax`, `Secure` в prod — это основная
защита, origin-проверка добавляет второй слой.

## 4. Аудит

Каждое изменение в админке пишется в `audit_log`: кто, когда, школа, действие,
тип и id объекта, JSON-детали. Пароли и временные учётные данные не пишутся.

Посмотреть:

```sql
SELECT created_at, actor_id, school_id, action, entity_type, entity_id, payload
FROM audit_log
ORDER BY created_at DESC
LIMIT 100;
```

Журнал не редактируется через API. Для расследования инцидента выгружайте его
из БД под ролью `app_ro`.

## 5. Импорт учеников из CSV

1. Откройте `/admin/students`, выберите класс.
2. Загрузите CSV в UTF-8 с заголовками `full_name,email` (до 500 строк, до 1 МБ).
3. Ответ покажет созданных учеников и временные пароли. Скачайте CSV с паролями
   и передайте их лично; после ухода со страницы пароли не показываются.
4. Ученики входят с временным паролем и обязаны сменить его при первом входе
   (`must_change_password = true`).
5. Повторный импорт пропускает уже существующие email.

Ограничения: только роль администратора школы/суперадмин, только классы своей
школы. Файл проверяется по размеру, кодировке, заголовкам и email.

## 6. Резервное копирование и восстановление

Скрипты: `deploy/scripts/backup.sh` и `deploy/scripts/restore.sh` (читают
`deploy/.env`).

```bash
# Ежедневный бэкап: pg_dump -Fc + архив media (если STORAGE_BACKEND=local)
deploy/scripts/backup.sh            # -> $BACKUP_DIR/db-<ts>.dump, media-<ts>.tgz

# Проверка восстановления (минимум раз в месяц) — на staging!
deploy/scripts/restore.sh /path/to/db-2026-11-23.dump --yes
BASE_URL=https://staging.example deploy/scripts/smoke.sh
```

Правила:

1. Бэкап лежит **вне** сервера приложения (rsync/object storage/лента).
2. `BACKUP_KEEP_DAYS` (по умолчанию 30) задаёт срок хранения; проверяйте, что
   ротация не удалила единственную копию.
3. Файлы при `STORAGE_BACKEND=s3` не попадают в `media`: включите versioning и
   replication бакета, восстановление файла проверяйте отдельно.
4. Раз в месяц восстановите дамп в пустую staging-БД и прогоните smoke-тест.
5. Фиксируйте дату проверки в журнале эксплуатации.

## 7. Миграции и откат

```bash
cd backend
uv run alembic upgrade head          # применить
uv run alembic current               # текущая ревизия
uv run alembic downgrade -1          # откатить последнюю
uv run alembic check                 # проверить, что модели и БД совпадают
```

Перед миграцией в prod — бэкап. Миграции запускает сервис `migrate` в
`deploy/docker-compose.prod.yml` до старта backend.

## 8. Создание администратора

Демо-данные: `make seed` (создаёт школу, класс, учителя и учеников; пароль из
`app/db/seed.py`).

Для реального администратора создайте пользователя с ролью `school_admin` или
`super_admin` и временным паролем, затем передайте пароль лично:

```bash
cd backend
uv run python - <<'PY'
from app.core.security import hash_password
# Вставьте сюда реальный email и временный пароль; не коммитьте их.
print(hash_password("CHANGE-ME-TEMP-PASSWORD"))
PY
```

Полученный хеш вставьте в `users.password_hash`, затем попросите администратора
сменить пароль. Не храните временные пароли в репозитории или чатах.

## 9. Ограничения и следующий шаг

- Нет 2FA и IP allowlist: для пилота админка живёт за HTTPS и обычным логином.
  Перед публичным запуском — отдельный поддомен/VPN и 2FA.
- Логин блокируется после 5 неверных попыток на 15 минут (`FailureTracker`).
- Админка закрыта от индексации: `robots.txt`, metadata и `X-Robots-Tag`.
- Payload CMS не используется (ADR-05). Если контент начнут править вручную
  ежедневно — отдельное приложение `admin/` на поддерживаемой версии Next.

---

## 10. Prod-деплой

Полный сценарий — `docs/release-checklist.md`. Кратко:

```bash
cp deploy/.env.example deploy/.env
$EDITOR deploy/.env                  # секреты, домен, пароли Redis/Postgres
docker compose -f deploy/docker-compose.prod.yml up -d --build
BASE_URL=https://project.school.example deploy/scripts/smoke.sh
```

Что делает compose:

1. `migrate` применяет Alembic и завершается; backend и worker стартуют только
   после успешной миграции.
2. `caddy` публикует 80/443, получает сертификат и проксирует всё в Next.js.
   FastAPI и БД не опубликованы на хост.
3. Next.js проксирует `/api/backend/*` в FastAPI (same-origin BFF, ADR-03).
4. `media_data`, `pg_data`, `redis_data` и данные Caddy живут в именованных
   томах.

Секреты только в `deploy/.env` (не в git, не в образе). Backend в prod
отказывается стартовать, если:

- `JWT_SECRET` короче 32 символов;
- в `DATABASE_URL` остался демо-пароль `myschoolproject`;
- `RATE_LIMIT_BACKEND` не `redis`.

## 11. TLS и домен

- `DOMAIN` в `deploy/.env` должен указывать A/AAAA-записью на сервер; Caddy
  выпустит сертификат через ACME.
- `ACME_EMAIL` — контакт для Let's Encrypt.
- `HSTS_ENABLED=true` добавляет `Strict-Transport-Security`; включайте только
  когда домен уже работает по HTTPS.
- Если TLS терминирует внешний ingress, уберите сервис `caddy` и направьте
  трафик на `frontend:3000`, сохранив заголовок `X-Forwarded-Proto`.
- Метрики (`/api/v1/metrics` и `/api/backend/metrics`) закрыты на уровне Caddy;
  скрейпьте их из приватной сети.

## 12. Наблюдаемость и алерты

- Логи backend в prod — JSON-строки. Поля: `time`, `level`, `logger`,
  `message`, `request_id`, `user_id`, `route`, `method`, `status`,
  `duration_ms`; ошибки фоновых задач — `task`, `count`.
- Поиск запроса: `docker compose -f deploy/docker-compose.prod.yml logs backend | grep <request_id>`.
  `X-Request-ID` возвращается клиенту и помогает связать жалобу с логом.
- Метрики: `http_requests_total`, `http_request_duration_seconds`,
  `db_pool_connections{state}`, `background_job_runs_total`,
  `background_job_failures_total`.
- Health: `/api/v1/healthz` (liveness), `/api/v1/readyz` (БД), healthcheck
  compose для backend и frontend.
- Минимальные алерты:
  - `/readyz` не 200 дольше 2 минут;
  - рост доли 5xx выше 2% за 5 минут;
  - `background_job_failures_total` увеличился;
  - свободное место на диске < 15% (бэкапы + media);
  - истёк срок сертификата Caddy.
- Sentry/аналог подключается на уровне ASGI-middleware или reverse proxy;
  в MVP не обязателен.

## 13. Инциденты

| Симптом | Действия |
|---|---|
| 5xx после деплоя | `smoke.sh`, логи backend по `request_id`, `docker compose ps`; при подтверждении — откат (ниже) |
| Ученики не могут войти | проверить `/readyz`, Redis (`redis-cli -a ... ping`), `RATE_LIMITED` в логах; при сбое Redis лимитер падает в память процесса (fail-open) и продолжает работать |
| Файлы не скачиваются | проверить `media_data`/S3, права роли, `Content-Disposition: attachment`; restore media из бэкапа |
| Фоновая задача падает | `background_job_failures_total`, логи worker, повторный запуск `arq` идемпотентен по `dedupe_key` |
| Подозрение на утечку секрета | ротировать `JWT_SECRET` (все сессии станут недействительны), пароли БД/Redis, ключи S3; проверить `audit_log` |

## 14. Откат релиза

1. Приложение: вернуть предыдущий образ/тег и `docker compose up -d`.
2. Миграции: `uv run alembic downgrade -1` **только** если релиз содержал
   миграцию и есть бэкап; сначала остановите backend и worker.
3. Данные: `deploy/scripts/restore.sh <dump> --yes` (разрушительно, только
   осознанно).
4. После отката — `smoke.sh` и запись в журнал инцидента.

