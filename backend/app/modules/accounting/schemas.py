import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import TaxRegime


class LegalEntityCreate(BaseModel):
    name: str = Field(max_length=255)
    legal_form: str | None = Field(default=None, max_length=64)
    country: str = Field(default="RU", max_length=2)
    registration_number: str | None = Field(default=None, max_length=64)
    tax_number: str | None = Field(default=None, max_length=64)
    residency_status: str | None = Field(default=None, max_length=32)
    base_currency: str = Field(default="RUB", max_length=3)
    bank_details_json: dict = Field(default_factory=dict)
    is_active: bool = True


class LegalEntityUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    legal_form: str | None = None
    country: str | None = Field(default=None, max_length=2)
    registration_number: str | None = None
    tax_number: str | None = None
    residency_status: str | None = None
    base_currency: str | None = Field(default=None, max_length=3)
    bank_details_json: dict | None = None
    is_active: bool | None = None


class LegalEntityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    legal_form: str | None
    country: str
    registration_number: str | None
    tax_number: str | None
    residency_status: str | None
    base_currency: str
    bank_details_json: dict
    is_active: bool
    created_at: datetime
    updated_at: datetime


class TaxProfileCreate(BaseModel):
    legal_entity_id: uuid.UUID
    code: str = Field(max_length=64)
    name: str = Field(max_length=255)
    country: str = Field(default="RU", max_length=2)
    tax_regime: TaxRegime = TaxRegime.GENERAL
    default_vat_rate: Decimal | None = None
    config_json: dict = Field(default_factory=dict)
    is_active: bool = True
    notes: str | None = None


class TaxProfileUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    country: str | None = Field(default=None, max_length=2)
    tax_regime: TaxRegime | None = None
    default_vat_rate: Decimal | None = None
    config_json: dict | None = None
    is_active: bool | None = None
    notes: str | None = None


class TaxProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    legal_entity_id: uuid.UUID
    code: str
    name: str
    country: str
    tax_regime: TaxRegime
    default_vat_rate: Decimal | None
    config_json: dict
    is_active: bool
    notes: str | None
    created_at: datetime
    updated_at: datetime
