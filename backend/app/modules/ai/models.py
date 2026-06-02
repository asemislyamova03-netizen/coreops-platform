import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.enums import (
    AIActionProposalStatus,
    AIActionType,
    AIApprovalDecision,
    AITaskStatus,
)
from app.core.models import AuditUserMixin, TimestampMixin, UUIDPrimaryKeyMixin


class AIAgent(Base, UUIDPrimaryKeyMixin, TimestampMixin, AuditUserMixin):
    __tablename__ = "ai_agents"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_ai_agent_tenant_code"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role_code: Mapped[str] = mapped_column(String(64), default="assistant", nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    system_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    config_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    requires_approval_for_critical: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class AITask(Base, UUIDPrimaryKeyMixin, TimestampMixin, AuditUserMixin):
    __tablename__ = "ai_tasks"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("ai_agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    task_type: Mapped[str] = mapped_column(String(64), default="general", nullable=False)
    status: Mapped[AITaskStatus] = mapped_column(
        Enum(AITaskStatus, name="ai_task_status", native_enum=False),
        default=AITaskStatus.PENDING,
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    input_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    output_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    context_entity_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    context_entity_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    agent: Mapped["AIAgent"] = relationship("AIAgent", lazy="joined")
    proposals: Mapped[list["AIActionProposal"]] = relationship(
        "AIActionProposal",
        back_populates="task",
        lazy="selectin",
    )


class AIActionProposal(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "ai_action_proposals"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("ai_agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    task_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("ai_tasks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action_type: Mapped[AIActionType] = mapped_column(
        Enum(AIActionType, name="ai_action_type", native_enum=False),
        nullable=False,
        index=True,
    )
    status: Mapped[AIActionProposalStatus] = mapped_column(
        Enum(AIActionProposalStatus, name="ai_action_proposal_status", native_enum=False),
        default=AIActionProposalStatus.PENDING,
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    target_entity_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    target_entity_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    is_critical: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    execution_result_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    task: Mapped["AITask | None"] = relationship("AITask", back_populates="proposals")
    approvals: Mapped[list["AIApproval"]] = relationship(
        "AIApproval",
        back_populates="proposal",
        lazy="selectin",
        cascade="all, delete-orphan",
    )


class AIApproval(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "ai_approvals"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    proposal_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("ai_action_proposals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    approver_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    decision: Mapped[AIApprovalDecision] = mapped_column(
        Enum(AIApprovalDecision, name="ai_approval_decision", native_enum=False),
        nullable=False,
    )
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    proposal: Mapped["AIActionProposal"] = relationship(
        "AIActionProposal",
        back_populates="approvals",
    )


class AIUsageEvent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "ai_usage_events"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("ai_agents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    task_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("ai_tasks.id", ondelete="SET NULL"),
        nullable=True,
    )
    proposal_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("ai_action_proposals.id", ondelete="SET NULL"),
        nullable=True,
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cost_units: Mapped[float] = mapped_column(Numeric(18, 4), default=0, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
