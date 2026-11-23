"""Reference-data schemas."""

from uuid import UUID

from pydantic import BaseModel, Field


class InterestAreaOut(BaseModel):
    id: UUID
    slug: str
    name: str
    description: str | None = None


class ProductGuidance(BaseModel):
    """Hints shown next to the product form.

    The reference row stores a free-form JSON object; unknown keys are ignored
    so administrators can add new hints without a migration.
    """

    examples: list[str] = Field(default_factory=list)
    must_have: list[str] = Field(default_factory=list)
    common_mistakes: list[str] = Field(default_factory=list)
    defense_tip: str | None = None


class ProductCategoryOut(BaseModel):
    id: UUID
    slug: str
    name: str
    description: str | None = None
    guidance: ProductGuidance | None = None


# --- Stage 6: admin reference-data CRUD -------------------------------------

SLUG_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"


class AdminInterestAreaOut(InterestAreaOut):
    is_active: bool
    sort_order: int


class InterestAreaCreateRequest(BaseModel):
    slug: str = Field(min_length=1, max_length=100, pattern=SLUG_PATTERN)
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    sort_order: int = 100
    is_active: bool = True


class InterestAreaUpdateRequest(BaseModel):
    slug: str | None = Field(default=None, min_length=1, max_length=100, pattern=SLUG_PATTERN)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    sort_order: int | None = None
    is_active: bool | None = None


class AdminProductCategoryOut(ProductCategoryOut):
    is_active: bool
    sort_order: int


class ProductCategoryCreateRequest(BaseModel):
    slug: str = Field(min_length=1, max_length=100, pattern=SLUG_PATTERN)
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    guidance: ProductGuidance | None = None
    sort_order: int = 100
    is_active: bool = True


class ProductCategoryUpdateRequest(BaseModel):
    slug: str | None = Field(default=None, min_length=1, max_length=100, pattern=SLUG_PATTERN)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    guidance: ProductGuidance | None = None
    sort_order: int | None = None
    is_active: bool | None = None
