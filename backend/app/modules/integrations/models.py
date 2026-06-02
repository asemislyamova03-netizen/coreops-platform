import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.enums import (
    ExternalSyncStatus,
    IntegrationConnectionStatus,
    SyncJobStatus,
    SyncJobType,
    SyncLogLevel,
)
from app.core.models import TimestampMixin, UUIDPrimaryKeyMixin


class IntegrationProvider(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "integration_providers"

    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider_type: Mapped[str] = mapped_column(String(32), default="crm", nullable=False)
    supported_modules_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    capabilities_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class IntegrationConnection(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "integration_connections"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "provider_code",
            "module_code",
            name="uq_integration_connection_tenant_provider_module",
        ),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    module_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[IntegrationConnectionStatus] = mapped_column(
        Enum(IntegrationConnectionStatus, name="integration_connection_status", native_enum=False),
        default=IntegrationConnectionStatus.PENDING,
        nullable=False,
        index=True,
    )
    credentials_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    settings_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    sync_jobs: Mapped[list["SyncJob"]] = relationship(
        "SyncJob",
        back_populates="connection",
        lazy="selectin",
    )


class ExternalReference(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "external_references"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "entity_type",
            "entity_id",
            "provider_code",
            name="uq_external_ref_tenant_entity_provider",
        ),
        UniqueConstraint(
            "tenant_id",
            "provider_code",
            "external_entity_type",
            "external_id",
            name="uq_external_ref_tenant_external_id",
        ),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    connection_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("integration_connections.id", ondelete="SET NULL"),
        nullable=True,
    )
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    entity_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    provider_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    external_entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    external_id: Mapped[str] = mapped_column(String(128), nullable=False)
    external_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    sync_status: Mapped[ExternalSyncStatus] = mapped_column(
        Enum(ExternalSyncStatus, name="external_sync_status", native_enum=False),
        default=ExternalSyncStatus.LINKED,
        nullable=False,
    )
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class SyncJob(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "sync_jobs"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    connection_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("integration_connections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_type: Mapped[SyncJobType] = mapped_column(
        Enum(SyncJobType, name="sync_job_type", native_enum=False),
        nullable=False,
    )
    status: Mapped[SyncJobStatus] = mapped_column(
        Enum(SyncJobStatus, name="sync_job_status", native_enum=False),
        default=SyncJobStatus.QUEUED,
        nullable=False,
        index=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    stats_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    connection: Mapped["IntegrationConnection"] = relationship(
        "IntegrationConnection",
        back_populates="sync_jobs",
    )
    logs: Mapped[list["SyncLog"]] = relationship(
        "SyncLog",
        back_populates="job",
        lazy="selectin",
        cascade="all, delete-orphan",
    )


class SyncLog(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "sync_logs"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("sync_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    connection_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("integration_connections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    level: Mapped[SyncLogLevel] = mapped_column(
        Enum(SyncLogLevel, name="sync_log_level", native_enum=False),
        default=SyncLogLevel.INFO,
        nullable=False,
    )
    message: Mapped[str] = mapped_column(String(512), nullable=False)
    details_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    job: Mapped["SyncJob"] = relationship("SyncJob", back_populates="logs")


class WebhookEvent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "webhook_events"

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    connection_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("integration_connections.id", ondelete="SET NULL"),
        nullable=True,
    )
    provider_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), default="unknown", nullable=False)
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="received", nullable=False)
