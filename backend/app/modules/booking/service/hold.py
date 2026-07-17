"""Hold creation and lazy expiry for Booking (E2b)."""

from __future__ import annotations

import uuid
from datetime import timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.entitlements import EntitlementService
from app.core.exceptions import NotFoundError
from app.core.modules import ModuleGuard
from app.modules.booking.enums import BookingItemStatus, BookingOrderStatus
from app.modules.booking.exceptions import BookingValidationError
from app.modules.booking.models import BookingBookableObject, BookingItem, BookingOrder, BookingTerritory
from app.modules.booking.repository import BookingRepository
from app.modules.booking.schemas import (
    BookingAvailabilityCartInput,
    BookingHoldCartInput,
    ResolvedStayInterval,
)
from app.modules.booking.service.availability import BookingAvailabilityService
from app.modules.booking.service.order import BookingOrderService
from app.modules.booking.service.timezone import utc_now
from app.modules.parties.repository import PartyRepository


class BookingHoldService:
    def __init__(self, db: Session, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.repo = BookingRepository(db)
        self.parties = PartyRepository(db)
        self.modules = ModuleGuard(db, tenant_id)
        self.entitlements = EntitlementService(db, tenant_id)
        self.availability = BookingAvailabilityService(db, tenant_id)
        self.orders = BookingOrderService(db, tenant_id)

    def expire_stale_holds(
        self,
        *,
        territory_id: uuid.UUID | None = None,
        now_utc=None,
    ) -> list[uuid.UUID]:
        self.modules.assert_enabled("booking")

        now = now_utc or utc_now()
        stale_orders = self.repo.find_stale_held_orders(
            self.tenant_id,
            now,
            territory_id=territory_id,
        )
        expired_ids: list[uuid.UUID] = []
        for order in stale_orders:
            self.orders.expire(order.id, now_utc=now)
            expired_ids.append(order.id)

        if expired_ids:
            self.db.commit()

        return expired_ids

    def create_hold(
        self,
        cart: BookingHoldCartInput,
        *,
        now_utc=None,
    ) -> BookingOrder:
        self.modules.assert_enabled("booking")
        self.entitlements.assert_feature("booking.orders.create")

        if not cart.items:
            raise BookingValidationError("Hold cart must contain at least one stay request")

        now = now_utc or utc_now()

        self.expire_stale_holds(territory_id=cart.territory_id, now_utc=now)

        territory = self.repo.get_territory(self.tenant_id, cart.territory_id)
        if territory is None:
            raise BookingValidationError(f"Territory '{cart.territory_id}' not found")

        if not self.parties.get_party(self.tenant_id, cart.guest_party_id):
            raise NotFoundError("Guest party not found")

        object_ids = sorted({item.bookable_object_id for item in cart.items})
        objects_by_id = {
            obj.id: obj
            for obj in self.repo.list_objects_for_territory(
                self.tenant_id,
                cart.territory_id,
                object_ids,
            )
        }
        if len(objects_by_id) != len(object_ids):
            raise BookingValidationError("One or more bookable objects were not found in territory")

        availability_cart = BookingAvailabilityCartInput(
            territory_id=cart.territory_id,
            items=cart.items,
        )

        try:
            self.repo.lock_bookable_objects(object_ids)
            intervals = self.availability.assert_cart_available(availability_cart, now_utc=now)
            order = self._persist_hold_order(cart, territory, objects_by_id, intervals, now)
            self.db.commit()
            self.db.refresh(order)
            return order
        except Exception:
            self.db.rollback()
            raise

    def _persist_hold_order(
        self,
        cart: BookingHoldCartInput,
        territory: BookingTerritory,
        objects_by_id: dict[uuid.UUID, BookingBookableObject],
        intervals: list[ResolvedStayInterval],
        now_utc,
    ) -> BookingOrder:
        hold_expires_at = now_utc + timedelta(minutes=territory.hold_duration_minutes)
        subtotal = Decimal("0")

        order = BookingOrder(
            tenant_id=self.tenant_id,
            territory_id=territory.id,
            order_number=cart.order_number or self.repo.next_order_number(self.tenant_id),
            guest_party_id=cart.guest_party_id,
            status=BookingOrderStatus.HELD,
            hold_expires_at=hold_expires_at,
            currency=territory.currency,
            source=cart.source,
        )
        self.db.add(order)
        self.db.flush()

        interval_by_object = {interval.bookable_object_id: interval for interval in intervals}

        for stay in cart.items:
            interval = interval_by_object[stay.bookable_object_id]
            obj = objects_by_id[stay.bookable_object_id]
            line_total = obj.base_price * interval.nights
            subtotal += line_total

            self.db.add(
                BookingItem(
                    tenant_id=self.tenant_id,
                    booking_order_id=order.id,
                    bookable_object_id=obj.id,
                    check_in_date=interval.check_in_date,
                    check_out_date=interval.check_out_date,
                    check_in_at=interval.check_in_at,
                    check_out_at=interval.check_out_at,
                    nights=interval.nights,
                    unit_price=obj.base_price,
                    line_total=line_total,
                    owner_id=obj.owner_id,
                    status=BookingItemStatus.ACTIVE,
                )
            )

        order.subtotal = subtotal
        self.db.flush()
        return order
