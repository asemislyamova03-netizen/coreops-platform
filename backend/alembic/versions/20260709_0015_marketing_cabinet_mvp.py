"""M6-BE1: Marketing Cabinet MVP schema — 6 tables (topics + packs subset for BE2 take).

Revision ID: 0015_marketing_cabinet_mvp
Revises: 0014_core_branches_baseline
Create Date: 2026-07-09

Local/schema readiness only. Do not run against production without separate approval.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0015_marketing_cabinet_mvp"
down_revision: Union[str, None] = "0014_core_branches_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "marketing_content_topics",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("legacy_topic_id", sa.String(length=64), nullable=True),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("rubric", sa.String(length=128), nullable=False),
        sa.Column("angle", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=False, server_default="manual"),
        sa.Column(
            "status",
            sa.Enum("draft", "approved", "used", "archived", name="marketing_topic_status", native_enum=False),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reusable", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("recommended_channels", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("used_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("slug_hint", sa.String(length=128), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("updated_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "legacy_topic_id", name="uq_marketing_topic_tenant_legacy_id"),
    )
    op.create_index(op.f("ix_marketing_content_topics_tenant_id"), "marketing_content_topics", ["tenant_id"])
    op.create_index("ix_marketing_topics_tenant_status", "marketing_content_topics", ["tenant_id", "status"])
    op.create_index("ix_marketing_topics_tenant_rubric", "marketing_content_topics", ["tenant_id", "rubric"])
    op.create_index("ix_marketing_topics_tenant_last_used", "marketing_content_topics", ["tenant_id", "last_used_at"])

    op.create_table(
        "marketing_publication_packs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=True),
        sa.Column("topic_id", sa.Uuid(), nullable=True),
        sa.Column("plan_item_id", sa.Uuid(), nullable=True),
        sa.Column("slug", sa.String(length=128), nullable=False),
        sa.Column("pack_dir_name", sa.String(length=255), nullable=True),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("planned_date", sa.Date(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "draft",
                "preflight_failed",
                "ready_for_approval",
                "approved",
                "scheduled",
                "publishing",
                "published",
                "failed",
                "archived",
                name="marketing_pack_status",
                native_enum=False,
            ),
            nullable=False,
            server_default="draft",
        ),
        sa.Column(
            "preflight_status",
            sa.Enum("not_run", "passed", "failed", name="marketing_preflight_status", native_enum=False),
            nullable=False,
            server_default="not_run",
        ),
        sa.Column("preflight_report_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("preflight_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "approval_status",
            sa.Enum("draft", "pending", "approved", "rejected", name="marketing_approval_status", native_enum=False),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by_user_id", sa.Uuid(), nullable=True),
        sa.Column(
            "publish_status",
            sa.Enum("not_started", "partial", "published", "failed", name="marketing_publish_status", native_enum=False),
            nullable=False,
            server_default="not_started",
        ),
        sa.Column("source", sa.String(length=64), nullable=False, server_default="console"),
        sa.Column("channel_config_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("legacy_git_path", sa.String(length=512), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("updated_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["topic_id"], ["marketing_content_topics.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "slug", name="uq_marketing_pack_tenant_slug"),
    )
    op.create_index(op.f("ix_marketing_publication_packs_tenant_id"), "marketing_publication_packs", ["tenant_id"])
    op.create_index(op.f("ix_marketing_publication_packs_topic_id"), "marketing_publication_packs", ["topic_id"])
    op.create_index("ix_marketing_packs_tenant_status", "marketing_publication_packs", ["tenant_id", "status"])
    op.create_index("ix_marketing_packs_tenant_planned_date", "marketing_publication_packs", ["tenant_id", "planned_date"])
    op.create_index("ix_marketing_packs_tenant_approval", "marketing_publication_packs", ["tenant_id", "approval_status"])
    op.create_index("ix_marketing_packs_tenant_publish", "marketing_publication_packs", ["tenant_id", "publish_status"])
    op.create_index("ix_marketing_packs_tenant_topic", "marketing_publication_packs", ["tenant_id", "topic_id"])

    op.create_table(
        "marketing_publication_texts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("pack_id", sa.Uuid(), nullable=False),
        sa.Column(
            "channel",
            sa.Enum("telegram", "instagram", "threads", "insights", name="marketing_channel", native_enum=False),
            nullable=False,
        ),
        sa.Column("text", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "status",
            sa.Enum("draft", "ready", "approved", name="marketing_text_status", native_enum=False),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("char_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("updated_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["pack_id"], ["marketing_publication_packs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pack_id", "channel", name="uq_marketing_text_pack_channel"),
    )
    op.create_index(op.f("ix_marketing_publication_texts_tenant_id"), "marketing_publication_texts", ["tenant_id"])
    op.create_index(op.f("ix_marketing_publication_texts_pack_id"), "marketing_publication_texts", ["pack_id"])
    op.create_index("ix_marketing_texts_tenant_pack", "marketing_publication_texts", ["tenant_id", "pack_id"])

    op.create_table(
        "marketing_media_assets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("pack_id", sa.Uuid(), nullable=True),
        sa.Column("role", sa.String(length=64), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=128), nullable=False),
        sa.Column("storage_provider", sa.String(length=32), nullable=False, server_default="git_path"),
        sa.Column("storage_key", sa.String(length=1024), nullable=False),
        sa.Column("public_url", sa.String(length=1024), nullable=True),
        sa.Column("preview_url", sa.String(length=1024), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("alt_text", sa.String(length=512), nullable=True),
        sa.Column(
            "status",
            sa.Enum("pending", "stored", "failed", "archived", name="marketing_media_status", native_enum=False),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("updated_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["pack_id"], ["marketing_publication_packs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_marketing_media_assets_tenant_id"), "marketing_media_assets", ["tenant_id"])
    op.create_index(op.f("ix_marketing_media_assets_pack_id"), "marketing_media_assets", ["pack_id"])
    op.create_index("ix_marketing_media_tenant_pack", "marketing_media_assets", ["tenant_id", "pack_id"])

    op.create_table(
        "marketing_publish_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("pack_id", sa.Uuid(), nullable=False),
        sa.Column("queue_item_id", sa.Uuid(), nullable=True),
        sa.Column("channel", sa.String(length=64), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("external_url", sa.String(length=1024), nullable=True),
        sa.Column("external_post_id", sa.String(length=255), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("actor", sa.String(length=64), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["pack_id"], ["marketing_publication_packs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_marketing_publish_logs_tenant_id"), "marketing_publish_logs", ["tenant_id"])
    op.create_index(op.f("ix_marketing_publish_logs_pack_id"), "marketing_publish_logs", ["pack_id"])
    op.create_index("ix_marketing_publish_logs_tenant_pack", "marketing_publish_logs", ["tenant_id", "pack_id"])
    op.create_index("ix_marketing_publish_logs_tenant_created", "marketing_publish_logs", ["tenant_id", "created_at"])

    op.create_table(
        "marketing_lead_attribution",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("party_id", sa.Uuid(), nullable=True),
        sa.Column("work_item_id", sa.Uuid(), nullable=True),
        sa.Column("campaign_id", sa.Uuid(), nullable=True),
        sa.Column("pack_id", sa.Uuid(), nullable=True),
        sa.Column("topic_id", sa.Uuid(), nullable=True),
        sa.Column("channel", sa.String(length=64), nullable=False),
        sa.Column(
            "source_type",
            sa.Enum("first_touch", "assisted", "converted", name="marketing_attribution_touch_type", native_enum=False),
            nullable=False,
        ),
        sa.Column("source_url", sa.String(length=1024), nullable=True),
        sa.Column("content_slug", sa.String(length=128), nullable=True),
        sa.Column("utm_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("first_touch_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_touch_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("updated_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["party_id"], ["parties.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["work_item_id"], ["work_items.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["pack_id"], ["marketing_publication_packs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["topic_id"], ["marketing_content_topics.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_marketing_lead_attribution_tenant_id"), "marketing_lead_attribution", ["tenant_id"])
    op.create_index(op.f("ix_marketing_lead_attribution_party_id"), "marketing_lead_attribution", ["party_id"])
    op.create_index(op.f("ix_marketing_lead_attribution_work_item_id"), "marketing_lead_attribution", ["work_item_id"])
    op.create_index(op.f("ix_marketing_lead_attribution_pack_id"), "marketing_lead_attribution", ["pack_id"])
    op.create_index(op.f("ix_marketing_lead_attribution_topic_id"), "marketing_lead_attribution", ["topic_id"])
    op.create_index("ix_marketing_attribution_tenant_work_item", "marketing_lead_attribution", ["tenant_id", "work_item_id"])
    op.create_index("ix_marketing_attribution_tenant_pack", "marketing_lead_attribution", ["tenant_id", "pack_id"])
    op.create_index("ix_marketing_attribution_tenant_party", "marketing_lead_attribution", ["tenant_id", "party_id"])


def downgrade() -> None:
    op.drop_table("marketing_lead_attribution")
    op.drop_table("marketing_publish_logs")
    op.drop_table("marketing_media_assets")
    op.drop_table("marketing_publication_texts")
    op.drop_table("marketing_publication_packs")
    op.drop_table("marketing_content_topics")

    for enum_name in (
        "marketing_attribution_touch_type",
        "marketing_media_status",
        "marketing_text_status",
        "marketing_channel",
        "marketing_publish_status",
        "marketing_approval_status",
        "marketing_preflight_status",
        "marketing_pack_status",
        "marketing_topic_status",
    ):
        sa.Enum(name=enum_name).drop(op.get_bind(), checkfirst=True)
