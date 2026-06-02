import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import CatalogItemType


class UnitOfMeasureCreate(BaseModel):
    code: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=128)
    symbol: str | None = Field(default=None, max_length=16)


class UnitOfMeasureResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    symbol: str | None


class CatalogItemCreate(BaseModel):
    item_type: CatalogItemType
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    sku: str | None = Field(default=None, max_length=64)
    unit_id: uuid.UUID | None = None
    base_price: Decimal | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, max_length=3)
    is_active: bool = True
    custom_fields: dict[str, Any] = Field(default_factory=dict)


class CatalogItemUpdate(BaseModel):
    item_type: CatalogItemType | None = None
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    sku: str | None = Field(default=None, max_length=64)
    unit_id: uuid.UUID | None = None
    base_price: Decimal | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, max_length=3)
    is_active: bool | None = None
    custom_fields: dict[str, Any] | None = None


class CatalogItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    item_type: CatalogItemType
    name: str
    description: str | None
    sku: str | None
    unit_id: uuid.UUID | None
    base_price: Decimal | None
    currency: str | None
    is_active: bool
    custom_fields: dict[str, Any] = Field(default_factory=dict)
    unit: UnitOfMeasureResponse | None = None
    created_at: datetime
    updated_at: datetime


class PriceListCreate(BaseModel):
    code: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9_]+$")
    name: str = Field(min_length=1, max_length=255)
    currency: str = Field(default="RUB", max_length=3)
    is_active: bool = True
    valid_from: datetime | None = None
    valid_to: datetime | None = None


class PriceListUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    currency: str | None = Field(default=None, max_length=3)
    is_active: bool | None = None
    valid_from: datetime | None = None
    valid_to: datetime | None = None


class PriceListItemCreate(BaseModel):
    catalog_item_id: uuid.UUID
    price: Decimal = Field(ge=0)
    min_quantity: Decimal | None = Field(default=None, ge=0)


class PriceListItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    catalog_item_id: uuid.UUID
    catalog_item_name: str
    price: Decimal
    min_quantity: Decimal | None


class PriceListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    code: str
    name: str
    currency: str
    is_active: bool
    valid_from: datetime | None
    valid_to: datetime | None
    items: list[PriceListItemResponse] = Field(default_factory=list)
    created_at: datetime
