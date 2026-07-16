import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.marketing.enums import (
    MarketingApprovalStatus,
    MarketingChannel,
    MarketingMediaAssetStatus,
    MarketingMediaValidationStatus,
    MarketingPackStatus,
    MarketingPreflightStatus,
    MarketingPublishingConnectionStatus,
    MarketingPublishingProvider,
    MarketingPublishingTokenStatus,
    MarketingPublishStatus,
    MarketingStorageProfileStatus,
    MarketingStorageResourceMode,
    MarketingTextStatus,
    MarketingTopicStatus,
)


class TopicCreate(BaseModel):
    title: str = Field(min_length=1, max_length=512)
    rubric: str = Field(min_length=1, max_length=128)
    angle: str | None = None
    source: str = Field(default="manual", max_length=64)
    status: MarketingTopicStatus = MarketingTopicStatus.DRAFT
    priority: int = 0
    reusable: bool = False
    recommended_channels: list[str] = Field(default_factory=list)
    legacy_topic_id: str | None = Field(default=None, max_length=64)
    slug_hint: str | None = Field(default=None, max_length=128)
    metadata_json: dict = Field(default_factory=dict)
    # M7-A editorial fields → merged into metadata_json (no migration)
    audience: str | None = Field(default=None, max_length=512)
    pain: str | None = None
    insight: str | None = None
    source_ref: str | None = None
    cta: str | None = Field(default=None, max_length=512)
    funnel_stage: str | None = Field(default=None, max_length=64)
    notes: str | None = None
    planned_date: str | None = Field(default=None, max_length=32)


class TopicUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=512)
    rubric: str | None = Field(default=None, min_length=1, max_length=128)
    angle: str | None = None
    source: str | None = Field(default=None, max_length=64)
    status: MarketingTopicStatus | None = None
    priority: int | None = None
    reusable: bool | None = None
    recommended_channels: list[str] | None = None
    legacy_topic_id: str | None = Field(default=None, max_length=64)
    slug_hint: str | None = Field(default=None, max_length=128)
    metadata_json: dict | None = None
    audience: str | None = Field(default=None, max_length=512)
    pain: str | None = None
    insight: str | None = None
    source_ref: str | None = None
    cta: str | None = Field(default=None, max_length=512)
    funnel_stage: str | None = Field(default=None, max_length=64)
    notes: str | None = None
    planned_date: str | None = Field(default=None, max_length=32)


class TopicResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    legacy_topic_id: str | None
    title: str
    rubric: str
    angle: str | None
    source: str
    status: MarketingTopicStatus
    priority: int
    reusable: bool
    recommended_channels: list
    used_count: int
    last_used_at: datetime | None
    slug_hint: str | None
    metadata_json: dict
    # Flattened editorial fields (read from metadata_json)
    audience: str | None = None
    pain: str | None = None
    insight: str | None = None
    source_ref: str | None = None
    cta: str | None = None
    funnel_stage: str | None = None
    notes: str | None = None
    planned_date: str | None = None
    created_at: datetime
    updated_at: datetime
    duplicate_status: Literal["ok", "warning", "blocked"] | None = None
    duplicate_detail: str | None = None


class TakeTopicRequest(BaseModel):
    planned_date: date | None = None
    slug: str | None = Field(default=None, max_length=128)
    source: str = Field(default="console", max_length=64)


class PackTextStubResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    channel: MarketingChannel
    text: str
    status: str
    char_count: int
    version: int


class TakeTopicPackResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    topic_id: uuid.UUID | None
    slug: str
    pack_dir_name: str | None
    title: str
    planned_date: date
    status: str
    approval_status: str
    publish_status: str
    source: str
    texts: list[PackTextStubResponse] = Field(default_factory=list)


class MarketingHealthResponse(BaseModel):
    status: str = "ok"
    module: str = "marketing"


