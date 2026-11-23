"""Topic submissions, duplicate detection and the approved-topic registry."""

import uuid
from dataclasses import dataclass

from sqlalchemy import func, literal, literal_column, or_, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AcademicYear,
    InterestArea,
    Project,
    SchoolClass,
    Topic,
    TopicSubmission,
    User,
)
from app.models.enums import TopicStatus, TopicSubmissionStatus

ACTIVE_SUBMISSION_STATUSES = (
    TopicSubmissionStatus.DRAFT,
    TopicSubmissionStatus.SUBMITTED,
)
PENDING_SUBMISSION_STATUSES = (
    TopicSubmissionStatus.SUBMITTED,
    TopicSubmissionStatus.APPROVED,
)


@dataclass(slots=True)
class SubmissionRow:
    submission: TopicSubmission
    project_id: uuid.UUID
    student_id: uuid.UUID
    student_full_name: str
    class_id: uuid.UUID
    class_label: str
    interest_area_name: str | None
    duplicate_of_title: str | None


@dataclass(slots=True)
class RegistryRow:
    topic: Topic
    author_full_name: str | None
    interest_area_name: str | None
    academic_year_name: str | None


def _submission_stmt():
    return (
        select(
            TopicSubmission,
            Project.id,
            Project.student_id,
            User.full_name,
            Project.class_id,
            SchoolClass.label,
            InterestArea.name,
            Topic.title,
        )
        .join(Project, Project.id == TopicSubmission.project_id)
        .join(User, User.id == TopicSubmission.author_student_id)
        .join(SchoolClass, SchoolClass.id == Project.class_id)
        .outerjoin(InterestArea, InterestArea.id == TopicSubmission.interest_area_id)
        .outerjoin(Topic, Topic.id == TopicSubmission.duplicate_of_topic_id)
    )


def _submission_row(row) -> SubmissionRow | None:
    if row is None:
        return None
    return SubmissionRow(row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7])


async def get_by_id(session: AsyncSession, submission_id: uuid.UUID) -> TopicSubmission | None:
    return await session.get(TopicSubmission, submission_id)


async def get_row(session: AsyncSession, submission_id: uuid.UUID) -> SubmissionRow | None:
    result = await session.execute(_submission_stmt().where(TopicSubmission.id == submission_id))
    return _submission_row(result.first())


async def get_active_for_project(
    session: AsyncSession, project_id: uuid.UUID
) -> TopicSubmission | None:
    result = await session.execute(
        select(TopicSubmission)
        .where(
            TopicSubmission.project_id == project_id,
            TopicSubmission.status.in_(ACTIVE_SUBMISSION_STATUSES),
        )
        .order_by(TopicSubmission.created_at.desc())
    )
    return result.scalars().first()


async def get_latest_for_project(
    session: AsyncSession, project_id: uuid.UUID
) -> TopicSubmission | None:
    result = await session.execute(
        select(TopicSubmission)
        .where(TopicSubmission.project_id == project_id)
        .order_by(TopicSubmission.created_at.desc())
    )
    return result.scalars().first()


async def create_submission(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    school_id: uuid.UUID,
    academic_year_id: uuid.UUID,
    author_student_id: uuid.UUID,
    interest_area_id: uuid.UUID | None,
    research_question: str,
    title: str,
    normalized_title: str,
    status: TopicSubmissionStatus = TopicSubmissionStatus.DRAFT,
) -> TopicSubmission:
    submission = TopicSubmission(
        project_id=project_id,
        school_id=school_id,
        academic_year_id=academic_year_id,
        author_student_id=author_student_id,
        interest_area_id=interest_area_id,
        research_question=research_question,
        title=title,
        normalized_title=normalized_title,
        status=status,
    )
    session.add(submission)
    await session.flush()
    return submission


async def update_submission(
    session: AsyncSession,
    submission_id: uuid.UUID,
    *,
    values: dict,
    expected_statuses: tuple[TopicSubmissionStatus, ...] | None = None,
) -> bool:
    """Conditional update: the row is only changed when it is still in a known state."""
    stmt = update(TopicSubmission).where(TopicSubmission.id == submission_id)
    if expected_statuses is not None:
        stmt = stmt.where(TopicSubmission.status.in_(expected_statuses))
    result = await session.execute(
        stmt.values(**values).execution_options(synchronize_session="fetch")
    )
    return bool(result.rowcount)


async def list_teacher_submissions(
    session: AsyncSession,
    *,
    teacher_id: uuid.UUID,
    status: TopicSubmissionStatus | None,
    limit: int,
    offset: int,
) -> list[SubmissionRow]:
    stmt = _submission_stmt().where(SchoolClass.curator_id == teacher_id)
    if status is not None:
        stmt = stmt.where(TopicSubmission.status == status)
    stmt = stmt.order_by(TopicSubmission.updated_at.asc()).limit(limit).offset(offset)
    result = await session.execute(stmt)
    return [row for raw in result.all() if (row := _submission_row(raw)) is not None]


