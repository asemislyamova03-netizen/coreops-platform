"""E1a: Process Overlay config and versioning skeleton.

Revision ID: 0019_process_overlay_e1a
Revises: 0015_marketing_cabinet_mvp
Create Date: 2026-07-17

Local/schema readiness only. Does not auto-create tenant configurations.
Does not activate overlay. Does not modify CRM/workflow tables.
Revision ID kept <= 32 chars for alembic_version.version_num (VARCHAR(32)).

Active version ownership:
- composite FK (tenant_process_configurations.id, active_definition_version_id)
  -> (process_definition_versions.tenant_process_configuration_id, id)
  ON DELETE RESTRICT
- added after both tables exist (avoids circular create without use_alter on raw SQL)
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0019_process_overlay_e1a"
down_revision: Union[str, None] = "0015_marketing_cabinet_mvp"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "process_templates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("default_pipeline_code", sa.String(length=64), nullable=False),
        sa.Column("default_policy_blueprint_json", sa.JSON(), nullable=False),
        sa.Column("required_module_codes_json", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_process_template_code"),
    )
    op.create_index(op.f("ix_process_templates_code"), "process_templates", ["code"], unique=True)

    op.create_table(
        "tenant_process_configurations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("process_template_id", sa.Uuid(), nullable=False),
        sa.Column("pipeline_id", sa.Uuid(), nullable=False),
        sa.Column(
            "activation_state",
            sa.Enum(
                "inactive",
                "active",
                name="process_overlay_activation_state",
                native_enum=False,
            ),
            nullable=False,
            server_default="inactive",
        ),
        sa.Column("active_definition_version_id", sa.Uuid(), nullable=True),
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
        sa.ForeignKeyConstraint(["pipeline_id"], ["pipelines.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["process_template_id"], ["process_templates.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "process_template_id",
            name="uq_tenant_process_config_tenant_template",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "pipeline_id",
            name="uq_tenant_process_config_tenant_pipeline",
        ),
    )
    op.create_index(
        op.f("ix_tenant_process_configurations_pipeline_id"),
        "tenant_process_configurations",
        ["pipeline_id"],
    )
    op.create_index(
        op.f("ix_tenant_process_configurations_process_template_id"),
        "tenant_process_configurations",
        ["process_template_id"],
    )
    op.create_index(
        op.f("ix_tenant_process_configurations_tenant_id"),
        "tenant_process_configurations",
        ["tenant_id"],
    )
    op.create_index(
        op.f("ix_tenant_process_configurations_active_definition_version_id"),
        "tenant_process_configurations",
        ["active_definition_version_id"],
    )

    op.create_table(
        "process_definition_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_process_configuration_id", sa.Uuid(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("pipeline_id", sa.Uuid(), nullable=False),
        sa.Column("pipeline_code", sa.String(length=64), nullable=False),
        sa.Column("stage_codes_json", sa.JSON(), nullable=False),
        sa.Column("policy_snapshot_json", sa.JSON(), nullable=False),
        sa.Column("module_requirements_json", sa.JSON(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("publish_reason", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["pipeline_id"], ["pipelines.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_process_configuration_id"],
            ["tenant_process_configurations.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_process_configuration_id",
            "version_number",
            name="uq_process_def_version_config_number",
        ),
        sa.UniqueConstraint(
            "tenant_process_configuration_id",
            "id",
            name="uq_process_def_version_config_id",
        ),
        sa.CheckConstraint("version_number > 0", name="ck_process_def_version_number_positive"),
        sa.CheckConstraint(
            "length(trim(publish_reason)) > 0",
            name="ck_process_def_version_publish_reason_nonempty",
        ),
    )
    op.create_index(
        op.f("ix_process_definition_versions_pipeline_id"),
        "process_definition_versions",
        ["pipeline_id"],
    )
    op.create_index(
        op.f("ix_process_definition_versions_tenant_id"),
        "process_definition_versions",
        ["tenant_id"],
    )
    op.create_index(
        op.f("ix_process_definition_versions_tenant_process_configuration_id"),
        "process_definition_versions",
        ["tenant_process_configuration_id"],
    )

    op.create_foreign_key(
        "fk_tenant_process_config_active_version",
        "tenant_process_configurations",
        "process_definition_versions",
        ["id", "active_definition_version_id"],
        ["tenant_process_configuration_id", "id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_tenant_process_config_active_version",
        "tenant_process_configurations",
        type_="foreignkey",
    )
    op.drop_index(
        op.f("ix_process_definition_versions_tenant_process_configuration_id"),
        table_name="process_definition_versions",
    )
    op.drop_index(
        op.f("ix_process_definition_versions_tenant_id"),
        table_name="process_definition_versions",
    )
    op.drop_index(
        op.f("ix_process_definition_versions_pipeline_id"),
        table_name="process_definition_versions",
    )
    op.drop_table("process_definition_versions")

    op.drop_index(
        op.f("ix_tenant_process_configurations_active_definition_version_id"),
        table_name="tenant_process_configurations",
    )
    op.drop_index(
        op.f("ix_tenant_process_configurations_tenant_id"),
        table_name="tenant_process_configurations",
    )
    op.drop_index(
        op.f("ix_tenant_process_configurations_process_template_id"),
        table_name="tenant_process_configurations",
    )
    op.drop_index(
        op.f("ix_tenant_process_configurations_pipeline_id"),
        table_name="tenant_process_configurations",
    )
    op.drop_table("tenant_process_configurations")

    op.drop_index(op.f("ix_process_templates_code"), table_name="process_templates")
    op.drop_table("process_templates")

    sa.Enum(name="process_overlay_activation_state").drop(op.get_bind(), checkfirst=True)
