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


class MarketingPublishingProvider(str, enum.Enum):
    TELEGRAM = "telegram"
    INSTAGRAM = "instagram"
    THREADS = "threads"
    TIKTOK = "tiktok"


class MarketingPublishingConnectionStatus(str, enum.Enum):
    NOT_CONNECTED = "not_connected"
    ACTIVE = "active"
    ERROR = "error"
    DISABLED = "disabled"
    EXPIRED = "expired"


class MarketingPublishingTokenStatus(str, enum.Enum):
    NOT_CONFIGURED = "not_configured"
    VALID = "valid"
    EXPIRING = "expiring"
    INVALID = "invalid"


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


class MarketingStorageResourceMode(str, enum.Enum):
    FLEXITY_MANAGED = "flexity_managed"
    CLIENT_PUBLIC_URL = "client_public_url"
    CLIENT_BUCKET = "client_bucket"  # reserved/deferred — reject activation in C2a


class MarketingStorageProfileStatus(str, enum.Enum):
    ACTIVE = "active"
    DISABLED = "disabled"


class MarketingMediaValidationStatus(str, enum.Enum):
    """Safety/eligibility track — orthogonal to MarketingMediaAssetStatus lifecycle."""

    LEGACY_UNVERIFIED = "legacy_unverified"
    REGISTERED_UNVERIFIED = "registered_unverified"
    VALIDATED_METADATA = "validated_metadata"
    REJECTED = "rejected"
    ARCHIVED = "archived"


# M8-C2a image MIME set (video deferred). image/jpg normalizes to image/jpeg.
C2A_ALLOWED_MEDIA_MIME_TYPES: frozenset[str] = frozenset(
    {
        "image/png",
        "image/jpeg",
        "image/webp",
    }
)

DEFAULT_MAX_UPLOAD_BYTES: int = 10 * 1024 * 1024  # 10 MiB
DEFAULT_MAX_URL_LENGTH: int = 1024
MAX_UPLOAD_BYTES_HARD_CAP: int = 50 * 1024 * 1024
MAX_URL_LENGTH_HARD_CAP: int = 2048
