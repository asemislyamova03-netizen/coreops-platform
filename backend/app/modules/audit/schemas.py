import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import AuditAction, DataAccessType, SecurityEventType


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID | None
    user_id: uuid.UUID | None
    action: AuditAction
    entity_type: str | None
    entity_id: uuid.UUID | None
    summary: str
    changes_json: dict
    ip_address: str | None
    user_agent: str | None
    ai_proposal_id: uuid.UUID | None
    approved_by_user_id: uuid.UUID | None
    metadata_json: dict
    created_at: datetime


class DataAccessLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    access_type: DataAccessType
    entity_type: str
    entity_id: uuid.UUID | None
    resource_label: str | None
    ip_address: str | None
    user_agent: str | None
    metadata_json: dict
    created_at: datetime


class SecurityEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID | None
    user_id: uuid.UUID | None
    event_type: SecurityEventType
    email: str | None
    ip_address: str | None
    user_agent: str | None
    details_json: dict
    occurred_at: datetime
    created_at: datetime


class ImportBatchEntitySummary(BaseModel):
    entity: str = Field(min_length=1, max_length=64)
    source_count: int = Field(ge=0)
    imported_count: int = Field(ge=0)
    skipped_count: int = Field(ge=0)
    error_count: int = Field(ge=0)
    review_count: int = Field(ge=0)


class ImportBatchSummary(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_by_user_id: uuid.UUID | None = None
    source_system: str = Field(default="consult_app", max_length=64)
    started_at: datetime
    finished_at: datetime | None = None
    total_source_rows: int = Field(ge=0)
    total_imported_rows: int = Field(ge=0)
    total_skipped_rows: int = Field(ge=0)
    total_error_rows: int = Field(ge=0)
    total_review_rows: int = Field(ge=0)
    status_mapping_warnings: int = Field(ge=0)
    entities: list[ImportBatchEntitySummary] = Field(default_factory=list)
    notes: str | None = None
