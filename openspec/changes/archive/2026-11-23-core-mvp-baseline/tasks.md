# Tasks

## 1. Фундамент (этап 0)

- [x] 1.1 Зафиксировать ADR-01…ADR-10 и доменную модель; проверить наличие `docs/adr/*.md` и `docs/domain.md`.
- [x] 1.2 Реализовать конфигурацию на pydantic-settings с обязательными `DATABASE_URL` и `JWT_SECRET`; проверить `backend/tests/test_config.py`.
- [x] 1.3 Подключить SQLAlchemy 2.0 async и Alembic, добавить расширения `citext` и `pg_trgm`; проверить цикл `alembic upgrade head → downgrade base → upgrade`.
- [x] 1.4 Собрать каркас FastAPI с единым форматом ошибок, request-id и health/readiness; проверить `backend/tests/test_health.py`.
- [x] 1.5 Описать dev/prod compose с Postgres, Redis и healthchecks; проверить `docker compose -f deploy/docker-compose.yml config` и prod-запуск миграций отдельным сервисом.
- [x] 1.6 Настроить CI для backend, frontend и docker-сборки; проверить наличие job'ов в `.github/workflows/ci.yml`.
- [x] 1.7 Подготовить frontend-фундамент: русская локаль, BFF-прокси, API-клиент, shadcn/ui; проверить `npm run lint`, `npx tsc --noEmit`, `npm run build`.

## 2. Модели, миграции и seed (этап 1)

- [x] 2.1 Описать доменные модели и enum'ы (`app/models/*`); проверить `python -c "import app.models"` и `backend/tests/test_constraints.py`.
- [x] 2.2 Создать миграции с ограничениями, индексами и частичными уникальными индексами; проверить `uv run alembic check` и `backend/tests/test_migrations.py`.
- [x] 2.3 Заполнить справочники и демо-данные; проверить повторный запуск `uv run python -m app.db.seed --dev` без дублей.
- [x] 2.4 Реализовать ранги статусов и query-модели для дашборда; проверить `backend/tests/test_stage5.py` (агрегаты и сортировка).
- [x] 2.5 Подготовить тестовую БД и фабрики; проверить полный прогон `uv run pytest -q`.

## 3. Аутентификация, роли и классы (этап 2)

- [x] 3.1 Реализовать регистрацию ученика по коду приглашения; проверить `backend/tests/test_auth.py` (успех, неверный и исчерпанный код).
- [x] 3.2 Реализовать вход, выход, refresh с ротацией и отзывом цепочки; проверить сценарии повторного использования refresh в `test_auth.py`.
- [x] 3.3 Реализовать cookies `access_token`/`refresh_token` с httpOnly, SameSite=Lax и Secure в prod; проверить тесты cookie-флагов.
- [x] 3.4 Реализовать RBAC и school/class-scope; проверить отказы при доступе к чужому классу/проекту в `test_auth.py` и `test_stage4.py`.
- [x] 3.5 Реализовать блокировку после пяти неудачных входов и rate limit login/register; проверить `backend/tests/test_stage7.py` (429, `Retry-After`, 423).
- [x] 3.6 Реализовать смену пароля и флаг обязательной смены для импортированных учеников; проверить `test_auth.py` и `test_stage6.py`.
- [x] 3.7 Реализовать проверку Origin/CSRF для мутаций; проверить `backend/tests/test_stage6.py`.

## 4. Мастер темы (этап 3)

- [x] 4.1 Отдавать справочник сфер интересов; проверить `backend/tests/test_topics.py`.
- [x] 4.2 Реализовать проверку темы на повтор и широту с уровнями `ok/warn/block`; проверить табличные правила в `backend/tests/test_topic_check.py`.
- [x] 4.3 Реализовать автосохранение черновика и единственную активную заявку; проверить `test_topics.py` (частичный уникальный индекс).
- [x] 4.4 Реализовать отправку темы и запрет изменения нормализованной формулировки; проверить `test_topics.py`.
- [x] 4.5 Реализовать очередь проверки и решения учителя (approve/reject, комментарий обязателен при `warn`); проверить `test_topics.py`.
- [x] 4.6 Реализовать реестр утверждённых тем и переход проекта на этап утверждённой темы; проверить `test_topics.py`.
- [x] 4.7 Создавать уведомления о теме идемпотентно; проверить `test_topics.py` и `test_stage5.py`.
- [x] 4.8 Реализовать UI мастера темы и очередь учителя; проверить `frontend/e2e/journey.spec.ts` (сценарий 1 и 2).

## 5. Продукт и работа над проектом (этап 4)

