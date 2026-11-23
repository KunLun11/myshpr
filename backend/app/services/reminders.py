"""Daily in-app reminders and the teacher digest.

Runs idempotently: every notification carries a dedupe key, so re-running the
job on the same day never creates duplicates. Email is deliberately out of
scope; the same rows can be picked up by an outbox later.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models import School
from app.models.enums import NotificationType, ProjectStatus, status_rank
from app.repositories import checkpoints as checkpoints_repo
from app.repositories import classes as classes_repo
from app.repositories import dashboard as dashboard_repo
from app.repositories import notifications as notifications_repo
from app.schemas.dashboard import DashboardStudentOut
from app.services import dashboard as dashboard_service


@dataclass(slots=True)
class ReminderResult:
    created: int = 0
    duplicates: int = 0

    def add(self, created: bool) -> None:
        if created:
            self.created += 1
        else:
            self.duplicates += 1


def _week_key(now: datetime) -> str:
    iso = now.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def _plural_days(days: int) -> str:
    if days % 10 == 1 and days % 100 != 11:
        return f"{days} день"
    if days % 10 in (2, 3, 4) and days % 100 not in (12, 13, 14):
        return f"{days} дня"
    return f"{days} дней"


async def _notify(
    session: AsyncSession,
    result: ReminderResult,
    *,
    user_id: uuid.UUID,
    type: NotificationType,
    title: str,
    body: str,
    dedupe_key: str,
    project_id: uuid.UUID | None = None,
    checkpoint_id: uuid.UUID | None = None,
) -> None:
    created = await notifications_repo.create_in_app(
        session,
        user_id=user_id,
        type=type,
        title=title,
        body=body,
        dedupe_key=dedupe_key,
        project_id=project_id,
        checkpoint_id=checkpoint_id,
    )
    result.add(created)


def _reason_text(student: DashboardStudentOut) -> str:
    return "; ".join(reason.label for reason in student.reasons) or "Нужно внимание"


async def _student_reminders(
    session: AsyncSession,
    student: DashboardStudentOut,
    *,
    result: ReminderResult,
    now: datetime,
    local_now: datetime,
    checkpoints: list,
) -> None:
    settings = get_settings()

    if student.project_id is None:
        if student.color == "red":
            await _notify(
                session,
                result,
                user_id=student.student_id,
                type=NotificationType.INACTIVITY,
                title="Проект ещё не создан",
                body="Откройте кабинет и начните с мастера темы — это займёт 10 минут.",
                dedupe_key=f"no_project:{student.student_id}:{_week_key(local_now)}",
            )
        return

    if student.color != "green" and (student.inactive_days or 0) >= settings.INACTIVITY_YELLOW_DAYS:
        await _notify(
            session,
            result,
            user_id=student.student_id,
            type=NotificationType.INACTIVITY,
            title="Пора вернуться к проекту",
            body=_reason_text(student),
            dedupe_key=f"inactivity:{student.project_id}:{_week_key(local_now)}",
            project_id=student.project_id,
        )

    rank = status_rank(ProjectStatus(student.status))
    for checkpoint in checkpoints:
        if status_rank(checkpoint.required_status) <= rank:
            continue
        days_left = (checkpoint.due_at.astimezone(local_now.tzinfo).date() - local_now.date()).days
        if days_left in (1, 3):
            await _notify(
                session,
                result,
                user_id=student.student_id,
                type=NotificationType.CHECKPOINT_DUE,
                title=f"Контрольная точка «{checkpoint.title}»",
                body=(
                    f"До дедлайна {_plural_days(days_left)}. "
                    "Проверьте, что проект дошёл до нужного этапа."
                ),
                dedupe_key=f"checkpoint:{checkpoint.id}:{student.student_id}:{days_left}",
                project_id=student.project_id,
                checkpoint_id=checkpoint.id,
            )

    if not student.has_final_file:
        ready_point = next(
            (
                checkpoint
                for checkpoint in checkpoints
                if checkpoint.required_status is ProjectStatus.READY_FOR_DEFENSE
            ),
            None,
        )
        if ready_point is not None:
            days_left = (
                ready_point.due_at.astimezone(local_now.tzinfo).date() - local_now.date()
            ).days
            if 0 <= days_left <= settings.FINAL_FILE_DAYS_BEFORE:
                await _notify(
                    session,
                    result,
                    user_id=student.student_id,
                    type=NotificationType.CHECKPOINT_DUE,
                    title="Не загружен итоговый файл",
                    body=(
                        f"До защиты {_plural_days(days_left)}. "
                        "Загрузите итоговую работу в разделе «Работа»."
                    ),
                    dedupe_key=f"final_file:{student.project_id}:{ready_point.id}",
                    project_id=student.project_id,
                    checkpoint_id=ready_point.id,
                )


async def _checklist_reminders(
    session: AsyncSession,
    student: DashboardStudentOut,
    states: list,
    *,
    result: ReminderResult,
    local_now: datetime,
) -> None:
    if student.project_id is None:
        return
    settings = get_settings()
    for state, item in states:
        if state.project_id != student.project_id or item.due_at is None:
            continue
        due_local = item.due_at.astimezone(local_now.tzinfo)
        days_left = (due_local.date() - local_now.date()).days
        if days_left < 0:
            title = "Просрочен пункт чек-листа"
            key = f"checklist_overdue:{state.id}:{due_local.date().isoformat()}"
            body = f"«{item.title}» нужно было закрыть {due_local.date().strftime('%d.%m.%Y')}."
        elif days_left <= settings.CHECKLIST_SOON_DAYS:
            title = "Скоро дедлайн пункта чек-листа"
            key = f"checklist_due:{state.id}:{due_local.date().isoformat()}"
            body = f"«{item.title}» — осталось {_plural_days(days_left)}."
        else:
            continue
        await _notify(
            session,
            result,
            user_id=student.student_id,
            type=NotificationType.CHECKLIST_DUE,
            title=title,
            body=body,
            dedupe_key=key,
            project_id=student.project_id,
        )


async def run_daily_reminders(
    session: AsyncSession, *, now: datetime | None = None
) -> ReminderResult:
    """Find stuck students and create in-app notifications for them and teachers."""
    now = now or datetime.now(UTC)
    result = ReminderResult()
    settings = get_settings()

    years = await classes_repo.list_current_years(session)
    for year in years:
        school = await session.get(School, year.school_id)
        timezone = ZoneInfo(school.timezone if school is not None else "Europe/Moscow")
        local_now = now.astimezone(timezone)
        checkpoints = await checkpoints_repo.list_active_for_year(
            session,
            academic_year_id=year.id,
            school_id=year.school_id,
        )
        classes = await classes_repo.list_classes_for_year(session, year.id)

        for school_class in classes:
            students, summary = await dashboard_service.build_class_students(
                session, school_class, now=now
            )
            project_ids = [
                student.project_id for student in students if student.project_id is not None
            ]
            states = await dashboard_repo.checklist_states_needing_reminder(
                session,
                project_ids,
                soon_before=now + timedelta(days=settings.CHECKLIST_SOON_DAYS),
            )
            for student in students:
                await _student_reminders(
                    session,
                    student,
                    result=result,
                    now=now,
                    local_now=local_now,
                    checkpoints=checkpoints,
                )
                await _checklist_reminders(
                    session,
                    student,
                    states,
                    result=result,
                    local_now=local_now,
                )

            if school_class.curator_id is not None and (summary.red or summary.yellow):
                await _notify(
                    session,
                    result,
                    user_id=school_class.curator_id,
                    type=NotificationType.TEACHER_DIGEST,
                    title=f"Сводка по классу {school_class.label}",
                    body=(
                        f"Красных: {summary.red}, жёлтых: {summary.yellow} "
                        f"из {summary.total}. Откройте дашборд «кто застрял»."
                    ),
                    dedupe_key=(
                        f"teacher_digest:{school_class.curator_id}:{local_now.date().isoformat()}"
                    ),
                )

    await session.commit()
    return result
