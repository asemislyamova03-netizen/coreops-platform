"""E1 model persistence tests for Flexity Booking."""

from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.database import Base
from app.core.enums import PartyStatus, PartyType, TenantStatus
from app.modules.auth.models import User
from app.modules.booking.enums import (
    BookableObjectType,
    BookingItemStatus,
    BookingOrderSource,
    BookingOrderStatus,
    BookingOwnerStatus,
    BookingTerritoryStatus,
)
from app.modules.booking.models import (
    BookingBookableObject,
    BookingCommissionRule,
    BookingItem,
    BookingObjectPhoto,
    BookingOrder,
    BookingOwner,
    BookingTerritory,
)
from app.modules.parties.models import Party
from app.modules.provider.models import ProviderCompany
from app.modules.tenants.models import Tenant


BOOKING_TABLES = {
    "booking_territories",
    "booking_owners",
    "booking_bookable_objects",
    "booking_object_photos",
    "booking_map_points",
    "booking_orders",
    "booking_items",
    "booking_management_permissions",
    "booking_commission_rules",
}


def test_booking_tables_registered_in_metadata():
    table_names = set(Base.metadata.tables.keys())
    assert BOOKING_TABLES.issubset(table_names)
    assert "booking_commission_accruals" not in table_names


def _bootstrap_tenant(db_session):
    provider = ProviderCompany(name="Booking Provider", slug="booking-provider", is_active=True)
    db_session.add(provider)
    db_session.flush()

    tenant = Tenant(
        provider_company_id=provider.id,
        name="Booking Tenant",
        slug="booking-tenant",
        status=TenantStatus.ACTIVE,
    )
    db_session.add(tenant)
    db_session.flush()
    return tenant


def _bootstrap_party(db_session, tenant_id):
    party = Party(
        tenant_id=tenant_id,
        party_type=PartyType.PERSON,
        display_name="Guest One",
        status=PartyStatus.ACTIVE,
        metadata_json={},
    )
    db_session.add(party)
    db_session.flush()
    return party


def _bootstrap_booking_graph(db_session):
    tenant = _bootstrap_tenant(db_session)
    guest_party = _bootstrap_party(db_session, tenant.id)
    owner_party = _bootstrap_party(db_session, tenant.id)
    owner_party.display_name = "Owner One"

    territory = BookingTerritory(
        tenant_id=tenant.id,
        code="main",
        name="Main Camp",
        slug="main-camp",
        timezone="Asia/Almaty",
        currency="KZT",
        default_check_in_time=time(14, 0),
        default_check_out_time=time(12, 0),
        hold_duration_minutes=30,
        min_stay_nights=1,
        status=BookingTerritoryStatus.ACTIVE,
    )
    db_session.add(territory)
    db_session.flush()

    owner = BookingOwner(
        tenant_id=tenant.id,
        party_id=owner_party.id,
        display_name="Owner One",
        status=BookingOwnerStatus.ACTIVE,
    )
    db_session.add(owner)
    db_session.flush()

    obj = BookingBookableObject(
        tenant_id=tenant.id,
        territory_id=territory.id,
        owner_id=owner.id,
        code="cabin-1",
        name="Cabin 1",
        object_type=BookableObjectType.CABIN,
        base_price=Decimal("15000.00"),
        check_in_time=time(15, 0),
        check_out_time=time(11, 0),
    )
    db_session.add(obj)
    db_session.flush()

    photo = BookingObjectPhoto(
        tenant_id=tenant.id,
        bookable_object_id=obj.id,
        url="https://example.com/cabin-1.jpg",
        storage_path="/media/cabin-1.jpg",
        sort_order=0,
    )
    db_session.add(photo)
    db_session.commit()

    return tenant, territory, owner, obj, guest_party


def test_create_booking_graph(db_session):
    tenant, territory, owner, obj, guest_party = _bootstrap_booking_graph(db_session)

    assert territory.timezone == "Asia/Almaty"
    assert obj.check_in_time == time(15, 0)
    assert obj.owner_id == owner.id

    photo = db_session.query(BookingObjectPhoto).filter_by(bookable_object_id=obj.id).one()
    assert photo.url.startswith("https://")
    assert guest_party.tenant_id == tenant.id


