"""Read-model building blocks for the teacher dashboard.

Kept free of lazy relationships: everything is expressed with explicit
``select()``/scalar subqueries so it can run on ``AsyncSession`` without
``MissingGreenlet`` surprises. Colour/reason computation lives in
``app/services/status.py`` from stage 5 onward.
"""

import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import ColumnElement, Select, and_, case, func, or_, select
from sqlalchemy.dialects.postgresql import distinct_on
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.checklist import ChecklistItem, ProjectChecklistState
from app.models.comment import ProjectComment
from app.models.enums import (
    PROJECT_STATUS_RANK,
    ChecklistState,
    FileKind,
    FileStatus,
    ProjectStatus,
    TopicSubmissionStatus,
)
from app.models.file import ProjectFile
from app.models.project import Project
from app.models.topic import TopicSubmission
from app.models.user import StudentProfile, User

CHECKLIST_DONE_STATES = (ChecklistState.DONE, ChecklistState.VERIFIED)


def status_rank_case() -> ColumnElement[int]:
    """Map ``projects.status`` to its business rank in SQL."""
    return case(
        *[(Project.status == status, rank) for status, rank in PROJECT_STATUS_RANK.items()],
        else_=0,
    ).label("status_rank")


def inactive_days_expr() -> ColumnElement[float]:
    return (func.extract("epoch", func.now() - Project.last_activity_at) / 86400.0).label(
        "inactive_days"
    )


def checklist_done_subquery() -> ColumnElement[int]:
    return (
        select(func.count())
        .select_from(ProjectChecklistState)
        .join(ChecklistItem, ChecklistItem.id == ProjectChecklistState.checklist_item_id)
        .where(
            ProjectChecklistState.project_id == Project.id,
            ChecklistItem.is_required.is_(True),
            ProjectChecklistState.status.in_(CHECKLIST_DONE_STATES),
        )
        .correlate(Project)
        .scalar_subquery()
        .label("checklist_done")
    )


def checklist_total_subquery() -> ColumnElement[int]:
    return (
        select(func.count())
        .select_from(ProjectChecklistState)
        .join(ChecklistItem, ChecklistItem.id == ProjectChecklistState.checklist_item_id)
        .where(
            ProjectChecklistState.project_id == Project.id,
            ChecklistItem.is_required.is_(True),
        )
        .correlate(Project)
        .scalar_subquery()
        .label("checklist_total")
    )


def class_dashboard_stmt(*, class_id: uuid.UUID, academic_year_id: uuid.UUID) -> Select:
    """Base statement: active projects of a class for a given year."""
    return select(
        Project,
        inactive_days_expr(),
        status_rank_case(),
        checklist_done_subquery(),
        checklist_total_subquery(),
    ).where(
        Project.class_id == class_id,
        Project.academic_year_id == academic_year_id,
        Project.archived_at.is_(None),
    )


def needs_attention_filter(min_inactive_days: float = 7.0) -> ColumnElement[bool]:
    """Cheap server-side pre-filter for the red/yellow bucket."""
    return or_(
        inactive_days_expr() >= min_inactive_days,
        Project.status.in_(
            [
                ProjectStatus.IDEA,
                ProjectStatus.TOPIC_DRAFT,
                ProjectStatus.TOPIC_SUBMITTED,
            ]
        ),
    )


# --- Per-class aggregation for the dashboard -------------------------------


@dataclass(slots=True)
class ClassStudentRow:
    student_id: uuid.UUID
    full_name: str
    project: Project | None


@dataclass(slots=True)
class ChecklistTotals:
    done: int = 0
    total: int = 0
    overdue: int = 0
    stalled: bool = False


@dataclass(slots=True)
class ProjectActivity:
    files_count: int = 0
    has_final_file: bool = False
    last_comment_at: datetime | None = None
    last_comment_excerpt: str | None = None


@dataclass(slots=True)
class SubmissionInfo:
    title: str
    status: TopicSubmissionStatus
    updated_at: datetime


async def list_class_students_with_projects(
    session: AsyncSession,
    *,
    class_id: uuid.UUID,
    academic_year_id: uuid.UUID,
) -> list[ClassStudentRow]:
    """Every student in the class, with their project for the given year (if any)."""
    stmt = (
        select(User.id, User.full_name, Project)
        .select_from(StudentProfile)
        .join(User, User.id == StudentProfile.user_id)
        .outerjoin(
            Project,
            and_(
                Project.student_id == User.id,
                Project.academic_year_id == academic_year_id,
                Project.class_id == class_id,
                Project.archived_at.is_(None),
            ),
        )
        .where(
            StudentProfile.class_id == class_id,
            User.deleted_at.is_(None),
            User.is_active.is_(True),
        )
        .order_by(User.full_name)
    )
    result = await session.execute(stmt)
    return [
        ClassStudentRow(student_id=row[0], full_name=row[1], project=row[2]) for row in result.all()
    ]


