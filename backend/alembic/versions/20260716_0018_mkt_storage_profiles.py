"""M8-C2a: storage resource profiles + media validation fields.

Revision ID: 0018_mkt_storage_profiles
Revises: 0017_mkt_secret_binding
Create Date: 2026-07-16

Local/schema readiness only. Do not run against production without separate approval.
Revision ID kept <= 32 chars for alembic_version.version_num (VARCHAR(32)).
Does not auto-create profiles for tenants.

Enum storage convention (matches ORM / existing PostgreSQL smoke evidence):
SQLAlchemy Enum NAME storage — uppercase member names, not lowercase `.value`.

Cardinality (HQ hardening):
- at most one ACTIVE profile per (tenant_id, mode);
- Mode A + Mode B may be ACTIVE simultaneously;
- at most one is_default=true per tenant;
- default requires ACTIVE;
- ACTIVE client_bucket forbidden.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0018_mkt_storage_profiles"
down_revision: Union[str, None] = "0017_mkt_secret_binding"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "marketing_storage_resource_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column(
            "mode",
            sa.Enum(
                "FLEXITY_MANAGED",
                "CLIENT_PUBLIC_URL",
                "CLIENT_BUCKET",
                name="marketing_storage_resource_mode",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "ACTIVE",
                "DISABLED",
                name="marketing_storage_profile_status",
                native_enum=False,
            ),
            nullable=False,
            server_default="DISABLED",
        ),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("max_upload_bytes", sa.BigInteger(), nullable=True),
        sa.Column("max_url_length", sa.Integer(), nullable=True),
        sa.Column("allowed_mime_types", sa.JSON(), nullable=True),
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
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            "mode IN ('FLEXITY_MANAGED','CLIENT_PUBLIC_URL','CLIENT_BUCKET')",
            name="ck_marketing_storage_profile_mode_values",
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE','DISABLED')",
            name="ck_marketing_storage_profile_status_values",
        ),
        sa.CheckConstraint(
            "(is_default IS FALSE) OR (status = 'ACTIVE')",
            name="ck_marketing_storage_profile_default_requires_active",
        ),
        sa.CheckConstraint(
            "NOT (status = 'ACTIVE' AND mode = 'CLIENT_BUCKET')",
            name="ck_marketing_storage_profile_no_active_client_bucket",
        ),
        sa.CheckConstraint(
            "max_upload_bytes IS NULL OR (max_upload_bytes > 0 AND max_upload_bytes <= 52428800)",
            name="ck_marketing_storage_profile_max_upload_bytes",
        ),
        sa.CheckConstraint(
            "max_url_length IS NULL OR (max_url_length > 0 AND max_url_length <= 2048)",
            name="ck_marketing_storage_profile_max_url_length",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_marketing_storage_profiles_tenant",
        "marketing_storage_resource_profiles",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_marketing_storage_resource_profiles_tenant_id"),
        "marketing_storage_resource_profiles",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_marketing_storage_resource_profiles_status"),
        "marketing_storage_resource_profiles",
        ["status"],
        unique=False,
    )
    op.create_index(
        "uq_marketing_storage_profile_tenant_mode_active",
        "marketing_storage_resource_profiles",
        ["tenant_id", "mode"],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE'"),
        sqlite_where=sa.text("status = 'ACTIVE'"),
    )
    op.create_index(
        "uq_marketing_storage_profile_tenant_default",
        "marketing_storage_resource_profiles",
        ["tenant_id"],
        unique=True,
        postgresql_where=sa.text("is_default IS TRUE"),
        sqlite_where=sa.text("is_default IS TRUE"),
    )

    op.add_column(
        "marketing_media_assets",
        sa.Column(
            "validation_status",
            sa.Enum(
                "LEGACY_UNVERIFIED",
                "REGISTERED_UNVERIFIED",
                "VALIDATED_METADATA",
                "REJECTED",
                "ARCHIVED",
                name="marketing_media_validation_status",
                native_enum=False,
            ),
            nullable=False,
            server_default="LEGACY_UNVERIFIED",
        ),
    )
    op.add_column(
        "marketing_media_assets",
        sa.Column("declared_mime_type", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "marketing_media_assets",
        sa.Column("declared_size_bytes", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "marketing_media_assets",
        sa.Column("verified_mime_type", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "marketing_media_assets",
        sa.Column("verified_size_bytes", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "marketing_media_assets",
        sa.Column("storage_profile_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "marketing_media_assets",
        sa.Column(
            "resource_mode",
            sa.Enum(
                "FLEXITY_MANAGED",
                "CLIENT_PUBLIC_URL",
                "CLIENT_BUCKET",
                name="marketing_media_resource_mode",
                native_enum=False,
            ),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_marketing_media_assets_storage_profile_id",
        "marketing_media_assets",
        "marketing_storage_resource_profiles",
        ["storage_profile_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_marketing_media_assets_storage_profile_id"),
        "marketing_media_assets",
        ["storage_profile_id"],
        unique=False,
    )
    op.create_check_constraint(
        "ck_marketing_media_validation_status_values",
        "marketing_media_assets",
        "validation_status IN ("
        "'LEGACY_UNVERIFIED','REGISTERED_UNVERIFIED','VALIDATED_METADATA',"
        "'REJECTED','ARCHIVED')",
    )
    op.create_check_constraint(
        "ck_marketing_media_resource_mode_values",
        "marketing_media_assets",
        "resource_mode IS NULL OR resource_mode IN ("
        "'FLEXITY_MANAGED','CLIENT_PUBLIC_URL','CLIENT_BUCKET')",
    )
    op.create_check_constraint(
        "ck_marketing_media_declared_size_nonneg",
        "marketing_media_assets",
        "declared_size_bytes IS NULL OR declared_size_bytes >= 0",
    )
    op.create_check_constraint(
        "ck_marketing_media_verified_size_nonneg",
        "marketing_media_assets",
        "verified_size_bytes IS NULL OR verified_size_bytes >= 0",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_marketing_media_verified_size_nonneg",
        "marketing_media_assets",
        type_="check",
    )
    op.drop_constraint(
        "ck_marketing_media_declared_size_nonneg",
        "marketing_media_assets",
        type_="check",
    )
    op.drop_constraint(
        "ck_marketing_media_resource_mode_values",
        "marketing_media_assets",
        type_="check",
    )
    op.drop_constraint(
        "ck_marketing_media_validation_status_values",
        "marketing_media_assets",
        type_="check",
    )
    op.drop_index(
        op.f("ix_marketing_media_assets_storage_profile_id"),
        table_name="marketing_media_assets",
    )
    op.drop_constraint(
        "fk_marketing_media_assets_storage_profile_id",
        "marketing_media_assets",
        type_="foreignkey",
    )
    op.drop_column("marketing_media_assets", "resource_mode")
    op.drop_column("marketing_media_assets", "storage_profile_id")
    op.drop_column("marketing_media_assets", "verified_size_bytes")
    op.drop_column("marketing_media_assets", "verified_mime_type")
    op.drop_column("marketing_media_assets", "declared_size_bytes")
    op.drop_column("marketing_media_assets", "declared_mime_type")
    op.drop_column("marketing_media_assets", "validation_status")

    op.drop_index(
        "uq_marketing_storage_profile_tenant_default",
        table_name="marketing_storage_resource_profiles",
    )
    op.drop_index(
        "uq_marketing_storage_profile_tenant_mode_active",
        table_name="marketing_storage_resource_profiles",
    )
    op.drop_index(
        op.f("ix_marketing_storage_resource_profiles_status"),
        table_name="marketing_storage_resource_profiles",
    )
    op.drop_index(
        op.f("ix_marketing_storage_resource_profiles_tenant_id"),
        table_name="marketing_storage_resource_profiles",
    )
    op.drop_index(
        "ix_marketing_storage_profiles_tenant",
        table_name="marketing_storage_resource_profiles",
    )
    op.drop_table("marketing_storage_resource_profiles")

    for enum_name in (
        "marketing_media_resource_mode",
        "marketing_media_validation_status",
        "marketing_storage_profile_status",
        "marketing_storage_resource_mode",
    ):
        sa.Enum(name=enum_name).drop(op.get_bind(), checkfirst=True)
