"""Staff-facing project cards (list + single project)."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.models.enums import UserRole
from app.repositories import comments as comments_repo
from app.repositories import files as files_repo
from app.repositories import projects as projects_repo
from app.repositories import reference as reference_repo
from app.repositories import topics as topics_repo
from app.schemas.projects import TeacherProjectOut
from app.services import project_access


async def _serialize(session: AsyncSession, row) -> TeacherProjectOut:
    project = row.project
    submission = await topics_repo.get_latest_for_project(session, project.id)
    category_name = None
    if project.product_category_id is not None:
        category = await reference_repo.get_product_category(session, project.product_category_id)
        category_name = category.name if category is not None else None

    return TeacherProjectOut(
        id=project.id,
        status=project.status.value,
        student_full_name=row.student_full_name,
        class_label=row.class_label,
        class_grade=row.class_grade,
        academic_year_name=row.academic_year_name,
        topic_title=submission.title if submission is not None else None,
        research_question=project.research_question,
        topic_status=submission.status.value if submission is not None else None,
        product_category_id=project.product_category_id,
        product_category_name=category_name,
        product_description=project.product_description,
        product_brief=project.product_brief,
        product_defined_at=project.product_defined_at,
        last_activity_at=project.last_activity_at,
        files_count=await files_repo.count_active(session, project.id),
        comments_count=await comments_repo.count_for_project(session, project.id),
    )


async def list_projects(session: AsyncSession, user: User) -> list[TeacherProjectOut]:
    if user.role is UserRole.SCHOOL_ADMIN:
        if user.school_id is None:
            return []
        rows = await projects_repo.list_school_projects(session, user.school_id)
    elif user.role is UserRole.TEACHER:
        rows = await projects_repo.list_teacher_projects(session, user.id)
    else:
        return []
    return [await _serialize(session, row) for row in rows]


async def get_project(
    session: AsyncSession, user: User, project_id: uuid.UUID
) -> TeacherProjectOut:
    row = await project_access.load_staff_project(session, user, project_id)
    return await _serialize(session, row)
