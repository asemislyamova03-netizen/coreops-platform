import enum


class BookingTerritoryStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class BookingOwnerStatus(str, enum.Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"


class BookableObjectStatus(str, enum.Enum):
    ACTIVE = "active"
    MAINTENANCE = "maintenance"
    UNLISTED = "unlisted"


class BookableObjectType(str, enum.Enum):
    CABIN = "cabin"
    ZONE = "zone"
    HALL = "hall"
    OTHER = "other"


class BookablePricingUnit(str, enum.Enum):
    PER_NIGHT = "per_night"
    PER_STAY = "per_stay"


class BookingOrderStatus(str, enum.Enum):
    DRAFT = "draft"
    HELD = "held"
    PENDING_PAYMENT = "pending_payment"
    PAID = "paid"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class BookingOrderSource(str, enum.Enum):
    PUBLIC_WEB = "public_web"
    ADMIN = "admin"
    TWOGIS = "2gis"
    EXTERNAL = "external"


class BookingItemStatus(str, enum.Enum):
    ACTIVE = "active"
    CANCELLED = "cancelled"


class BookingPermissionScope(str, enum.Enum):
    TERRITORY = "territory"
    OWNER = "owner"
    OBJECT = "object"


class BookingPermission(str, enum.Enum):
    VIEW = "view"
    MANAGE = "manage"
    FINANCE = "finance"
    NOTIFY = "notify"
