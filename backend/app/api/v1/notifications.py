"""In-app notification endpoints for the current user."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_session
from app.models import User
from app.schemas.notification import NotificationListOut, NotificationOut
from app.services import notifications as notifications_service

router = APIRouter(prefix="/me/notifications", tags=["notifications"])

CurrentUser = Annotated[User, Depends(get_current_user)]


@router.get("", response_model=NotificationListOut, summary="Мои уведомления")
async def list_notifications(
    user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> NotificationListOut:
    return await notifications_service.list_my(session, user, limit=limit, offset=offset)


@router.post(
    "/{notification_id}/read",
    response_model=NotificationOut,
    summary="Отметить уведомление прочитанным",
)
async def mark_notification_read(
    notification_id: uuid.UUID,
    user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> NotificationOut:
    return await notifications_service.mark_read(session, user, notification_id)
