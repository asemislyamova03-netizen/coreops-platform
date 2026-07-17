import uuid
from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.models import AuditUserMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.modules.booking.enums import (
    BookableObjectStatus,
    BookableObjectType,
    BookablePricingUnit,
    BookingItemStatus,
    BookingOrderSource,
    BookingOrderStatus,
    BookingOwnerStatus,
    BookingPermission,
    BookingPermissionScope,
    BookingTerritoryStatus,
)


class BookingTerritory(Base, UUIDPrimaryKeyMixin, TimestampMixin, AuditUserMixin):
    __tablename__ = "booking_territories"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_booking_territory_tenant_code"),
        UniqueConstraint("tenant_id", "slug", name="uq_booking_territory_tenant_slug"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC")
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="KZT")
    default_check_in_time: Mapped[time] = mapped_column(Time, nullable=False, default=time(14, 0))
    default_check_out_time: Mapped[time] = mapped_column(Time, nullable=False, default=time(12, 0))
    hold_duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    min_stay_nights: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    map_config_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    settings_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[BookingTerritoryStatus] = mapped_column(
        Enum(BookingTerritoryStatus, name="booking_territory_status", native_enum=False),
        default=BookingTerritoryStatus.DRAFT,
        nullable=False,
        index=True,
    )

    bookable_objects: Mapped[list["BookingBookableObject"]] = relationship(
        "BookingBookableObject",
        back_populates="territory",
        lazy="selectin",
    )
    orders: Mapped[list["BookingOrder"]] = relationship(
        "BookingOrder",
        back_populates="territory",
        lazy="selectin",
    )


