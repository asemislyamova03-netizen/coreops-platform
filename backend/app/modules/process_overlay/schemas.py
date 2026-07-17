import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.process_overlay.enums import ProcessOverlayActivationState, ProcessRunState
from app.modules.process_overlay.policy_schema import PolicySnapshotV1


class ProcessTemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    description: str | None
    default_pipeline_code: str
    default_policy_blueprint_json: dict
    required_module_codes_json: list
    is_active: bool


class TenantProcessConfigurationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    process_template_id: uuid.UUID
    pipeline_id: uuid.UUID
    activation_state: ProcessOverlayActivationState
    active_definition_version_id: uuid.UUID | None


class ProcessDefinitionVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    tenant_process_configuration_id: uuid.UUID
    version_number: int
    pipeline_id: uuid.UUID
    pipeline_code: str
    stage_codes_json: list
    policy_snapshot_json: dict
    module_requirements_json: list
    published_at: datetime
    published_by_user_id: uuid.UUID
    publish_reason: str
    created_at: datetime


class PublishDefinitionVersionRequest(BaseModel):
    policy: PolicySnapshotV1
    publish_reason: str = Field(min_length=1, max_length=2000)


class ProcessRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    tenant_process_configuration_id: uuid.UUID
    process_definition_version_id: uuid.UUID
    work_item_id: uuid.UUID
    run_state: ProcessRunState
    started_at: datetime
    started_by_user_id: uuid.UUID
    completed_at: datetime | None
    completed_by_user_id: uuid.UUID | None
    completion_reason: str | None
    current_stage_code: str | None
    created_at: datetime
    updated_at: datetime
