import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import (
    ExternalSyncStatus,
    IntegrationConnectionStatus,
    SyncJobStatus,
    SyncJobType,
    SyncLogLevel,
)


class IntegrationProviderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    description: str | None
    provider_type: str
    supported_modules_json: list
    capabilities_json: dict
    is_active: bool


class IntegrationConnectionCreate(BaseModel):
    provider_code: str = Field(max_length=64)
    module_code: str = Field(max_length=64)
    name: str = Field(max_length=255)
    credentials_json: dict = Field(default_factory=dict)
    settings_json: dict = Field(default_factory=dict)


class IntegrationConnectionUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    status: IntegrationConnectionStatus | None = None
    credentials_json: dict | None = None
    settings_json: dict | None = None


class IntegrationConnectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    provider_code: str
    module_code: str
    name: str
    status: IntegrationConnectionStatus
    settings_json: dict
    has_credentials: bool
    last_sync_at: datetime | None
    last_error: str | None
    created_at: datetime
    updated_at: datetime


class ConnectionTestResponse(BaseModel):
    success: bool
    message: str
    details: dict = Field(default_factory=dict)


class SyncJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    connection_id: uuid.UUID
    job_type: SyncJobType
    status: SyncJobStatus
    started_at: datetime | None
    completed_at: datetime | None
    stats_json: dict
    error_message: str | None
    created_at: datetime


class SyncLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    level: SyncLogLevel
    message: str
    details_json: dict
    created_at: datetime


class SyncJobDetailResponse(SyncJobResponse):
    logs: list[SyncLogResponse] = Field(default_factory=list)


class ExternalReferenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    connection_id: uuid.UUID | None
    entity_type: str
    entity_id: uuid.UUID
    provider_code: str
    external_entity_type: str
    external_id: str
    external_url: str | None
    sync_status: ExternalSyncStatus
    last_synced_at: datetime | None
    metadata_json: dict
    created_at: datetime


class ExternalReferenceCreate(BaseModel):
    entity_type: str = Field(max_length=64)
    entity_id: uuid.UUID
    provider_code: str = Field(max_length=64)
    external_entity_type: str = Field(max_length=64)
    external_id: str = Field(max_length=128)
    external_url: str | None = Field(default=None, max_length=512)
    connection_id: uuid.UUID | None = None
    metadata_json: dict = Field(default_factory=dict)


class WebhookPayload(BaseModel):
    event_type: str = Field(default="unknown", max_length=64)
    payload: dict = Field(default_factory=dict)
    tenant_id: uuid.UUID | None = None


class WebhookReceiveResponse(BaseModel):
    event_id: uuid.UUID
    status: str
    message: str
