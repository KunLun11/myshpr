"""Small async factories for building test rows."""

import uuid
from datetime import UTC, date, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models import (
    AcademicYear,
    ChecklistItem,
    Checkpoint,
    ClassInvite,
    InterestArea,
    ProductCategory,
    Project,
    School,
    SchoolClass,
    StudentProfile,
    Topic,
    User,
)
from app.models.enums import ProjectStatus, TopicStatus, UserRole


def _uid() -> str:
    return uuid.uuid4().hex[:8]


async def create_school(session: AsyncSession, name: str | None = None) -> School:
    school = School(name=name or f"School {_uid()}", is_active=True)
    session.add(school)
    await session.flush()
    return school


async def create_year(
    session: AsyncSession, school: School, name: str | None = None, *, is_current: bool = False
) -> AcademicYear:
    year = AcademicYear(
        school_id=school.id,
        name=name or f"2026/{_uid()}",
        starts_on=date(2026, 9, 1),
        ends_on=date(2027, 5, 31),
        is_current=is_current,
    )
    session.add(year)
    await session.flush()
    return year


async def create_user(
    session: AsyncSession,
    school: School,
    role: UserRole = UserRole.STUDENT,
    *,
    email: str | None = None,
    password: str | None = None,
    full_name: str = "Test User",
    is_active: bool = True,
) -> User:
    user = User(
        school_id=school.id,
        role=role,
        email=email or f"{_uid()}@example.com",
        password_hash=hash_password(password) if password else "x",
        full_name=full_name,
        is_active=is_active,
    )
    session.add(user)
    await session.flush()
    return user


async def create_class(
    session: AsyncSession,
    school: School,
    year: AcademicYear,
    *,
    grade: int = 9,
    label: str | None = None,
    curator_id: uuid.UUID | None = None,
) -> SchoolClass:
    klass = SchoolClass(
        school_id=school.id,
        academic_year_id=year.id,
        grade=grade,
        label=label or f"9{_uid()[:2]}",
        curator_id=curator_id,
    )
    session.add(klass)
    await session.flush()
    return klass


async def create_invite(
    session: AsyncSession,
    school_class: SchoolClass,
    *,
    code: str | None = None,
    expires_in_days: int = 14,
    max_uses: int | None = None,
    uses_count: int = 0,
    revoked: bool = False,
    created_by: uuid.UUID | None = None,
) -> ClassInvite:
    now = datetime.now(UTC)
    invite = ClassInvite(
        class_id=school_class.id,
        code=code or f"C{_uid().upper()}",
        created_by=created_by,
        expires_at=now + timedelta(days=expires_in_days),
        max_uses=max_uses,
        uses_count=uses_count,
        revoked_at=now if revoked else None,
    )
    session.add(invite)
    await session.flush()
    return invite


async def create_project(
    session: AsyncSession, student: User, year: AcademicYear, klass: SchoolClass, **kwargs
) -> Project:
    project = Project(
        student_id=student.id,
        academic_year_id=year.id,
        class_id=klass.id,
        **kwargs,
    )
    session.add(project)
    await session.flush()
    return project


async def create_student(
    session: AsyncSession,
    school: School,
    school_class: SchoolClass,
    *,
    email: str | None = None,
    password: str | None = "password123",
    full_name: str = "Ученик Тестовый",
) -> User:
    student = await create_user(
        session,
        school,
        UserRole.STUDENT,
        email=email,
        password=password,
        full_name=full_name,
    )
    session.add(StudentProfile(user_id=student.id, class_id=school_class.id))
    await session.flush()
    return student


async def create_interest_area(
    session: AsyncSession,
    *,
    slug: str | None = None,
    name: str = "Экология",
    is_active: bool = True,
) -> InterestArea:
    area = InterestArea(
        slug=slug or f"area-{_uid()}",
        name=name,
        description="Тестовая сфера",
        is_active=is_active,
        sort_order=10,
    )
    session.add(area)
    await session.flush()
    return area


async def create_topic(
    session: AsyncSession,
    school: School,
    year: AcademicYear,
    *,
    title: str,
    normalized_title: str,
    author_student_id: uuid.UUID | None = None,
) -> Topic:
    topic = Topic(
        school_id=school.id,
        academic_year_id=year.id,
        title=title,
        normalized_title=normalized_title,
        author_student_id=author_student_id,
        status=TopicStatus.ACTIVE,
        approved_at=datetime.now(UTC),
    )
    session.add(topic)
    await session.flush()
    return topic


async def create_product_category(
    session: AsyncSession,
    *,
    slug: str | None = None,
    name: str = "Исследование",
    is_active: bool = True,
) -> ProductCategory:
    category = ProductCategory(
        slug=slug or f"product-{_uid()}",
        name=name,
        description="Тестовая категория",
        guidance={
            "examples": ["Пример продукта"],
            "must_have": ["Методика"],
            "common_mistakes": ["Нет данных"],
            "defense_tip": "Покажи результат",
        },
        is_active=is_active,
        sort_order=10,
    )
    session.add(category)
    await session.flush()
    return category


async def create_checkpoint(
    session: AsyncSession,
    year: AcademicYear,
    *,
    school_id: uuid.UUID | None = None,
    code: str | None = None,
    title: str = "Контрольная точка",
    due_at: datetime | None = None,
    required_status: ProjectStatus = ProjectStatus.TOPIC_APPROVED,
    is_active: bool = True,
) -> Checkpoint:
    checkpoint = Checkpoint(
        school_id=school_id,
        academic_year_id=year.id,
        code=code or f"cp-{_uid()}",
        title=title,
        due_at=due_at or datetime.now(UTC) + timedelta(days=10),
        required_status=required_status,
        is_active=is_active,
        sort_order=10,
    )
    session.add(checkpoint)
    await session.flush()
    return checkpoint


async def create_checklist_item(
    session: AsyncSession,
    year: AcademicYear,
    *,
    school_id: uuid.UUID | None = None,
    code: str | None = None,
    title: str = "Собрать источники",
    stage: ProjectStatus = ProjectStatus.IN_PROGRESS,
    is_required: bool = True,
    due_at: datetime | None = None,
) -> ChecklistItem:
    item = ChecklistItem(
        school_id=school_id,
        academic_year_id=year.id,
        stage=stage,
        code=code or f"item-{_uid()}",
        title=title,
        sort_order=10,
        is_required=is_required,
        due_at=due_at,
        is_active=True,
    )
    session.add(item)
    await session.flush()
    return item
