import enum


class ProcessOverlayActivationState(str, enum.Enum):
    INACTIVE = "inactive"
    ACTIVE = "active"


class ProcessRunState(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
