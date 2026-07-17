from app.core.exceptions import ConflictError, CoreOpsError


class BookingError(CoreOpsError):
    """Base error for Flexity Booking domain logic."""


class BookingTimezoneError(BookingError):
    """Invalid timezone, local datetime, or stay interval."""


class BookingAvailabilityError(ConflictError):
    """Requested stay overlaps an existing blocking booking."""

    def __init__(
        self,
        message: str = "Booking slot is not available",
        *,
        conflicts: list | None = None,
    ):
        super().__init__(message)
        self.conflicts = conflicts or []


class BookingValidationError(BookingError):
    """Territory, object, or cart input failed validation."""


class BookingStatusTransitionError(BookingError):
    """Invalid booking order status transition."""

    def __init__(
        self,
        message: str = "Invalid booking order status transition",
        *,
        current_status: str | None = None,
        target_status: str | None = None,
    ):
        super().__init__(message)
        self.current_status = current_status
        self.target_status = target_status
