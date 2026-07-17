"""E2b hold, status machine, and atomicity tests for Flexity Booking."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.core.enums import SubscriptionStatus
from app.modules.booking.enums import (
    BookableObjectType,
    BookingItemStatus,
    BookingOrderSource,
    BookingOrderStatus,
)
from app.modules.booking.exceptions import (
    BookingAvailabilityError,
    BookingStatusTransitionError,
)
from app.modules.booking.models import BookingBookableObject, BookingItem, BookingOrder
from app.modules.booking.schemas import BookingHoldCartInput, BookingStayRequest
from app.modules.booking.service.availability import BookingAvailabilityService
from app.modules.booking.service.hold import BookingHoldService
from app.modules.booking.service.order import BookingOrderService
from app.modules.module_registry.service import ModuleRegistryService
from app.modules.subscriptions.repository import SubscriptionRepository
from tests.test_booking_availability import _create_blocking_order, _enable_booking_modules
from tests.test_booking_models import _bootstrap_booking_graph


def _setup_tenant_for_hold(db_session, tenant_id):
    _enable_booking_modules(db_session, tenant_id)
    repo = SubscriptionRepository(db_session)
    plan = repo.get_plan_by_code("enterprise")
    assert plan is not None
    repo.upsert_subscription(
        tenant_id=tenant_id,
        plan_id=plan.id,
        status=SubscriptionStatus.TRIAL,
    )
    db_session.commit()


def _hold_cart(territory_id, guest_id, obj_id, **date_kwargs):
    return BookingHoldCartInput(
        territory_id=territory_id,
        guest_party_id=guest_id,
        source=BookingOrderSource.PUBLIC_WEB,
        items=[
            BookingStayRequest(
                bookable_object_id=obj_id,
                check_in_date=date_kwargs.get("check_in_date", date(2026, 12, 1)),
                check_out_date=date_kwargs.get("check_out_date", date(2026, 12, 3)),
            )
        ],
    )


def test_create_hold_sets_status_and_expiry(db_session):
    tenant, territory, _owner, obj, guest = _bootstrap_booking_graph(db_session)
    _setup_tenant_for_hold(db_session, tenant.id)
    now = datetime(2026, 12, 1, 8, 0, tzinfo=UTC)

    order = BookingHoldService(db_session, tenant.id).create_hold(
        _hold_cart(territory.id, guest.id, obj.id),
        now_utc=now,
    )

    assert order.status == BookingOrderStatus.HELD
    assert order.hold_expires_at is not None
    expected_expiry = now + timedelta(minutes=territory.hold_duration_minutes)
    actual_expiry = order.hold_expires_at
    if actual_expiry.tzinfo is None:
        actual_expiry = actual_expiry.replace(tzinfo=UTC)
    assert actual_expiry == expected_expiry
    assert len(order.items) == 1
    assert order.items[0].status == BookingItemStatus.ACTIVE


def test_create_hold_multi_object_atomic(db_session):
    tenant, territory, owner, obj, guest = _bootstrap_booking_graph(db_session)
    _setup_tenant_for_hold(db_session, tenant.id)

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

    order = BookingHoldService(db_session, tenant.id).create_hold(
        BookingHoldCartInput(
            territory_id=territory.id,
            guest_party_id=guest.id,
            source=BookingOrderSource.PUBLIC_WEB,
            items=[
                BookingStayRequest(obj.id, date(2026, 12, 10), date(2026, 12, 12)),
                BookingStayRequest(obj_two.id, date(2026, 12, 15), date(2026, 12, 17)),
            ],
        )
    )

    assert len(order.items) == 2
    assert order.subtotal > 0


def test_create_hold_rolls_back_when_cart_unavailable(db_session):
    tenant, territory, owner, obj, guest = _bootstrap_booking_graph(db_session)
    _setup_tenant_for_hold(db_session, tenant.id)

    _create_blocking_order(
        db_session,
        tenant=tenant,
        territory=territory,
        owner=owner,
        obj=obj,
        guest_party=guest,
        status=BookingOrderStatus.CONFIRMED,
        check_in_at=datetime(2026, 12, 1, 10, 0, tzinfo=UTC),
        check_out_at=datetime(2026, 12, 3, 6, 0, tzinfo=UTC),
    )

    before = db_session.scalar(select(func.count()).select_from(BookingOrder)) or 0

    with pytest.raises(BookingAvailabilityError):
        BookingHoldService(db_session, tenant.id).create_hold(
            _hold_cart(territory.id, guest.id, obj.id)
        )

    after = db_session.scalar(select(func.count()).select_from(BookingOrder)) or 0
    assert after == before


def test_expire_stale_holds_transitions_to_expired(db_session):
    tenant, territory, owner, obj, guest = _bootstrap_booking_graph(db_session)
    _setup_tenant_for_hold(db_session, tenant.id)
    now = datetime(2026, 12, 1, 12, 0, tzinfo=UTC)

    order = BookingHoldService(db_session, tenant.id).create_hold(
        _hold_cart(territory.id, guest.id, obj.id),
        now_utc=now - timedelta(minutes=40),
    )
    assert order.status == BookingOrderStatus.HELD

    expired_ids = BookingHoldService(db_session, tenant.id).expire_stale_holds(
        territory_id=territory.id,
        now_utc=now,
    )

    assert order.id in expired_ids
    stored = db_session.get(BookingOrder, order.id)
    assert stored.status == BookingOrderStatus.EXPIRED


def test_lazy_expire_allows_new_hold_after_previous_expired(db_session):
    tenant, territory, owner, obj, guest = _bootstrap_booking_graph(db_session)
    _setup_tenant_for_hold(db_session, tenant.id)
    now = datetime(2026, 12, 5, 12, 0, tzinfo=UTC)
    hold_service = BookingHoldService(db_session, tenant.id)

    first = hold_service.create_hold(
        _hold_cart(territory.id, guest.id, obj.id, check_in_date=date(2026, 12, 20), check_out_date=date(2026, 12, 22)),
        now_utc=now - timedelta(minutes=45),
    )
    assert first.status == BookingOrderStatus.HELD

    second = hold_service.create_hold(
        _hold_cart(territory.id, guest.id, obj.id, check_in_date=date(2026, 12, 20), check_out_date=date(2026, 12, 22)),
        now_utc=now,
    )

    assert second.id != first.id
    assert second.status == BookingOrderStatus.HELD
    assert db_session.get(BookingOrder, first.id).status == BookingOrderStatus.EXPIRED


def test_second_active_hold_on_same_slot_fails(db_session):
    tenant, territory, _owner, obj, guest = _bootstrap_booking_graph(db_session)
    _setup_tenant_for_hold(db_session, tenant.id)
    hold_service = BookingHoldService(db_session, tenant.id)

    hold_service.create_hold(_hold_cart(territory.id, guest.id, obj.id))

    with pytest.raises(BookingAvailabilityError):
        hold_service.create_hold(_hold_cart(territory.id, guest.id, obj.id))


def test_status_machine_happy_path(db_session):
    tenant, territory, _owner, obj, guest = _bootstrap_booking_graph(db_session)
    _setup_tenant_for_hold(db_session, tenant.id)

    order = BookingHoldService(db_session, tenant.id).create_hold(
        _hold_cart(territory.id, guest.id, obj.id)
    )
    order_service = BookingOrderService(db_session, tenant.id)

    order = order_service.submit_for_payment(order.id)
    assert order.status == BookingOrderStatus.PENDING_PAYMENT
    assert order.hold_expires_at is None

    order = order_service.mark_paid(order.id)
    assert order.status == BookingOrderStatus.PAID

    order = order_service.confirm(order.id)
    assert order.status == BookingOrderStatus.CONFIRMED
    assert order.confirmed_at is not None


def test_status_machine_cancel_from_held(db_session):
    tenant, territory, _owner, obj, guest = _bootstrap_booking_graph(db_session)
    _setup_tenant_for_hold(db_session, tenant.id)

    order = BookingHoldService(db_session, tenant.id).create_hold(
        _hold_cart(territory.id, guest.id, obj.id)
    )
    cancelled = BookingOrderService(db_session, tenant.id).cancel(order.id)

    assert cancelled.status == BookingOrderStatus.CANCELLED
    assert cancelled.cancelled_at is not None
    assert all(item.status == BookingItemStatus.CANCELLED for item in cancelled.items)


def test_invalid_status_transition_rejected(db_session):
    tenant, territory, _owner, obj, guest = _bootstrap_booking_graph(db_session)
    _setup_tenant_for_hold(db_session, tenant.id)

    order = BookingHoldService(db_session, tenant.id).create_hold(
        _hold_cart(territory.id, guest.id, obj.id)
    )

    with pytest.raises(BookingStatusTransitionError) as exc_info:
        BookingOrderService(db_session, tenant.id).confirm(order.id)

    assert exc_info.value.current_status == "held"
    assert exc_info.value.target_status == "confirmed"


def test_multi_object_hold_fails_atomically_on_single_conflict(db_session):
    tenant, territory, owner, obj, guest = _bootstrap_booking_graph(db_session)
    _setup_tenant_for_hold(db_session, tenant.id)

    obj_two = BookingBookableObject(
        tenant_id=tenant.id,
        territory_id=territory.id,
        owner_id=owner.id,
        code="cabin-2b",
        name="Cabin 2b",
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
        check_in_at=datetime(2026, 12, 10, 10, 0, tzinfo=UTC),
        check_out_at=datetime(2026, 12, 12, 6, 0, tzinfo=UTC),
    )

    before_items = db_session.scalar(select(func.count()).select_from(BookingItem)) or 0

    with pytest.raises(BookingAvailabilityError):
        BookingHoldService(db_session, tenant.id).create_hold(
            BookingHoldCartInput(
                territory_id=territory.id,
                guest_party_id=guest.id,
                source=BookingOrderSource.PUBLIC_WEB,
                items=[
                    BookingStayRequest(obj.id, date(2026, 12, 10), date(2026, 12, 12)),
                    BookingStayRequest(obj_two.id, date(2026, 12, 15), date(2026, 12, 17)),
                ],
            )
        )

    after_items = db_session.scalar(select(func.count()).select_from(BookingItem)) or 0
    assert after_items == before_items


def test_expired_hold_does_not_block_availability_after_lazy_expire(db_session):
    tenant, territory, _owner, obj, guest = _bootstrap_booking_graph(db_session)
    _setup_tenant_for_hold(db_session, tenant.id)
    now = datetime(2026, 12, 8, 12, 0, tzinfo=UTC)

    hold_service = BookingHoldService(db_session, tenant.id)
    hold_service.create_hold(
        _hold_cart(territory.id, guest.id, obj.id, check_in_date=date(2026, 12, 25), check_out_date=date(2026, 12, 27)),
        now_utc=now - timedelta(minutes=45),
    )

    hold_service.expire_stale_holds(territory_id=territory.id, now_utc=now)

    from app.modules.booking.schemas import BookingAvailabilityCartInput

    result = BookingAvailabilityService(db_session, tenant.id).check_cart(
        BookingAvailabilityCartInput(
            territory_id=territory.id,
            items=[BookingStayRequest(obj.id, date(2026, 12, 25), date(2026, 12, 27))],
        ),
        now_utc=now,
    )
    assert result.is_available
