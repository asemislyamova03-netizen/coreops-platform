import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import DocumentFileType, DocumentStatus, SignatureStatus


class DocumentFieldCreate(BaseModel):
    field_key: str = Field(max_length=64)
    label: str = Field(max_length=255)
    field_type: str = Field(default="string", max_length=32)
    is_required: bool = False
    default_value: str | None = None


class DocumentFieldResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    field_key: str
    label: str
    field_type: str
    is_required: bool
    default_value: str | None


class DocumentTemplateCreate(BaseModel):
    code: str = Field(max_length=64)
    name: str = Field(max_length=255)
    description: str | None = None
    document_type: str = Field(default="contract", max_length=64)
    body_template: str
    is_active: bool = True
    fields: list[DocumentFieldCreate] = Field(default_factory=list)


class DocumentTemplateUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    description: str | None = None
    document_type: str | None = Field(default=None, max_length=64)
    body_template: str | None = None
    is_active: bool | None = None


class DocumentTemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    code: str
    name: str
    description: str | None
    document_type: str
    body_template: str
    is_active: bool
    fields: list[DocumentFieldResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class DocumentFileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    file_type: DocumentFileType
    storage_path: str
    filename: str
    mime_type: str
    size_bytes: int
    created_at: datetime


class SignatureRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: SignatureStatus
    sent_at: datetime | None
    signed_at: datetime | None
    notes: str | None
    created_at: datetime


class DocumentAuditResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    action: str
    actor_user_id: uuid.UUID | None
    details_json: dict
    created_at: datetime


class DocumentGenerateRequest(BaseModel):
    template_id: uuid.UUID
    title: str | None = Field(default=None, max_length=255)
    context: dict[str, str] = Field(default_factory=dict)
    party_id: uuid.UUID | None = None
    work_item_id: uuid.UUID | None = None


class DocumentUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    status: DocumentStatus | None = None


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    template_id: uuid.UUID | None
    title: str
    status: DocumentStatus
    rendered_content: str | None
    context_json: dict
    party_id: uuid.UUID | None
    work_item_id: uuid.UUID | None
    files: list[DocumentFileResponse] = Field(default_factory=list)
    signature_requests: list[SignatureRequestResponse] = Field(default_factory=list)
    audit_trail: list[DocumentAuditResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
