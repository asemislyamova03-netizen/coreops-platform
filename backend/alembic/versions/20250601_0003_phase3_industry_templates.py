"""Phase 3: industry templates, tenant settings, pipelines, custom fields

Revision ID: 0003_phase3
Revises: 0002_phase2
Create Date: 2025-06-01

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_phase3"
down_revision: Union[str, None] = "0002_phase2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "industry_templates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("default_modules", sa.JSON(), nullable=False),
        sa.Column("default_roles", sa.JSON(), nullable=False),
        sa.Column("default_pipelines", sa.JSON(), nullable=False),
        sa.Column("default_statuses", sa.JSON(), nullable=False),
        sa.Column("default_custom_fields", sa.JSON(), nullable=False),
        sa.Column("default_document_templates", sa.JSON(), nullable=False),
        sa.Column("default_catalog_items", sa.JSON(), nullable=False),
        sa.Column("default_dashboards", sa.JSON(), nullable=False),
        sa.Column("default_ai_agents", sa.JSON(), nullable=False),
        sa.Column("labels_config", sa.JSON(), nullable=False),
        sa.Column("settings_schema", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_industry_templates_code"), "industry_templates", ["code"], unique=True)

    op.create_foreign_key(
        "fk_tenants_industry_template_id",
        "tenants",
        "industry_templates",
        ["industry_template_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "tenant_settings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("labels_config", sa.JSON(), nullable=False),
        sa.Column("industry_config_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id"),
    )

    op.create_table(
        "pipelines",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "code", name="uq_pipeline_tenant_code"),
    )
    op.create_index(op.f("ix_pipelines_tenant_id"), "pipelines", ["tenant_id"])

    op.create_table(
        "pipeline_stages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("pipeline_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("is_terminal", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["pipeline_id"], ["pipelines.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pipeline_id", "code", name="uq_pipeline_stage_code"),
    )
    op.create_index(op.f("ix_pipeline_stages_pipeline_id"), "pipeline_stages", ["pipeline_id"])

    op.create_table(
        "custom_field_definitions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("field_key", sa.String(length=64), nullable=False),
        sa.Column("field_type", sa.String(length=32), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("applies_to_json", sa.JSON(), nullable=False),
        sa.Column("options_json", sa.JSON(), nullable=False),
        sa.Column("is_required", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("source_template_code", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "entity_type",
            "field_key",
            name="uq_custom_field_tenant_entity_key",
        ),
    )
    op.create_index(op.f("ix_custom_field_definitions_entity_type"), "custom_field_definitions", ["entity_type"])
    op.create_index(op.f("ix_custom_field_definitions_tenant_id"), "custom_field_definitions", ["tenant_id"])


def downgrade() -> None:
    op.drop_table("custom_field_definitions")
    op.drop_table("pipeline_stages")
    op.drop_table("pipelines")
    op.drop_table("tenant_settings")
    op.drop_constraint("fk_tenants_industry_template_id", "tenants", type_="foreignkey")
    op.drop_table("industry_templates")
