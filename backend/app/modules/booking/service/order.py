"""Booking order status transitions (E2b)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.modules.booking.enums import BookingItemStatus, BookingOrderStatus
from app.modules.booking.exceptions import BookingStatusTransitionError
from app.modules.booking.models import BookingOrder
from app.modules.booking.repository import BookingRepository
from app.modules.booking.service.timezone import utc_now

ALLOWED_TRANSITIONS: dict[BookingOrderStatus, frozenset[BookingOrderStatus]] = {
    BookingOrderStatus.DRAFT: frozenset({BookingOrderStatus.HELD}),
    BookingOrderStatus.HELD: frozenset(
        {
            BookingOrderStatus.PENDING_PAYMENT,
            BookingOrderStatus.CANCELLED,
            BookingOrderStatus.EXPIRED,
        }
    ),
    BookingOrderStatus.PENDING_PAYMENT: frozenset(
        {
            BookingOrderStatus.PAID,
            BookingOrderStatus.CANCELLED,
        }
    ),
    BookingOrderStatus.PAID: frozenset({BookingOrderStatus.CONFIRMED}),
}


class BookingOrderService:
    def __init__(self, db: Session, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.repo = BookingRepository(db)

    def get_order(self, order_id: uuid.UUID) -> BookingOrder:
        order = self.repo.get_order(self.tenant_id, order_id)
        if order is None:
            raise NotFoundError(f"Booking order '{order_id}' not found")
        return order

    def transition(
        self,
        order_id: uuid.UUID,
        target_status: BookingOrderStatus,
        *,
        now_utc: datetime | None = None,
    ) -> BookingOrder:
        order = self.get_order(order_id)
        now = now_utc or utc_now()
        self._validate_transition(order.status, target_status)
        self._apply_transition(order, target_status, now)
        self.db.flush()
        self.db.refresh(order)
        return order

    def submit_for_payment(self, order_id: uuid.UUID, *, now_utc: datetime | None = None) -> BookingOrder:
        order = self.transition(order_id, BookingOrderStatus.PENDING_PAYMENT, now_utc=now_utc)
        order.hold_expires_at = None
        self.db.flush()
        return order

    def mark_paid(self, order_id: uuid.UUID, *, now_utc: datetime | None = None) -> BookingOrder:
        return self.transition(order_id, BookingOrderStatus.PAID, now_utc=now_utc)

    def confirm(self, order_id: uuid.UUID, *, now_utc: datetime | None = None) -> BookingOrder:
        return self.transition(order_id, BookingOrderStatus.CONFIRMED, now_utc=now_utc)

    def cancel(self, order_id: uuid.UUID, *, now_utc: datetime | None = None) -> BookingOrder:
        return self.transition(order_id, BookingOrderStatus.CANCELLED, now_utc=now_utc)

    def expire(self, order_id: uuid.UUID, *, now_utc: datetime | None = None) -> BookingOrder:
        order = self.transition(order_id, BookingOrderStatus.EXPIRED, now_utc=now_utc)
        order.hold_expires_at = None
        self.db.flush()
        return order

    def _validate_transition(
        self,
        current: BookingOrderStatus,
        target: BookingOrderStatus,
    ) -> None:
        allowed = ALLOWED_TRANSITIONS.get(current, frozenset())
        if target not in allowed:
            raise BookingStatusTransitionError(
                f"Cannot transition booking order from '{current.value}' to '{target.value}'",
                current_status=current.value,
                target_status=target.value,
            )

    def _apply_transition(
        self,
        order: BookingOrder,
        target: BookingOrderStatus,
        now_utc: datetime,
    ) -> None:
        if target == BookingOrderStatus.CANCELLED:
            order.cancelled_at = now_utc
            for item in order.items:
                if item.status == BookingItemStatus.ACTIVE:
                    item.status = BookingItemStatus.CANCELLED

        if target == BookingOrderStatus.CONFIRMED:
            order.confirmed_at = now_utc

        order.status = target
