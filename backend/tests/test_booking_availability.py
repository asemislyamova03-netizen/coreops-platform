"""E2a availability overlap and multi-object tests for Flexity Booking."""

from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal

import pytest

from app.modules.booking.enums import (
    BookableObjectType,
    BookingItemStatus,
    BookingOrderSource,
    BookingOrderStatus,
)
from app.modules.booking.exceptions import BookingAvailabilityError, BookingValidationError
from app.modules.booking.models import BookingBookableObject, BookingItem, BookingOrder
from app.modules.booking.repository import is_order_blocking
from app.modules.booking.schemas import BookingAvailabilityCartInput, BookingStayRequest
from app.modules.booking.service.availability import BookingAvailabilityService
from app.modules.module_registry.service import ModuleRegistryService
from tests.test_booking_models import _bootstrap_booking_graph


def _enable_booking_modules(db_session, tenant_id):
    service = ModuleRegistryService(db_session)
    service.provision_tenant_modules(tenant_id)
    service.enable_modules_ordered(tenant_id, ["parties", "booking"])
    db_session.commit()


def _create_blocking_order(
    db_session,
    *,
    tenant,
    territory,
    owner,
    obj,
    guest_party,
    status: BookingOrderStatus,
    check_in_at: datetime,
    check_out_at: datetime,
    hold_expires_at: datetime | None = None,
):
    order = BookingOrder(
        tenant_id=tenant.id,
        territory_id=territory.id,
        order_number=f"BO-BLOCK-{obj.code}",
        guest_party_id=guest_party.id,
        status=status,
        hold_expires_at=hold_expires_at,
        currency="KZT",
        source=BookingOrderSource.PUBLIC_WEB,
    )
    db_session.add(order)
    db_session.flush()

    db_session.add(
        BookingItem(
            tenant_id=tenant.id,
            booking_order_id=order.id,
            bookable_object_id=obj.id,
            check_in_date=check_in_at.date(),
            check_out_date=check_out_at.date(),
            check_in_at=check_in_at,
            check_out_at=check_out_at,
            nights=max((check_out_at.date() - check_in_at.date()).days, 1),
            unit_price=Decimal("10000.00"),
            line_total=Decimal("10000.00"),
            owner_id=owner.id,
            status=BookingItemStatus.ACTIVE,
        )
    )
    db_session.commit()
    return order


def test_is_order_blocking_rules():
    now = datetime(2026, 8, 1, 12, 0, tzinfo=UTC)

    held_active = BookingOrder(
        status=BookingOrderStatus.HELD,
        hold_expires_at=now + timedelta(minutes=30),
    )
    held_expired = BookingOrder(
        status=BookingOrderStatus.HELD,
        hold_expires_at=now - timedelta(minutes=1),
    )
    confirmed = BookingOrder(status=BookingOrderStatus.CONFIRMED)
    cancelled = BookingOrder(status=BookingOrderStatus.CANCELLED)

    assert is_order_blocking(held_active, now) is True
    assert is_order_blocking(held_expired, now) is False
    assert is_order_blocking(confirmed, now) is True
    assert is_order_blocking(cancelled, now) is False


def test_availability_empty_cart_requires_items(db_session):
    tenant, territory, _owner, _obj, _guest = _bootstrap_booking_graph(db_session)
    _enable_booking_modules(db_session, tenant.id)

    service = BookingAvailabilityService(db_session, tenant.id)
    with pytest.raises(BookingValidationError):
        service.check_cart(BookingAvailabilityCartInput(territory_id=territory.id, items=[]))


def test_availability_no_conflict_when_cart_is_free(db_session):
    tenant, territory, owner, obj, guest = _bootstrap_booking_graph(db_session)
    _enable_booking_modules(db_session, tenant.id)

    service = BookingAvailabilityService(db_session, tenant.id)
    result = service.check_cart(
        BookingAvailabilityCartInput(
            territory_id=territory.id,
            items=[
                BookingStayRequest(
                    bookable_object_id=obj.id,
                    check_in_date=date(2026, 9, 1),
                    check_out_date=date(2026, 9, 3),
                )
            ],
        )
    )

    assert result.is_available
    assert len(result.intervals) == 1
    assert result.intervals[0].check_in_at == datetime(2026, 9, 1, 10, 0, tzinfo=UTC)


