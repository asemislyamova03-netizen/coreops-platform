import uuid
from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
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
    text,
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
    MarketingPublishingConnectionStatus,
    MarketingPublishingProvider,
    MarketingPublishingTokenStatus,
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


class MarketingPublishingConnection(Base, UUIDPrimaryKeyMixin, TimestampMixin, AuditUserMixin):
    __tablename__ = "marketing_publishing_connections"
    __table_args__ = (
        CheckConstraint(
            "(status <> 'ACTIVE') OR (account_identifier IS NOT NULL AND trim(account_identifier) <> '')",
            name="ck_marketing_publishing_conn_active_requires_identifier",
        ),
        CheckConstraint(
            "(token_status NOT IN ('VALID','EXPIRING')) OR (secret_ref IS NOT NULL AND trim(secret_ref) <> '')",
            name="ck_marketing_publishing_conn_healthy_requires_secret_ref",
        ),
        CheckConstraint(
            "provider IN ('TELEGRAM','INSTAGRAM','THREADS','TIKTOK')",
            name="ck_marketing_publishing_conn_provider_values",
        ),
        CheckConstraint(
            "status IN ('NOT_CONNECTED','ACTIVE','ERROR','DISABLED','EXPIRED')",
            name="ck_marketing_publishing_conn_status_values",
        ),
        CheckConstraint(
            "token_status IN ('NOT_CONFIGURED','VALID','EXPIRING','INVALID')",
            name="ck_marketing_publishing_conn_token_status_values",
        ),
        CheckConstraint(
            "("
            " (secret_ref IS NULL AND secret_version IS NULL AND secret_bound_at IS NULL)"
            " OR "
            " (secret_ref IS NOT NULL AND trim(secret_ref) <> ''"
            "  AND secret_version IS NOT NULL AND secret_version > 0"
            "  AND secret_bound_at IS NOT NULL)"
            ")",
            name="ck_marketing_publishing_conn_secret_binding_consistent",
        ),
        Index(
            "uq_marketing_publishing_conn_tenant_provider_account",
            "tenant_id",
            "provider",
            "account_identifier",
            unique=True,
            postgresql_where=text("account_identifier IS NOT NULL"),
            sqlite_where=text("account_identifier IS NOT NULL"),
        ),
        Index("ix_marketing_publishing_connections_tenant_provider", "tenant_id", "provider"),
        Index("ix_marketing_publishing_connections_tenant_status", "tenant_id", "status"),
        Index(
            "ix_marketing_publishing_connections_tenant_token_status",
            "tenant_id",
            "token_status",
        ),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider: Mapped[MarketingPublishingProvider] = mapped_column(
        Enum(MarketingPublishingProvider, name="marketing_publishing_provider", native_enum=False),
        nullable=False,
        index=True,
    )
    account_display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    account_identifier: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[MarketingPublishingConnectionStatus] = mapped_column(
        Enum(
            MarketingPublishingConnectionStatus,
            name="marketing_publishing_connection_status",
            native_enum=False,
        ),
        default=MarketingPublishingConnectionStatus.NOT_CONNECTED,
        nullable=False,
        index=True,
    )
    token_status: Mapped[MarketingPublishingTokenStatus] = mapped_column(
        Enum(
            MarketingPublishingTokenStatus,
            name="marketing_publishing_token_status",
            native_enum=False,
        ),
        default=MarketingPublishingTokenStatus.NOT_CONFIGURED,
        nullable=False,
        index=True,
    )
    secret_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    secret_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    secret_bound_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scopes_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_error_message_redacted: Mapped[str | None] = mapped_column(String(512), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


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
