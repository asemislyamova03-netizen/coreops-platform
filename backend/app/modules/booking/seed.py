"""Idempotent demo seed for Flexity Booking (E1b platform enablement)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import time
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import InvoiceStatus, PartyStatus, PartyType
from app.core.exceptions import NotFoundError
from app.modules.booking.enums import (
    BookableObjectType,
    BookingOrderSource,
    BookingOrderStatus,
    BookingOwnerStatus,
    BookingTerritoryStatus,
)
from app.modules.booking.models import (
    BookingBookableObject,
    BookingMapPoint,
    BookingObjectPhoto,
    BookingOrder,
    BookingOwner,
    BookingTerritory,
)
from app.modules.finance.repository import FinanceRepository
from app.modules.parties.models import Party
from app.modules.tenants.models import Tenant

DEMO_TERRITORY_CODE = "main-camp"
DEMO_TERRITORY_SLUG = "main-camp"
DEMO_ORDER_NUMBER = "BO-DEMO-001"

OWNER_SPECS = (
    {"code": "owner-one", "display_name": "Booking Demo Owner One"},
    {"code": "owner-two", "display_name": "Booking Demo Owner Two"},
)

OBJECT_SPECS = (
    {
        "code": "cabin-1",
        "name": "Cabin 1",
        "object_type": BookableObjectType.CABIN,
        "owner_index": 0,
        "base_price": Decimal("15000.00"),
        "check_in_time": time(15, 0),
        "check_out_time": time(11, 0),
        "map": {"x": 0.25, "y": 0.4, "label": "Cabin 1"},
        "photo": True,
    },
    {
        "code": "cabin-2",
        "name": "Cabin 2",
        "object_type": BookableObjectType.CABIN,
        "owner_index": 0,
        "base_price": Decimal("12000.00"),
        "check_in_time": None,
        "check_out_time": None,
        "map": None,
        "photo": False,
    },
    {
        "code": "gazebo-1",
        "name": "Gazebo 1",
        "object_type": BookableObjectType.ZONE,
        "owner_index": 1,
        "base_price": Decimal("8000.00"),
        "check_in_time": None,
        "check_out_time": None,
        "map": {"x": 0.7, "y": 0.55, "label": "Gazebo"},
        "photo": False,
    },
)

GUEST_DISPLAY_NAME = "Booking Demo Guest"


@dataclass(frozen=True)
class BookingDemoSeedResult:
    tenant_id: uuid.UUID
    territory_id: uuid.UUID
    owner_ids: tuple[uuid.UUID, ...]
    object_ids: tuple[uuid.UUID, ...]
    guest_party_id: uuid.UUID
    order_id: uuid.UUID | None


def resolve_tenant(
    db: Session,
    *,
    tenant_id: uuid.UUID | None = None,
    tenant_slug: str | None = None,
) -> Tenant:
    if tenant_id is not None:
        tenant = db.get(Tenant, tenant_id)
        if tenant is None:
            raise NotFoundError(f"Tenant '{tenant_id}' not found")
        return tenant

    if tenant_slug:
        tenant = db.scalar(select(Tenant).where(Tenant.slug == tenant_slug).limit(1))
        if tenant is None:
            raise NotFoundError(f"Tenant with slug '{tenant_slug}' not found")
        return tenant

    raise ValueError("tenant_id or tenant_slug is required")


def _get_or_create_party(db: Session, tenant_id: uuid.UUID, display_name: str) -> Party:
    party = db.scalar(
        select(Party).where(
            Party.tenant_id == tenant_id,
            Party.display_name == display_name,
        )
    )
    if party:
        return party

    party = Party(
        tenant_id=tenant_id,
        party_type=PartyType.PERSON,
        display_name=display_name,
        status=PartyStatus.ACTIVE,
        metadata_json={},
    )
    db.add(party)
    db.flush()
    return party


def _get_or_create_territory(db: Session, tenant_id: uuid.UUID) -> BookingTerritory:
    territory = db.scalar(
        select(BookingTerritory).where(
            BookingTerritory.tenant_id == tenant_id,
            BookingTerritory.code == DEMO_TERRITORY_CODE,
        )
    )
    if territory:
        return territory

    territory = BookingTerritory(
        tenant_id=tenant_id,
        code=DEMO_TERRITORY_CODE,
        name="Main Camp",
        slug=DEMO_TERRITORY_SLUG,
        timezone="Asia/Almaty",
        currency="KZT",
        default_check_in_time=time(14, 0),
        default_check_out_time=time(12, 0),
        hold_duration_minutes=30,
        min_stay_nights=1,
        status=BookingTerritoryStatus.ACTIVE,
    )
    db.add(territory)
    db.flush()
    return territory


def _get_or_create_owner(
    db: Session,
    tenant_id: uuid.UUID,
    party: Party,
    display_name: str,
) -> BookingOwner:
    owner = db.scalar(
        select(BookingOwner).where(
            BookingOwner.tenant_id == tenant_id,
            BookingOwner.party_id == party.id,
        )
    )
    if owner:
        return owner

    owner = BookingOwner(
        tenant_id=tenant_id,
        party_id=party.id,
        display_name=display_name,
        status=BookingOwnerStatus.ACTIVE,
    )
    db.add(owner)
    db.flush()
    return owner


def _get_or_create_object(
    db: Session,
    tenant_id: uuid.UUID,
    territory_id: uuid.UUID,
    owner_id: uuid.UUID,
    spec: dict,
) -> BookingBookableObject:
    obj = db.scalar(
        select(BookingBookableObject).where(
            BookingBookableObject.territory_id == territory_id,
            BookingBookableObject.code == spec["code"],
        )
    )
    if obj:
        return obj

    obj = BookingBookableObject(
        tenant_id=tenant_id,
        territory_id=territory_id,
        owner_id=owner_id,
        code=spec["code"],
        name=spec["name"],
        object_type=spec["object_type"],
        base_price=spec["base_price"],
        check_in_time=spec.get("check_in_time"),
        check_out_time=spec.get("check_out_time"),
    )
    db.add(obj)
    db.flush()
    return obj


def _ensure_photo(db: Session, tenant_id: uuid.UUID, obj: BookingBookableObject) -> None:
    existing = db.scalar(
        select(BookingObjectPhoto).where(BookingObjectPhoto.bookable_object_id == obj.id)
    )
    if existing:
        return

    db.add(
        BookingObjectPhoto(
            tenant_id=tenant_id,
            bookable_object_id=obj.id,
            url=f"https://example.com/{obj.code}.jpg",
            storage_path=f"/media/{obj.code}.jpg",
            sort_order=0,
        )
    )


def _ensure_map_point(
    db: Session,
    tenant_id: uuid.UUID,
    territory_id: uuid.UUID,
    obj: BookingBookableObject,
    map_spec: dict,
) -> None:
    existing = db.scalar(
        select(BookingMapPoint).where(BookingMapPoint.bookable_object_id == obj.id)
    )
    if existing:
        return

    db.add(
        BookingMapPoint(
            tenant_id=tenant_id,
            territory_id=territory_id,
            bookable_object_id=obj.id,
            x=map_spec["x"],
            y=map_spec["y"],
            label=map_spec.get("label"),
        )
    )


def _get_or_create_demo_order(
    db: Session,
    tenant_id: uuid.UUID,
    territory_id: uuid.UUID,
    guest_party_id: uuid.UUID,
) -> BookingOrder:
    order = db.scalar(
        select(BookingOrder).where(
            BookingOrder.tenant_id == tenant_id,
            BookingOrder.order_number == DEMO_ORDER_NUMBER,
        )
    )
    if order:
        return order

    order = BookingOrder(
        tenant_id=tenant_id,
        territory_id=territory_id,
        order_number=DEMO_ORDER_NUMBER,
        guest_party_id=guest_party_id,
        status=BookingOrderStatus.DRAFT,
        currency="KZT",
        source=BookingOrderSource.ADMIN,
        invoice_id=None,
        payment_id=None,
    )
    db.add(order)
    db.flush()
    return order


def seed_demo(
    db: Session,
    tenant_id: uuid.UUID,
    *,
    include_order: bool = True,
) -> BookingDemoSeedResult:
    """Create or refresh the minimal booking demo graph for an existing tenant."""
    territory = _get_or_create_territory(db, tenant_id)

    owner_parties = [
        _get_or_create_party(db, tenant_id, spec["display_name"]) for spec in OWNER_SPECS
    ]
    owners = [
        _get_or_create_owner(db, tenant_id, party, spec["display_name"])
        for party, spec in zip(owner_parties, OWNER_SPECS, strict=True)
    ]

    objects: list[BookingBookableObject] = []
    for spec in OBJECT_SPECS:
        owner = owners[spec["owner_index"]]
        obj = _get_or_create_object(db, tenant_id, territory.id, owner.id, spec)
        objects.append(obj)
        if spec.get("photo"):
            _ensure_photo(db, tenant_id, obj)
        map_spec = spec.get("map")
        if map_spec:
            _ensure_map_point(db, tenant_id, territory.id, obj, map_spec)

    guest_party = _get_or_create_party(db, tenant_id, GUEST_DISPLAY_NAME)
    order_id: uuid.UUID | None = None
    if include_order:
        order = _get_or_create_demo_order(db, tenant_id, territory.id, guest_party.id)
        order_id = order.id

    db.commit()

    return BookingDemoSeedResult(
        tenant_id=tenant_id,
        territory_id=territory.id,
        owner_ids=tuple(owner.id for owner in owners),
        object_ids=tuple(obj.id for obj in objects),
        guest_party_id=guest_party.id,
        order_id=order_id,
    )


def attach_demo_invoice_to_order(
    db: Session,
    tenant_id: uuid.UUID,
    order_id: uuid.UUID,
    party_id: uuid.UUID,
) -> uuid.UUID:
    """Optional Core FK smoke: link a finance invoice to a booking order."""
    order = db.scalar(
        select(BookingOrder).where(
            BookingOrder.tenant_id == tenant_id,
            BookingOrder.id == order_id,
        )
    )
    if order is None:
        raise NotFoundError(f"Booking order '{order_id}' not found")

    if order.invoice_id is not None:
        return order.invoice_id

    finance = FinanceRepository(db)
    invoice = finance.create_invoice(
        tenant_id=tenant_id,
        party_id=party_id,
        invoice_number=finance.next_invoice_number(tenant_id),
        status=InvoiceStatus.DRAFT,
        currency="KZT",
        subtotal=Decimal("0"),
        tax_amount=Decimal("0"),
        total=Decimal("0"),
    )
    order.invoice_id = invoice.id
    db.commit()
    return invoice.id
