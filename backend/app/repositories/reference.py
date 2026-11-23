"""Reference-data queries: interest areas and product categories."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import InterestArea, ProductCategory


async def list_interest_areas(
    session: AsyncSession, *, active_only: bool = True
) -> list[InterestArea]:
    stmt = select(InterestArea).order_by(InterestArea.sort_order, InterestArea.name)
    if active_only:
        stmt = stmt.where(InterestArea.is_active.is_(True))
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_interest_area(session: AsyncSession, area_id: uuid.UUID) -> InterestArea | None:
    return await session.get(InterestArea, area_id)


async def list_product_categories(
    session: AsyncSession, *, active_only: bool = True
) -> list[ProductCategory]:
    stmt = select(ProductCategory).order_by(ProductCategory.sort_order, ProductCategory.name)
    if active_only:
        stmt = stmt.where(ProductCategory.is_active.is_(True))
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_product_category(
    session: AsyncSession, category_id: uuid.UUID
) -> ProductCategory | None:
    return await session.get(ProductCategory, category_id)


async def get_interest_area_by_slug(session: AsyncSession, slug: str) -> InterestArea | None:
    result = await session.execute(select(InterestArea).where(InterestArea.slug == slug))
    return result.scalars().first()


async def get_product_category_by_slug(session: AsyncSession, slug: str) -> ProductCategory | None:
    result = await session.execute(select(ProductCategory).where(ProductCategory.slug == slug))
    return result.scalars().first()


async def create_interest_area(
    session: AsyncSession,
    *,
    slug: str,
    name: str,
    description: str | None,
    sort_order: int,
    is_active: bool,
) -> InterestArea:
    area = InterestArea(
        slug=slug,
        name=name,
        description=description,
        sort_order=sort_order,
        is_active=is_active,
    )
    session.add(area)
    await session.flush()
    return area


async def update_interest_area(session: AsyncSession, area: InterestArea, *, values: dict) -> None:
    for field, value in values.items():
        setattr(area, field, value)
    await session.flush()


async def create_product_category(
    session: AsyncSession,
    *,
    slug: str,
    name: str,
    description: str | None,
    guidance: dict | None,
    sort_order: int,
    is_active: bool,
) -> ProductCategory:
    category = ProductCategory(
        slug=slug,
        name=name,
        description=description,
        guidance=guidance,
        sort_order=sort_order,
        is_active=is_active,
    )
    session.add(category)
    await session.flush()
    return category


async def update_product_category(
    session: AsyncSession, category: ProductCategory, *, values: dict
) -> None:
    for field, value in values.items():
        setattr(category, field, value)
    await session.flush()
