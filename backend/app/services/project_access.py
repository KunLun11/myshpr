"""Shared access helpers for the student project and staff project card.

The topic wizard already has its own private helpers; stage 4 features
(products, files, comments, checklists) share the ones below so scoping
rules stay in one place.
"""

import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ensure_school_access
from app.core.errors import ForbiddenError, NotFoundError, ValidationError
from app.models import Project, SchoolClass, User
from app.models.enums import ProjectStatus, UserRole, status_rank
from app.repositories import classes as classes_repo
from app.repositories import projects as projects_repo
from app.repositories.projects import StaffProjectRow


@dataclass(slots=True)
class StudentProject:
    project: Project
    school_class: SchoolClass


async def get_student_class(session: AsyncSession, student: User) -> SchoolClass:
    profile = await classes_repo.get_student_profile(session, student.id)
    if profile is None:
        raise ValidationError("Вы не привязаны к классу. Обратитесь к учителю.", "STUDENT_NO_CLASS")
    school_class = await classes_repo.get_by_id(session, profile.class_id)
    if school_class is None:
        raise ValidationError("Класс не найден. Обратитесь к учителю.", "STUDENT_NO_CLASS")
    return school_class


async def get_or_create_student_project(
    session: AsyncSession, student: User, school_class: SchoolClass
) -> Project:
    project = await projects_repo.get_student_project(
        session, student_id=student.id, academic_year_id=school_class.academic_year_id
    )
    if project is not None:
        return project

    project = await projects_repo.create(
        session,
        student_id=student.id,
        academic_year_id=school_class.academic_year_id,
        class_id=school_class.id,
    )
    await projects_repo.add_event(
        session, project_id=project.id, event_type="project_created", actor_id=student.id
    )
    return project


async def load_student_project(session: AsyncSession, student: User) -> StudentProject:
    school_class = await get_student_class(session, student)
    project = await projects_repo.get_student_project(
        session, student_id=student.id, academic_year_id=school_class.academic_year_id
    )
    if project is None:
        raise NotFoundError("Проект ещё не создан", "PROJECT_NOT_FOUND")
    return StudentProject(project=project, school_class=school_class)


async def get_or_create_any_project(session: AsyncSession, student: User) -> StudentProject:
    school_class = await get_student_class(session, student)
    project = await get_or_create_student_project(session, student, school_class)
    return StudentProject(project=project, school_class=school_class)


def require_topic_approved(project: Project) -> None:
    if project.status is ProjectStatus.ARCHIVED or status_rank(project.status) < status_rank(
        ProjectStatus.TOPIC_APPROVED
    ):
        raise ValidationError(
            "Сначала утвердите тему — продукт выбирается после решения учителя.",
            "TOPIC_NOT_APPROVED",
        )


async def load_staff_project(
    session: AsyncSession, user: User, project_id: uuid.UUID
) -> StaffProjectRow:
    row = await projects_repo.get_staff_row(session, project_id)
    if row is None:
        raise NotFoundError("Проект не найден", "PROJECT_NOT_FOUND")

    if user.role is UserRole.SUPER_ADMIN:
        return row
    if user.role is UserRole.SCHOOL_ADMIN:
        ensure_school_access(user, row.school_id)
        return row
    if row.curator_id == user.id:
        return row
    raise ForbiddenError("Этот проект не из ваших классов", "PROJECT_ACCESS_DENIED")


def ensure_student_owns(project: Project, student: User) -> None:
    if project.student_id != student.id:
        raise ForbiddenError("Нет доступа к этому проекту", "PROJECT_ACCESS_DENIED")
