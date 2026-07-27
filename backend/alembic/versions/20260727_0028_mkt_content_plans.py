"""M7.5-B: marketing content plans + plan items.

Revision ID: 0028_mkt_content_plans
Revises: 0027_mkt_guides_rubrics
Create Date: 2026-07-27

Additive only. Does not alter packs / topics schema (no plan_item_id on packs).
Local/schema readiness — no production migrate without separate approval.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0028_mkt_content_plans"
down_revision: Union[str, None] = "0027_mkt_guides_rubrics"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "marketing_content_plans",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "draft",
                "approved",
                "archived",
                name="marketing_content_plan_status",
                native_enum=False,
            ),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("guide_id", sa.Uuid(), nullable=True),
        sa.Column("guide_version", sa.Integer(), nullable=True),
        sa.Column(
            "source",
            sa.Enum(
                "manual",
                "json_import",
                name="marketing_content_plan_source",
                native_enum=False,
            ),
            nullable=False,
            server_default="manual",
        ),
        sa.Column("import_fingerprint", sa.String(length=128), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("updated_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "period_start <= period_end",
            name="ck_marketing_content_plans_period",
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["guide_id"],
            ["marketing_guides.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_marketing_content_plans_tenant_id"),
        "marketing_content_plans",
        ["tenant_id"],
    )
    op.create_index(
        "ix_marketing_content_plans_tenant_status",
        "marketing_content_plans",
        ["tenant_id", "status"],
    )
    op.create_index(
        "ix_marketing_content_plans_tenant_period",
        "marketing_content_plans",
        ["tenant_id", "period_start", "period_end"],
    )
    op.create_index(
        "uq_marketing_content_plans_tenant_fingerprint",
        "marketing_content_plans",
        ["tenant_id", "import_fingerprint"],
        unique=True,
        postgresql_where=sa.text("import_fingerprint IS NOT NULL"),
        sqlite_where=sa.text("import_fingerprint IS NOT NULL"),
    )

    op.create_table(
        "marketing_content_plan_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("plan_id", sa.Uuid(), nullable=False),
        sa.Column("planned_date", sa.Date(), nullable=False),
        sa.Column("rubric_id", sa.Uuid(), nullable=False),
        sa.Column("working_title", sa.String(length=512), nullable=False),
        sa.Column("angle", sa.Text(), nullable=True),
        sa.Column("channels", sa.JSON(), nullable=False),
        sa.Column("format", sa.String(length=64), nullable=True),
        sa.Column("goal", sa.Text(), nullable=True),
        sa.Column("audience", sa.Text(), nullable=True),
        sa.Column("cta", sa.Text(), nullable=True),
        sa.Column("pain", sa.Text(), nullable=True),
        sa.Column("insight", sa.Text(), nullable=True),
        sa.Column("funnel_stage", sa.String(length=64), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "draft",
                "approved",
                "topic_created",
                "cancelled",
                name="marketing_content_plan_item_status",
                native_enum=False,
            ),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("topic_id", sa.Uuid(), nullable=True),
        sa.Column("external_line_key", sa.String(length=128), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("updated_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "sort_order >= 0",
            name="ck_marketing_content_plan_items_sort_order",
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["plan_id"],
            ["marketing_content_plans.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["rubric_id"],
            ["marketing_rubrics.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["topic_id"],
            ["marketing_content_topics.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_marketing_content_plan_items_tenant_id"),
        "marketing_content_plan_items",
        ["tenant_id"],
    )
    op.create_index(
        "ix_marketing_content_plan_items_tenant_plan",
        "marketing_content_plan_items",
        ["tenant_id", "plan_id"],
    )
    op.create_index(
        "ix_marketing_content_plan_items_tenant_planned_date",
        "marketing_content_plan_items",
        ["tenant_id", "planned_date"],
    )
    op.create_index(
        "ix_marketing_content_plan_items_order",
        "marketing_content_plan_items",
        ["tenant_id", "plan_id", "planned_date", "sort_order"],
    )
    op.create_index(
        "uq_marketing_content_plan_items_line_key",
        "marketing_content_plan_items",
        ["tenant_id", "plan_id", "external_line_key"],
        unique=True,
        postgresql_where=sa.text("external_line_key IS NOT NULL"),
        sqlite_where=sa.text("external_line_key IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_marketing_content_plan_items_line_key",
        table_name="marketing_content_plan_items",
    )
    op.drop_index(
        "ix_marketing_content_plan_items_order",
        table_name="marketing_content_plan_items",
    )
    op.drop_index(
        "ix_marketing_content_plan_items_tenant_planned_date",
        table_name="marketing_content_plan_items",
    )
    op.drop_index(
        "ix_marketing_content_plan_items_tenant_plan",
        table_name="marketing_content_plan_items",
    )
    op.drop_index(
        op.f("ix_marketing_content_plan_items_tenant_id"),
        table_name="marketing_content_plan_items",
    )
    op.drop_table("marketing_content_plan_items")

    op.drop_index(
        "uq_marketing_content_plans_tenant_fingerprint",
        table_name="marketing_content_plans",
    )
    op.drop_index(
        "ix_marketing_content_plans_tenant_period",
        table_name="marketing_content_plans",
    )
    op.drop_index(
        "ix_marketing_content_plans_tenant_status",
        table_name="marketing_content_plans",
    )
    op.drop_index(
        op.f("ix_marketing_content_plans_tenant_id"),
        table_name="marketing_content_plans",
    )
    op.drop_table("marketing_content_plans")