class TopicSummaryInPack(BaseModel):
    """Nested topic on pack list/detail. M7-B: editorial fields from metadata_json."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    legacy_topic_id: str | None
    title: str
    rubric: str
    status: MarketingTopicStatus
    angle: str | None = None
    priority: int = 0
    audience: str | None = None
    pain: str | None = None
    insight: str | None = None
    source_ref: str | None = None
    cta: str | None = None
    funnel_stage: str | None = None
    notes: str | None = None
    planned_date: str | None = None


class PackTextResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    channel: MarketingChannel
    text: str
    status: MarketingTextStatus
    char_count: int
    version: int
    created_at: datetime
    updated_at: datetime


class PackMediaAssetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: str
    file_name: str
    mime_type: str
    storage_provider: str
    storage_key: str
    public_url: str | None
    preview_url: str | None
    width: int | None
    height: int | None
    alt_text: str | None
    status: MarketingMediaAssetStatus
    validation_status: MarketingMediaValidationStatus = (
        MarketingMediaValidationStatus.LEGACY_UNVERIFIED
    )
    created_at: datetime
    updated_at: datetime


class PackPublishLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    channel: str
    action: str
    status: str
    external_url: str | None
    external_post_id: str | None
    published_at: datetime | None
    error_message: str | None
    actor: str | None
    created_at: datetime


class PackSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    topic_id: uuid.UUID | None
    slug: str
    pack_dir_name: str | None
    title: str
    planned_date: date
    status: MarketingPackStatus
    preflight_status: MarketingPreflightStatus
    approval_status: MarketingApprovalStatus
    publish_status: MarketingPublishStatus
    source: str
    created_by_user_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
    topic: TopicSummaryInPack | None = None


class PackDetailResponse(PackSummaryResponse):
    campaign_id: uuid.UUID | None = None
    plan_item_id: uuid.UUID | None = None
    preflight_at: datetime | None = None
    preflight_report_json: dict = Field(default_factory=dict)
    approved_at: datetime | None = None
    approved_by_user_id: uuid.UUID | None = None
    channel_config_json: dict = Field(default_factory=dict)
    legacy_git_path: str | None = None
    metadata_json: dict = Field(default_factory=dict)
    texts: list[PackTextResponse] = Field(default_factory=list)
    media_assets: list[PackMediaAssetResponse] = Field(default_factory=list)
    publish_logs: list[PackPublishLogResponse] = Field(default_factory=list)


class PackCreate(BaseModel):
    title: str = Field(min_length=1, max_length=512)
    slug: str | None = Field(default=None, max_length=128)
    planned_date: date | None = None
    topic_id: uuid.UUID | None = None
    source: str = Field(default="console", max_length=64)
    metadata_json: dict = Field(default_factory=dict)


class PackUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=512)
    topic_id: uuid.UUID | None = None
    source: str | None = Field(default=None, max_length=64)
    status: MarketingPackStatus | None = None


class PackTextUpsert(BaseModel):
    text: str = ""
    status: MarketingTextStatus | None = None


class MediaCreate(BaseModel):
    file_name: str = Field(min_length=1, max_length=255)
    mime_type: str = Field(min_length=1, max_length=128)
    storage_provider: str = Field(default="git_path", max_length=32)
    storage_key: str = Field(min_length=1, max_length=1024)
    public_url: str | None = Field(default=None, max_length=1024)
    preview_url: str | None = Field(default=None, max_length=1024)
    width: int | None = Field(default=None, ge=1)
    height: int | None = Field(default=None, ge=1)
    role: str = Field(default="instagram_feed", max_length=64)
    alt_text: str | None = Field(default=None, max_length=512)
    metadata_json: dict = Field(default_factory=dict)


class MediaUpdate(BaseModel):
    file_name: str | None = Field(default=None, min_length=1, max_length=255)
    mime_type: str | None = Field(default=None, max_length=128)
    storage_provider: str | None = Field(default=None, max_length=32)
    storage_key: str | None = Field(default=None, max_length=1024)
    public_url: str | None = Field(default=None, max_length=1024)
    preview_url: str | None = Field(default=None, max_length=1024)
    width: int | None = Field(default=None, ge=1)
    height: int | None = Field(default=None, ge=1)
    role: str | None = Field(default=None, max_length=64)
    alt_text: str | None = Field(default=None, max_length=512)
    status: MarketingMediaAssetStatus | None = None
    metadata_json: dict | None = None


class PreflightIssue(BaseModel):
    code: str
    message: str
    channel: str | None = None


class PreflightCheckItem(BaseModel):
    code: str
    passed: bool
    message: str | None = None
    channel: str | None = None


class PreflightRequest(BaseModel):
    channels: list[MarketingChannel] | None = None
    strict: bool = True


class PreflightResponse(BaseModel):
    """M7-C1: additive v2 fields; keep errors/checks for FE compatibility."""

    pack_id: uuid.UUID
    status: Literal["passed", "failed", "warning"]
    checked_at: datetime
    errors: list[PreflightIssue] = Field(default_factory=list)
    warnings: list[PreflightIssue] = Field(default_factory=list)
    checks: list[PreflightCheckItem] = Field(default_factory=list)
    channel_eligibility: dict[str, bool] = Field(default_factory=dict)
    pack_status: MarketingPackStatus
    preflight_status: MarketingPreflightStatus
    approval_status: MarketingApprovalStatus
    # M7-C1 report v2 (also stored in preflight_report_json)
    version: str = "m7-c1"
    passed: bool = False
    blockers: list[PreflightIssue] = Field(default_factory=list)
    checklist: list[PreflightCheckItem] = Field(default_factory=list)
    topic_context_summary: dict | None = None
    channel_checks: list[dict] = Field(default_factory=list)
    media_checks: dict = Field(default_factory=dict)


class ApproveRequest(BaseModel):
    note: str | None = Field(default=None, max_length=1024)


class RejectRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=1024)


# --- M7-D historical publish (no outbound publisher) ---

HistoricalPublishChannel = Literal[
    "telegram",
    "instagram",
    "threads",
    "insights",
    "insights_site",
    "manual",
    "external",
]

HistoricalPublishSource = Literal[
    "historical_import",
    "margosya_archive",
    "manual",
]


class HistoricalPublishRequest(BaseModel):
    channels: list[HistoricalPublishChannel] = Field(min_length=1)
    published_at: datetime | None = None
    source: HistoricalPublishSource = "historical_import"
    external_url: str | None = Field(default=None, max_length=1024)
    evidence_ref: str | None = Field(default=None, max_length=512)
    note: str | None = Field(default=None, max_length=2048)
    target_social_channels: list[HistoricalPublishChannel] | None = None
    needs_review: bool = False
    update_publish_status: bool = True


class HistoricalPublishChannelResult(BaseModel):
    channel: str
    status: Literal["created", "existing", "skipped"]
    log_id: uuid.UUID | None = None


class HistoricalPublishResponse(BaseModel):
    pack_id: uuid.UUID
    publish_status: MarketingPublishStatus
    pack_status: MarketingPackStatus
    approval_status: MarketingApprovalStatus
    logs_created: int
    skipped_existing: int
    needs_review: bool = False
    channel_results: list[HistoricalPublishChannelResult] = Field(default_factory=list)


# --- M8-B internal service view (not exposed via HTTP routes) ---


class PublishingConnectionView(BaseModel):
    """Service-layer DTO; never includes secret_ref (has_secret only)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    provider: MarketingPublishingProvider
    account_display_name: str
    account_identifier: str | None
    status: MarketingPublishingConnectionStatus
    token_status: MarketingPublishingTokenStatus
    has_secret: bool
    scopes_json: list[str] = Field(default_factory=list)
    expires_at: datetime | None = None
    last_checked_at: datetime | None = None
    last_error_code: str | None = None
    last_error_message_redacted: str | None = None
    metadata_json: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    created_by_user_id: uuid.UUID | None = None
    updated_by_user_id: uuid.UUID | None = None


# --- M8-C2a storage profiles / managed media (domain DTOs; no HTTP routes) ---


class StorageResourceProfileView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    mode: MarketingStorageResourceMode
    status: MarketingStorageProfileStatus
    is_default: bool = False
    display_name: str
    max_upload_bytes: int | None = None
    max_url_length: int | None = None
    allowed_mime_types: list[str] | None = None
    created_at: datetime
    updated_at: datetime
    created_by_user_id: uuid.UUID | None = None
    updated_by_user_id: uuid.UUID | None = None


class ManagedMediaAssetView(BaseModel):
    """Internal view for Mode A/B lifecycle — never exposes credentials."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    pack_id: uuid.UUID | None = None
    role: str
    file_name: str
    mime_type: str
    storage_provider: str
    status: MarketingMediaAssetStatus
    validation_status: MarketingMediaValidationStatus
    declared_mime_type: str | None = None
    declared_size_bytes: int | None = None
    verified_mime_type: str | None = None
    verified_size_bytes: int | None = None
    resource_mode: MarketingStorageResourceMode | None = None
    storage_profile_id: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime
