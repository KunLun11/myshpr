"""Reference data (interest areas, product categories)."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_session
from app.models import User
from app.repositories import reference as reference_repo
from app.schemas.reference import InterestAreaOut, ProductCategoryOut
from app.services import product_guide

router = APIRouter(prefix="/reference", tags=["reference"])


@router.get(
    "/interest-areas",
    response_model=list[InterestAreaOut],
    summary="Сферы интересов",
)
async def interest_areas(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[InterestAreaOut]:
    areas = await reference_repo.list_interest_areas(session)
    return [
        InterestAreaOut(
            id=area.id,
            slug=area.slug,
            name=area.name,
            description=area.description,
        )
        for area in areas
    ]


@router.get(
    "/product-categories",
    response_model=list[ProductCategoryOut],
    summary="Категории продукта",
)
async def product_categories(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[ProductCategoryOut]:
    return await product_guide.list_categories(session)