async def count_teacher_submissions(
    session: AsyncSession, *, teacher_id: uuid.UUID, status: TopicSubmissionStatus
) -> int:
    result = await session.execute(
        select(func.count(TopicSubmission.id))
        .join(Project, Project.id == TopicSubmission.project_id)
        .join(SchoolClass, SchoolClass.id == Project.class_id)
        .where(SchoolClass.curator_id == teacher_id, TopicSubmission.status == status)
    )
    return int(result.scalar_one())


async def find_duplicate_titles(
    session: AsyncSession,
    *,
    school_id: uuid.UUID,
    academic_year_id: uuid.UUID,
    normalized_title: str,
    threshold: float,
    exclude_submission_id: uuid.UUID | None = None,
    limit: int = 10,
) -> list[tuple[str, uuid.UUID, str, float]]:
    """Return ``(source, id, title, score)`` rows ordered by similarity.

    Uses pg_trgm's ``%`` operator so the GIN index on ``normalized_title`` is
    used. The comparison threshold is applied for the current transaction.
    """
    await session.execute(text("SELECT set_limit(:threshold)"), {"threshold": threshold})

    registry_score = func.similarity(Topic.normalized_title, normalized_title).label("score")
    pending_score = func.similarity(TopicSubmission.normalized_title, normalized_title).label(
        "score"
    )

    registry = select(
        literal("registry").label("source"),
        Topic.id,
        Topic.title,
        registry_score,
    ).where(
        Topic.school_id == school_id,
        Topic.status == TopicStatus.ACTIVE,
        or_(
            Topic.normalized_title == normalized_title,
            Topic.normalized_title.op("%")(normalized_title),
        ),
    )

    pending_stmt = select(
        literal("pending").label("source"),
        TopicSubmission.id,
        TopicSubmission.title,
        pending_score,
    ).where(
        TopicSubmission.school_id == school_id,
        TopicSubmission.academic_year_id == academic_year_id,
        TopicSubmission.status.in_(PENDING_SUBMISSION_STATUSES),
        TopicSubmission.normalized_title.op("%")(normalized_title),
    )
    if exclude_submission_id is not None:
        pending_stmt = pending_stmt.where(TopicSubmission.id != exclude_submission_id)

    stmt = registry.union_all(pending_stmt).order_by(literal_column("score").desc()).limit(limit)
    rows = (await session.execute(stmt)).all()
    return [(row[0], row[1], row[2], float(row[3])) for row in rows]


async def get_topic_by_title(
    session: AsyncSession, *, school_id: uuid.UUID, normalized_title: str
) -> Topic | None:
    result = await session.execute(
        select(Topic).where(
            Topic.school_id == school_id,
            Topic.normalized_title == normalized_title,
        )
    )
    return result.scalars().first()


async def create_topic(
    session: AsyncSession,
    *,
    school_id: uuid.UUID,
    academic_year_id: uuid.UUID,
    title: str,
    normalized_title: str,
    research_question: str | None,
    author_student_id: uuid.UUID,
    source_submission_id: uuid.UUID,
    approved_at,
) -> Topic:
    topic = Topic(
        school_id=school_id,
        academic_year_id=academic_year_id,
        title=title,
        normalized_title=normalized_title,
        research_question=research_question,
        author_student_id=author_student_id,
        source_submission_id=source_submission_id,
        status=TopicStatus.ACTIVE,
        approved_at=approved_at,
    )
    session.add(topic)
    await session.flush()
    return topic


async def list_registry(
    session: AsyncSession,
    *,
    teacher_id: uuid.UUID,
    academic_year_id: uuid.UUID | None,
    interest_area_id: uuid.UUID | None,
    limit: int,
    offset: int,
) -> list[RegistryRow]:
    stmt = (
        select(Topic, User.full_name, InterestArea.name, AcademicYear.name)
        .join(TopicSubmission, TopicSubmission.id == Topic.source_submission_id)
        .join(Project, Project.id == TopicSubmission.project_id)
        .join(SchoolClass, SchoolClass.id == Project.class_id)
        .outerjoin(User, User.id == Topic.author_student_id)
        .outerjoin(InterestArea, InterestArea.id == TopicSubmission.interest_area_id)
        .join(AcademicYear, AcademicYear.id == Topic.academic_year_id)
        .where(SchoolClass.curator_id == teacher_id, Topic.status == TopicStatus.ACTIVE)
    )
    if academic_year_id is not None:
        stmt = stmt.where(Topic.academic_year_id == academic_year_id)
    if interest_area_id is not None:
        stmt = stmt.where(TopicSubmission.interest_area_id == interest_area_id)
    stmt = stmt.order_by(Topic.approved_at.desc()).limit(limit).offset(offset)
    result = await session.execute(stmt)
    return [RegistryRow(row[0], row[1], row[2], row[3]) for row in result.all()]
