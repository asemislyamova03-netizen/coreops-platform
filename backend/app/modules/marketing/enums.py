import enum


class MarketingTopicStatus(str, enum.Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    USED = "used"
    ARCHIVED = "archived"


class MarketingPackStatus(str, enum.Enum):
    DRAFT = "draft"
    PREFLIGHT_FAILED = "preflight_failed"
    READY_FOR_APPROVAL = "ready_for_approval"
    APPROVED = "approved"
    SCHEDULED = "scheduled"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    FAILED = "failed"
    ARCHIVED = "archived"


class MarketingPreflightStatus(str, enum.Enum):
    NOT_RUN = "not_run"
    PASSED = "passed"
    FAILED = "failed"


class MarketingApprovalStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class MarketingPublishStatus(str, enum.Enum):
    NOT_STARTED = "not_started"
    PARTIAL = "partial"
    PUBLISHED = "published"
    FAILED = "failed"


class MarketingChannel(str, enum.Enum):
    TELEGRAM = "telegram"
    INSTAGRAM = "instagram"
    THREADS = "threads"
    INSIGHTS = "insights"


class MarketingTextStatus(str, enum.Enum):
    DRAFT = "draft"
    READY = "ready"
    APPROVED = "approved"


class MarketingMediaAssetStatus(str, enum.Enum):
    PENDING = "pending"
    STORED = "stored"
    FAILED = "failed"
    ARCHIVED = "archived"


class MarketingAttributionTouchType(str, enum.Enum):
    FIRST_TOUCH = "first_touch"
    ASSISTED = "assisted"
    CONVERTED = "converted"


DEFAULT_PACK_CHANNELS: tuple[MarketingChannel, ...] = (
    MarketingChannel.TELEGRAM,
    MarketingChannel.INSTAGRAM,
    MarketingChannel.THREADS,
    MarketingChannel.INSIGHTS,
)

ALLOWED_MEDIA_MIME_TYPES: frozenset[str] = frozenset(
    {
        "image/png",
        "image/jpeg",
        "image/jpg",
        "image/webp",
    }
)
