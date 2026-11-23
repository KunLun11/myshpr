"""Teacher comments for a project (one-way: teacher -> student)."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ForbiddenError, NotFoundError, ValidationError
from app.models import ProjectComment, User
from app.models.enums import CommentVisibility, NotificationType, UserRole
from app.repositories import comments as comments_repo
from app.repositories import notifications as notifications_repo
from app.repositories import projects as projects_repo
from app.schemas.comment import CommentCreateRequest, CommentOut, CommentUpdateRequest
from app.services import project_access


def _can_edit(comment: ProjectComment, user: User) -> bool:
    return user.role is UserRole.SUPER_ADMIN or comment.author_id == user.id


def serialize_comment(
    comment: ProjectComment, author_name: str | None, *, user: User
) -> CommentOut:
    return CommentOut(
        id=comment.id,
        project_id=comment.project_id,
        body=comment.body,
        visibility=comment.visibility,
        stage=comment.stage,
        author_full_name=author_name,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
        can_edit=_can_edit(comment, user),
    )


async def list_student_comments(session: AsyncSession, student: User) -> list[CommentOut]:
    school_class = await project_access.get_student_class(session, student)
    project = await projects_repo.get_student_project(
        session, student_id=student.id, academic_year_id=school_class.academic_year_id
    )
    if project is None:
        return []
    rows = await comments_repo.list_for_project(
        session,
        project.id,
        visibility=CommentVisibility.STUDENT_VISIBLE,
    )
    return [serialize_comment(comment, author_name, user=student) for comment, author_name in rows]


async def list_staff_comments(
    session: AsyncSession, user: User, project_id: uuid.UUID
) -> list[CommentOut]:
    await project_access.load_staff_project(session, user, project_id)
    rows = await comments_repo.list_for_project(session, project_id)
    return [serialize_comment(comment, author_name, user=user) for comment, author_name in rows]


async def create_comment(
    session: AsyncSession,
    user: User,
    project_id: uuid.UUID,
    payload: CommentCreateRequest,
) -> CommentOut:
    row = await project_access.load_staff_project(session, user, project_id)
    body = payload.body.strip()
    if not body:
        raise ValidationError("Комментарий не может быть пустым", "COMMENT_EMPTY")

    comment = await comments_repo.create(
        session,
        project_id=project_id,
        author_id=user.id,
        body=body,
        visibility=payload.visibility,
        stage=payload.stage,
    )
    await projects_repo.add_event(
        session,
        project_id=project_id,
        event_type="comment_added",
        actor_id=user.id,
        payload={"comment_id": str(comment.id), "visibility": payload.visibility.value},
    )

    if payload.visibility is CommentVisibility.STUDENT_VISIBLE:
        await notifications_repo.create_in_app(
            session,
            user_id=row.project.student_id,
            type=NotificationType.NEW_COMMENT,
            title="Новый комментарий учителя",
            body=body[:300],
            dedupe_key=f"new_comment:{comment.id}",
            project_id=project_id,
            payload={"comment_id": str(comment.id)},
        )

    await session.commit()
    return serialize_comment(comment, user.full_name, user=user)


async def _load_editable(
    session: AsyncSession, user: User, comment_id: uuid.UUID
) -> ProjectComment:
    comment = await comments_repo.get(session, comment_id)
    if comment is None or comment.deleted_at is not None:
        raise NotFoundError("Комментарий не найден", "COMMENT_NOT_FOUND")
    await project_access.load_staff_project(session, user, comment.project_id)
    if not _can_edit(comment, user):
        raise ForbiddenError("Редактировать можно только свой комментарий", "COMMENT_EDIT_DENIED")
    return comment


async def update_comment(
    session: AsyncSession,
    user: User,
    comment_id: uuid.UUID,
    payload: CommentUpdateRequest,
) -> CommentOut:
    comment = await _load_editable(session, user, comment_id)
    fields = payload.model_fields_set
    values: dict = {}

    if "body" in fields:
        body = (payload.body or "").strip()
        if not body:
            raise ValidationError("Комментарий не может быть пустым", "COMMENT_EMPTY")
        values["body"] = body
    if "visibility" in fields and payload.visibility is not None:
        values["visibility"] = payload.visibility
    if "stage" in fields:
        values["stage"] = payload.stage

    if values:
        await comments_repo.update_fields(session, comment.id, values=values)

    await session.commit()
    refreshed = await comments_repo.get_with_author(session, comment.id)
    if refreshed is None:  # pragma: no cover
        raise NotFoundError("Комментарий не найден", "COMMENT_NOT_FOUND")
    return serialize_comment(refreshed[0], refreshed[1], user=user)


async def delete_comment(session: AsyncSession, user: User, comment_id: uuid.UUID) -> None:
    comment = await _load_editable(session, user, comment_id)
    await comments_repo.soft_delete(session, comment.id)
    await session.commit()
