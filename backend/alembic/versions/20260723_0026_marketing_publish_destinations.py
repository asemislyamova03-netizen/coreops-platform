"""M8-D1: marketing publish destinations allow-list table.

Revision ID: 0026_mkt_publish_destinations
Revises: 0025_secret_envelope_versions
Create Date: 2026-07-23

Local/schema readiness only. Do not run against production without separate approval.
Revision ID kept <= 32 chars for alembic_version.version_num (VARCHAR(32)).
(HQ label was 0026_marketing_publish_destinations — shortened to fit 32.)

Enum storage convention (matches M8-C2a / ORM):
SQLAlchemy Enum NAME storage — uppercase member names, not lowercase `.value`.

HQ locks encoded here:
- tenant_id FK ON DELETE RESTRICT (no CASCADE on destinations)
- composite FK (tenant_id, publishing_connection_id) → connections (tenant_id, id)
  ON DELETE RESTRICT (SoT; no separate single-column connection FK)
- UNIQUE (tenant_id, id) on marketing_publishing_connections (added here only)
- identity_locked_at for monotonic external_id lock after first VALID
- partial unique among non-archived destinations
- lifecycle enabled/disabled/archived (no hard delete)
- validation unchecked/valid/invalid/unavailable
- TikTok type reserved in CHECK; capability disabled in application code
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0026_mkt_publish_destinations"
down_revision: Union[str, None] = "0025_secret_envelope_versions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_marketing_publishing_conn_tenant_id_id",
        "marketing_publishing_connections",
        ["tenant_id", "id"],
    )
    op.create_table(
        "marketing_publish_destinations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("publishing_connection_id", sa.Uuid(), nullable=False),
        sa.Column(
            "provider",
            sa.Enum(
                "TELEGRAM",
                "INSTAGRAM",
                "THREADS",
                "TIKTOK",
                name="marketing_publish_destination_provider",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "destination_type",
            sa.Enum(
                "TELEGRAM_CHAT",
                "INSTAGRAM_USER",
                "THREADS_USER",
                "TIKTOK_USER",
                name="marketing_publish_destination_type",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "ENABLED",
                "DISABLED",
                "ARCHIVED",
                name="marketing_destination_status",
                native_enum=False,
            ),
            nullable=False,
            server_default="ENABLED",
        ),
        sa.Column(
            "validation_status",
            sa.Enum(
                "UNCHECKED",
                "VALID",
                "INVALID",
                "UNAVAILABLE",
                name="marketing_destination_validation_status",
                native_enum=False,
            ),
            nullable=False,
            server_default="UNCHECKED",
        ),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("validation_error_code", sa.String(length=64), nullable=True),
        sa.Column("identity_locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("updated_by_user_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            ondelete="RESTRICT",
            name="fk_mkt_publish_dest_tenant",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "publishing_connection_id"],
            ["marketing_publishing_connections.tenant_id", "marketing_publishing_connections.id"],
            ondelete="RESTRICT",
            name="fk_mkt_publish_dest_tenant_connection",
        ),
        sa.CheckConstraint(
            "status IN ('ENABLED','DISABLED','ARCHIVED')",
            name="ck_mkt_publish_dest_status_values",
        ),
        sa.CheckConstraint(
            "validation_status IN ('UNCHECKED','VALID','INVALID','UNAVAILABLE')",
            name="ck_mkt_publish_dest_validation_status_values",
        ),
        sa.CheckConstraint(
            "destination_type IN ("
            "'TELEGRAM_CHAT','INSTAGRAM_USER','THREADS_USER','TIKTOK_USER')",
            name="ck_mkt_publish_dest_type_values",
        ),
        sa.CheckConstraint(
            "provider IN ('TELEGRAM','INSTAGRAM','THREADS','TIKTOK')",
            name="ck_mkt_publish_dest_provider_values",
        ),
        sa.CheckConstraint(
            "trim(external_id) <> ''",
            name="ck_mkt_publish_dest_external_id_nonempty",
        ),
        sa.CheckConstraint(
            "trim(display_name) <> ''",
            name="ck_mkt_publish_dest_display_name_nonempty",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_marketing_publish_destinations_tenant_id"),
        "marketing_publish_destinations",
        ["tenant_id"],
    )
    op.create_index(
        op.f("ix_marketing_publish_destinations_publishing_connection_id"),
        "marketing_publish_destinations",
        ["publishing_connection_id"],
    )
    op.create_index(
        op.f("ix_marketing_publish_destinations_status"),
        "marketing_publish_destinations",
        ["status"],
    )
    op.create_index(
        "ix_marketing_publish_destinations_tenant_status",
        "marketing_publish_destinations",
        ["tenant_id", "status"],
    )
    op.create_index(
        "ix_marketing_publish_destinations_tenant_connection",
        "marketing_publish_destinations",
        ["tenant_id", "publishing_connection_id"],
    )
    op.create_index(
        "uq_mkt_publish_dest_active_identity",
        "marketing_publish_destinations",
        ["tenant_id", "publishing_connection_id", "destination_type", "external_id"],
        unique=True,
        postgresql_where=sa.text("status <> 'ARCHIVED'"),
        sqlite_where=sa.text("status <> 'ARCHIVED'"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_mkt_publish_dest_active_identity",
        table_name="marketing_publish_destinations",
    )
    op.drop_index(
        "ix_marketing_publish_destinations_tenant_connection",
        table_name="marketing_publish_destinations",
    )
    op.drop_index(
        "ix_marketing_publish_destinations_tenant_status",
        table_name="marketing_publish_destinations",
    )
    op.drop_index(
        op.f("ix_marketing_publish_destinations_status"),
        table_name="marketing_publish_destinations",
    )
    op.drop_index(
        op.f("ix_marketing_publish_destinations_publishing_connection_id"),
        table_name="marketing_publish_destinations",
    )
    op.drop_index(
        op.f("ix_marketing_publish_destinations_tenant_id"),
        table_name="marketing_publish_destinations",
    )
    op.drop_table("marketing_publish_destinations")
    for enum_name in (
        "marketing_destination_validation_status",
        "marketing_destination_status",
        "marketing_publish_destination_type",
        "marketing_publish_destination_provider",
    ):
        sa.Enum(name=enum_name).drop(op.get_bind(), checkfirst=True)
    op.drop_constraint(
        "uq_marketing_publishing_conn_tenant_id_id",
        "marketing_publishing_connections",
        type_="unique",
    )
