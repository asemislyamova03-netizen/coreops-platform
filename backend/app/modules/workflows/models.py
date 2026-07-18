import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.enums import (
    ActivityType,
    ReminderStatus,
    TaskStatus,
    WorkItemParticipantRole,
    WorkItemStatus,
)
from app.core.models import AuditUserMixin, TimestampMixin, UUIDPrimaryKeyMixin

ENTITY_WORK_ITEM = "work_item"


class Pipeline(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "pipelines"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_pipeline_tenant_code"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), default="work_item", nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    stages: Mapped[list["PipelineStage"]] = relationship(
        "PipelineStage",
        back_populates="pipeline",
        lazy="selectin",
        order_by="PipelineStage.sort_order",
    )


class PipelineStage(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "pipeline_stages"
    __table_args__ = (
        UniqueConstraint("pipeline_id", "code", name="uq_pipeline_stage_code"),
    )

    pipeline_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("pipelines.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_terminal: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    pipeline: Mapped["Pipeline"] = relationship("Pipeline", back_populates="stages")
    work_items: Mapped[list["WorkItem"]] = relationship("WorkItem", back_populates="stage")


class WorkItem(Base, UUIDPrimaryKeyMixin, TimestampMixin, AuditUserMixin):
    __tablename__ = "work_items"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pipeline_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("pipelines.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    stage_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("pipeline_stages.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    work_item_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    primary_party_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("parties.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[WorkItemStatus] = mapped_column(
        Enum(WorkItemStatus, name="work_item_status", native_enum=False),
        default=WorkItemStatus.OPEN,
        nullable=False,
        index=True,
    )
    amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    source: Mapped[str | None] = mapped_column(String(128), nullable=True)
    custom_fields_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    pipeline: Mapped["Pipeline"] = relationship("Pipeline")
    stage: Mapped["PipelineStage"] = relationship("PipelineStage", back_populates="work_items")
    participants: Mapped[list["WorkItemParticipant"]] = relationship(
        "WorkItemParticipant",
        back_populates="work_item",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    activities: Mapped[list["Activity"]] = relationship(
        "Activity",
        back_populates="work_item",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    tasks: Mapped[list["Task"]] = relationship(
        "Task",
        back_populates="work_item",
        lazy="selectin",
        cascade="all, delete-orphan",
    )


class WorkItemParticipant(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "work_item_participants"
    __table_args__ = (
        UniqueConstraint("work_item_id", "party_id", "role", name="uq_work_item_party_role"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    work_item_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("work_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    party_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("parties.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[WorkItemParticipantRole] = mapped_column(
        Enum(WorkItemParticipantRole, name="work_item_participant_role", native_enum=False),
        default=WorkItemParticipantRole.CLIENT,
        nullable=False,
    )

    work_item: Mapped["WorkItem"] = relationship("WorkItem", back_populates="participants")


class Activity(Base, UUIDPrimaryKeyMixin, TimestampMixin, AuditUserMixin):
    __tablename__ = "activities"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    work_item_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("work_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    activity_type: Mapped[ActivityType] = mapped_column(
        Enum(ActivityType, name="activity_type", native_enum=False),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    work_item: Mapped["WorkItem"] = relationship("WorkItem", back_populates="activities")


class Note(Base, UUIDPrimaryKeyMixin, TimestampMixin, AuditUserMixin):
    __tablename__ = "notes"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    work_item_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("work_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)


class Task(Base, UUIDPrimaryKeyMixin, TimestampMixin, AuditUserMixin):
    __tablename__ = "tasks"
    __table_args__ = (
        CheckConstraint(
            "("
            " (process_run_id IS NULL AND automation_key IS NULL)"
            " OR "
            " (process_run_id IS NOT NULL AND automation_key IS NOT NULL)"
            ")",
            name="ck_tasks_process_run_automation_key_pair",
        ),
        Index(
            "uq_tasks_tenant_process_run_automation_key",
            "tenant_id",
            "process_run_id",
            "automation_key",
            unique=True,
            postgresql_where=text(
                "process_run_id IS NOT NULL AND automation_key IS NOT NULL"
            ),
            sqlite_where=text(
                "process_run_id IS NOT NULL AND automation_key IS NOT NULL"
            ),
        ),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    work_item_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("work_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    process_run_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("process_runs.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    automation_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, name="task_status", native_enum=False),
        default=TaskStatus.PENDING,
        nullable=False,
    )
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    assigned_to_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)

    work_item: Mapped["WorkItem"] = relationship("WorkItem", back_populates="tasks")


class Reminder(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "reminders"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    work_item_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("work_items.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    task_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    remind_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[ReminderStatus] = mapped_column(
        Enum(ReminderStatus, name="reminder_status", native_enum=False),
        default=ReminderStatus.SCHEDULED,
        nullable=False,
    )
    message: Mapped[str | None] = mapped_column(String(500), nullable=True)
