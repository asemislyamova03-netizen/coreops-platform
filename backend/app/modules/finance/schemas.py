import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.enums import InvoiceStatus, PaymentDirection, PaymentMethod, PaymentStatus


class InvoiceLineCreate(BaseModel):
    catalog_item_id: uuid.UUID | None = None
    description: str = Field(max_length=512)
    quantity: Decimal = Field(default=Decimal("1"), gt=0)
    unit_price: Decimal
    sort_order: int = 0


class InvoiceCreate(BaseModel):
    party_id: uuid.UUID
    legal_entity_id: uuid.UUID | None = None
    tax_profile_id: uuid.UUID | None = None
    work_item_id: uuid.UUID | None = None
    document_id: uuid.UUID | None = None
    currency: str = Field(default="RUB", max_length=3)
    due_date: date | None = None
    notes: str | None = None
    lines: list[InvoiceLineCreate] = Field(min_length=1)
    issue: bool = False

    @field_validator("lines")
    @classmethod
    def validate_lines(cls, value: list[InvoiceLineCreate]) -> list[InvoiceLineCreate]:
        if not value:
            raise ValueError("At least one invoice line is required")
        return value


class InvoiceUpdate(BaseModel):
    status: InvoiceStatus | None = None
    due_date: date | None = None
    notes: str | None = None
    legal_entity_id: uuid.UUID | None = None
    tax_profile_id: uuid.UUID | None = None


class InvoiceLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    catalog_item_id: uuid.UUID | None
    description: str
    quantity: Decimal
    unit_price: Decimal
    line_total: Decimal
    sort_order: int


class InvoiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    legal_entity_id: uuid.UUID | None
    tax_profile_id: uuid.UUID | None
    party_id: uuid.UUID
    work_item_id: uuid.UUID | None
    document_id: uuid.UUID | None
    invoice_number: str
    status: InvoiceStatus
    currency: str
    subtotal: Decimal
    tax_amount: Decimal
    total: Decimal
    amount_paid: Decimal
    balance_due: Decimal
    issue_date: date | None
    due_date: date | None
    issued_at: datetime | None
    notes: str | None
    lines: list[InvoiceLineResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class PaymentCreate(BaseModel):
    party_id: uuid.UUID | None = None
    amount: Decimal = Field(gt=0)
    currency: str = Field(default="RUB", max_length=3)
    payment_date: date
    method: PaymentMethod = PaymentMethod.BANK_TRANSFER
    status: PaymentStatus = PaymentStatus.COMPLETED
    direction: PaymentDirection = PaymentDirection.INCOMING
    reference_number: str | None = Field(default=None, max_length=128)
    notes: str | None = None
    legacy_payment_type: str | None = Field(
        default=None,
        max_length=64,
        description="Optional legacy consult_app payments.type; maps to direction when set",
    )


class PaymentAllocationItem(BaseModel):
    invoice_id: uuid.UUID
    amount: Decimal = Field(gt=0)
    notes: str | None = None


class PaymentAllocateRequest(BaseModel):
    allocations: list[PaymentAllocationItem] = Field(min_length=1)


class PaymentAllocationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    invoice_id: uuid.UUID
    amount: Decimal
    notes: str | None
    created_at: datetime


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    party_id: uuid.UUID | None
    payment_number: str
    amount: Decimal
    currency: str
    amount_allocated: Decimal
    unallocated_amount: Decimal
    payment_date: date
    method: PaymentMethod
    status: PaymentStatus
    direction: PaymentDirection
    reference_number: str | None
    notes: str | None
    allocations: list[PaymentAllocationResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class ReceivableResponse(BaseModel):
    invoice_id: uuid.UUID
    invoice_number: str
    party_id: uuid.UUID
    status: InvoiceStatus
    currency: str
    total: Decimal
    amount_paid: Decimal
    balance_due: Decimal
    due_date: date | None
    is_overdue: bool


class FinanceSummaryResponse(BaseModel):
    currency: str
    total_invoiced: Decimal
    total_paid: Decimal
    total_outstanding: Decimal
    open_invoices_count: int
    overdue_invoices_count: int
    overdue_amount: Decimal


# Backward-compatible alias used by C1/C2a mapping helpers and tests.
LegacyPaymentDirection = PaymentDirection


def map_legacy_payment_type(value: str | None) -> tuple[PaymentDirection, PaymentStatus, bool]:
    if value is None:
        return PaymentDirection.NEEDS_REVIEW, PaymentStatus.PENDING, True
    normalized = value.strip().upper()
    if normalized == "INCOME":
        return PaymentDirection.INCOMING, PaymentStatus.COMPLETED, False
    if normalized == "EXPENSE":
        return PaymentDirection.OUTGOING, PaymentStatus.COMPLETED, False
    return PaymentDirection.NEEDS_REVIEW, PaymentStatus.PENDING, True
