"""Internal DTOs for Booking domain services (not HTTP API schemas)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime

from app.modules.booking.enums import BookingOrderSource


@dataclass(frozen=True)
class BookingHoldCartInput:
    territory_id: uuid.UUID
    guest_party_id: uuid.UUID
    source: BookingOrderSource
    items: list[BookingStayRequest]
    order_number: str | None = None


@dataclass(frozen=True)
class BookingStayRequest:
    bookable_object_id: uuid.UUID
    check_in_date: date
    check_out_date: date


@dataclass(frozen=True)
class BookingAvailabilityCartInput:
    territory_id: uuid.UUID
    items: list[BookingStayRequest]


@dataclass(frozen=True)
class ResolvedStayInterval:
    bookable_object_id: uuid.UUID
    check_in_date: date
    check_out_date: date
    check_in_at: datetime
    check_out_at: datetime
    nights: int


@dataclass(frozen=True)
class AvailabilityConflict:
    bookable_object_id: uuid.UUID
    requested_check_in_at: datetime
    requested_check_out_at: datetime
    conflicting_item_id: uuid.UUID
    conflicting_order_id: uuid.UUID
    conflicting_order_status: str


@dataclass
class BookingAvailabilityResult:
    intervals: list[ResolvedStayInterval] = field(default_factory=list)
    conflicts: list[AvailabilityConflict] = field(default_factory=list)
    validation_errors: list[str] = field(default_factory=list)

    @property
    def is_available(self) -> bool:
        return not self.conflicts and not self.validation_errors
