"""Idempotent development seed.

Run after migrations:

    uv run python -m app.db.seed --dev

Creates reference data, a demo school/year/class, teacher and students,
checkpoints and the base checklist. Re-running is safe: every row is
looked up before insert.
"""

import argparse
import asyncio
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.db.session import async_session_factory, engine
from app.models import (
    AcademicYear,
    ChecklistItem,
    Checkpoint,
    InterestArea,
    ProductCategory,
    Project,
    ProjectChecklistState,
    School,
    SchoolClass,
    StudentProfile,
    User,
)
from app.models.enums import ChecklistState, CheckpointAudience, ProjectStatus, UserRole

DEMO_PASSWORD = "student123"

INTEREST_AREAS = [
    ("tech", "Техника и инженерия", "Роботы, устройства, конструирование"),
    ("ecology", "Экология", "Природа, отходы, вода, климат"),
    ("medicine", "Медицина и здоровье", "Здоровье, биология, гигиена"),
    ("art", "Искусство и дизайн", "Изобразительное искусство, музыка, дизайн"),
    ("society", "Общество", "Социология, право, волонтёрство"),
    ("sport", "Спорт", "Физическая культура и здоровый образ жизни"),
    ("it", "Информационные технологии", "Программирование, данные, ИИ"),
    ("economy", "Экономика", "Финансы, бизнес, потребление"),
    ("language", "Язык и литература", "Лингвистика, литература, перевод"),
    ("history", "История и краеведение", "История, музеи, местность"),
]

PRODUCT_CATEGORIES = [
    {
        "slug": "model",
        "name": "Модель / макет",
        "description": "Физическая или цифровая модель объекта.",
        "guidance": {
            "examples": ["Действующая модель очистки воды", "Макет школьного двора"],
            "must_have": ["Понятная функция", "Материалы или технологии", "Что показать на защите"],
            "common_mistakes": ["Модель не связана с вопросом"],
            "defense_tip": "Покажи модель и объясни, как она отвечает на вопрос.",
        },
    },
    {
        "slug": "software",
        "name": "Программа / приложение",
        "description": "Код, сайт, бот или приложение.",
        "guidance": {
            "examples": ["Бот-напоминание", "Сайт школьного музея"],
            "must_have": ["Работающий прототип", "Пользовательский сценарий"],
            "common_mistakes": ["Нет демонстрации работы"],
            "defense_tip": "Продемонстрируй работающий прототип.",
        },
    },
    {
        "slug": "research",
        "name": "Исследование",
        "description": "Исследовательская работа с данными и выводами.",
        "guidance": {
            "examples": ["Исследование качества воды в районе"],
            "must_have": ["Методика", "Данные", "Выводы"],
            "common_mistakes": ["Выводы не следуют из данных"],
            "defense_tip": "Расскажи методику и покажи данные.",
        },
    },
    {
        "slug": "media",
        "name": "Видео / подкаст",
        "description": "Медиапродукт на тему проекта.",
        "guidance": {
            "examples": ["Документальный ролик о проблеме"],
            "must_have": ["Сценарий", "Готовый файл"],
            "common_mistakes": ["Нет связи с исследовательским вопросом"],
            "defense_tip": "Покажи фрагмент и объясни замысел.",
        },
    },
    {
        "slug": "event",
        "name": "Мероприятие",
        "description": "Организованное событие для аудитории.",
        "guidance": {
            "examples": ["Экологическая акция в школе"],
            "must_have": ["План", "Проведение", "Результат"],
            "common_mistakes": ["Мероприятие не проведено"],
            "defense_tip": "Покажи план и результаты проведения.",
        },
    },
    {
        "slug": "handbook",
        "name": "Пособие / буклет",
        "description": "Печатный или цифровой материал.",
        "guidance": {
            "examples": ["Памятка по раздельному сбору"],
            "must_have": ["Содержание", "Оформление"],
            "common_mistakes": ["Материал не проверен"],
            "defense_tip": "Покажи пособие и обоснуй содержание.",
        },
    },
    {
        "slug": "device",
        "name": "Эксперимент / устройство",
        "description": "Экспериментальная установка или устройство.",
        "guidance": {
            "examples": ["Устройство для полива растений"],
            "must_have": ["Работоспособность", "Измерения"],
            "common_mistakes": ["Устройство не работает"],
            "defense_tip": "Продемонстрируй работу устройства.",
        },
    },
    {
        "slug": "other",
        "name": "Другое",
        "description": "Иной формат продукта.",
        "guidance": {"examples": [], "must_have": [], "common_mistakes": [], "defense_tip": ""},
    },
]

CHECKPOINTS = [
    ("topic_draft", "Черновик темы", date(2026, 10, 15), ProjectStatus.TOPIC_DRAFT),
    ("topic_approved", "Утверждение темы", date(2026, 11, 15), ProjectStatus.TOPIC_APPROVED),
    ("product_defined", "Определение продукта", date(2026, 12, 15), ProjectStatus.PRODUCT_DEFINED),
    ("midway_check", "Промежуточная проверка", date(2027, 3, 1), ProjectStatus.IN_PROGRESS),
    (
        "ready_for_defense",
        "Готовность к защите",
        date(2027, 4, 15),
        ProjectStatus.READY_FOR_DEFENSE,
    ),
]