def test_unique_territory_slug_per_tenant(db_session):
    tenant = _bootstrap_tenant(db_session)
    db_session.add(
        BookingTerritory(
            tenant_id=tenant.id,
            code="a",
            name="Territory A",
            slug="same-slug",
            timezone="UTC",
            currency="KZT",
        )
    )
    db_session.add(
        BookingTerritory(
            tenant_id=tenant.id,
            code="b",
            name="Territory B",
            slug="same-slug",
            timezone="UTC",
            currency="KZT",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_booking_item_checkout_must_be_after_checkin(db_session):
    tenant, territory, owner, obj, guest_party = _bootstrap_booking_graph(db_session)

    order = BookingOrder(
        tenant_id=tenant.id,
        territory_id=territory.id,
        order_number="BO-001",
        guest_party_id=guest_party.id,
        status=BookingOrderStatus.HELD,
        currency="KZT",
        source=BookingOrderSource.PUBLIC_WEB,
    )
    db_session.add(order)
    db_session.flush()

    check_in = datetime(2026, 7, 10, 9, 0, tzinfo=UTC)
    check_out = datetime(2026, 7, 9, 9, 0, tzinfo=UTC)

    db_session.add(
        BookingItem(
            tenant_id=tenant.id,
            booking_order_id=order.id,
            bookable_object_id=obj.id,
            check_in_date=date(2026, 7, 10),
            check_out_date=date(2026, 7, 9),
            check_in_at=check_in,
            check_out_at=check_out,
            nights=1,
            unit_price=Decimal("15000.00"),
            line_total=Decimal("15000.00"),
            owner_id=owner.id,
            status=BookingItemStatus.ACTIVE,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_booking_order_without_finance_links(db_session):
    tenant, territory, _owner, _obj, guest_party = _bootstrap_booking_graph(db_session)

    order = BookingOrder(
        tenant_id=tenant.id,
        territory_id=territory.id,
        order_number="BO-002",
        guest_party_id=guest_party.id,
        status=BookingOrderStatus.PENDING_PAYMENT,
        currency="KZT",
        subtotal=Decimal("30000.00"),
        source=BookingOrderSource.TWOGIS,
        invoice_id=None,
        payment_id=None,
    )
    db_session.add(order)
    db_session.commit()

    stored = db_session.get(BookingOrder, order.id)
    assert stored.invoice_id is None
    assert stored.payment_id is None
    assert stored.source == BookingOrderSource.TWOGIS


def test_multi_object_booking_order(db_session):
    tenant, territory, owner, obj, guest_party = _bootstrap_booking_graph(db_session)

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
    db_session.flush()

    order = BookingOrder(
        tenant_id=tenant.id,
        territory_id=territory.id,
        order_number="BO-003",
        guest_party_id=guest_party.id,
        status=BookingOrderStatus.HELD,
        hold_expires_at=datetime.now(UTC) + timedelta(minutes=30),
        currency="KZT",
        subtotal=Decimal("27000.00"),
        source=BookingOrderSource.PUBLIC_WEB,
    )
    db_session.add(order)
    db_session.flush()

    db_session.add_all(
        [
            BookingItem(
                tenant_id=tenant.id,
                booking_order_id=order.id,
                bookable_object_id=obj.id,
                check_in_date=date(2026, 8, 1),
                check_out_date=date(2026, 8, 3),
                check_in_at=datetime(2026, 8, 1, 9, 0, tzinfo=UTC),
                check_out_at=datetime(2026, 8, 3, 9, 0, tzinfo=UTC),
                nights=2,
                unit_price=Decimal("15000.00"),
                line_total=Decimal("30000.00"),
                owner_id=owner.id,
            ),
            BookingItem(
                tenant_id=tenant.id,
                booking_order_id=order.id,
                bookable_object_id=obj_two.id,
                check_in_date=date(2026, 8, 5),
                check_out_date=date(2026, 8, 7),
                check_in_at=datetime(2026, 8, 5, 9, 0, tzinfo=UTC),
                check_out_at=datetime(2026, 8, 7, 9, 0, tzinfo=UTC),
                nights=2,
                unit_price=Decimal("12000.00"),
                line_total=Decimal("24000.00"),
                owner_id=owner.id,
            ),
        ]
    )
    db_session.commit()

    stored = db_session.get(BookingOrder, order.id)
    assert len(stored.items) == 2
    assert stored.items[0].check_in_date != stored.items[1].check_in_date


def test_commission_rules_without_accruals_table(db_session):
    tenant, territory, owner, _obj, _guest = _bootstrap_booking_graph(db_session)

    rule = BookingCommissionRule(
        tenant_id=tenant.id,
        territory_id=territory.id,
        owner_id=owner.id,
        rate_percent=Decimal("10.0000"),
        effective_from=date(2026, 1, 1),
    )
    db_session.add(rule)
    db_session.commit()

    assert rule.id is not None


def test_booking_item_foreign_keys_defined():
    table = BookingItem.__table__
    fk_map = {column.name: fk.target_fullname for column, fk in ((c, list(c.foreign_keys)[0]) for c in table.c if c.foreign_keys)}
    assert fk_map["booking_order_id"] == "booking_orders.id"
    assert fk_map["bookable_object_id"] == "booking_bookable_objects.id"
    assert fk_map["owner_id"] == "booking_owners.id"
    assert fk_map["tenant_id"] == "tenants.id"
