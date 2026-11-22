"""Read-model building blocks for the teacher dashboard.

Kept free of lazy relationships: everything is expressed with explicit
``select()``/scalar subqueries so it can run on ``AsyncSession`` without
``MissingGreenlet`` surprises. Colour/reason computation lives in
``app/services/status.py`` from stage 5 onward.
"""

import uuid

from sqlalchemy import ColumnElement, Select, case, func, or_, select

from app.models.checklist import ChecklistItem, ProjectChecklistState
from app.models.enums import PROJECT_STATUS_RANK, ChecklistState, ProjectStatus
from app.models.project import Project

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