async def checklist_totals(
    session: AsyncSession,
    project_ids: list[uuid.UUID],
    *,
    now: datetime,
    stalled_before: datetime,
) -> dict[uuid.UUID, ChecklistTotals]:
    """Required-item progress, overdue count and stalled flag per project."""
    if not project_ids:
        return {}
    result = await session.execute(
        select(ProjectChecklistState, ChecklistItem)
        .join(ChecklistItem, ChecklistItem.id == ProjectChecklistState.checklist_item_id)
        .where(
            ProjectChecklistState.project_id.in_(project_ids),
            ChecklistItem.is_required.is_(True),
            ChecklistItem.is_active.is_(True),
        )
    )
    totals: dict[uuid.UUID, ChecklistTotals] = defaultdict(ChecklistTotals)
    for state, item in result.all():
        bucket = totals[state.project_id]
        bucket.total += 1
        if state.status in CHECKLIST_DONE_STATES:
            bucket.done += 1
        elif item.due_at is not None and item.due_at < now:
            bucket.overdue += 1
        if state.status is ChecklistState.IN_PROGRESS and state.updated_at < stalled_before:
            bucket.stalled = True
    return dict(totals)


async def project_activity(
    session: AsyncSession,
    project_ids: list[uuid.UUID],
) -> dict[uuid.UUID, ProjectActivity]:
    """File counts + the latest teacher comment per project."""
    activity: dict[uuid.UUID, ProjectActivity] = {
        project_id: ProjectActivity() for project_id in project_ids
    }
    if not project_ids:
        return activity

    file_rows = await session.execute(
        select(ProjectFile.project_id, ProjectFile.kind, func.count(ProjectFile.id))
        .where(
            ProjectFile.project_id.in_(project_ids),
            ProjectFile.status != FileStatus.DELETED,
            ProjectFile.deleted_at.is_(None),
        )
        .group_by(ProjectFile.project_id, ProjectFile.kind)
    )
    for project_id, kind, count in file_rows.all():
        bucket = activity[project_id]
        bucket.files_count += int(count)
        if kind is FileKind.FINAL_WORK:
            bucket.has_final_file = True

    comment_rows = await session.execute(
        select(ProjectComment.project_id, ProjectComment.body, ProjectComment.created_at)
        .where(
            ProjectComment.project_id.in_(project_ids),
            ProjectComment.deleted_at.is_(None),
        )
        .ext(distinct_on(ProjectComment.project_id))
        .order_by(ProjectComment.project_id, ProjectComment.created_at.desc())
    )
    for project_id, body, created_at in comment_rows.all():
        bucket = activity[project_id]
        bucket.last_comment_at = created_at
        excerpt = " ".join(body.split())
        bucket.last_comment_excerpt = excerpt[:160] + ("…" if len(excerpt) > 160 else "")
    return activity


async def latest_submissions(
    session: AsyncSession,
    project_ids: list[uuid.UUID],
) -> dict[uuid.UUID, SubmissionInfo]:
    if not project_ids:
        return {}
    result = await session.execute(
        select(
            TopicSubmission.project_id,
            TopicSubmission.title,
            TopicSubmission.status,
            TopicSubmission.updated_at,
        )
        .where(TopicSubmission.project_id.in_(project_ids))
        .ext(distinct_on(TopicSubmission.project_id))
        .order_by(TopicSubmission.project_id, TopicSubmission.updated_at.desc())
    )
    return {
        row[0]: SubmissionInfo(title=row[1], status=row[2], updated_at=row[3])
        for row in result.all()
    }


async def checklist_states_needing_reminder(
    session: AsyncSession,
    project_ids: list[uuid.UUID],
    *,
    soon_before: datetime,
) -> list[tuple[ProjectChecklistState, ChecklistItem]]:
    """Required items that are due soon or already overdue, still unfinished."""
    if not project_ids:
        return []
    result = await session.execute(
        select(ProjectChecklistState, ChecklistItem)
        .join(ChecklistItem, ChecklistItem.id == ProjectChecklistState.checklist_item_id)
        .where(
            ProjectChecklistState.project_id.in_(project_ids),
            ChecklistItem.is_required.is_(True),
            ChecklistItem.is_active.is_(True),
            ChecklistItem.due_at.is_not(None),
            ChecklistItem.due_at <= soon_before,
            ProjectChecklistState.status.not_in(
                (
                    ChecklistState.DONE,
                    ChecklistState.VERIFIED,
                    ChecklistState.SKIPPED,
                )
            ),
        )
        .order_by(ChecklistItem.due_at)
    )
    return [(row[0], row[1]) for row in result.all()]
