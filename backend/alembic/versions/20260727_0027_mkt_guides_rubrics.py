"""M7.5-A: marketing guides + tenant rubric directory.

Revision ID: 0027_mkt_guides_rubrics
Revises: 0026_mkt_publish_destinations
Create Date: 2026-07-27

Additive only. Does not alter marketing_content_topics / packs.
Local/schema readiness — no production migrate without separate approval.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0027_mkt_guides_rubrics"
down_revision: Union[str, None] = "0026_mkt_publish_destinations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "marketing_guides",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "draft",
                "active",
                "superseded",
                name="marketing_guide_status",
                native_enum=False,
            ),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("business_name", sa.String(length=255), nullable=False),
        sa.Column("business_summary", sa.Text(), nullable=False),
        sa.Column("products_services", sa.Text(), nullable=False),
        sa.Column("audiences", sa.Text(), nullable=False),
        sa.Column("goals", sa.Text(), nullable=False),
        sa.Column("channels", sa.JSON(), nullable=False),
        sa.Column("default_frequency", sa.String(length=64), nullable=False),
        sa.Column("tone_rules", sa.Text(), nullable=True),
        sa.Column("constraints", sa.Text(), nullable=True),
        sa.Column("sources_notes", sa.Text(), nullable=True),
        sa.Column("extra_json", sa.JSON(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("updated_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "version",
            name="uq_marketing_guides_tenant_version",
        ),
    )
    op.create_index(
        op.f("ix_marketing_guides_tenant_id"),
        "marketing_guides",
        ["tenant_id"],
    )
    op.create_index(
        "ix_marketing_guides_tenant_status",
        "marketing_guides",
        ["tenant_id", "status"],
    )
    op.create_index(
        "uq_marketing_guides_tenant_active",
        "marketing_guides",
        ["tenant_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
        sqlite_where=sa.text("status = 'active'"),
    )

    op.create_table(
        "marketing_rubrics",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("content_instructions", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "active",
                "inactive",
                "archived",
                name="marketing_rubric_status",
                native_enum=False,
            ),
            nullable=False,
            server_default="active",
        ),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("updated_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "code",
            name="uq_marketing_rubrics_tenant_code",
        ),
    )
    op.create_index(
        op.f("ix_marketing_rubrics_tenant_id"),
        "marketing_rubrics",
        ["tenant_id"],
    )
    op.create_index(
        "ix_marketing_rubrics_tenant_status",
        "marketing_rubrics",
        ["tenant_id", "status"],
    )
    op.create_index(
        "ix_marketing_rubrics_tenant_sort",
        "marketing_rubrics",
        ["tenant_id", "sort_order"],
    )


def downgrade() -> None:
    op.drop_index("ix_marketing_rubrics_tenant_sort", table_name="marketing_rubrics")
    op.drop_index("ix_marketing_rubrics_tenant_status", table_name="marketing_rubrics")
    op.drop_index(op.f("ix_marketing_rubrics_tenant_id"), table_name="marketing_rubrics")
    op.drop_table("marketing_rubrics")
    op.drop_index("uq_marketing_guides_tenant_active", table_name="marketing_guides")
    op.drop_index("ix_marketing_guides_tenant_status", table_name="marketing_guides")
    op.drop_index(op.f("ix_marketing_guides_tenant_id"), table_name="marketing_guides")
    op.drop_table("marketing_guides")
    for enum_name in ("marketing_rubric_status", "marketing_guide_status"):
        sa.Enum(name=enum_name).drop(op.get_bind(), checkfirst=True)
