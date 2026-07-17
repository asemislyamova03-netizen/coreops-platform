"""Data access helpers for Booking domain services."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.modules.booking.enums import (
    BookableObjectStatus,
    BookingItemStatus,
    BookingOrderStatus,
    BookingTerritoryStatus,
)
from app.modules.booking.models import (
    BookingBookableObject,
    BookingItem,
    BookingOrder,
    BookingTerritory,
)
from app.modules.booking.service.timezone import utc_now


BLOCKING_ORDER_STATUSES = frozenset(
    {
        BookingOrderStatus.HELD,
        BookingOrderStatus.PENDING_PAYMENT,
        BookingOrderStatus.PAID,
        BookingOrderStatus.CONFIRMED,
    }
)


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def is_order_blocking(order: BookingOrder, now_utc: datetime | None = None) -> bool:
    now = _as_utc(now_utc or utc_now())

    if order.status in {BookingOrderStatus.CANCELLED, BookingOrderStatus.EXPIRED, BookingOrderStatus.DRAFT}:
        return False

    if order.status == BookingOrderStatus.HELD:
        if order.hold_expires_at is None:
            return False
        return _as_utc(order.hold_expires_at) > now

    return order.status in BLOCKING_ORDER_STATUSES


class BookingRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_territory(self, tenant_id: uuid.UUID, territory_id: uuid.UUID) -> BookingTerritory | None:
        return self.db.scalar(
            select(BookingTerritory).where(
                BookingTerritory.tenant_id == tenant_id,
                BookingTerritory.id == territory_id,
            )
        )

    def get_bookable_object(
        self,
        tenant_id: uuid.UUID,
        bookable_object_id: uuid.UUID,
    ) -> BookingBookableObject | None:
        return self.db.scalar(
            select(BookingBookableObject)
            .where(
                BookingBookableObject.tenant_id == tenant_id,
                BookingBookableObject.id == bookable_object_id,
            )
            .options(selectinload(BookingBookableObject.territory))
        )

    def list_objects_for_territory(
        self,
        tenant_id: uuid.UUID,
        territory_id: uuid.UUID,
        object_ids: list[uuid.UUID],
    ) -> list[BookingBookableObject]:
        if not object_ids:
            return []

        stmt = (
            select(BookingBookableObject)
            .where(
                BookingBookableObject.tenant_id == tenant_id,
                BookingBookableObject.territory_id == territory_id,
                BookingBookableObject.id.in_(object_ids),
            )
            .options(selectinload(BookingBookableObject.territory))
        )
        return list(self.db.scalars(stmt).all())

    def find_overlapping_items(
        self,
        bookable_object_id: uuid.UUID,
        check_in_at: datetime,
        check_out_at: datetime,
        *,
        now_utc: datetime | None = None,
        exclude_order_id: uuid.UUID | None = None,
    ) -> list[BookingItem]:
        """Return active items on the object whose order effectively blocks the interval."""
        now = now_utc or utc_now()

        stmt = (
            select(BookingItem)
            .join(BookingOrder, BookingItem.booking_order_id == BookingOrder.id)
            .where(
                BookingItem.bookable_object_id == bookable_object_id,
                BookingItem.status == BookingItemStatus.ACTIVE,
                BookingOrder.status.in_(BLOCKING_ORDER_STATUSES),
                BookingItem.check_in_at < check_out_at,
                BookingItem.check_out_at > check_in_at,
            )
            .options(selectinload(BookingItem.order))
        )

        if exclude_order_id is not None:
            stmt = stmt.where(BookingOrder.id != exclude_order_id)

        candidates = list(self.db.scalars(stmt).all())
        return [item for item in candidates if is_order_blocking(item.order, now)]

    def find_stale_held_orders(
        self,
        tenant_id: uuid.UUID,
        now_utc: datetime,
        *,
        territory_id: uuid.UUID | None = None,
    ) -> list[BookingOrder]:
        now = _as_utc(now_utc)
        stmt = (
            select(BookingOrder)
            .where(
                BookingOrder.tenant_id == tenant_id,
                BookingOrder.status == BookingOrderStatus.HELD,
                BookingOrder.hold_expires_at.is_not(None),
                BookingOrder.hold_expires_at <= now,
            )
            .options(selectinload(BookingOrder.items))
        )
        if territory_id is not None:
            stmt = stmt.where(BookingOrder.territory_id == territory_id)
        return list(self.db.scalars(stmt).all())

    def get_order(self, tenant_id: uuid.UUID, order_id: uuid.UUID) -> BookingOrder | None:
        return self.db.scalar(
            select(BookingOrder)
            .where(
                BookingOrder.tenant_id == tenant_id,
                BookingOrder.id == order_id,
            )
            .options(selectinload(BookingOrder.items))
        )

    def lock_bookable_objects(self, object_ids: list[uuid.UUID]) -> list[BookingBookableObject]:
        if not object_ids:
            return []

        ordered_ids = sorted(object_ids)
        stmt = (
            select(BookingBookableObject)
            .where(BookingBookableObject.id.in_(ordered_ids))
            .order_by(BookingBookableObject.id)
            .with_for_update()
        )
        locked = list(self.db.scalars(stmt).all())
        if len(locked) != len(ordered_ids):
            raise ValueError("Failed to lock all bookable objects for hold")
        return locked

    def next_order_number(self, tenant_id: uuid.UUID) -> str:
        count = self.db.scalar(
            select(func.count()).select_from(BookingOrder).where(BookingOrder.tenant_id == tenant_id)
        ) or 0
        year = date.today().year
        return f"BO-{year}-{count + 1:05d}"

    def territory_is_bookable(self, territory: BookingTerritory) -> bool:
        return territory.status == BookingTerritoryStatus.ACTIVE

    def object_is_bookable(self, bookable_object: BookingBookableObject) -> bool:
        return bookable_object.status == BookableObjectStatus.ACTIVE