CHECKLIST = [
    (ProjectStatus.TOPIC_DRAFT, "choose_interest", "Выбрать сферу интересов"),
    (ProjectStatus.TOPIC_DRAFT, "research_question", "Сформулировать исследовательский вопрос"),
    (ProjectStatus.TOPIC_DRAFT, "draft_title", "Подготовить черновик темы"),
    (ProjectStatus.TOPIC_SUBMITTED, "submit_topic", "Отправить тему учителю"),
    (ProjectStatus.TOPIC_APPROVED, "approve_topic", "Утвердить тему"),
    (ProjectStatus.PRODUCT_DRAFT, "choose_product_category", "Выбрать категорию продукта"),
    (ProjectStatus.PRODUCT_DEFINED, "describe_product", "Описать продукт и результат"),
    (ProjectStatus.IN_PROGRESS, "collect_sources", "Собрать источники"),
    (ProjectStatus.IN_PROGRESS, "do_research", "Провести исследование/изготовление"),
    (ProjectStatus.IN_PROGRESS, "upload_final", "Загрузить итоговый файл"),
    (ProjectStatus.READY_FOR_DEFENSE, "make_presentation", "Подготовить презентацию"),
    (ProjectStatus.READY_FOR_DEFENSE, "rehearse", "Отрепетировать защиту"),
]

STUDENTS = [
    ("Анна Смирнова", "student1@example.com"),
    ("Иван Петров", "student2@example.com"),
    ("Мария Кузнецова", "student3@example.com"),
    ("Даниил Волков", "student4@example.com"),
    ("Елизавета Соколова", "student5@example.com"),
]


def _as_datetime(value: date) -> datetime:
    return datetime(value.year, value.month, value.day, tzinfo=UTC)


async def _get_or_create[T](
    session: AsyncSession,
    model: type[T],
    *,
    defaults: dict[str, Any] | None = None,
    **filters: Any,
) -> T:
    result = await session.execute(select(model).filter_by(**filters))
    obj = result.scalars().first()
    if obj is not None:
        return obj
    obj = model(**filters, **(defaults or {}))
    session.add(obj)
    await session.flush()
    return obj


async def seed(session: AsyncSession) -> None:
    # Reference data
    areas: dict[str, InterestArea] = {}
    for sort_order, (slug, name, description) in enumerate(INTEREST_AREAS):
        areas[slug] = await _get_or_create(
            session,
            InterestArea,
            slug=slug,
            defaults={"name": name, "description": description, "sort_order": sort_order},
        )

    for sort_order, item in enumerate(PRODUCT_CATEGORIES):
        await _get_or_create(
            session,
            ProductCategory,
            slug=item["slug"],
            defaults={
                "name": item["name"],
                "description": item["description"],
                "guidance": item["guidance"],
                "sort_order": sort_order,
            },
        )

    # School / year / class
    school = await _get_or_create(
        session,
        School,
        name="МБОУ «Примерная школа»",
        defaults={"region": "Москва", "city": "Москва", "timezone": "Europe/Moscow"},
    )
    year = await _get_or_create(
        session,
        AcademicYear,
        school_id=school.id,
        name="2026/2027",
        defaults={"starts_on": date(2026, 9, 1), "ends_on": date(2027, 5, 31), "is_current": True},
    )

    teacher = await _get_or_create(
        session,
        User,
        email="teacher@example.com",
        defaults={
            "school_id": school.id,
            "role": UserRole.TEACHER,
            "password_hash": hash_password(DEMO_PASSWORD),
            "full_name": "Иванова Мария Петровна",
        },
    )

    school_class = await _get_or_create(
        session,
        SchoolClass,
        school_id=school.id,
        academic_year_id=year.id,
        grade=9,
        label="9А",
        defaults={"curator_id": teacher.id},
    )

    students: list[User] = []
    for full_name, email in STUDENTS:
        student = await _get_or_create(
            session,
            User,
            email=email,
            defaults={
                "school_id": school.id,
                "role": UserRole.STUDENT,
                "password_hash": hash_password(DEMO_PASSWORD),
                "full_name": full_name,
            },
        )
        students.append(student)
        await _get_or_create(
            session, StudentProfile, user_id=student.id, defaults={"class_id": school_class.id}
        )

    # Checkpoints (school-scoped, per year)
    for sort_order, (code, title, due, required) in enumerate(CHECKPOINTS):
        await _get_or_create(
            session,
            Checkpoint,
            school_id=school.id,
            academic_year_id=year.id,
            code=code,
            defaults={
                "title": title,
                "due_at": _as_datetime(due),
                "required_status": required,
                "audience": CheckpointAudience.STUDENT,
                "sort_order": sort_order,
            },
        )

    # Global checklist template (school_id = NULL)
    checklist_items: list[ChecklistItem] = []
    for sort_order, (stage, code, title) in enumerate(CHECKLIST):
        item = await _get_or_create(
            session,
            ChecklistItem,
            school_id=None,
            academic_year_id=year.id,
            code=code,
            defaults={"stage": stage, "title": title, "sort_order": sort_order},
        )
        checklist_items.append(item)

    # One demo project with checklist states for the first student
    if students:
        project = await _get_or_create(
            session,
            Project,
            student_id=students[0].id,
            academic_year_id=year.id,
            defaults={
                "class_id": school_class.id,
                "status": ProjectStatus.IDEA,
                "interest_area_id": areas["ecology"].id,
            },
        )
        for item in checklist_items:
            await _get_or_create(
                session,
                ProjectChecklistState,
                project_id=project.id,
                checklist_item_id=item.id,
                defaults={"status": ChecklistState.PENDING},
            )

    await session.commit()


async def _main(dev: bool) -> None:
    if not dev:
        raise SystemExit("Refusing to seed without --dev. This is demo data only.")
    async with async_session_factory() as session:
        await seed(session)
    await engine.dispose()
    print("Seed complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed demo data")
    parser.add_argument("--dev", action="store_true", help="allow seeding demo data")
    args = parser.parse_args()
    asyncio.run(_main(dev=args.dev))
