"""Versioned API router aggregator."""

from fastapi import APIRouter

from app.api.v1 import health

api_router = APIRouter()
api_router.include_router(health.router)

# Remaining routers are added in later stages:
# auth, me, reference, projects, topics, products, teacher, notifications, admin.
