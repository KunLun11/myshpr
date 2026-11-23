# Backend

FastAPI + SQLAlchemy 2.0 async + Alembic. См. `docs/domain.md` и `TASKS.md`.

## Запуск

```bash
uv sync
uv run alembic upgrade head
uv run python -m app.db.seed --dev
uv run uvicorn app.main:app --reload
```

Переменные окружения — в `.env.example`.

## Этап 3: мастер темы

### Эндпоинты

| Метод | Путь | Роль |
|---|---|---|
| GET | `/api/v1/reference/interest-areas` | auth |
| GET/PATCH | `/api/v1/me/project` | student |
| POST | `/api/v1/me/project/topic/check` | student |
| POST | `/api/v1/me/project/topic/submit` | student |
| GET | `/api/v1/teacher/submissions?status=submitted` | teacher |
| POST | `/api/v1/teacher/submissions/{id}/approve` | teacher |
| POST | `/api/v1/teacher/submissions/{id}/reject` | teacher |
| GET | `/api/v1/teacher/topics` | teacher |

### Проверки темы

Проверки детерминированные, без LLM:

1. **Нормализация** — `normalize_title`: нижний регистр, `ё → е`, удаление
   пунктуации, схлопывание пробелов.
2. **Повтор** — pg_trgm-сходство по GIN-индексам `topics.normalized_title` и
   `topic_submissions.normalized_title`, плюс точное совпадение. Сравниваются
   реестр школы и активные заявки текущего учебного года.
3. **Широта** — старт 50; +10 за каждую категорию сужения (место, период,
   группа, технология/материал, сравнение, метод), максимум +30; −15 за каждое
   слово широты. Жёсткие блокировки: меньше 4 слов, только общие слова, вопрос
   без объекта, «как влияет интернет на людей?».

### Пороги

Пороги задаются в `.env` (см. `.env.example`):

| Переменная | По умолчанию | Значение |
|---|---:|---|
| `TOPIC_DUPLICATE_WARN` | 0.55 | похожая тема → предупреждение |
| `TOPIC_DUPLICATE_BLOCK` | 0.85 | почти повтор → блокировка |
| `TOPIC_BROADNESS_OK` | 70 | хорошая конкретность |
| `TOPIC_BROADNESS_WARN` | 40 | можно утвердить с комментарием |

Учитель может утвердить тему уровня `warn` только с комментарием. Тему уровня
`block` утвердить нельзя.

### Тесты

```bash
uv run pytest
```

`tests/test_topic_check.py` — табличные тесты правил (нормализация, вопрос,
широта), `tests/test_topics.py` — полный цикл через API.

## Этап 4: продукт, файлы, комментарии и чек-листы

### Эндпоинты

| Метод | Путь | Роль |
|---|---|---|
| GET | `/api/v1/reference/product-categories` | auth |
| GET/PATCH | `/api/v1/me/project/product` | student |
| GET/POST | `/api/v1/me/project/files` | student |
| DELETE | `/api/v1/me/project/files/{id}` | student |
| GET | `/api/v1/files/{id}/download` | auth (по правам) |
| GET | `/api/v1/me/project/checklist` | student |
| PATCH | `/api/v1/me/project/checklist/{item_id}` | student |
| GET | `/api/v1/me/project/comments` | student |
| GET | `/api/v1/teacher/projects` | teacher/school_admin |
| GET | `/api/v1/teacher/projects/{id}` | teacher/school_admin |
| GET | `/api/v1/teacher/projects/{id}/files` | teacher/school_admin |
| GET | `/api/v1/teacher/projects/{id}/checklist` | teacher/school_admin |
| GET/POST | `/api/v1/teacher/projects/{id}/comments` | teacher/school_admin |
| PATCH/DELETE | `/api/v1/teacher/comments/{id}` | автор |
| POST | `/api/v1/teacher/checklist-states/{id}/verify` | teacher/school_admin |
| POST | `/api/v1/teacher/checklist-states/{id}/skip` | teacher/school_admin |
| GET/POST/PATCH/DELETE | `/api/v1/admin/checklist-items` | school_admin/super_admin |

### Файлы

- Локальное хранилище (`STORAGE_BACKEND=local`, `MEDIA_ROOT=media`) в dev;
  S3-совместимое — в prod (`STORAGE_BACKEND=s3`, optional extra `s3`).
- Лимиты: 25 МБ на файл, 10 файлов на проект.
- Разрешены `.pdf`, `.docx`, `.pptx`, `.png`, `.jpg`, `.jpeg`, `.zip`;
  проверяются расширение, declared MIME и сигнатура (DOCX/PPTX — ZIP).
- Дубликат по `(project_id, sha256)` отклоняется. Удаление — soft delete.
- Скачивание только через API: ученик-владелец, куратор класса или
  администратор школы. Публичных ссылок нет.

### Комментарии и чек-листы

- Комментарии односторонние (учитель → ученик), без ответов и тредов.
  `teachers_only` ученику не отдаётся; на `student_visible` создаётся
  уведомление `new_comment`.
- Чек-лист создаёт состояния лениво при первом чтении. Ученик ставит
  `in_progress`/`done`; `verified`/`skipped` — только staff.
- Прогресс = закрытые обязательные пункты / все обязательные пункты.
  Просроченные обязательные пункты помечаются `overdue`.

`tests/test_stage4.py` покрывает продукт, загрузку/скачивание/удаление файлов,
права, дубликаты, комментарии, чек-лист, админский CRUD и сквозной сценарий.
