import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, Numeric, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.enums import CatalogItemType
from app.core.models import AuditUserMixin, TimestampMixin, UUIDPrimaryKeyMixin

ENTITY_CATALOG_ITEM = "catalog_item"


class UnitOfMeasure(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "units_of_measure"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_unit_tenant_code"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    symbol: Mapped[str | None] = mapped_column(String(16), nullable=True)


class CatalogItem(Base, UUIDPrimaryKeyMixin, TimestampMixin, AuditUserMixin):
    __tablename__ = "catalog_items"
    __table_args__ = (
        UniqueConstraint("tenant_id", "sku", name="uq_catalog_item_tenant_sku"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    item_type: Mapped[CatalogItemType] = mapped_column(
        Enum(CatalogItemType, name="catalog_item_type", native_enum=False),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sku: Mapped[str | None] = mapped_column(String(64), nullable=True)
    unit_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("units_of_measure.id", ondelete="SET NULL"),
        nullable=True,
    )
    base_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    custom_fields_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    unit: Mapped["UnitOfMeasure | None"] = relationship("UnitOfMeasure", lazy="joined")


class PriceList(Base, UUIDPrimaryKeyMixin, TimestampMixin, AuditUserMixin):
    __tablename__ = "price_lists"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_price_list_tenant_code"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="RUB", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    items: Mapped[list["PriceListItem"]] = relationship(
        "PriceListItem",
        back_populates="price_list",
        lazy="selectin",
        cascade="all, delete-orphan",
    )


class PriceListItem(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "price_list_items"
    __table_args__ = (
        UniqueConstraint("price_list_id", "catalog_item_id", name="uq_price_list_catalog_item"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    price_list_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("price_lists.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    catalog_item_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("catalog_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    price: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    min_quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)

    price_list: Mapped["PriceList"] = relationship("PriceList", back_populates="items")
    catalog_item: Mapped["CatalogItem"] = relationship("CatalogItem", lazy="joined")
