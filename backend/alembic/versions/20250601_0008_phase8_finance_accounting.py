"""Phase 8: accounting profiles and finance MVP

Revision ID: 0008_phase8
Revises: 0007_phase7
Create Date: 2025-06-01

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008_phase8"
down_revision: Union[str, None] = "0007_phase7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "legal_entities",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("legal_form", sa.String(length=64), nullable=True),
        sa.Column("country", sa.String(length=2), nullable=False),
        sa.Column("registration_number", sa.String(length=64), nullable=True),
        sa.Column("tax_number", sa.String(length=64), nullable=True),
        sa.Column("residency_status", sa.String(length=32), nullable=True),
        sa.Column("base_currency", sa.String(length=3), nullable=False),
        sa.Column("bank_details_json", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "name", name="uq_legal_entity_tenant_name"),
    )
    op.create_index(op.f("ix_legal_entities_tenant_id"), "legal_entities", ["tenant_id"])

    op.create_table(
        "tax_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("legal_entity_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("country", sa.String(length=2), nullable=False),
        sa.Column(
            "tax_regime",
            sa.Enum("general", "simplified", "patent", "other", name="tax_regime", native_enum=False),
            nullable=False,
        ),
        sa.Column("default_vat_rate", sa.Numeric(5, 2), nullable=True),
        sa.Column("config_json", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["legal_entity_id"], ["legal_entities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "code", name="uq_tax_profile_tenant_code"),
    )
    op.create_index(op.f("ix_tax_profiles_legal_entity_id"), "tax_profiles", ["legal_entity_id"])
    op.create_index(op.f("ix_tax_profiles_tenant_id"), "tax_profiles", ["tenant_id"])

    op.create_table(
        "invoices",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("legal_entity_id", sa.Uuid(), nullable=True),
        sa.Column("tax_profile_id", sa.Uuid(), nullable=True),
        sa.Column("party_id", sa.Uuid(), nullable=False),
        sa.Column("work_item_id", sa.Uuid(), nullable=True),
        sa.Column("document_id", sa.Uuid(), nullable=True),
        sa.Column("invoice_number", sa.String(length=64), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "draft",
                "issued",
                "sent",
                "partial",
                "paid",
                "overdue",
                "cancelled",
                "void",
                name="invoice_status",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("subtotal", sa.Numeric(18, 2), nullable=False),
        sa.Column("tax_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("total", sa.Numeric(18, 2), nullable=False),
        sa.Column("amount_paid", sa.Numeric(18, 2), nullable=False),
        sa.Column("issue_date", sa.Date(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("updated_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["legal_entity_id"], ["legal_entities.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tax_profile_id"], ["tax_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "invoice_number", name="uq_invoice_tenant_number"),
    )
    op.create_index(op.f("ix_invoices_due_date"), "invoices", ["due_date"])
    op.create_index(op.f("ix_invoices_invoice_number"), "invoices", ["invoice_number"])
    op.create_index(op.f("ix_invoices_party_id"), "invoices", ["party_id"])
    op.create_index(op.f("ix_invoices_status"), "invoices", ["status"])
    op.create_index(op.f("ix_invoices_tenant_id"), "invoices", ["tenant_id"])
    op.create_index(op.f("ix_invoices_work_item_id"), "invoices", ["work_item_id"])

    op.create_table(
        "invoice_lines",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("invoice_id", sa.Uuid(), nullable=False),
        sa.Column("catalog_item_id", sa.Uuid(), nullable=True),
        sa.Column("description", sa.String(length=512), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 4), nullable=False),
        sa.Column("unit_price", sa.Numeric(18, 2), nullable=False),
        sa.Column("line_total", sa.Numeric(18, 2), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["catalog_item_id"], ["catalog_items.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_invoice_lines_invoice_id"), "invoice_lines", ["invoice_id"])
    op.create_index(op.f("ix_invoice_lines_tenant_id"), "invoice_lines", ["tenant_id"])

    op.create_table(
        "payments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("party_id", sa.Uuid(), nullable=True),
        sa.Column("payment_number", sa.String(length=64), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("amount_allocated", sa.Numeric(18, 2), nullable=False),
        sa.Column("payment_date", sa.Date(), nullable=False),
        sa.Column(
            "method",
            sa.Enum(
                "bank_transfer",
                "cash",
                "card",
                "online",
                "other",
                name="payment_method",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "completed",
                "failed",
                "refunded",
                "cancelled",
                name="payment_status",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("reference_number", sa.String(length=128), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("updated_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_payments_party_id"), "payments", ["party_id"])
    op.create_index(op.f("ix_payments_payment_date"), "payments", ["payment_date"])
    op.create_index(op.f("ix_payments_payment_number"), "payments", ["payment_number"])
    op.create_index(op.f("ix_payments_status"), "payments", ["status"])
    op.create_index(op.f("ix_payments_tenant_id"), "payments", ["tenant_id"])

    op.create_table(
        "payment_allocations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("payment_id", sa.Uuid(), nullable=False),
        sa.Column("invoice_id", sa.Uuid(), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["payment_id"], ["payments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("payment_id", "invoice_id", name="uq_payment_allocation_payment_invoice"),
    )
    op.create_index(op.f("ix_payment_allocations_invoice_id"), "payment_allocations", ["invoice_id"])
    op.create_index(op.f("ix_payment_allocations_payment_id"), "payment_allocations", ["payment_id"])
    op.create_index(op.f("ix_payment_allocations_tenant_id"), "payment_allocations", ["tenant_id"])


def downgrade() -> None:
    op.drop_table("payment_allocations")
    op.drop_table("payments")
    op.drop_table("invoice_lines")
    op.drop_table("invoices")
    op.drop_table("tax_profiles")
    op.drop_table("legal_entities")