- [x] 5.1 Реализовать справочник категорий продукта с кэшем и инвалидацией; проверить `backend/tests/test_stage4.py`.
- [x] 5.2 Реализовать определение продукта 120–1500 символов с гейтом после темы и событиями; проверить `test_stage4.py`.
- [x] 5.3 Реализовать загрузку/скачивание/удаление файлов с лимитами, allowlist, проверкой сигнатуры и sha256; проверить `test_stage4.py`.
- [x] 5.4 Реализовать комментарии с видимостью и уведомлениями без продления активности; проверить `test_stage4.py`.
- [x] 5.5 Реализовать чек-лист: ленивое создание состояний, переходы ученика, подтверждение педагога, прогресс и просрочки; проверить `test_stage4.py`.
- [x] 5.6 Реализовать карточку проекта для учителя и администратора школы; проверить `test_stage4.py`.
- [x] 5.7 Реализовать UI продукта и вкладок работы (чек-лист, файлы, комментарии); проверить `journey.spec.ts` (сценарии 3 и 4).

## 6. Дашборд и напоминания (этап 5)

- [x] 6.1 Реализовать чистый движок статусов с цветом и кодами причин; проверить матрицу статусов в `backend/tests/test_stage5.py`.
- [x] 6.2 Реализовать дашборд класса с фильтрами и сортировкой; проверить `test_stage5.py` и `journey.spec.ts` (сценарий 5).
- [x] 6.3 Реализовать CRUD контрольных точек и ближайшую точку в проекте ученика; проверить `test_stage5.py`.
- [x] 6.4 Реализовать in-app уведомления с `dedupe_key`; проверить отсутствие дублей в `test_stage5.py`.
- [x] 6.5 Реализовать daily reminders в ARQ и compose-сервис worker; проверить идемпотентность в `test_stage5.py` и конфигурацию `app/workers/settings.py`.
- [x] 6.6 Реализовать UI дашборда и колокольчик уведомлений; проверить `frontend/e2e` и сборку frontend.

## 7. Администрация (этап 6)

- [x] 7.1 Зафиксировать решение «вариант A — без Payload» в ADR-05 и runbook; проверить `docs/adr/adr-05-admin.md`.
- [x] 7.2 Реализовать управление школами для `super_admin`; проверить `backend/tests/test_stage6.py`.
- [x] 7.3 Реализовать учебные годы с единственным текущим годом на школу; проверить `test_stage6.py`.
- [x] 7.4 Реализовать глобальные справочники с правами school_admin/super_admin и инвалидацией кэша; проверить `test_stage6.py`.
- [x] 7.5 Реализовать классы, приглашения и их отзыв; проверить `test_stage6.py`.
- [x] 7.6 Реализовать CSV-импорт учеников с лимитами и временными паролями; проверить `test_stage6.py`.
- [x] 7.7 Реализовать шаблон чек-листа и деактивацию пунктов; проверить `test_stage4.py` и `test_stage6.py`.
- [x] 7.8 Реализовать журнал аудита без секретов; проверить `test_stage6.py`.
- [x] 7.9 Реализовать админ-страницы Next.js с ролевым доступом и noindex; проверить `npm run build` и заголовки `X-Robots-Tag` в `next.config.ts`.

## 8. Безопасность, наблюдаемость и релиз (этап 7)

- [x] 8.1 Заменить `python-jose` на `PyJWT` и устранить критичные advisory; проверить `backend/tests/test_security.py`, `pip-audit`, `npm audit`.
- [x] 8.2 Реализовать Redis/memory rate limit с fail-open; проверить `test_stage7.py`.
- [x] 8.3 Реализовать JSON-логи, request-id и security headers; проверить `test_stage7.py`.
- [x] 8.4 Реализовать метрики Prometheus и флаги `METRICS_ENABLED`/`HSTS_ENABLED`; проверить `test_stage7.py`.
- [x] 8.5 Настроить prod compose с Caddy, one-shot миграциями, worker и healthchecks; проверить `docker compose -f deploy/docker-compose.prod.yml config`.
- [x] 8.6 Добавить скрипты backup/restore/smoke и алерты Prometheus; проверить наличие `deploy/scripts/*.sh` и `deploy/monitoring/prometheus-alerts.yml`.
- [x] 8.7 Реализовать 5 Playwright-сценариев и nightly workflow; проверить `npx playwright test` (2 прогона подряд) и `.github/workflows/e2e.yml`.
- [x] 8.8 Подготовить README, runbook, инструкции ученика и учителя, чек-лист релиза и CHANGELOG; проверить наличие `docs/guides/*.md`, `docs/runbook.md`, `docs/release-checklist.md`, `CHANGELOG.md`.

## 9. Синхронизация OpenSpec и плана

- [x] 9.1 Зафиксировать delta-спеки для семи capability и проверить `openspec validate core-mvp-baseline --strict`.
- [x] 9.2 Актуализировать `TASKS.md`: отметить выполненные критерии и явно оставить внешние/отложенные пункты.
- [x] 9.3 Сверить перечень переменных окружения с `backend/app/core/config.py`, `backend/.env.example` и `deploy/.env.example`.
- [x] 9.4 Проверить, что код, тесты и сборка не менялись этим change: `git diff --stat` и полный прогон проверок.

## Workflow follow-up

- Архивировать change после ревью: `openspec archive core-mvp-baseline`.
- Проверить, что `openspec/specs/**` содержит семь основных спецификаций и `openspec validate --specs --strict` проходит.
