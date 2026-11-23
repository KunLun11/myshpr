"""Product brief schemas (stage 4)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.reference import ProductCategoryOut, ProductGuidance

PRODUCT_DESCRIPTION_MIN = 120
PRODUCT_DESCRIPTION_MAX = 1500


class ProductBrief(BaseModel):
    """What the student will show at the defence and for whom."""

    defense_plan: str | None = None
    audience: str | None = None


class ProductRequirements(BaseModel):
    description_min: int = PRODUCT_DESCRIPTION_MIN
    description_max: int = PRODUCT_DESCRIPTION_MAX


class ProductOut(BaseModel):
    project_id: UUID
    status: str
    category: ProductCategoryOut | None = None
    description: str | None = None
    brief: ProductBrief | None = None
    guidance: ProductGuidance | None = None
    requirements: ProductRequirements = Field(default_factory=ProductRequirements)
    product_defined_at: datetime | None = None


class ProductUpdateRequest(BaseModel):
    product_category_id: UUID
    product_description: str
    defense_plan: str | None = Field(default=None, max_length=1000)
    audience: str | None = Field(default=None, max_length=500)
