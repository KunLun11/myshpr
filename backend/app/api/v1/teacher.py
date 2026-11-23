"""Teacher endpoints: own classes, topic review queue and registry."""

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, require_roles
from app.models import User
from app.models.enums import UserRole
from app.repositories import classes as classes_repo
from app.schemas.checklist import (
    ChecklistItemStateOut,
    ChecklistOut,
    ChecklistVerifyRequest,
)
from app.schemas.classes import ClassOut
from app.schemas.comment import CommentCreateRequest, CommentOut, CommentUpdateRequest
from app.schemas.dashboard import ClassDashboardOut
from app.schemas.file import ProjectFileOut
from app.schemas.projects import TeacherProjectOut
from app.schemas.topic import (
    RegistryTopicOut,
    SubmissionDecisionRequest,
    SubmissionOut,
    SubmissionRejectRequest,
)
from app.services import checklists as checklists_service
from app.services import comments as comments_service
from app.services import dashboard as dashboard_service
from app.services import files as files_service
from app.services import project_cards
from app.services import topics as topics_service
from app.services.classes import serialize_class

router = APIRouter(prefix="/teacher", tags=["teacher"])

Teacher = Annotated[User, Depends(require_roles(UserRole.TEACHER))]
Staff = Annotated[User, Depends(require_roles(UserRole.TEACHER, UserRole.SCHOOL_ADMIN))]


@router.get("/classes", response_model=list[ClassOut], summary="Мои классы")
async def my_classes(
    user: Teacher,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[ClassOut]:
    rows = await classes_repo.list_teacher_classes(session, user.id)
    return [serialize_class(row) for row in rows]


@router.get(
    "/classes/{class_id}/dashboard",
    response_model=ClassDashboardOut,
    summary="Дашборд «кто застрял»",
)
async def class_dashboard(
    class_id: uuid.UUID,
    user: Staff,
    session: Annotated[AsyncSession, Depends(get_session)],
    color: Annotated[Literal["green", "yellow", "red"] | None, Query()] = None,
    project_status: Annotated[str | None, Query(alias="status")] = None,
    q: Annotated[str | None, Query(max_length=100)] = None,
) -> ClassDashboardOut:
    return await dashboard_service.get_class_dashboard(
        session,
        user,
        class_id,
        color=color,
        project_status=project_status,
        query=q,
    )


@router.get(
    "/submissions",
    response_model=list[SubmissionOut],
    summary="Очередь тем на проверку",
)
async def submissions(
    user: Teacher,
    session: Annotated[AsyncSession, Depends(get_session)],
    submission_status: Annotated[str, Query(alias="status")] = "submitted",
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[SubmissionOut]:
    return await topics_service.list_teacher_submissions(
        session,
        user,
        status=submission_status,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/submissions/{submission_id}/approve",
    response_model=SubmissionOut,
    summary="Утвердить тему",
)
async def approve_submission(
    submission_id: uuid.UUID,
    payload: SubmissionDecisionRequest,
    user: Teacher,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SubmissionOut:
    return await topics_service.approve_submission(
        session, user, submission_id, comment=payload.comment
    )


@router.post(
    "/submissions/{submission_id}/reject",
    response_model=SubmissionOut,
    summary="Отклонить тему",
)
async def reject_submission(
    submission_id: uuid.UUID,
    payload: SubmissionRejectRequest,
    user: Teacher,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SubmissionOut:
    return await topics_service.reject_submission(
        session, user, submission_id, comment=payload.comment
    )


@router.get(
    "/topics",
    response_model=list[RegistryTopicOut],
    summary="Реестр утверждённых тем",
)
async def topic_registry(
    user: Teacher,
    session: Annotated[AsyncSession, Depends(get_session)],
    academic_year_id: uuid.UUID | None = None,
    interest_area_id: uuid.UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[RegistryTopicOut]:
    return await topics_service.list_registry(
        session,
        user,
        academic_year_id=academic_year_id,
        interest_area_id=interest_area_id,
        limit=limit,
        offset=offset,
    )


# --- Stage 4: project workspace --------------------------------------------


@router.get(
    "/projects",
    response_model=list[TeacherProjectOut],
    summary="Проекты моих учеников",
)
async def list_projects(
    user: Staff,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[TeacherProjectOut]:
    return await project_cards.list_projects(session, user)


@router.get(
    "/projects/{project_id}",
    response_model=TeacherProjectOut,
    summary="Карточка проекта",
)
async def get_project(
    project_id: uuid.UUID,
    user: Staff,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TeacherProjectOut:
    return await project_cards.get_project(session, user, project_id)


@router.get(
    "/projects/{project_id}/files",
    response_model=list[ProjectFileOut],
    summary="Файлы проекта",
)
async def project_files(
    project_id: uuid.UUID,
    user: Staff,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[ProjectFileOut]:
    return await files_service.list_staff_files(session, user, project_id)


@router.get(
    "/projects/{project_id}/checklist",
    response_model=ChecklistOut,
    summary="Чек-лист проекта",
)
async def project_checklist(
    project_id: uuid.UUID,
    user: Staff,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ChecklistOut:
    return await checklists_service.get_staff_checklist(session, user, project_id)


@router.get(
    "/projects/{project_id}/comments",
    response_model=list[CommentOut],
    summary="Комментарии проекта",
)
async def project_comments(
    project_id: uuid.UUID,
    user: Staff,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[CommentOut]:
    return await comments_service.list_staff_comments(session, user, project_id)


@router.post(
    "/projects/{project_id}/comments",
    response_model=CommentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Оставить комментарий ученику",
)
async def create_comment(
    project_id: uuid.UUID,
    payload: CommentCreateRequest,
    user: Staff,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CommentOut:
    return await comments_service.create_comment(session, user, project_id, payload)


@router.patch(
    "/comments/{comment_id}",
    response_model=CommentOut,
    summary="Изменить комментарий",
)
async def update_comment(
    comment_id: uuid.UUID,
    payload: CommentUpdateRequest,
    user: Staff,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CommentOut:
    return await comments_service.update_comment(session, user, comment_id, payload)


@router.delete(
    "/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить комментарий",
)
async def delete_comment(
    comment_id: uuid.UUID,
    user: Staff,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    await comments_service.delete_comment(session, user, comment_id)


@router.post(
    "/checklist-states/{state_id}/verify",
    response_model=ChecklistItemStateOut,
    summary="Подтвердить пункт чек-листа",
)
async def verify_checklist_state(
    state_id: uuid.UUID,
    payload: ChecklistVerifyRequest,
    user: Staff,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ChecklistItemStateOut:
    return await checklists_service.verify_state(session, user, state_id, comment=payload.comment)


@router.post(
    "/checklist-states/{state_id}/skip",
    response_model=ChecklistItemStateOut,
    summary="Пропустить пункт чек-листа",
)
async def skip_checklist_state(
    state_id: uuid.UUID,
    payload: ChecklistVerifyRequest,
    user: Staff,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ChecklistItemStateOut:
    return await checklists_service.skip_state(session, user, state_id, comment=payload.comment)
