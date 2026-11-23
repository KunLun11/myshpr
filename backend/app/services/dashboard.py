"""Teacher dashboard: build the class read model and apply filters."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ensure_class_access
from app.core.config import get_settings
from app.core.errors import NotFoundError
from app.models import AcademicYear, SchoolClass, User
from app.models.enums import TopicSubmissionStatus
from app.repositories import checkpoints as checkpoints_repo
from app.repositories import classes as classes_repo
from app.repositories import dashboard as dashboard_repo
from app.schemas.dashboard import (
    ClassDashboardOut,
    DashboardStudentOut,
    DashboardSummaryOut,
    StatusReasonOut,
)
from app.services import checkpoints as checkpoints_service
from app.services import status as status_service

COLOR_ORDER: dict[str, int] = {
    status_service.TrafficLight.RED.value: 0,
    status_service.TrafficLight.YELLOW.value: 1,
    status_service.TrafficLight.GREEN.value: 2,
}


def _inactive_days(project, now: datetime) -> float:
    return max((now - project.last_activity_at).total_seconds() / 86400.0, 0.0)


async def _build_students(
    session: AsyncSession,
    school_class: SchoolClass,
    *,
    now: datetime,
) -> list[DashboardStudentOut]:
    settings = get_settings()
    year = await session.get(AcademicYear, school_class.academic_year_id)
    year_starts_on = year.starts_on if year is not None else now.date()

    checkpoints = await checkpoints_repo.list_active_for_year(
        session,
        academic_year_id=school_class.academic_year_id,
        school_id=school_class.school_id,
    )
    rows = await dashboard_repo.list_class_students_with_projects(
        session,
        class_id=school_class.id,
        academic_year_id=school_class.academic_year_id,
    )
    project_ids = [row.project.id for row in rows if row.project is not None]
    totals = await dashboard_repo.checklist_totals(
        session,
        project_ids,
        now=now,
        stalled_before=now - timedelta(days=settings.CHECKLIST_STALLED_DAYS),
    )
    activity = await dashboard_repo.project_activity(session, project_ids)
    submissions = await dashboard_repo.latest_submissions(session, project_ids)

    students: list[DashboardStudentOut] = []
    for row in rows:
        project = row.project
        if project is None:
            result = status_service.evaluate(
                None,
                status_service.StatusContext(
                    now=now,
                    year_starts_on=year_starts_on,
                    checkpoints=checkpoints,
                ),
            )
            students.append(
                DashboardStudentOut(
                    student_id=row.student_id,
                    student_full_name=row.full_name,
                    project_id=None,
                    status="no_project",
                    color=result.color.value,
                    reasons=[
                        StatusReasonOut(
                            code=reason.code,
                            label=reason.label,
                            severity=reason.severity.value,
                        )
                        for reason in result.reasons
                    ],
                )
            )
            continue

        checklist = totals.get(project.id, dashboard_repo.ChecklistTotals())
        files = activity.get(project.id, dashboard_repo.ProjectActivity())
        submission = submissions.get(project.id)
        inactive = _inactive_days(project, now)
        review_since = (
            submission.updated_at
            if submission is not None and submission.status is TopicSubmissionStatus.SUBMITTED
            else None
        )

        result = status_service.evaluate(
            project,
            status_service.StatusContext(
                now=now,
                year_starts_on=year_starts_on,
                checkpoints=checkpoints,
                inactive_days=inactive,
                checklist_overdue=checklist.overdue,
                checklist_stalled=checklist.stalled,
                has_final_file=files.has_final_file,
                review_waiting_since=review_since,
            ),
        )
        next_checkpoint = (
            checkpoints_service.to_next(result.next_checkpoint, now=now)
            if result.next_checkpoint is not None
            else None
        )
        students.append(
            DashboardStudentOut(
                student_id=row.student_id,
                student_full_name=row.full_name,
                project_id=project.id,
                status=project.status.value,
                color=result.color.value,
                reasons=[
                    StatusReasonOut(
                        code=reason.code,
                        label=reason.label,
                        severity=reason.severity.value,
                    )
                    for reason in result.reasons
                ],
                last_activity_at=project.last_activity_at,
                inactive_days=round(inactive),
                next_checkpoint=next_checkpoint,
                checklist_done=checklist.done,
                checklist_total=checklist.total,
                checklist_overdue=checklist.overdue,
                has_final_file=files.has_final_file,
                files_count=files.files_count,
                last_comment_at=files.last_comment_at,
                last_comment_excerpt=files.last_comment_excerpt,
                topic_title=submission.title if submission is not None else None,
            )
        )
    return students


def _summary(students: list[DashboardStudentOut]) -> DashboardSummaryOut:
    return DashboardSummaryOut(
        total=len(students),
        green=sum(
            1 for student in students if student.color == status_service.TrafficLight.GREEN.value
        ),
        yellow=sum(
            1 for student in students if student.color == status_service.TrafficLight.YELLOW.value
        ),
        red=sum(
            1 for student in students if student.color == status_service.TrafficLight.RED.value
        ),
    )


async def build_class_students(
    session: AsyncSession,
    school_class: SchoolClass,
    *,
    now: datetime | None = None,
) -> tuple[list[DashboardStudentOut], DashboardSummaryOut]:
    """Internal builder used by the API and the reminder job."""
    now = now or datetime.now(UTC)
    students = await _build_students(session, school_class, now=now)
    return students, _summary(students)


async def get_class_dashboard(
    session: AsyncSession,
    user: User,
    class_id: uuid.UUID,
    *,
    color: Literal["green", "yellow", "red"] | None = None,
    project_status: str | None = None,
    query: str | None = None,
    now: datetime | None = None,
) -> ClassDashboardOut:
    school_class = await classes_repo.get_by_id(session, class_id)
    if school_class is None:
        raise NotFoundError("Класс не найден", "CLASS_NOT_FOUND")
    await ensure_class_access(session, user, school_class)

    now = now or datetime.now(UTC)
    row = await classes_repo.get_class_row(session, class_id)
    students, summary = await build_class_students(session, school_class, now=now)

    filtered = students
    if color is not None:
        filtered = [student for student in filtered if student.color == color]
    if project_status:
        filtered = [student for student in filtered if student.status == project_status]
    if query:
        needle = query.strip().casefold()
        filtered = [
            student for student in filtered if needle in student.student_full_name.casefold()
        ]

    filtered.sort(
        key=lambda student: (
            COLOR_ORDER[student.color],
            student.student_full_name.casefold(),
        )
    )

    return ClassDashboardOut(
        class_id=school_class.id,
        class_label=school_class.label,
        class_grade=school_class.grade,
        academic_year_name=row.academic_year_name if row is not None else None,
        generated_at=now,
        summary=summary,
        students=filtered,
    )


__all__ = ["build_class_students", "get_class_dashboard"]
