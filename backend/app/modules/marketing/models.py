import uuid
from datetime import date, datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
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
    MarketingDestinationStatus,
    MarketingDestinationValidationStatus,
    MarketingMediaAssetStatus,
    MarketingMediaValidationStatus,
    MarketingPackStatus,
    MarketingPreflightStatus,
    MarketingPublishDestinationType,
    MarketingPublishingConnectionStatus,
    MarketingPublishingProvider,
    MarketingPublishingTokenStatus,
    MarketingPublishStatus,
    MarketingStorageProfileStatus,
    MarketingStorageResourceMode,
    MarketingTextStatus,
    MarketingTopicStatus,
    destination_capability_enabled,
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


class MarketingStorageResourceProfile(Base, UUIDPrimaryKeyMixin, TimestampMixin, AuditUserMixin):
    """Tenant-scoped storage mode + limits. No credentials / config_json."""

    __tablename__ = "marketing_storage_resource_profiles"
    __table_args__ = (
        Index("ix_marketing_storage_profiles_tenant", "tenant_id"),
        Index(
            "uq_marketing_storage_profile_tenant_mode_active",
            "tenant_id",
            "mode",
            unique=True,
            sqlite_where=text("status = 'ACTIVE'"),
            postgresql_where=text("status = 'ACTIVE'"),
        ),
        Index(
            "uq_marketing_storage_profile_tenant_default",
            "tenant_id",
            unique=True,
            sqlite_where=text("is_default IS TRUE"),
            postgresql_where=text("is_default IS TRUE"),
        ),
        CheckConstraint(
            "mode IN ('FLEXITY_MANAGED','CLIENT_PUBLIC_URL','CLIENT_BUCKET')",
            name="ck_marketing_storage_profile_mode_values",
        ),
        CheckConstraint(
            "status IN ('ACTIVE','DISABLED')",
            name="ck_marketing_storage_profile_status_values",
        ),
        CheckConstraint(
            "(is_default IS FALSE) OR (status = 'ACTIVE')",
            name="ck_marketing_storage_profile_default_requires_active",
        ),
        # Portable with SQLAlchemy Enum name storage (ACTIVE/CLIENT_BUCKET names).
        CheckConstraint(
            "NOT (status = 'ACTIVE' AND mode = 'CLIENT_BUCKET')",
            name="ck_marketing_storage_profile_no_active_client_bucket",
        ),
        CheckConstraint(
            "max_upload_bytes IS NULL OR (max_upload_bytes > 0 AND max_upload_bytes <= 52428800)",
            name="ck_marketing_storage_profile_max_upload_bytes",
        ),
        CheckConstraint(
            "max_url_length IS NULL OR (max_url_length > 0 AND max_url_length <= 2048)",
            name="ck_marketing_storage_profile_max_url_length",
        ),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    mode: Mapped[MarketingStorageResourceMode] = mapped_column(
        Enum(
            MarketingStorageResourceMode,
            name="marketing_storage_resource_mode",
            native_enum=False,
        ),
        nullable=False,
    )
    status: Mapped[MarketingStorageProfileStatus] = mapped_column(
        Enum(
            MarketingStorageProfileStatus,
            name="marketing_storage_profile_status",
            native_enum=False,
        ),
        default=MarketingStorageProfileStatus.DISABLED,
        server_default="DISABLED",
        nullable=False,
        index=True,
    )
    is_default: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false"), nullable=False
    )
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    max_upload_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    max_url_length: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Normalized unique MIME list as JSON array (portable across SQLite/PG).
    allowed_mime_types: Mapped[list | None] = mapped_column(JSON, nullable=True)


