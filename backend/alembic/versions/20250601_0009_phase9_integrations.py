"""Phase 9: integrations foundation

Revision ID: 0009_phase9
Revises: 0008_phase8
Create Date: 2025-06-01

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0009_phase9"
down_revision: Union[str, None] = "0008_phase8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "integration_providers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("provider_type", sa.String(length=32), nullable=False),
        sa.Column("supported_modules_json", sa.JSON(), nullable=False),
        sa.Column("capabilities_json", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index(op.f("ix_integration_providers_code"), "integration_providers", ["code"])

    op.create_table(
        "integration_connections",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("provider_code", sa.String(length=64), nullable=False),
        sa.Column("module_code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "status",
            sa.Enum("pending", "active", "error", "disconnected", name="integration_connection_status", native_enum=False),
            nullable=False,
        ),
        sa.Column("credentials_json", sa.JSON(), nullable=False),
        sa.Column("settings_json", sa.JSON(), nullable=False),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "provider_code",
            "module_code",
            name="uq_integration_connection_tenant_provider_module",
        ),
    )
    op.create_index(op.f("ix_integration_connections_module_code"), "integration_connections", ["module_code"])
    op.create_index(op.f("ix_integration_connections_provider_code"), "integration_connections", ["provider_code"])
    op.create_index(op.f("ix_integration_connections_status"), "integration_connections", ["status"])
    op.create_index(op.f("ix_integration_connections_tenant_id"), "integration_connections", ["tenant_id"])

    op.create_table(
        "external_references",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("connection_id", sa.Uuid(), nullable=True),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("provider_code", sa.String(length=64), nullable=False),
        sa.Column("external_entity_type", sa.String(length=64), nullable=False),
        sa.Column("external_id", sa.String(length=128), nullable=False),
        sa.Column("external_url", sa.String(length=512), nullable=True),
        sa.Column(
            "sync_status",
            sa.Enum("pending", "linked", "synced", "error", name="external_sync_status", native_enum=False),
            nullable=False,
        ),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["connection_id"], ["integration_connections.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "entity_type",
            "entity_id",
            "provider_code",
            name="uq_external_ref_tenant_entity_provider",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "provider_code",
            "external_entity_type",
            "external_id",
            name="uq_external_ref_tenant_external_id",
        ),
    )
    op.create_index(op.f("ix_external_references_entity_id"), "external_references", ["entity_id"])
    op.create_index(op.f("ix_external_references_entity_type"), "external_references", ["entity_type"])
    op.create_index(op.f("ix_external_references_provider_code"), "external_references", ["provider_code"])
    op.create_index(op.f("ix_external_references_tenant_id"), "external_references", ["tenant_id"])

    op.create_table(
        "sync_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("connection_id", sa.Uuid(), nullable=False),
        sa.Column(
            "job_type",
            sa.Enum("test", "full_sync", "incremental", name="sync_job_type", native_enum=False),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum("queued", "running", "completed", "failed", "cancelled", name="sync_job_status", native_enum=False),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stats_json", sa.JSON(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["connection_id"], ["integration_connections.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_sync_jobs_connection_id"), "sync_jobs", ["connection_id"])
    op.create_index(op.f("ix_sync_jobs_status"), "sync_jobs", ["status"])
    op.create_index(op.f("ix_sync_jobs_tenant_id"), "sync_jobs", ["tenant_id"])

    op.create_table(
        "sync_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("connection_id", sa.Uuid(), nullable=False),
        sa.Column(
            "level",
            sa.Enum("info", "warning", "error", name="sync_log_level", native_enum=False),
            nullable=False,
        ),
        sa.Column("message", sa.String(length=512), nullable=False),
        sa.Column("details_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["connection_id"], ["integration_connections.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_id"], ["sync_jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_sync_logs_connection_id"), "sync_logs", ["connection_id"])
    op.create_index(op.f("ix_sync_logs_job_id"), "sync_logs", ["job_id"])
    op.create_index(op.f("ix_sync_logs_tenant_id"), "sync_logs", ["tenant_id"])

    op.create_table(
        "webhook_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=True),
        sa.Column("connection_id", sa.Uuid(), nullable=True),
        sa.Column("provider_code", sa.String(length=64), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["connection_id"], ["integration_connections.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_webhook_events_provider_code"), "webhook_events", ["provider_code"])
    op.create_index(op.f("ix_webhook_events_tenant_id"), "webhook_events", ["tenant_id"])


def downgrade() -> None:
    op.drop_table("webhook_events")
    op.drop_table("sync_logs")
    op.drop_table("sync_jobs")
    op.drop_table("external_references")
    op.drop_table("integration_connections")
    op.drop_table("integration_providers")