class BookingOwner(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "booking_owners"
    __table_args__ = (
        UniqueConstraint("tenant_id", "party_id", name="uq_booking_owner_tenant_party"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    party_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("parties.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    payout_details_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    telegram_chat_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    whatsapp_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[BookingOwnerStatus] = mapped_column(
        Enum(BookingOwnerStatus, name="booking_owner_status", native_enum=False),
        default=BookingOwnerStatus.ACTIVE,
        nullable=False,
    )

    bookable_objects: Mapped[list["BookingBookableObject"]] = relationship(
        "BookingBookableObject",
        back_populates="owner",
        lazy="selectin",
    )


class BookingBookableObject(Base, UUIDPrimaryKeyMixin, TimestampMixin, AuditUserMixin):
    __tablename__ = "booking_bookable_objects"
    __table_args__ = (
        UniqueConstraint("territory_id", "code", name="uq_booking_object_territory_code"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    territory_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("booking_territories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("booking_owners.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    object_type: Mapped[BookableObjectType] = mapped_column(
        Enum(BookableObjectType, name="bookable_object_type", native_enum=False),
        default=BookableObjectType.OTHER,
        nullable=False,
    )
    capacity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    base_price: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    pricing_unit: Mapped[BookablePricingUnit] = mapped_column(
        Enum(BookablePricingUnit, name="bookable_pricing_unit", native_enum=False),
        default=BookablePricingUnit.PER_NIGHT,
        nullable=False,
    )
    check_in_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    check_out_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    catalog_item_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("catalog_items.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[BookableObjectStatus] = mapped_column(
        Enum(BookableObjectStatus, name="bookable_object_status", native_enum=False),
        default=BookableObjectStatus.ACTIVE,
        nullable=False,
        index=True,
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    territory: Mapped["BookingTerritory"] = relationship(
        "BookingTerritory",
        back_populates="bookable_objects",
    )
    owner: Mapped["BookingOwner"] = relationship(
        "BookingOwner",
        back_populates="bookable_objects",
    )
    photos: Mapped[list["BookingObjectPhoto"]] = relationship(
        "BookingObjectPhoto",
        back_populates="bookable_object",
        lazy="selectin",
        cascade="all, delete-orphan",
        order_by="BookingObjectPhoto.sort_order",
    )
    map_point: Mapped["BookingMapPoint | None"] = relationship(
        "BookingMapPoint",
        back_populates="bookable_object",
        uselist=False,
        lazy="selectin",
    )
    booking_items: Mapped[list["BookingItem"]] = relationship(
        "BookingItem",
        back_populates="bookable_object",
        lazy="selectin",
    )


class BookingObjectPhoto(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "booking_object_photos"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    bookable_object_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("booking_bookable_objects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    storage_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    alt_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    bookable_object: Mapped["BookingBookableObject"] = relationship(
        "BookingBookableObject",
        back_populates="photos",
    )


class BookingMapPoint(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "booking_map_points"
    __table_args__ = (
        UniqueConstraint("bookable_object_id", name="uq_booking_map_point_object"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    territory_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("booking_territories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    bookable_object_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("booking_bookable_objects.id", ondelete="CASCADE"),
        nullable=False,
    )
    x: Mapped[float] = mapped_column(nullable=False)
    y: Mapped[float] = mapped_column(nullable=False)
    label: Mapped[str | None] = mapped_column(String(128), nullable=True)
    layer: Mapped[str] = mapped_column(String(64), default="main", nullable=False)

    bookable_object: Mapped["BookingBookableObject"] = relationship(
        "BookingBookableObject",
        back_populates="map_point",
    )


class BookingOrder(Base, UUIDPrimaryKeyMixin, TimestampMixin, AuditUserMixin):
    __tablename__ = "booking_orders"
    __table_args__ = (
        Index(
            "ix_booking_orders_tenant_status_hold",
            "tenant_id",
            "status",
            "hold_expires_at",
        ),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    territory_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("booking_territories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    order_number: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    guest_party_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("parties.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status: Mapped[BookingOrderStatus] = mapped_column(
        Enum(BookingOrderStatus, name="booking_order_status", native_enum=False),
        default=BookingOrderStatus.DRAFT,
        nullable=False,
        index=True,
    )
    hold_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="KZT")
    subtotal: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"), nullable=False)
    commission_total: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        default=Decimal("0"),
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[BookingOrderSource] = mapped_column(
        Enum(BookingOrderSource, name="booking_order_source", native_enum=False),
        default=BookingOrderSource.PUBLIC_WEB,
        nullable=False,
    )
    work_item_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("work_items.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    invoice_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("invoices.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    payment_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("payments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    territory: Mapped["BookingTerritory"] = relationship(
        "BookingTerritory",
        back_populates="orders",
    )
    items: Mapped[list["BookingItem"]] = relationship(
        "BookingItem",
        back_populates="order",
        lazy="selectin",
        cascade="all, delete-orphan",
    )


class BookingItem(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "booking_items"
    __table_args__ = (
        CheckConstraint("check_out_at > check_in_at", name="ck_booking_item_checkout_after_checkin"),
        Index(
            "ix_booking_items_object_interval",
            "bookable_object_id",
            "check_in_at",
            "check_out_at",
        ),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    booking_order_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("booking_orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    bookable_object_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("booking_bookable_objects.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    check_in_date: Mapped[date] = mapped_column(Date, nullable=False)
    check_out_date: Mapped[date] = mapped_column(Date, nullable=False)
    check_in_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    check_out_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    nights: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("booking_owners.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status: Mapped[BookingItemStatus] = mapped_column(
        Enum(BookingItemStatus, name="booking_item_status", native_enum=False),
        default=BookingItemStatus.ACTIVE,
        nullable=False,
    )

    order: Mapped["BookingOrder"] = relationship("BookingOrder", back_populates="items")
    bookable_object: Mapped["BookingBookableObject"] = relationship(
        "BookingBookableObject",
        back_populates="booking_items",
    )


class BookingManagementPermission(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "booking_management_permissions"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "user_id",
            "scope_type",
            "scope_id",
            "permission",
            name="uq_booking_mgmt_perm",
        ),
        Index("ix_booking_mgmt_perm_user_tenant", "user_id", "tenant_id"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scope_type: Mapped[BookingPermissionScope] = mapped_column(
        Enum(BookingPermissionScope, name="booking_permission_scope", native_enum=False),
        nullable=False,
    )
    scope_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    permission: Mapped[BookingPermission] = mapped_column(
        Enum(BookingPermission, name="booking_permission", native_enum=False),
        nullable=False,
    )
    granted_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )


class BookingCommissionRule(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "booking_commission_rules"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    territory_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("booking_territories.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("booking_owners.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    rate_percent: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False, default=Decimal("0"))
    fixed_fee: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
