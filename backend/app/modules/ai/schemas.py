import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import (
    AIActionProposalStatus,
    AIActionType,
    AIApprovalDecision,
    AITaskStatus,
)


class AIAgentCreate(BaseModel):
    code: str = Field(max_length=64)
    name: str = Field(max_length=255)
    role_code: str = Field(default="assistant", max_length=64)
    description: str | None = None
    system_prompt: str | None = None
    config_json: dict = Field(default_factory=dict)
    is_active: bool = True
    requires_approval_for_critical: bool = True


class AIAgentUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    role_code: str | None = Field(default=None, max_length=64)
    description: str | None = None
    system_prompt: str | None = None
    config_json: dict | None = None
    is_active: bool | None = None
    requires_approval_for_critical: bool | None = None


class AIAgentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    code: str
    name: str
    role_code: str
    description: str | None
    system_prompt: str | None
    config_json: dict
    is_active: bool
    requires_approval_for_critical: bool
    created_at: datetime
    updated_at: datetime


class AITaskCreate(BaseModel):
    agent_id: uuid.UUID
    task_type: str = Field(default="general", max_length=64)
    title: str = Field(max_length=255)
    input_json: dict = Field(default_factory=dict)
    context_entity_type: str | None = Field(default=None, max_length=64)
    context_entity_id: uuid.UUID | None = None
    run_mock: bool = True


class AITaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    agent_id: uuid.UUID
    task_type: str
    status: AITaskStatus
    title: str
    input_json: dict
    output_json: dict
    context_entity_type: str | None
    context_entity_id: uuid.UUID | None
    error_message: str | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AIActionProposalCreate(BaseModel):
    agent_id: uuid.UUID
    task_id: uuid.UUID | None = None
    action_type: AIActionType
    title: str = Field(max_length=255)
    description: str | None = None
    payload_json: dict = Field(default_factory=dict)
    target_entity_type: str | None = Field(default=None, max_length=64)
    target_entity_id: uuid.UUID | None = None


class AIApprovalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    approver_user_id: uuid.UUID
    decision: AIApprovalDecision
    comment: str | None
    decided_at: datetime


class AIActionProposalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    agent_id: uuid.UUID
    task_id: uuid.UUID | None
    action_type: AIActionType
    status: AIActionProposalStatus
    title: str
    description: str | None
    payload_json: dict
    target_entity_type: str | None
    target_entity_id: uuid.UUID | None
    is_critical: bool
    expires_at: datetime | None
    executed_at: datetime | None
    execution_result_json: dict
    approvals: list[AIApprovalResponse] = Field(default_factory=list)
    created_at: datetime


class AIApprovalRequest(BaseModel):
    comment: str | None = None


class AIUsageEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agent_id: uuid.UUID | None
    task_id: uuid.UUID | None
    proposal_id: uuid.UUID | None
    event_type: str
    tokens_used: int
    cost_units: Decimal
    metadata_json: dict
    created_at: datetime


class AIUsageSummaryResponse(BaseModel):
    total_tokens: int
    total_cost_units: Decimal
    events_count: int
