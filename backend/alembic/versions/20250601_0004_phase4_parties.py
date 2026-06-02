"""Phase 4: parties, contacts, addresses, custom field values

Revision ID: 0004_phase4
Revises: 0003_phase3
Create Date: 2025-06-01

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_phase4"
down_revision: Union[str, None] = "0003_phase3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "parties",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column(
            "party_type",
            sa.Enum("person", "organization", "sole_proprietor", name="party_type", native_enum=False),
            nullable=False,
        ),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column(
            "status",
            sa.Enum("active", "inactive", "archived", name="party_status", native_enum=False),
            nullable=False,
        ),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("updated_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_parties_display_name"), "parties", ["display_name"])
    op.create_index(op.f("ix_parties_tenant_id"), "parties", ["tenant_id"])

    op.create_table(
        "contact_methods",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("party_id", sa.Uuid(), nullable=False),
        sa.Column(
            "method_type",
            sa.Enum(
                "email",
                "phone",
                "mobile",
                "telegram",
                "whatsapp",
                "other",
                name="contact_method_type",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("value", sa.String(length=320), nullable=False),
        sa.Column("label", sa.String(length=128), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["party_id"], ["parties.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_contact_methods_party_id"), "contact_methods", ["party_id"])
    op.create_index(op.f("ix_contact_methods_tenant_id"), "contact_methods", ["tenant_id"])

    op.create_table(
        "addresses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("party_id", sa.Uuid(), nullable=False),
        sa.Column(
            "address_type",
            sa.Enum("legal", "actual", "mailing", "other", name="address_type", native_enum=False),
            nullable=False,
        ),
        sa.Column("country", sa.String(length=2), nullable=True),
        sa.Column("city", sa.String(length=128), nullable=True),
        sa.Column("line1", sa.String(length=255), nullable=True),
        sa.Column("line2", sa.String(length=255), nullable=True),
        sa.Column("postal_code", sa.String(length=32), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["party_id"], ["parties.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_addresses_party_id"), "addresses", ["party_id"])
    op.create_index(op.f("ix_addresses_tenant_id"), "addresses", ["tenant_id"])

    op.create_table(
        "custom_field_values",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("field_key", sa.String(length=64), nullable=False),
        sa.Column("value_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "entity_type",
            "entity_id",
            "field_key",
            name="uq_custom_field_value_entity_key",
        ),
    )
    op.create_index(op.f("ix_custom_field_values_entity_id"), "custom_field_values", ["entity_id"])
    op.create_index(op.f("ix_custom_field_values_entity_type"), "custom_field_values", ["entity_type"])
    op.create_index(op.f("ix_custom_field_values_tenant_id"), "custom_field_values", ["tenant_id"])


def downgrade() -> None:
    op.drop_table("custom_field_values")
    op.drop_table("addresses")
    op.drop_table("contact_methods")
    op.drop_table("parties")
