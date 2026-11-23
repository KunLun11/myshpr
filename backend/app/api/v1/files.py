"""Authorised file downloads (never public links)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_session
from app.models import User
from app.services import files as files_service

router = APIRouter(prefix="/files", tags=["files"])


@router.get("/{file_id}/download", summary="Скачать файл проекта")
async def download_file(
    file_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    file, local_path, presigned = await files_service.get_download_target(session, user, file_id)
    disposition = files_service.content_disposition(file.original_name)

    if presigned is not None:
        return RedirectResponse(presigned, status_code=302)

    if local_path is not None:
        return FileResponse(
            local_path,
            media_type=file.mime_type,
            headers={"Content-Disposition": disposition},
        )

    stream = await files_service.open_file_stream(file)
    return StreamingResponse(
        stream,
        media_type=file.mime_type,
        headers={"Content-Disposition": disposition},
    )
