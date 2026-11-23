"""Student endpoints: my project and the topic wizard."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, require_roles
from app.core.rate_limit import enforce_rate_limit, topic_check_limiter, upload_limiter
from app.models import User
from app.models.enums import ChecklistState, FileKind, UserRole
from app.schemas.checklist import ChecklistItemStateOut, ChecklistOut, ChecklistStateUpdateRequest
from app.schemas.comment import CommentOut
from app.schemas.file import ProjectFileOut
from app.schemas.product import ProductOut, ProductUpdateRequest
from app.schemas.projects import ProjectOut, ProjectPatchRequest, ProjectPatchResponse
from app.schemas.topic import TopicCheckOut, TopicCheckRequest, TopicSubmitRequest
from app.services import checklists as checklists_service
from app.services import comments as comments_service
from app.services import files as files_service
from app.services import product_guide
from app.services import topics as topics_service

router = APIRouter(prefix="/me", tags=["me"])

Student = Annotated[User, Depends(require_roles(UserRole.STUDENT))]


@router.get("/project", response_model=ProjectOut | None, summary="Мой проект")
async def get_my_project(
    user: Student,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ProjectOut | None:
    return await topics_service.get_my_project(session, user)


@router.patch("/project", response_model=ProjectPatchResponse, summary="Черновик проекта")
async def patch_my_project(
    payload: ProjectPatchRequest,
    user: Student,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ProjectPatchResponse:
    return await topics_service.update_my_project(session, user, payload)


@router.post(
    "/project/topic/check",
    response_model=TopicCheckOut,
    summary="Проверить формулировку темы",
)
async def check_topic(
    payload: TopicCheckRequest,
    user: Student,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TopicCheckOut:
    enforce_rate_limit(topic_check_limiter, str(user.id))
    return await topics_service.check_my_topic(session, user, payload)


@router.post(
    "/project/topic/submit",
    response_model=ProjectOut,
    summary="Отправить тему учителю",
)
async def submit_topic(
    payload: TopicSubmitRequest,
    user: Student,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ProjectOut:
    return await topics_service.submit_my_topic(session, user, payload)


# --- Stage 4: product, files, checklist, comments --------------------------


@router.get("/project/product", response_model=ProductOut, summary="Мой продукт")
async def get_product(
    user: Student,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ProductOut:
    return await product_guide.get_product_state(session, user)


@router.patch("/project/product", response_model=ProductOut, summary="Определить продукт")
async def update_product(
    payload: ProductUpdateRequest,
    user: Student,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ProductOut:
    return await product_guide.update_product(session, user, payload)


@router.get(
    "/project/files",
    response_model=list[ProjectFileOut],
    summary="Файлы проекта",
)
async def list_files(
    user: Student,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[ProjectFileOut]:
    return await files_service.list_student_files(session, user)


@router.post(
    "/project/files",
    response_model=ProjectFileOut,
    status_code=status.HTTP_201_CREATED,
    summary="Загрузить файл",
)
async def upload_file(
    user: Student,
    session: Annotated[AsyncSession, Depends(get_session)],
    file: Annotated[UploadFile, File()],
    kind: Annotated[FileKind, Form()] = FileKind.FINAL_WORK,
) -> ProjectFileOut:
    enforce_rate_limit(upload_limiter, str(user.id))
    return await files_service.upload_file(session, user, file, kind=kind)


@router.delete(
    "/project/files/{file_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить файл",
)
async def delete_file(
    file_id: uuid.UUID,
    user: Student,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    await files_service.delete_file(session, user, file_id)


@router.get(
    "/project/checklist",
    response_model=ChecklistOut,
    summary="Чек-лист проекта",
)
async def get_checklist(
    user: Student,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ChecklistOut:
    return await checklists_service.get_student_checklist(session, user)


@router.patch(
    "/project/checklist/{item_id}",
    response_model=ChecklistItemStateOut,
    summary="Отметить пункт чек-листа",
)
async def update_checklist_item(
    item_id: uuid.UUID,
    payload: ChecklistStateUpdateRequest,
    user: Student,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ChecklistItemStateOut:
    return await checklists_service.update_student_item(
        session, user, item_id, ChecklistState(payload.status)
    )


@router.get(
    "/project/comments",
    response_model=list[CommentOut],
    summary="Комментарии учителя",
)
async def list_comments(
    user: Student,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[CommentOut]:
    return await comments_service.list_student_comments(session, user)
