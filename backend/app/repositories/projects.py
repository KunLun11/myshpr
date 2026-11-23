"""Project queries: the student's project for a year and its event log."""

import uuid
from dataclasses import dataclass

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AcademicYear, InterestArea, Project, ProjectEvent, SchoolClass, User
from app.models.enums import ProjectStatus

ACTIVE_PROJECT_STATUSES = tuple(
    status for status in ProjectStatus if status is not ProjectStatus.ARCHIVED
)


@dataclass(slots=True)
class ProjectRow:
    project: Project
    class_label: str
    class_grade: int
    academic_year_name: str | None
    interest_area_name: str | None
    interest_area_slug: str | None


@dataclass(slots=True)
class StaffProjectRow:
    """Project joined with the data staff needs to scope access."""

    project: Project
    student_full_name: str
    class_label: str
    class_grade: int
    school_id: uuid.UUID
    curator_id: uuid.UUID | None
    academic_year_name: str | None


def _project_row_stmt():
    return (
        select(
            Project,
            SchoolClass.label,
            SchoolClass.grade,
            AcademicYear.name,
            InterestArea.name,
            InterestArea.slug,
        )
        .join(SchoolClass, SchoolClass.id == Project.class_id)
        .join(AcademicYear, AcademicYear.id == Project.academic_year_id)
        .outerjoin(InterestArea, InterestArea.id == Project.interest_area_id)
    )


def _row(result_row) -> ProjectRow | None:
    if result_row is None:
        return None
    return ProjectRow(
        result_row[0],
        result_row[1],
        result_row[2],
        result_row[3],
        result_row[4],
        result_row[5],
    )


async def get_by_id(session: AsyncSession, project_id: uuid.UUID) -> Project | None:
    return await session.get(Project, project_id)


async def get_row(session: AsyncSession, project_id: uuid.UUID) -> ProjectRow | None:
    result = await session.execute(_project_row_stmt().where(Project.id == project_id))
    return _row(result.first())


async def get_student_project(
    session: AsyncSession, *, student_id: uuid.UUID, academic_year_id: uuid.UUID
) -> Project | None:
    result = await session.execute(
        select(Project).where(
            Project.student_id == student_id,
            Project.academic_year_id == academic_year_id,
        )
    )
    return result.scalars().first()


async def get_student_project_row(
    session: AsyncSession, *, student_id: uuid.UUID, class_id: uuid.UUID
) -> ProjectRow | None:
    result = await session.execute(
        _project_row_stmt().where(Project.student_id == student_id, Project.class_id == class_id)
    )
    return _row(result.first())


async def create(
    session: AsyncSession,
    *,
    student_id: uuid.UUID,
    academic_year_id: uuid.UUID,
    class_id: uuid.UUID,
) -> Project:
    project = Project(
        student_id=student_id,
        academic_year_id=academic_year_id,
        class_id=class_id,
        status=ProjectStatus.IDEA,
    )
    session.add(project)
    await session.flush()
    return project


async def update_fields(
    session: AsyncSession, project_id: uuid.UUID, *, values: dict, expected_statuses=None
) -> bool:
    """Update the project, optionally guarding the current status atomically."""
    stmt = update(Project).where(Project.id == project_id)
    if expected_statuses is not None:
        stmt = stmt.where(Project.status.in_(expected_statuses))
    result = await session.execute(
        stmt.values(**values).execution_options(synchronize_session="fetch")
    )
    return bool(result.rowcount)


async def add_event(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    event_type: str,
    actor_id: uuid.UUID | None = None,
    payload: dict | None = None,
) -> None:
    session.add(
        ProjectEvent(
            project_id=project_id,
            actor_id=actor_id,
            event_type=event_type,
            payload=payload,
        )
    )


def _staff_project_stmt():
    return (
        select(
            Project,
            User.full_name,
            SchoolClass.label,
            SchoolClass.grade,
            SchoolClass.school_id,
            SchoolClass.curator_id,
            AcademicYear.name,
        )
        .join(User, User.id == Project.student_id)
        .join(SchoolClass, SchoolClass.id == Project.class_id)
        .join(AcademicYear, AcademicYear.id == Project.academic_year_id)
    )


def _staff_row(result_row) -> StaffProjectRow | None:
    if result_row is None:
        return None
    return StaffProjectRow(
        result_row[0],
        result_row[1],
        result_row[2],
        result_row[3],
        result_row[4],
        result_row[5],
        result_row[6],
    )


async def get_staff_row(session: AsyncSession, project_id: uuid.UUID) -> StaffProjectRow | None:
    result = await session.execute(_staff_project_stmt().where(Project.id == project_id))
    return _staff_row(result.first())


async def list_teacher_projects(
    session: AsyncSession, teacher_id: uuid.UUID
) -> list[StaffProjectRow]:
    stmt = (
        _staff_project_stmt()
        .where(SchoolClass.curator_id == teacher_id, Project.archived_at.is_(None))
        .order_by(Project.last_activity_at.desc())
    )
    result = await session.execute(stmt)
    return [row for row in (_staff_row(item) for item in result.all()) if row is not None]


async def list_school_projects(
    session: AsyncSession, school_id: uuid.UUID
) -> list[StaffProjectRow]:
    stmt = (
        _staff_project_stmt()
        .where(SchoolClass.school_id == school_id, Project.archived_at.is_(None))
        .order_by(Project.last_activity_at.desc())
    )
    result = await session.execute(stmt)
    return [row for row in (_staff_row(item) for item in result.all()) if row is not None]
