"""Versioned API router aggregator."""

from fastapi import APIRouter

from app.api.v1 import (
    admin,
    auth,
    files,
    health,
    me,
    notifications,
    reference,
    teacher,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(reference.router)
api_router.include_router(me.router)
api_router.include_router(teacher.router)
api_router.include_router(admin.router)
api_router.include_router(files.router)
api_router.include_router(notifications.router)
