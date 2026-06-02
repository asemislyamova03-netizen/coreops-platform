import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.enums import InvoiceStatus, PaymentStatus
from app.modules.finance.models import Invoice, InvoiceLine, Payment, PaymentAllocation


class FinanceRepository:
    def __init__(self, db: Session):
        self.db = db

    def next_invoice_number(self, tenant_id: uuid.UUID) -> str:
        count = self.db.scalar(
            select(func.count())
            .select_from(Invoice)
            .where(Invoice.tenant_id == tenant_id)
        ) or 0
        year = date.today().year
        return f"INV-{year}-{count + 1:05d}"

    def next_payment_number(self, tenant_id: uuid.UUID) -> str:
        count = self.db.scalar(
            select(func.count())
            .select_from(Payment)
            .where(Payment.tenant_id == tenant_id)
        ) or 0
        year = date.today().year
        return f"PAY-{year}-{count + 1:05d}"

    def list_invoices(
        self,
        tenant_id: uuid.UUID,
        *,
        status: InvoiceStatus | None = None,
        party_id: uuid.UUID | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Invoice]:
        stmt = (
            select(Invoice)
            .where(Invoice.tenant_id == tenant_id)
            .options(
                selectinload(Invoice.lines),
                selectinload(Invoice.allocations),
            )
            .order_by(Invoice.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        if status:
            stmt = stmt.where(Invoice.status == status)
        if party_id:
            stmt = stmt.where(Invoice.party_id == party_id)
        return list(self.db.scalars(stmt).all())

    def get_invoice(self, tenant_id: uuid.UUID, invoice_id: uuid.UUID) -> Invoice | None:
        stmt = (
            select(Invoice)
            .where(Invoice.tenant_id == tenant_id, Invoice.id == invoice_id)
            .options(
                selectinload(Invoice.lines),
                selectinload(Invoice.allocations),
            )
        )
        return self.db.scalar(stmt)

    def create_invoice(self, **kwargs) -> Invoice:
        invoice = Invoice(**kwargs)
        self.db.add(invoice)
        self.db.flush()
        return invoice

    def create_invoice_line(self, **kwargs) -> InvoiceLine:
        line = InvoiceLine(**kwargs)
        self.db.add(line)
        self.db.flush()
        return line

    def list_payments(
        self,
        tenant_id: uuid.UUID,
        *,
        status: PaymentStatus | None = None,
        party_id: uuid.UUID | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Payment]:
        stmt = (
            select(Payment)
            .where(Payment.tenant_id == tenant_id)
            .options(selectinload(Payment.allocations))
            .order_by(Payment.payment_date.desc())
            .offset(skip)
            .limit(limit)
        )
        if status:
            stmt = stmt.where(Payment.status == status)
        if party_id:
            stmt = stmt.where(Payment.party_id == party_id)
        return list(self.db.scalars(stmt).all())

    def get_payment(self, tenant_id: uuid.UUID, payment_id: uuid.UUID) -> Payment | None:
        stmt = (
            select(Payment)
            .where(Payment.tenant_id == tenant_id, Payment.id == payment_id)
            .options(selectinload(Payment.allocations))
        )
        return self.db.scalar(stmt)

    def create_payment(self, **kwargs) -> Payment:
        payment = Payment(**kwargs)
        self.db.add(payment)
        self.db.flush()
        return payment

    def create_allocation(self, **kwargs) -> PaymentAllocation:
        allocation = PaymentAllocation(**kwargs)
        self.db.add(allocation)
        self.db.flush()
        return allocation

    def get_allocation(
        self,
        tenant_id: uuid.UUID,
        payment_id: uuid.UUID,
        invoice_id: uuid.UUID,
    ) -> PaymentAllocation | None:
        stmt = select(PaymentAllocation).where(
            PaymentAllocation.tenant_id == tenant_id,
            PaymentAllocation.payment_id == payment_id,
            PaymentAllocation.invoice_id == invoice_id,
        )
        return self.db.scalar(stmt)

    def list_receivable_invoices(self, tenant_id: uuid.UUID) -> list[Invoice]:
        stmt = (
            select(Invoice)
            .where(
                Invoice.tenant_id == tenant_id,
                Invoice.status.in_(
                    [
                        InvoiceStatus.ISSUED,
                        InvoiceStatus.SENT,
                        InvoiceStatus.PARTIAL,
                        InvoiceStatus.OVERDUE,
                    ]
                ),
            )
            .options(selectinload(Invoice.lines))
            .order_by(Invoice.due_date.asc().nulls_last())
        )
        return list(self.db.scalars(stmt).all())

    def sum_invoiced(self, tenant_id: uuid.UUID) -> float:
        total = self.db.scalar(
            select(func.coalesce(func.sum(Invoice.total), 0)).where(
                Invoice.tenant_id == tenant_id,
                Invoice.status.not_in([InvoiceStatus.DRAFT, InvoiceStatus.CANCELLED, InvoiceStatus.VOID]),
            )
        )
        return float(total or 0)

    def sum_paid(self, tenant_id: uuid.UUID) -> float:
        total = self.db.scalar(
            select(func.coalesce(func.sum(Payment.amount), 0)).where(
                Payment.tenant_id == tenant_id,
                Payment.status == PaymentStatus.COMPLETED,
            )
        )
        return float(total or 0)
