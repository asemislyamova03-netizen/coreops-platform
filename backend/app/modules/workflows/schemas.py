import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

DispositionCode = Literal[
    "spam",
    "off_topic",
    "duplicate",
    "test",
    "no_response",
    "other",
]

from app.core.enums import (
    ActivityType,
    TaskStatus,
    WorkItemParticipantRole,
    WorkItemStatus,
)


class PipelineStageCreate(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    sort_order: int = 0
    is_terminal: bool = False


class PipelineStageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    sort_order: int
    is_terminal: bool


class PipelineCreate(BaseModel):
    code: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9_]+$")
    name: str = Field(min_length=1, max_length=255)
    entity_type: str = "work_item"
    is_default: bool = False
    stages: list[PipelineStageCreate] = Field(default_factory=list)


class PipelineUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    is_default: bool | None = None


class PipelineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    code: str
    name: str
    entity_type: str
    is_default: bool
    stages: list[PipelineStageResponse]
    created_at: datetime


class WorkItemParticipantCreate(BaseModel):
    party_id: uuid.UUID
    role: WorkItemParticipantRole = WorkItemParticipantRole.CLIENT


class WorkItemParticipantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    party_id: uuid.UUID
    role: WorkItemParticipantRole


class WorkItemCreate(BaseModel):
    pipeline_id: uuid.UUID
    stage_id: uuid.UUID | None = None
    work_item_type: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    primary_party_id: uuid.UUID | None = None
    status: WorkItemStatus = WorkItemStatus.OPEN
    amount: Decimal | None = None
    currency: str | None = Field(default=None, max_length=3)
    source: str | None = Field(default=None, max_length=128)
    participants: list[WorkItemParticipantCreate] = Field(default_factory=list)
    custom_fields: dict[str, Any] = Field(default_factory=dict)


class WorkItemUpdate(BaseModel):
    stage_id: uuid.UUID | None = None
    work_item_type: str | None = Field(default=None, min_length=1, max_length=64)
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    primary_party_id: uuid.UUID | None = None
    status: WorkItemStatus | None = None
    amount: Decimal | None = None
    currency: str | None = Field(default=None, max_length=3)
    source: str | None = Field(default=None, max_length=128)
    custom_fields: dict[str, Any] | None = None


class MoveStageRequest(BaseModel):
    stage_id: uuid.UUID


class CloseWorkItemRequest(BaseModel):
    disposition: DispositionCode
    disposition_note: str | None = Field(default=None, max_length=2000)


class ReopenWorkItemRequest(BaseModel):
    note: str | None = Field(default=None, max_length=2000)


class ActivityCreate(BaseModel):
    activity_type: ActivityType = ActivityType.NOTE
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    occurred_at: datetime | None = None


class ActivityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    activity_type: ActivityType
    title: str
    description: str | None
    occurred_at: datetime
    created_by_user_id: uuid.UUID | None
    created_at: datetime


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    status: TaskStatus = TaskStatus.PENDING
    due_at: datetime | None = None
    assigned_to_user_id: uuid.UUID | None = None


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    description: str | None
    status: TaskStatus
    due_at: datetime | None
    assigned_to_user_id: uuid.UUID | None
    created_at: datetime


class WorkItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    pipeline_id: uuid.UUID
    stage_id: uuid.UUID
    work_item_type: str
    title: str
    description: str | None
    primary_party_id: uuid.UUID | None
    status: WorkItemStatus
    amount: Decimal | None
    currency: str | None
    source: str | None
    custom_fields: dict[str, Any] = Field(default_factory=dict)
    participants: list[WorkItemParticipantResponse] = Field(default_factory=list)
    activities: list[ActivityResponse] = Field(default_factory=list)
    tasks: list[TaskResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    created_by_user_id: uuid.UUID | None
    updated_by_user_id: uuid.UUID | None
