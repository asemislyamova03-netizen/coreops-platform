"""M8-B: tenant-scoped marketing publishing connections.

Revision ID: 0021_mkt_publishing_conn
Revises: 0020_process_overlay_e1b
Create Date: 2026-07-16

Local/schema readiness only. Do not run against production without separate approval.
Revision ID kept <= 32 chars for alembic_version.version_num (VARCHAR(32)).
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0021_mkt_publishing_conn"
down_revision: Union[str, None] = "0020_process_overlay_e1b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "marketing_publishing_connections",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column(
            "provider",
            sa.Enum(
                "telegram",
                "instagram",
                "threads",
                "tiktok",
                name="marketing_publishing_provider",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("account_display_name", sa.String(length=255), nullable=False),
        sa.Column("account_identifier", sa.String(length=255), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "not_connected",
                "active",
                "error",
                "disabled",
                "expired",
                name="marketing_publishing_connection_status",
                native_enum=False,
            ),
            nullable=False,
            server_default="not_connected",
        ),
        sa.Column(
            "token_status",
            sa.Enum(
                "not_configured",
                "valid",
                "expiring",
                "invalid",
                name="marketing_publishing_token_status",
                native_enum=False,
            ),
            nullable=False,
            server_default="not_configured",
        ),
        sa.Column("secret_ref", sa.String(length=255), nullable=True),
        sa.Column("scopes_json", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_code", sa.String(length=64), nullable=True),
        sa.Column("last_error_message_redacted", sa.String(length=512), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("updated_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            "(status <> 'ACTIVE') OR (account_identifier IS NOT NULL AND trim(account_identifier) <> '')",
            name="ck_marketing_publishing_conn_active_requires_identifier",
        ),
        sa.CheckConstraint(
            "(token_status NOT IN ('VALID','EXPIRING')) OR (secret_ref IS NOT NULL AND trim(secret_ref) <> '')",
            name="ck_marketing_publishing_conn_healthy_requires_secret_ref",
        ),
        sa.CheckConstraint(
            "provider IN ('TELEGRAM','INSTAGRAM','THREADS','TIKTOK')",
            name="ck_marketing_publishing_conn_provider_values",
        ),
        sa.CheckConstraint(
            "status IN ('NOT_CONNECTED','ACTIVE','ERROR','DISABLED','EXPIRED')",
            name="ck_marketing_publishing_conn_status_values",
        ),
        sa.CheckConstraint(
            "token_status IN ('NOT_CONFIGURED','VALID','EXPIRING','INVALID')",
            name="ck_marketing_publishing_conn_token_status_values",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_marketing_publishing_connections_tenant_id"),
        "marketing_publishing_connections",
        ["tenant_id"],
    )
    op.create_index(
        op.f("ix_marketing_publishing_connections_provider"),
        "marketing_publishing_connections",
        ["provider"],
    )
    op.create_index(
        op.f("ix_marketing_publishing_connections_status"),
        "marketing_publishing_connections",
        ["status"],
    )
    op.create_index(
        op.f("ix_marketing_publishing_connections_token_status"),
        "marketing_publishing_connections",
        ["token_status"],
    )
    op.create_index(
        "ix_marketing_publishing_connections_tenant_provider",
        "marketing_publishing_connections",
        ["tenant_id", "provider"],
    )
    op.create_index(
        "ix_marketing_publishing_connections_tenant_status",
        "marketing_publishing_connections",
        ["tenant_id", "status"],
    )
    op.create_index(
        "ix_marketing_publishing_connections_tenant_token_status",
        "marketing_publishing_connections",
        ["tenant_id", "token_status"],
    )
    op.create_index(
        "uq_marketing_publishing_conn_tenant_provider_account",
        "marketing_publishing_connections",
        ["tenant_id", "provider", "account_identifier"],
        unique=True,
        postgresql_where=sa.text("account_identifier IS NOT NULL"),
        sqlite_where=sa.text("account_identifier IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_marketing_publishing_conn_tenant_provider_account",
        table_name="marketing_publishing_connections",
    )
    op.drop_index(
        "ix_marketing_publishing_connections_tenant_token_status",
        table_name="marketing_publishing_connections",
    )
    op.drop_index(
        "ix_marketing_publishing_connections_tenant_status",
        table_name="marketing_publishing_connections",
    )
    op.drop_index(
        "ix_marketing_publishing_connections_tenant_provider",
        table_name="marketing_publishing_connections",
    )
    op.drop_index(
        op.f("ix_marketing_publishing_connections_token_status"),
        table_name="marketing_publishing_connections",
    )
    op.drop_index(
        op.f("ix_marketing_publishing_connections_status"),
        table_name="marketing_publishing_connections",
    )
    op.drop_index(
        op.f("ix_marketing_publishing_connections_provider"),
        table_name="marketing_publishing_connections",
    )
    op.drop_index(
        op.f("ix_marketing_publishing_connections_tenant_id"),
        table_name="marketing_publishing_connections",
    )
    op.drop_table("marketing_publishing_connections")
    for enum_name in (
        "marketing_publishing_token_status",
        "marketing_publishing_connection_status",
        "marketing_publishing_provider",
    ):
        sa.Enum(name=enum_name).drop(op.get_bind(), checkfirst=True)