class MarketingMediaAsset(Base, UUIDPrimaryKeyMixin, TimestampMixin, AuditUserMixin):
    __tablename__ = "marketing_media_assets"
    __table_args__ = (
        Index("ix_marketing_media_tenant_pack", "tenant_id", "pack_id"),
        CheckConstraint(
            "validation_status IN ("
            "'LEGACY_UNVERIFIED','REGISTERED_UNVERIFIED','VALIDATED_METADATA',"
            "'REJECTED','ARCHIVED')",
            name="ck_marketing_media_validation_status_values",
        ),
        CheckConstraint(
            "resource_mode IS NULL OR resource_mode IN ("
            "'FLEXITY_MANAGED','CLIENT_PUBLIC_URL','CLIENT_BUCKET')",
            name="ck_marketing_media_resource_mode_values",
        ),
        CheckConstraint(
            "declared_size_bytes IS NULL OR declared_size_bytes >= 0",
            name="ck_marketing_media_declared_size_nonneg",
        ),
        CheckConstraint(
            "verified_size_bytes IS NULL OR verified_size_bytes >= 0",
            name="ck_marketing_media_verified_size_nonneg",
        ),
    )

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
    # M8-C2a: safety track. Existing/legacy rows default to LEGACY_UNVERIFIED —
    # never treated as malware-safe or publish-ready.
    validation_status: Mapped[MarketingMediaValidationStatus] = mapped_column(
        Enum(
            MarketingMediaValidationStatus,
            name="marketing_media_validation_status",
            native_enum=False,
        ),
        default=MarketingMediaValidationStatus.LEGACY_UNVERIFIED,
        server_default="LEGACY_UNVERIFIED",
        nullable=False,
    )
    declared_mime_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    declared_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    verified_mime_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    verified_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    storage_profile_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("marketing_storage_resource_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    resource_mode: Mapped[MarketingStorageResourceMode | None] = mapped_column(
        Enum(
            MarketingStorageResourceMode,
            name="marketing_media_resource_mode",
            native_enum=False,
        ),
        nullable=True,
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
        # Composite FK target for publish destinations (added conceptually with M8-D1 / 0026).
        UniqueConstraint(
            "tenant_id",
            "id",
            name="uq_marketing_publishing_conn_tenant_id_id",
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


class MarketingPublishDestination(Base, UUIDPrimaryKeyMixin, TimestampMixin, AuditUserMixin):
    """Publish target allow-list entry. Never stores secrets / tokens / secret_ref.

    Enum storage convention (matches M8-C2a): SQLAlchemy Enum NAME storage —
    uppercase member names in DB CHECKs / partial indexes (ENABLED, UNCHECKED, …).
    HQ wording lives on enum `.value` (enabled, unchecked, telegram_chat, …).

    identity_locked_at: set once on first VALID (and reserved for future D4 live use).
    Resetting validation to UNCHECKED does not clear the lock.
    """

    __tablename__ = "marketing_publish_destinations"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            ondelete="RESTRICT",
            name="fk_mkt_publish_dest_tenant",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "publishing_connection_id"],
            [
                "marketing_publishing_connections.tenant_id",
                "marketing_publishing_connections.id",
            ],
            ondelete="RESTRICT",
            name="fk_mkt_publish_dest_tenant_connection",
        ),
        CheckConstraint(
            "status IN ('ENABLED','DISABLED','ARCHIVED')",
            name="ck_mkt_publish_dest_status_values",
        ),
        CheckConstraint(
            "validation_status IN ('UNCHECKED','VALID','INVALID','UNAVAILABLE')",
            name="ck_mkt_publish_dest_validation_status_values",
        ),
        CheckConstraint(
            "destination_type IN ("
            "'TELEGRAM_CHAT','INSTAGRAM_USER','THREADS_USER','TIKTOK_USER')",
            name="ck_mkt_publish_dest_type_values",
        ),
        CheckConstraint(
            "provider IN ('TELEGRAM','INSTAGRAM','THREADS','TIKTOK')",
            name="ck_mkt_publish_dest_provider_values",
        ),
        CheckConstraint(
            "trim(external_id) <> ''",
            name="ck_mkt_publish_dest_external_id_nonempty",
        ),
        CheckConstraint(
            "trim(display_name) <> ''",
            name="ck_mkt_publish_dest_display_name_nonempty",
        ),
        Index(
            "uq_mkt_publish_dest_active_identity",
            "tenant_id",
            "publishing_connection_id",
            "destination_type",
            "external_id",
            unique=True,
            postgresql_where=text("status <> 'ARCHIVED'"),
            sqlite_where=text("status <> 'ARCHIVED'"),
        ),
        Index("ix_marketing_publish_destinations_tenant_status", "tenant_id", "status"),
        Index(
            "ix_marketing_publish_destinations_tenant_connection",
            "tenant_id",
            "publishing_connection_id",
        ),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    publishing_connection_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, nullable=False, index=True
    )
    provider: Mapped[MarketingPublishingProvider] = mapped_column(
        Enum(
            MarketingPublishingProvider,
            name="marketing_publish_destination_provider",
            native_enum=False,
        ),
        nullable=False,
    )
    destination_type: Mapped[MarketingPublishDestinationType] = mapped_column(
        Enum(
            MarketingPublishDestinationType,
            name="marketing_publish_destination_type",
            native_enum=False,
        ),
        nullable=False,
    )
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[MarketingDestinationStatus] = mapped_column(
        Enum(
            MarketingDestinationStatus,
            name="marketing_destination_status",
            native_enum=False,
        ),
        default=MarketingDestinationStatus.ENABLED,
        server_default="ENABLED",
        nullable=False,
        index=True,
    )
    validation_status: Mapped[MarketingDestinationValidationStatus] = mapped_column(
        Enum(
            MarketingDestinationValidationStatus,
            name="marketing_destination_validation_status",
            native_enum=False,
        ),
        default=MarketingDestinationValidationStatus.UNCHECKED,
        server_default="UNCHECKED",
        nullable=False,
    )
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    validation_error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    identity_locked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    def assert_external_id_mutable(self) -> None:
        """Mutable only while unchecked AND identity not yet locked."""
        from app.modules.marketing.exceptions import MarketingPublishDestinationValidationError

        if (
            self.validation_status != MarketingDestinationValidationStatus.UNCHECKED
            or self.identity_locked_at is not None
        ):
            raise MarketingPublishDestinationValidationError("external_id_immutable")

    def update_external_id(self, external_id: str) -> None:
        from app.modules.marketing.exceptions import MarketingPublishDestinationValidationError

        self.assert_external_id_mutable()
        value = external_id.strip()
        if not value:
            raise MarketingPublishDestinationValidationError("external_id_required")
        self.external_id = value

    def enable(self) -> None:
        from app.modules.marketing.exceptions import MarketingPublishDestinationValidationError

        if self.status == MarketingDestinationStatus.ARCHIVED:
            raise MarketingPublishDestinationValidationError("archived_destination_immutable")
        if self.status == MarketingDestinationStatus.ENABLED:
            return
        if self.status != MarketingDestinationStatus.DISABLED:
            raise MarketingPublishDestinationValidationError("invalid_status_transition")
        if not destination_capability_enabled(self.destination_type):
            raise MarketingPublishDestinationValidationError("destination_capability_disabled")
        self.status = MarketingDestinationStatus.ENABLED

    def disable(self) -> None:
        from app.modules.marketing.exceptions import MarketingPublishDestinationValidationError

        if self.status == MarketingDestinationStatus.ARCHIVED:
            raise MarketingPublishDestinationValidationError("archived_destination_immutable")
        if self.status == MarketingDestinationStatus.DISABLED:
            return
        if self.status != MarketingDestinationStatus.ENABLED:
            raise MarketingPublishDestinationValidationError("invalid_status_transition")
        self.status = MarketingDestinationStatus.DISABLED

    def archive(self) -> None:
        from app.modules.marketing.exceptions import MarketingPublishDestinationValidationError

        if self.status == MarketingDestinationStatus.ARCHIVED:
            return
        if self.status not in (
            MarketingDestinationStatus.ENABLED,
            MarketingDestinationStatus.DISABLED,
        ):
            raise MarketingPublishDestinationValidationError("invalid_status_transition")
        self.status = MarketingDestinationStatus.ARCHIVED

    def apply_structural_validation(
        self,
        *,
        validation_status: MarketingDestinationValidationStatus,
        validation_error_code: str | None = None,
        validated_at: datetime | None = None,
    ) -> None:
        """Structural validation only (D1). Provider validate requires adapter (later).

        TikTok capability disabled: cannot mark VALID / available; UNAVAILABLE only.
        First transition to VALID sets identity_locked_at once; UNCHECKED reset does not unlock.
        """
        from datetime import UTC

        from app.modules.marketing.exceptions import MarketingPublishDestinationValidationError

        if self.status == MarketingDestinationStatus.ARCHIVED:
            raise MarketingPublishDestinationValidationError("archived_destination_immutable")

        if not destination_capability_enabled(self.destination_type):
            if validation_status == MarketingDestinationValidationStatus.VALID:
                raise MarketingPublishDestinationValidationError(
                    "destination_capability_disabled"
                )
            if validation_status not in (
                MarketingDestinationValidationStatus.UNAVAILABLE,
                MarketingDestinationValidationStatus.INVALID,
                MarketingDestinationValidationStatus.UNCHECKED,
            ):
                raise MarketingPublishDestinationValidationError(
                    "destination_capability_disabled"
                )

        if validation_status == MarketingDestinationValidationStatus.UNCHECKED:
            self.validation_status = validation_status
            self.validated_at = None
            self.validation_error_code = None
            # identity_locked_at intentionally preserved
            return

        stamp = validated_at or datetime.now(UTC)
        self.validation_status = validation_status
        self.validated_at = stamp
        code = (validation_error_code or "").strip() or None
        if validation_status in (
            MarketingDestinationValidationStatus.INVALID,
            MarketingDestinationValidationStatus.UNAVAILABLE,
        ):
            self.validation_error_code = code
        else:
            self.validation_error_code = None

        if (
            validation_status == MarketingDestinationValidationStatus.VALID
            and self.identity_locked_at is None
        ):
            self.identity_locked_at = stamp


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
