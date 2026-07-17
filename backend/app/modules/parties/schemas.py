import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.enums import AddressType, ContactMethodType, PartyStatus, PartyType


class ContactMethodCreate(BaseModel):
    method_type: ContactMethodType
    value: str = Field(min_length=1, max_length=320)
    label: str | None = Field(default=None, max_length=128)
    is_primary: bool = False


class ContactMethodResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    method_type: ContactMethodType
    value: str
    label: str | None
    is_primary: bool


class AddressCreate(BaseModel):
    address_type: AddressType = AddressType.ACTUAL
    country: str | None = Field(default=None, max_length=2)
    city: str | None = Field(default=None, max_length=128)
    line1: str | None = Field(default=None, max_length=255)
    line2: str | None = Field(default=None, max_length=255)
    postal_code: str | None = Field(default=None, max_length=32)
    is_primary: bool = False


class AddressResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    address_type: AddressType
    country: str | None
    city: str | None
    line1: str | None
    line2: str | None
    postal_code: str | None
    is_primary: bool


class CustomFieldDefinitionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    entity_type: str
    field_key: str
    field_type: str
    label: str
    applies_to_json: dict
    options_json: dict
    is_required: bool
    sort_order: int


class PartyCreate(BaseModel):
    party_type: PartyType
    display_name: str = Field(min_length=1, max_length=255)
    status: PartyStatus = PartyStatus.ACTIVE
    metadata_json: dict = Field(default_factory=dict)
    contact_methods: list[ContactMethodCreate] = Field(default_factory=list)
    addresses: list[AddressCreate] = Field(default_factory=list)
    custom_fields: dict[str, Any] = Field(default_factory=dict)
    party_role: str | None = Field(
        default=None,
        description="Optional role tag for custom field filtering (e.g. enrollee, guardian)",
    )


class PartyUpdate(BaseModel):
    party_type: PartyType | None = None
    display_name: str | None = Field(default=None, min_length=1, max_length=255)
    status: PartyStatus | None = None
    metadata_json: dict | None = None
    contact_methods: list[ContactMethodCreate] | None = None
    addresses: list[AddressCreate] | None = None
    custom_fields: dict[str, Any] | None = None
    party_role: str | None = None


class PartyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    party_type: PartyType
    display_name: str
    status: PartyStatus
    metadata_json: dict
    contact_methods: list[ContactMethodResponse]
    addresses: list[AddressResponse]
    custom_fields: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    created_by_user_id: uuid.UUID | None
    updated_by_user_id: uuid.UUID | None


class PartyListParams(BaseModel):
    party_type: PartyType | None = None
    status: PartyStatus | None = None
    search: str | None = None
    skip: int = Field(default=0, ge=0)
    limit: int = Field(default=50, ge=1, le=200)


class PartyMatchRequest(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=320)
    email: str | None = Field(default=None, max_length=320)
    telegram_username: str | None = Field(default=None, max_length=320)
    telegram_user_id: str | None = Field(default=None, max_length=320)
    whatsapp: str | None = Field(default=None, max_length=320)

    @model_validator(mode="after")
    def require_at_least_one_field(self) -> "PartyMatchRequest":
        fields = (
            self.name,
            self.phone,
            self.email,
            self.telegram_username,
            self.telegram_user_id,
            self.whatsapp,
        )
        if not any(value is not None and str(value).strip() for value in fields):
            raise ValueError(
                "At least one of name, phone, email, telegram_username, "
                "telegram_user_id, whatsapp is required"
            )
        return self


class PartyMatchContactPreview(BaseModel):
    method_type: ContactMethodType
    value: str
    label: str | None = None
    is_primary: bool = False


class PartyMatchWorkItemPreview(BaseModel):
    id: uuid.UUID
    title: str
    status: str
    updated_at: datetime


class PartyMatchHit(BaseModel):
    party_id: uuid.UUID
    display_name: str
    party_type: PartyType
    status: PartyStatus
    match_type: Literal["exact", "weak"]
    score: int
    matched_on: list[str]
    contact_methods: list[PartyMatchContactPreview] = Field(default_factory=list)
    recent_work_items: list[PartyMatchWorkItemPreview] = Field(default_factory=list)


class PartyMatchNormalizedQuery(BaseModel):
    name: str | None = None
    phone: str | None = None
    email: str | None = None
    telegram_username: str | None = None
    telegram_user_id: str | None = None
    whatsapp: str | None = None


class PartyMatchResponse(BaseModel):
    matches: list[PartyMatchHit]
    query_normalized: PartyMatchNormalizedQuery
