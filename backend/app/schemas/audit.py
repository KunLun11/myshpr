"""Audit-log schema (stage 6)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AuditEntryOut(BaseModel):
    id: int
    created_at: datetime
    actor_id: UUID | None = None
    actor_name: str | None = None
    school_id: UUID | None = None
    action: str
    entity_type: str
    entity_id: str | None = None
    payload: dict | None = None