def test_availability_detects_confirmed_overlap(db_session):
    tenant, territory, owner, obj, guest = _bootstrap_booking_graph(db_session)
    _enable_booking_modules(db_session, tenant.id)

    _create_blocking_order(
        db_session,
        tenant=tenant,
        territory=territory,
        owner=owner,
        obj=obj,
        guest_party=guest,
        status=BookingOrderStatus.CONFIRMED,
        check_in_at=datetime(2026, 9, 1, 10, 0, tzinfo=UTC),
        check_out_at=datetime(2026, 9, 3, 6, 0, tzinfo=UTC),
    )

    service = BookingAvailabilityService(db_session, tenant.id)
    result = service.check_cart(
        BookingAvailabilityCartInput(
            territory_id=territory.id,
            items=[
                BookingStayRequest(
                    bookable_object_id=obj.id,
                    check_in_date=date(2026, 9, 2),
                    check_out_date=date(2026, 9, 4),
                )
            ],
        )
    )

    assert not result.is_available
    assert len(result.conflicts) == 1
    assert result.conflicts[0].conflicting_order_status == "confirmed"


def test_availability_ignores_expired_hold(db_session):
    tenant, territory, owner, obj, guest = _bootstrap_booking_graph(db_session)
    _enable_booking_modules(db_session, tenant.id)
    now = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)

    _create_blocking_order(
        db_session,
        tenant=tenant,
        territory=territory,
        owner=owner,
        obj=obj,
        guest_party=guest,
        status=BookingOrderStatus.HELD,
        check_in_at=datetime(2026, 9, 1, 10, 0, tzinfo=UTC),
        check_out_at=datetime(2026, 9, 3, 6, 0, tzinfo=UTC),
        hold_expires_at=now - timedelta(minutes=5),
    )

    service = BookingAvailabilityService(db_session, tenant.id)
    result = service.check_cart(
        BookingAvailabilityCartInput(
            territory_id=territory.id,
            items=[
                BookingStayRequest(
                    bookable_object_id=obj.id,
                    check_in_date=date(2026, 9, 1),
                    check_out_date=date(2026, 9, 3),
                )
            ],
        ),
        now_utc=now,
    )

    assert result.is_available


def test_multi_object_availability_one_conflict_blocks_cart(db_session):
    tenant, territory, owner, obj, guest = _bootstrap_booking_graph(db_session)
    _enable_booking_modules(db_session, tenant.id)

    obj_two = BookingBookableObject(
        tenant_id=tenant.id,
        territory_id=territory.id,
        owner_id=owner.id,
        code="cabin-2",
        name="Cabin 2",
        object_type=BookableObjectType.CABIN,
        base_price=Decimal("12000.00"),
    )
    db_session.add(obj_two)
    db_session.commit()

    _create_blocking_order(
        db_session,
        tenant=tenant,
        territory=territory,
        owner=owner,
        obj=obj,
        guest_party=guest,
        status=BookingOrderStatus.CONFIRMED,
        check_in_at=datetime(2026, 10, 1, 10, 0, tzinfo=UTC),
        check_out_at=datetime(2026, 10, 3, 6, 0, tzinfo=UTC),
    )

    service = BookingAvailabilityService(db_session, tenant.id)
    result = service.check_cart(
        BookingAvailabilityCartInput(
            territory_id=territory.id,
            items=[
                BookingStayRequest(
                    bookable_object_id=obj.id,
                    check_in_date=date(2026, 10, 2),
                    check_out_date=date(2026, 10, 4),
                ),
                BookingStayRequest(
                    bookable_object_id=obj_two.id,
                    check_in_date=date(2026, 10, 5),
                    check_out_date=date(2026, 10, 7),
                ),
            ],
        )
    )

    assert not result.is_available
    assert len(result.conflicts) == 1
    assert result.conflicts[0].bookable_object_id == obj.id
    assert len(result.intervals) == 2


def test_assert_cart_available_raises_on_conflict(db_session):
    tenant, territory, owner, obj, guest = _bootstrap_booking_graph(db_session)
    _enable_booking_modules(db_session, tenant.id)

    _create_blocking_order(
        db_session,
        tenant=tenant,
        territory=territory,
        owner=owner,
        obj=obj,
        guest_party=guest,
        status=BookingOrderStatus.CONFIRMED,
        check_in_at=datetime(2026, 11, 1, 10, 0, tzinfo=UTC),
        check_out_at=datetime(2026, 11, 3, 6, 0, tzinfo=UTC),
    )

    service = BookingAvailabilityService(db_session, tenant.id)
    with pytest.raises(BookingAvailabilityError) as exc_info:
        service.assert_cart_available(
            BookingAvailabilityCartInput(
                territory_id=territory.id,
                items=[
                    BookingStayRequest(
                        bookable_object_id=obj.id,
                        check_in_date=date(2026, 11, 1),
                        check_out_date=date(2026, 11, 3),
                    )
                ],
            )
        )

    assert exc_info.value.conflicts
