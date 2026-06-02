import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import ModuleMode, ModuleStatus


class ModuleDefinitionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    description: str | None
    default_mode: ModuleMode
    dependencies_json: dict
    is_active: bool


class TenantModuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    module_code: str
    status: ModuleStatus
    mode: ModuleMode
    external_provider_code: str | None
    settings_json: dict
    created_at: datetime
    updated_at: datetime


class TenantModuleUpdate(BaseModel):
    status: ModuleStatus | None = None
    mode: ModuleMode | None = None
    external_provider_code: str | None = None
    settings_json: dict | None = None


class TenantModuleModeUpdate(BaseModel):
    mode: ModuleMode
    external_provider_code: str | None = None
    settings_json: dict | None = None
