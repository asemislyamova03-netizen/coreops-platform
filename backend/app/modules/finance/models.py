import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import JSON, Date, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.enums import InvoiceStatus, PaymentDirection, PaymentMethod, PaymentStatus
from app.core.models import AuditUserMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Invoice(Base, UUIDPrimaryKeyMixin, TimestampMixin, AuditUserMixin):
    __tablename__ = "invoices"
    __table_args__ = (
        UniqueConstraint("tenant_id", "invoice_number", name="uq_invoice_tenant_number"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    legal_entity_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("legal_entities.id", ondelete="SET NULL"),
        nullable=True,
    )
    tax_profile_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("tax_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    party_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    work_item_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    document_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)

    invoice_number: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[InvoiceStatus] = mapped_column(
        Enum(InvoiceStatus, name="invoice_status", native_enum=False),
        default=InvoiceStatus.DRAFT,
        nullable=False,
        index=True,
    )
    currency: Mapped[str] = mapped_column(String(3), default="RUB", nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"), nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"), nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"), nullable=False)
    amount_paid: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"), nullable=False)

    issue_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    lines: Mapped[list["InvoiceLine"]] = relationship(
        "InvoiceLine",
        back_populates="invoice",
        lazy="selectin",
        cascade="all, delete-orphan",
        order_by="InvoiceLine.sort_order",
    )
    allocations: Mapped[list["PaymentAllocation"]] = relationship(
        "PaymentAllocation",
        back_populates="invoice",
        lazy="selectin",
    )


class InvoiceLine(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "invoice_lines"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("invoices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    catalog_item_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("catalog_items.id", ondelete="SET NULL"),
        nullable=True,
    )
    description: Mapped[str] = mapped_column(String(512), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("1"), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    invoice: Mapped["Invoice"] = relationship("Invoice", back_populates="lines")


class Payment(Base, UUIDPrimaryKeyMixin, TimestampMixin, AuditUserMixin):
    __tablename__ = "payments"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    party_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    payment_number: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="RUB", nullable=False)
    amount_allocated: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"), nullable=False)

    payment_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    method: Mapped[PaymentMethod] = mapped_column(
        Enum(PaymentMethod, name="payment_method", native_enum=False),
        default=PaymentMethod.BANK_TRANSFER,
        nullable=False,
    )
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, name="payment_status", native_enum=False),
        default=PaymentStatus.COMPLETED,
        nullable=False,
        index=True,
    )
    direction: Mapped[PaymentDirection] = mapped_column(
        Enum(PaymentDirection, name="payment_direction", native_enum=False),
        default=PaymentDirection.INCOMING,
        nullable=False,
        index=True,
    )
    reference_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    allocations: Mapped[list["PaymentAllocation"]] = relationship(
        "PaymentAllocation",
        back_populates="payment",
        lazy="selectin",
        cascade="all, delete-orphan",
    )


class PaymentAllocation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "payment_allocations"
    __table_args__ = (
        UniqueConstraint("payment_id", "invoice_id", name="uq_payment_allocation_payment_invoice"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    payment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("payments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("invoices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    payment: Mapped["Payment"] = relationship("Payment", back_populates="allocations")
    invoice: Mapped["Invoice"] = relationship("Invoice", back_populates="allocations")
