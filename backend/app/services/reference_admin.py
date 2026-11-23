"""Admin CRUD for global reference data (stage 6).

Interest areas and product categories are shared by every school, so only a
super admin may change them. School admins can read the same records.
"""

import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, ForbiddenError, NotFoundError
from app.models import InterestArea, ProductCategory, User
from app.models.enums import UserRole
from app.repositories import reference as reference_repo
from app.schemas.reference import (
    AdminInterestAreaOut,
    AdminProductCategoryOut,
    InterestAreaCreateRequest,
    InterestAreaUpdateRequest,
    ProductCategoryCreateRequest,
    ProductCategoryUpdateRequest,
)
from app.services.product_guide import clear_product_category_cache


def serialize_area(area: InterestArea) -> AdminInterestAreaOut:
    return AdminInterestAreaOut(
        id=area.id,
        slug=area.slug,
        name=area.name,
        description=area.description,
        is_active=area.is_active,
        sort_order=area.sort_order,
    )


def serialize_category(category: ProductCategory) -> AdminProductCategoryOut:
    return AdminProductCategoryOut(
        id=category.id,
        slug=category.slug,
        name=category.name,
        description=category.description,
        guidance=category.guidance,
        is_active=category.is_active,
        sort_order=category.sort_order,
    )


def _require_super_admin(user: User) -> None:
    if user.role is not UserRole.SUPER_ADMIN:
        raise ForbiddenError(
            "Справочники платформы меняет только суперадмин", "SUPER_ADMIN_REQUIRED"
        )


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    return value.strip() or None


async def list_interest_areas(session: AsyncSession) -> list[AdminInterestAreaOut]:
    rows = await reference_repo.list_interest_areas(session, active_only=False)
    return [serialize_area(row) for row in rows]


async def create_interest_area(
    session: AsyncSession, user: User, payload: InterestAreaCreateRequest
) -> AdminInterestAreaOut:
    _require_super_admin(user)
    try:
        area = await reference_repo.create_interest_area(
            session,
            slug=payload.slug,
            name=payload.name.strip(),
            description=_clean_text(payload.description),
            sort_order=payload.sort_order,
            is_active=payload.is_active,
        )
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError("Сфера с таким кодом уже есть", "INTEREST_AREA_DUPLICATE") from exc
    await session.refresh(area)
    return serialize_area(area)


async def update_interest_area(
    session: AsyncSession,
    user: User,
    area_id: uuid.UUID,
    payload: InterestAreaUpdateRequest,
) -> AdminInterestAreaOut:
    _require_super_admin(user)
    area = await reference_repo.get_interest_area(session, area_id)
    if area is None:
        raise NotFoundError("Сфера интересов не найдена", "INTEREST_AREA_NOT_FOUND")

    values = payload.model_dump(exclude_unset=True)
    if "name" in values and values["name"] is not None:
        values["name"] = values["name"].strip()
    if "description" in values:
        values["description"] = _clean_text(values["description"])

    try:
        if values:
            await reference_repo.update_interest_area(session, area, values=values)
            await session.commit()
            await session.refresh(area)
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError("Сфера с таким кодом уже есть", "INTEREST_AREA_DUPLICATE") from exc
    return serialize_area(area)


async def list_product_categories(session: AsyncSession) -> list[AdminProductCategoryOut]:
    rows = await reference_repo.list_product_categories(session, active_only=False)
    return [serialize_category(row) for row in rows]


async def create_product_category(
    session: AsyncSession, user: User, payload: ProductCategoryCreateRequest
) -> AdminProductCategoryOut:
    _require_super_admin(user)
    try:
        category = await reference_repo.create_product_category(
            session,
            slug=payload.slug,
            name=payload.name.strip(),
            description=_clean_text(payload.description),
            guidance=payload.guidance.model_dump() if payload.guidance else None,
            sort_order=payload.sort_order,
            is_active=payload.is_active,
        )
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError(
            "Категория с таким кодом уже есть", "PRODUCT_CATEGORY_DUPLICATE"
        ) from exc
    clear_product_category_cache()
    await session.refresh(category)
    return serialize_category(category)


async def update_product_category(
    session: AsyncSession,
    user: User,
    category_id: uuid.UUID,
    payload: ProductCategoryUpdateRequest,
) -> AdminProductCategoryOut:
    _require_super_admin(user)
    category = await reference_repo.get_product_category(session, category_id)
    if category is None:
        raise NotFoundError("Категория продукта не найдена", "PRODUCT_CATEGORY_NOT_FOUND")

    values = payload.model_dump(exclude_unset=True)
    if "name" in values and values["name"] is not None:
        values["name"] = values["name"].strip()
    if "description" in values:
        values["description"] = _clean_text(values["description"])

    try:
        if values:
            await reference_repo.update_product_category(session, category, values=values)
            await session.commit()
            await session.refresh(category)
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError(
            "Категория с таким кодом уже есть", "PRODUCT_CATEGORY_DUPLICATE"
        ) from exc
    clear_product_category_cache()
    return serialize_category(category)
