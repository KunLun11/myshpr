"""Product brief: reference categories and the student's product choice."""

import time
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ValidationError
from app.models import ProductCategory, Project, User
from app.models.enums import ProjectStatus, status_rank
from app.repositories import projects as projects_repo
from app.repositories import reference as reference_repo
from app.schemas.product import (
    PRODUCT_DESCRIPTION_MAX,
    PRODUCT_DESCRIPTION_MIN,
    ProductBrief,
    ProductOut,
    ProductRequirements,
    ProductUpdateRequest,
)
from app.schemas.reference import ProductCategoryOut, ProductGuidance
from app.services import project_access

CACHE_TTL_SECONDS = 300

_cache: tuple[float, list[ProductCategoryOut]] | None = None


def clear_product_category_cache() -> None:
    """Tests call this after creating reference rows inside a transaction."""
    global _cache
    _cache = None


def _serialize_category(category: ProductCategory) -> ProductCategoryOut:
    raw = category.guidance
    guidance = ProductGuidance.model_validate(raw) if isinstance(raw, dict) else None
    return ProductCategoryOut(
        id=category.id,
        slug=category.slug,
        name=category.name,
        description=category.description,
        guidance=guidance,
    )


async def list_categories(
    session: AsyncSession, *, use_cache: bool = True
) -> list[ProductCategoryOut]:
    global _cache
    now = time.monotonic()
    if use_cache and _cache is not None and now - _cache[0] < CACHE_TTL_SECONDS:
        return _cache[1]

    rows = await reference_repo.list_product_categories(session, active_only=True)
    serialized = [_serialize_category(row) for row in rows]
    _cache = (now, serialized)
    return serialized


async def _category_out(session: AsyncSession, project: Project) -> ProductCategoryOut | None:
    if project.product_category_id is None:
        return None
    category = await reference_repo.get_product_category(session, project.product_category_id)
    return _serialize_category(category) if category is not None else None


def _brief(project: Project) -> ProductBrief | None:
    raw = project.product_brief
    if not isinstance(raw, dict):
        return None
    brief = ProductBrief(
        defense_plan=raw.get("defense_plan") or None,
        audience=raw.get("audience") or None,
    )
    if brief.defense_plan is None and brief.audience is None:
        return None
    return brief


async def get_product_state(session: AsyncSession, student: User) -> ProductOut:
    context = await project_access.load_student_project(session, student)
    project = context.project
    category = await _category_out(session, project)
    return ProductOut(
        project_id=project.id,
        status=project.status.value,
        category=category,
        description=project.product_description,
        brief=_brief(project),
        guidance=category.guidance if category else None,
        requirements=ProductRequirements(),
        product_defined_at=project.product_defined_at,
    )


async def update_product(
    session: AsyncSession, student: User, payload: ProductUpdateRequest
) -> ProductOut:
    context = await project_access.load_student_project(session, student)
    project = context.project
    project_access.require_topic_approved(project)

    description = payload.product_description.strip()
    length = len(description)
    if length < PRODUCT_DESCRIPTION_MIN or length > PRODUCT_DESCRIPTION_MAX:
        raise ValidationError(
            f"Описание продукта должно быть от {PRODUCT_DESCRIPTION_MIN} "
            f"до {PRODUCT_DESCRIPTION_MAX} символов.",
            "PRODUCT_DESCRIPTION_INVALID",
            errors=[
                {
                    "field": "product_description",
                    "message": f"Сейчас {length} символов.",
                }
            ],
        )

    category = await reference_repo.get_product_category(session, payload.product_category_id)
    if category is None or not category.is_active:
        raise ValidationError("Категория продукта не найдена", "INVALID_PRODUCT_CATEGORY")

    brief_values = {
        "defense_plan": (payload.defense_plan or "").strip() or None,
        "audience": (payload.audience or "").strip() or None,
    }
    brief = {key: value for key, value in brief_values.items() if value is not None}

    now = datetime.now(UTC)
    first_definition = status_rank(project.status) < status_rank(ProjectStatus.PRODUCT_DEFINED)

    project.product_category_id = category.id
    project.product_description = description
    project.product_brief = brief or None
    project.last_activity_at = now
    if first_definition:
        project.status = ProjectStatus.PRODUCT_DEFINED
        project.product_defined_at = now

    await projects_repo.add_event(
        session,
        project_id=project.id,
        event_type="product_defined" if first_definition else "product_updated",
        actor_id=student.id,
        payload={"product_category_id": str(category.id)},
    )
    await session.commit()

    return await get_product_state(session, student)
