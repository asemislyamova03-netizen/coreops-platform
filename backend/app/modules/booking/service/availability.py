"""Availability checks for Booking — overlap detection on UTC instants."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.core.modules import ModuleGuard
from app.modules.booking.exceptions import BookingAvailabilityError, BookingValidationError
from app.modules.booking.models import BookingBookableObject, BookingTerritory
from app.modules.booking.repository import BookingRepository
from app.modules.booking.schemas import (
    AvailabilityConflict,
    BookingAvailabilityCartInput,
    BookingAvailabilityResult,
    BookingStayRequest,
    ResolvedStayInterval,
)
from app.modules.booking.service.timezone import build_item_interval, utc_now


class BookingAvailabilityService:
    def __init__(self, db: Session, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.repo = BookingRepository(db)
        self.modules = ModuleGuard(db, tenant_id)

    def check_cart(
        self,
        cart: BookingAvailabilityCartInput,
        *,
        exclude_order_id: uuid.UUID | None = None,
        now_utc=None,
    ) -> BookingAvailabilityResult:
        self.modules.assert_enabled("booking")

        if not cart.items:
            raise BookingValidationError("Cart must contain at least one stay request")

        now = now_utc or utc_now()
        result = BookingAvailabilityResult()

        territory = self.repo.get_territory(self.tenant_id, cart.territory_id)
        if territory is None:
            raise BookingValidationError(f"Territory '{cart.territory_id}' not found")

        if not self.repo.territory_is_bookable(territory):
            result.validation_errors.append("Territory is not active")
            return result

        object_ids = [item.bookable_object_id for item in cart.items]
        objects_by_id = {
            obj.id: obj
            for obj in self.repo.list_objects_for_territory(
                self.tenant_id,
                cart.territory_id,
                object_ids,
            )
        }

        resolved_intervals: list[ResolvedStayInterval] = []

        for stay in cart.items:
            obj = objects_by_id.get(stay.bookable_object_id)
            if obj is None:
                result.validation_errors.append(
                    f"Object '{stay.bookable_object_id}' not found in territory"
                )
                continue

            if not self.repo.object_is_bookable(obj):
                result.validation_errors.append(f"Object '{obj.code}' is not available for booking")
                continue

            interval = build_item_interval(territory, obj, stay.check_in_date, stay.check_out_date)
            if interval.nights < territory.min_stay_nights:
                result.validation_errors.append(
                    f"Object '{obj.code}' requires at least {territory.min_stay_nights} night(s)"
                )
                continue

            resolved_intervals.append(interval)

            overlapping = self.repo.find_overlapping_items(
                obj.id,
                interval.check_in_at,
                interval.check_out_at,
                now_utc=now,
                exclude_order_id=exclude_order_id,
            )
            for existing in overlapping:
                result.conflicts.append(
                    AvailabilityConflict(
                        bookable_object_id=obj.id,
                        requested_check_in_at=interval.check_in_at,
                        requested_check_out_at=interval.check_out_at,
                        conflicting_item_id=existing.id,
                        conflicting_order_id=existing.booking_order_id,
                        conflicting_order_status=existing.order.status.value,
                    )
                )

        result.intervals = resolved_intervals
        return result

    def assert_cart_available(
        self,
        cart: BookingAvailabilityCartInput,
        *,
        exclude_order_id: uuid.UUID | None = None,
        now_utc=None,
    ) -> list[ResolvedStayInterval]:
        result = self.check_cart(
            cart,
            exclude_order_id=exclude_order_id,
            now_utc=now_utc,
        )

        if result.validation_errors:
            raise BookingValidationError("; ".join(result.validation_errors))

        if result.conflicts:
            raise BookingAvailabilityError(
                "One or more requested stays are not available",
                conflicts=result.conflicts,
            )

        return result.intervals

    def check_stay(
        self,
        territory: BookingTerritory,
        bookable_object: BookingBookableObject,
        stay: BookingStayRequest,
        *,
        exclude_order_id: uuid.UUID | None = None,
        now_utc=None,
    ) -> BookingAvailabilityResult:
        return self.check_cart(
            BookingAvailabilityCartInput(
                territory_id=territory.id,
                items=[stay],
            ),
            exclude_order_id=exclude_order_id,
            now_utc=now_utc,
        )
