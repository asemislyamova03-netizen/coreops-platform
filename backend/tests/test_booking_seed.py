"""E1b platform enablement tests for Flexity Booking seed and Core FK links."""

import uuid
from decimal import Decimal

from sqlalchemy import func, select

from app.core.entitlements import EntitlementService
from app.core.enums import TenantStatus
from app.core.exceptions import FeatureNotEntitledError, ModuleDisabledError
from app.modules.booking.models import (
    BookingBookableObject,
    BookingMapPoint,
    BookingObjectPhoto,
    BookingOrder,
    BookingOwner,
    BookingTerritory,
)
from app.modules.booking.seed import attach_demo_invoice_to_order, seed_demo
from app.modules.provider.models import ProviderCompany
from app.modules.subscriptions.repository import SubscriptionRepository
from app.modules.subscriptions.seed import FEATURES
from app.modules.tenants.models import Tenant


def _create_tenant(db_session, slug: str = "booking-demo") -> Tenant:
    provider = ProviderCompany(name="Booking Seed Provider", slug=f"prov-{slug}", is_active=True)
    db_session.add(provider)
    db_session.flush()

    tenant = Tenant(
        provider_company_id=provider.id,
        name="Booking Demo Tenant",
        slug=slug,
        status=TenantStatus.ACTIVE,
    )
    db_session.add(tenant)
    db_session.commit()
    return tenant


def test_demo_seed_creates_graph(db_session):
    tenant = _create_tenant(db_session)

    result = seed_demo(db_session, tenant.id)

    territory = db_session.get(BookingTerritory, result.territory_id)
    assert territory is not None
    assert territory.timezone == "Asia/Almaty"
    assert territory.code == "main-camp"

    owner_count = db_session.scalar(
        select(func.count()).select_from(BookingOwner).where(BookingOwner.tenant_id == tenant.id)
    )
    assert owner_count == 2

    object_count = db_session.scalar(
        select(func.count())
        .select_from(BookingBookableObject)
        .where(BookingBookableObject.territory_id == territory.id)
    )
    assert object_count == 3

    photo_count = db_session.scalar(
        select(func.count()).select_from(BookingObjectPhoto).where(
            BookingObjectPhoto.tenant_id == tenant.id
        )
    )
    assert photo_count == 1

    map_count = db_session.scalar(
        select(func.count()).select_from(BookingMapPoint).where(
            BookingMapPoint.tenant_id == tenant.id
        )
    )
    assert map_count == 2

    assert result.order_id is not None
    order = db_session.get(BookingOrder, result.order_id)
    assert order.invoice_id is None
    assert order.payment_id is None


def test_demo_seed_idempotent(db_session):
    tenant = _create_tenant(db_session, slug="booking-demo-idem")

    first = seed_demo(db_session, tenant.id)
    second = seed_demo(db_session, tenant.id)

    assert first.territory_id == second.territory_id
    assert first.owner_ids == second.owner_ids
    assert first.object_ids == second.object_ids
    assert first.order_id == second.order_id

    territory_count = db_session.scalar(
        select(func.count()).select_from(BookingTerritory).where(BookingTerritory.tenant_id == tenant.id)
    )
    assert territory_count == 1

    object_count = db_session.scalar(
        select(func.count()).select_from(BookingBookableObject).where(
            BookingBookableObject.tenant_id == tenant.id
        )
    )
    assert object_count == 3


def test_optional_invoice_fk(db_session):
    tenant = _create_tenant(db_session, slug="booking-demo-invoice")
    result = seed_demo(db_session, tenant.id)
    assert result.order_id is not None

    invoice_id = attach_demo_invoice_to_order(
        db_session,
        tenant.id,
        result.order_id,
        result.guest_party_id,
    )

    order = db_session.get(BookingOrder, result.order_id)
    assert order.invoice_id == invoice_id


def test_booking_features_in_catalog(db_session):
    repo = SubscriptionRepository(db_session)
    booking_codes = {item["code"] for item in FEATURES if item["module_code"] == "booking"}
    assert len(booking_codes) >= 6

    for code in booking_codes:
        assert repo.get_feature(code) is not None


def test_business_plan_booking_entitlements(client, db_session):
    headers = {
        "Authorization": f"Bearer {_register_and_login(client)}",
    }
    tenant_id = client.post(
        "/api/v1/tenants",
        json={"name": "Booking Biz", "slug": "booking-biz", "plan_code": "business"},
        headers=headers,
    ).json()["id"]

    service = EntitlementService(db_session, uuid.UUID(tenant_id))
    service.assert_feature("booking.orders.read")
    service.assert_feature("booking.objects.manage")

    try:
        service.assert_feature("booking.orders.create")
        raised = False
    except FeatureNotEntitledError:
        raised = True
    assert raised


def test_starter_plan_has_no_booking_create(client, db_session):
    headers = {
        "Authorization": f"Bearer {_register_and_login(client, slug='starter-owner')}",
    }
    tenant_id = client.post(
        "/api/v1/tenants",
        json={"name": "Starter Only", "slug": "starter-booking", "plan_code": "starter"},
        headers=headers,
    ).json()["id"]

    service = EntitlementService(db_session, uuid.UUID(tenant_id))
    assert not service.has_feature("booking.orders.create")


def _register_and_login(client, slug: str = "booking-seed-owner") -> str:
    register = {
        "email": f"{slug}@example.com",
        "password": "securepass123",
        "full_name": "Seed Owner",
        "company_name": "Seed Provider",
        "company_slug": f"seed-{slug}",
    }
    client.post("/api/v1/auth/register", json=register)
    return client.post(
        "/api/v1/auth/login",
        json={"email": register["email"], "password": register["password"]},
    ).json()["access_token"]
