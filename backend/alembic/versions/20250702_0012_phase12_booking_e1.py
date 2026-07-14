"""Phase 12: Flexity Booking E1 — domain persistence tables

Revision ID: 0012_booking_e1
Revises: 0011_phase11
Create Date: 2025-07-02

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0012_booking_e1"
down_revision: Union[str, None] = "0011_phase11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "booking_territories",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=128), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("default_check_in_time", sa.Time(), nullable=False),
        sa.Column("default_check_out_time", sa.Time(), nullable=False),
        sa.Column("hold_duration_minutes", sa.Integer(), nullable=False),
        sa.Column("min_stay_nights", sa.Integer(), nullable=False),
        sa.Column("map_config_json", sa.JSON(), nullable=False),
        sa.Column("settings_json", sa.JSON(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("draft", "active", "archived", name="booking_territory_status", native_enum=False),
            nullable=False,
        ),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("updated_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "code", name="uq_booking_territory_tenant_code"),
        sa.UniqueConstraint("tenant_id", "slug", name="uq_booking_territory_tenant_slug"),
    )
    op.create_index(op.f("ix_booking_territories_slug"), "booking_territories", ["slug"])
    op.create_index(op.f("ix_booking_territories_status"), "booking_territories", ["status"])
    op.create_index(op.f("ix_booking_territories_tenant_id"), "booking_territories", ["tenant_id"])

    op.create_table(
        "booking_owners",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("party_id", sa.Uuid(), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("payout_details_json", sa.JSON(), nullable=False),
        sa.Column("telegram_chat_id", sa.String(length=64), nullable=True),
        sa.Column("whatsapp_phone", sa.String(length=32), nullable=True),
        sa.Column(
            "status",
            sa.Enum("active", "suspended", name="booking_owner_status", native_enum=False),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["party_id"], ["parties.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "party_id", name="uq_booking_owner_tenant_party"),
    )
    op.create_index(op.f("ix_booking_owners_party_id"), "booking_owners", ["party_id"])
    op.create_index(op.f("ix_booking_owners_tenant_id"), "booking_owners", ["tenant_id"])

    op.create_table(
        "booking_bookable_objects",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("territory_id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "object_type",
            sa.Enum("cabin", "zone", "hall", "other", name="bookable_object_type", native_enum=False),
            nullable=False,
        ),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("base_price", sa.Numeric(18, 2), nullable=False),
        sa.Column(
            "pricing_unit",
            sa.Enum("per_night", "per_stay", name="bookable_pricing_unit", native_enum=False),
            nullable=False,
        ),
        sa.Column("check_in_time", sa.Time(), nullable=True),
        sa.Column("check_out_time", sa.Time(), nullable=True),
        sa.Column("catalog_item_id", sa.Uuid(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("active", "maintenance", "unlisted", name="bookable_object_status", native_enum=False),
            nullable=False,
        ),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("updated_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["catalog_item_id"], ["catalog_items.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["booking_owners.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["territory_id"], ["booking_territories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("territory_id", "code", name="uq_booking_object_territory_code"),
    )
    op.create_index(op.f("ix_booking_bookable_objects_owner_id"), "booking_bookable_objects", ["owner_id"])
    op.create_index(op.f("ix_booking_bookable_objects_status"), "booking_bookable_objects", ["status"])
    op.create_index(op.f("ix_booking_bookable_objects_tenant_id"), "booking_bookable_objects", ["tenant_id"])
    op.create_index(op.f("ix_booking_bookable_objects_territory_id"), "booking_bookable_objects", ["territory_id"])

    op.create_table(
        "booking_object_photos",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("bookable_object_id", sa.Uuid(), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("storage_path", sa.String(length=1024), nullable=True),
        sa.Column("alt_text", sa.String(length=255), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["bookable_object_id"], ["booking_bookable_objects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_booking_object_photos_bookable_object_id"), "booking_object_photos", ["bookable_object_id"])
    op.create_index(op.f("ix_booking_object_photos_tenant_id"), "booking_object_photos", ["tenant_id"])

    op.create_table(
        "booking_map_points",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("territory_id", sa.Uuid(), nullable=False),
        sa.Column("bookable_object_id", sa.Uuid(), nullable=False),
        sa.Column("x", sa.Float(), nullable=False),
        sa.Column("y", sa.Float(), nullable=False),
        sa.Column("label", sa.String(length=128), nullable=True),
        sa.Column("layer", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["bookable_object_id"], ["booking_bookable_objects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["territory_id"], ["booking_territories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("bookable_object_id", name="uq_booking_map_point_object"),
    )
    op.create_index(op.f("ix_booking_map_points_tenant_id"), "booking_map_points", ["tenant_id"])
    op.create_index(op.f("ix_booking_map_points_territory_id"), "booking_map_points", ["territory_id"])

    op.create_table(
        "booking_orders",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("territory_id", sa.Uuid(), nullable=False),
        sa.Column("order_number", sa.String(length=64), nullable=False),
        sa.Column("guest_party_id", sa.Uuid(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "draft",
                "held",
                "pending_payment",
                "paid",
                "confirmed",
                "cancelled",
                "expired",
                name="booking_order_status",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("hold_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("subtotal", sa.Numeric(18, 2), nullable=False),
        sa.Column("commission_total", sa.Numeric(18, 2), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "source",
            sa.Enum("public_web", "admin", "2gis", "external", name="booking_order_source", native_enum=False),
            nullable=False,
        ),
        sa.Column("work_item_id", sa.Uuid(), nullable=True),
        sa.Column("invoice_id", sa.Uuid(), nullable=True),
        sa.Column("payment_id", sa.Uuid(), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("updated_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["guest_party_id"], ["parties.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["payment_id"], ["payments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["territory_id"], ["booking_territories.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["work_item_id"], ["work_items.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_booking_orders_guest_party_id"), "booking_orders", ["guest_party_id"])
    op.create_index(op.f("ix_booking_orders_invoice_id"), "booking_orders", ["invoice_id"])
    op.create_index(op.f("ix_booking_orders_order_number"), "booking_orders", ["order_number"])
    op.create_index(op.f("ix_booking_orders_payment_id"), "booking_orders", ["payment_id"])
    op.create_index(op.f("ix_booking_orders_status"), "booking_orders", ["status"])
    op.create_index(op.f("ix_booking_orders_tenant_id"), "booking_orders", ["tenant_id"])
    op.create_index(op.f("ix_booking_orders_territory_id"), "booking_orders", ["territory_id"])
    op.create_index(op.f("ix_booking_orders_work_item_id"), "booking_orders", ["work_item_id"])
    op.create_index(
        "ix_booking_orders_tenant_status_hold",
        "booking_orders",
        ["tenant_id", "status", "hold_expires_at"],
    )

    op.create_table(
        "booking_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("booking_order_id", sa.Uuid(), nullable=False),
        sa.Column("bookable_object_id", sa.Uuid(), nullable=False),
        sa.Column("check_in_date", sa.Date(), nullable=False),
        sa.Column("check_out_date", sa.Date(), nullable=False),
        sa.Column("check_in_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("check_out_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("nights", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(18, 2), nullable=False),
        sa.Column("line_total", sa.Numeric(18, 2), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("active", "cancelled", name="booking_item_status", native_enum=False),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("check_out_at > check_in_at", name="ck_booking_item_checkout_after_checkin"),
        sa.ForeignKeyConstraint(["bookable_object_id"], ["booking_bookable_objects.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["booking_order_id"], ["booking_orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_id"], ["booking_owners.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_booking_items_bookable_object_id"), "booking_items", ["bookable_object_id"])
    op.create_index(op.f("ix_booking_items_booking_order_id"), "booking_items", ["booking_order_id"])
    op.create_index(op.f("ix_booking_items_owner_id"), "booking_items", ["owner_id"])
    op.create_index(op.f("ix_booking_items_tenant_id"), "booking_items", ["tenant_id"])
    op.create_index(
        "ix_booking_items_object_interval",
        "booking_items",
        ["bookable_object_id", "check_in_at", "check_out_at"],
    )

    op.create_table(
        "booking_management_permissions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "scope_type",
            sa.Enum("territory", "owner", "object", name="booking_permission_scope", native_enum=False),
            nullable=False,
        ),
        sa.Column("scope_id", sa.Uuid(), nullable=False),
        sa.Column(
            "permission",
            sa.Enum("view", "manage", "finance", "notify", name="booking_permission", native_enum=False),
            nullable=False,
        ),
        sa.Column("granted_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["granted_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "user_id",
            "scope_type",
            "scope_id",
            "permission",
            name="uq_booking_mgmt_perm",
        ),
    )
    op.create_index(
        "ix_booking_mgmt_perm_user_tenant",
        "booking_management_permissions",
        ["user_id", "tenant_id"],
    )
    op.create_index(op.f("ix_booking_management_permissions_tenant_id"), "booking_management_permissions", ["tenant_id"])
    op.create_index(op.f("ix_booking_management_permissions_user_id"), "booking_management_permissions", ["user_id"])

    op.create_table(
        "booking_commission_rules",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("territory_id", sa.Uuid(), nullable=True),
        sa.Column("owner_id", sa.Uuid(), nullable=True),
        sa.Column("rate_percent", sa.Numeric(8, 4), nullable=False),
        sa.Column("fixed_fee", sa.Numeric(18, 2), nullable=True),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["booking_owners.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["territory_id"], ["booking_territories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_booking_commission_rules_owner_id"), "booking_commission_rules", ["owner_id"])
    op.create_index(op.f("ix_booking_commission_rules_tenant_id"), "booking_commission_rules", ["tenant_id"])
    op.create_index(op.f("ix_booking_commission_rules_territory_id"), "booking_commission_rules", ["territory_id"])


def downgrade() -> None:
    op.drop_table("booking_commission_rules")
    op.drop_table("booking_management_permissions")
    op.drop_table("booking_items")
    op.drop_table("booking_orders")
    op.drop_table("booking_map_points")
    op.drop_table("booking_object_photos")
    op.drop_table("booking_bookable_objects")
    op.drop_table("booking_owners")
    op.drop_table("booking_territories")

    for name in (
        "booking_permission",
        "booking_permission_scope",
        "booking_item_status",
        "booking_order_source",
        "booking_order_status",
        "bookable_object_status",
        "bookable_pricing_unit",
        "bookable_object_type",
        "booking_owner_status",
        "booking_territory_status",
    ):
        sa.Enum(name=name).drop(op.get_bind(), checkfirst=True)
