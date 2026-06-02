import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

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
