import uuid
from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.models import AuditUserMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.modules.marketing.enums import (
    MarketingApprovalStatus,
    MarketingAttributionTouchType,
    MarketingChannel,
    MarketingMediaAssetStatus,
    MarketingPackStatus,
    MarketingPreflightStatus,
    MarketingPublishStatus,
    MarketingTextStatus,
    MarketingTopicStatus,
)


class MarketingContentTopic(Base, UUIDPrimaryKeyMixin, TimestampMixin, AuditUserMixin):
    __tablename__ = "marketing_content_topics"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "legacy_topic_id",
            name="uq_marketing_topic_tenant_legacy_id",
        ),
        Index("ix_marketing_topics_tenant_status", "tenant_id", "status"),
        Index("ix_marketing_topics_tenant_rubric", "tenant_id", "rubric"),
        Index("ix_marketing_topics_tenant_last_used", "tenant_id", "last_used_at"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    legacy_topic_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    rubric: Mapped[str] = mapped_column(String(128), nullable=False)
    angle: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False, default="manual")
    status: Mapped[MarketingTopicStatus] = mapped_column(
        Enum(MarketingTopicStatus, name="marketing_topic_status", native_enum=False),
        default=MarketingTopicStatus.DRAFT,
        nullable=False,
    )
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reusable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    recommended_channels: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    used_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    slug_hint: Mapped[str | None] = mapped_column(String(128), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    packs: Mapped[list["MarketingPublicationPack"]] = relationship(
        "MarketingPublicationPack",
        back_populates="topic",
        lazy="selectin",
    )


class MarketingPublicationPack(Base, UUIDPrimaryKeyMixin, TimestampMixin, AuditUserMixin):
    __tablename__ = "marketing_publication_packs"
    __table_args__ = (
        UniqueConstraint("tenant_id", "slug", name="uq_marketing_pack_tenant_slug"),
        Index("ix_marketing_packs_tenant_status", "tenant_id", "status"),
        Index("ix_marketing_packs_tenant_planned_date", "tenant_id", "planned_date"),
        Index("ix_marketing_packs_tenant_approval", "tenant_id", "approval_status"),
        Index("ix_marketing_packs_tenant_publish", "tenant_id", "publish_status"),
        Index("ix_marketing_packs_tenant_topic", "tenant_id", "topic_id"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    topic_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("marketing_content_topics.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    plan_item_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    slug: Mapped[str] = mapped_column(String(128), nullable=False)
    pack_dir_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    planned_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[MarketingPackStatus] = mapped_column(
        Enum(MarketingPackStatus, name="marketing_pack_status", native_enum=False),
        default=MarketingPackStatus.DRAFT,
        nullable=False,
    )
    preflight_status: Mapped[MarketingPreflightStatus] = mapped_column(
        Enum(MarketingPreflightStatus, name="marketing_preflight_status", native_enum=False),
        default=MarketingPreflightStatus.NOT_RUN,
        nullable=False,
    )
    preflight_report_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    preflight_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approval_status: Mapped[MarketingApprovalStatus] = mapped_column(
        Enum(MarketingApprovalStatus, name="marketing_approval_status", native_enum=False),
        default=MarketingApprovalStatus.DRAFT,
        nullable=False,
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    publish_status: Mapped[MarketingPublishStatus] = mapped_column(
        Enum(MarketingPublishStatus, name="marketing_publish_status", native_enum=False),
        default=MarketingPublishStatus.NOT_STARTED,
        nullable=False,
    )
    source: Mapped[str] = mapped_column(String(64), nullable=False, default="console")
    channel_config_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    legacy_git_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    topic: Mapped["MarketingContentTopic | None"] = relationship(
        "MarketingContentTopic",
        back_populates="packs",
        lazy="selectin",
    )
    texts: Mapped[list["MarketingPublicationText"]] = relationship(
        "MarketingPublicationText",
        back_populates="pack",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    media_assets: Mapped[list["MarketingMediaAsset"]] = relationship(
        "MarketingMediaAsset",
        back_populates="pack",
        lazy="selectin",
    )
    publish_logs: Mapped[list["MarketingPublishLog"]] = relationship(
        "MarketingPublishLog",
        back_populates="pack",
        lazy="selectin",
    )


class MarketingPublicationText(Base, UUIDPrimaryKeyMixin, TimestampMixin, AuditUserMixin):
    __tablename__ = "marketing_publication_texts"
    __table_args__ = (
        UniqueConstraint("pack_id", "channel", name="uq_marketing_text_pack_channel"),
        Index("ix_marketing_texts_tenant_pack", "tenant_id", "pack_id"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pack_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("marketing_publication_packs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    channel: Mapped[MarketingChannel] = mapped_column(
        Enum(MarketingChannel, name="marketing_channel", native_enum=False),
        nullable=False,
    )
    text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[MarketingTextStatus] = mapped_column(
        Enum(MarketingTextStatus, name="marketing_text_status", native_enum=False),
        default=MarketingTextStatus.DRAFT,
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    char_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    pack: Mapped["MarketingPublicationPack"] = relationship(
        "MarketingPublicationPack",
        back_populates="texts",
        lazy="selectin",
    )


class MarketingMediaAsset(Base, UUIDPrimaryKeyMixin, TimestampMixin, AuditUserMixin):
    __tablename__ = "marketing_media_assets"
    __table_args__ = (Index("ix_marketing_media_tenant_pack", "tenant_id", "pack_id"),)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pack_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("marketing_publication_packs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(64), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    storage_provider: Mapped[str] = mapped_column(String(32), nullable=False, default="git_path")
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    public_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    preview_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    alt_text: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[MarketingMediaAssetStatus] = mapped_column(
        Enum(MarketingMediaAssetStatus, name="marketing_media_status", native_enum=False),
        default=MarketingMediaAssetStatus.PENDING,
        nullable=False,
    )
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    pack: Mapped["MarketingPublicationPack | None"] = relationship(
        "MarketingPublicationPack",
        back_populates="media_assets",
        lazy="selectin",
    )


class MarketingPublishLog(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "marketing_publish_logs"
    __table_args__ = (
        Index("ix_marketing_publish_logs_tenant_pack", "tenant_id", "pack_id"),
        Index("ix_marketing_publish_logs_tenant_created", "tenant_id", "created_at"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pack_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("marketing_publication_packs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    queue_item_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    channel: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    external_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    external_post_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    actor: Mapped[str | None] = mapped_column(String(64), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    pack: Mapped["MarketingPublicationPack"] = relationship(
        "MarketingPublicationPack",
        back_populates="publish_logs",
        lazy="selectin",
    )


class MarketingLeadAttribution(Base, UUIDPrimaryKeyMixin, TimestampMixin, AuditUserMixin):
    __tablename__ = "marketing_lead_attribution"
    __table_args__ = (
        Index("ix_marketing_attribution_tenant_work_item", "tenant_id", "work_item_id"),
        Index("ix_marketing_attribution_tenant_pack", "tenant_id", "pack_id"),
        Index("ix_marketing_attribution_tenant_party", "tenant_id", "party_id"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    party_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("parties.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    work_item_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("work_items.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    pack_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("marketing_publication_packs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    topic_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("marketing_content_topics.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    channel: Mapped[str] = mapped_column(String(64), nullable=False)
    source_type: Mapped[MarketingAttributionTouchType] = mapped_column(
        Enum(
            MarketingAttributionTouchType,
            name="marketing_attribution_touch_type",
            native_enum=False,
        ),
        nullable=False,
    )
    source_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    content_slug: Mapped[str | None] = mapped_column(String(128), nullable=True)
    utm_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    first_touch_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_touch_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
