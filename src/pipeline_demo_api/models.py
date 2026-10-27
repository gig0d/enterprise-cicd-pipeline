"""Public API schemas."""

from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Sku = Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^[A-Z0-9-]{3,32}$")]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]


class ItemCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    sku: Sku
    name: Name
    quantity: int = Field(ge=0, le=1_000_000, strict=True)
    unit_price: Decimal = Field(ge=0, le=1_000_000, max_digits=9, decimal_places=2)


class Item(ItemCreate):
    id: int = Field(gt=0)


class Info(BaseModel):
    name: str
    version: str
    environment: str
    build_id: str | None


class Health(BaseModel):
    status: str
    dependencies: dict[str, str] = Field(default_factory=dict)
