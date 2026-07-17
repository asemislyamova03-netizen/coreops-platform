import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.entitlements import EntitlementService
from app.core.enums import AuditAction, InvoiceStatus, PaymentDirection, PaymentStatus
from app.modules.audit.recorder import AuditRecorder
from app.core.exceptions import ConflictError, NotFoundError
from app.modules.auth.models import User
from app.modules.catalog.repository import CatalogRepository
from app.modules.finance.repository import FinanceRepository
from app.modules.finance.schemas import (
    FinanceSummaryResponse,
    InvoiceCreate,
    InvoiceLineResponse,
    InvoiceResponse,
    InvoiceUpdate,
    PaymentAllocateRequest,
    PaymentAllocationResponse,
    PaymentCreate,
    PaymentResponse,
    ReceivableResponse,
    map_legacy_payment_type,
)
from app.modules.parties.repository import PartyRepository


class FinanceService:
    def __init__(self, db: Session, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.repo = FinanceRepository(db)
        self.parties = PartyRepository(db)
        self.catalog = CatalogRepository(db)
        self.entitlements = EntitlementService(db, tenant_id)

    def list_invoices(
        self,
        *,
        status: InvoiceStatus | None = None,
        party_id: uuid.UUID | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[InvoiceResponse]:
        invoices = self.repo.list_invoices(
            self.tenant_id,
            status=status,
            party_id=party_id,
            skip=skip,
            limit=limit,
        )
        return [self._to_invoice_response(inv) for inv in invoices]

    def get_invoice(self, invoice_id: uuid.UUID) -> InvoiceResponse:
        invoice = self._get_invoice_or_404(invoice_id)
        return self._to_invoice_response(invoice)

    def create_invoice(self, user: User, payload: InvoiceCreate) -> InvoiceResponse:
        self.entitlements.assert_within_limit("finance.invoices", increment=1)

        if not self.parties.get_party(self.tenant_id, payload.party_id):
            raise NotFoundError("Party not found")

        if payload.legal_entity_id:
            from app.modules.accounting.repository import AccountingRepository

            if not AccountingRepository(self.db).get_legal_entity(
                self.tenant_id, payload.legal_entity_id
            ):
                raise NotFoundError("Legal entity not found")

        if payload.tax_profile_id:
            from app.modules.accounting.repository import AccountingRepository

            if not AccountingRepository(self.db).get_tax_profile(
                self.tenant_id, payload.tax_profile_id
            ):
                raise NotFoundError("Tax profile not found")

        subtotal = Decimal("0")
        invoice = self.repo.create_invoice(
            tenant_id=self.tenant_id,
            party_id=payload.party_id,
            legal_entity_id=payload.legal_entity_id,
            tax_profile_id=payload.tax_profile_id,
            work_item_id=payload.work_item_id,
            document_id=payload.document_id,
            invoice_number=self.repo.next_invoice_number(self.tenant_id),
            status=InvoiceStatus.DRAFT,
            currency=payload.currency,
            due_date=payload.due_date,
            notes=payload.notes,
            created_by_user_id=user.id,
            updated_by_user_id=user.id,
        )

        for index, line_data in enumerate(payload.lines):
            if line_data.catalog_item_id:
                item = self.catalog.get_item(self.tenant_id, line_data.catalog_item_id)
                if not item:
                    raise NotFoundError(f"Catalog item not found: {line_data.catalog_item_id}")

            line_total = (line_data.quantity * line_data.unit_price).quantize(Decimal("0.01"))
            subtotal += line_total
            self.repo.create_invoice_line(
                tenant_id=self.tenant_id,
                invoice_id=invoice.id,
                catalog_item_id=line_data.catalog_item_id,
                description=line_data.description,
                quantity=line_data.quantity,
                unit_price=line_data.unit_price,
                line_total=line_total,
                sort_order=line_data.sort_order or index * 10,
            )

        invoice.subtotal = subtotal
        invoice.tax_amount = Decimal("0")
        invoice.total = subtotal
        self.db.flush()

        if payload.issue:
            self._issue_invoice(invoice)

        AuditRecorder(self.db).audit_log(
            action=AuditAction.CREATE,
            summary=f"Invoice created: {invoice.invoice_number}",
            tenant_id=self.tenant_id,
            user_id=user.id,
            entity_type="invoice",
            entity_id=invoice.id,
            changes_json={"total": str(invoice.total), "party_id": str(payload.party_id)},
        )

        self.entitlements.subscriptions.record_usage_event(
            tenant_id=self.tenant_id,
            limit_code="finance.invoices",
            quantity=1,
            metadata_json={"invoice_id": str(invoice.id)},
        )
        self.db.flush()
        self.db.refresh(invoice)
        return self._to_invoice_response(invoice)

    def update_invoice(
        self,
        user: User,
        invoice_id: uuid.UUID,
        payload: InvoiceUpdate,
    ) -> InvoiceResponse:
        invoice = self._get_invoice_or_404(invoice_id)

        if payload.status is not None:
            self._transition_status(invoice, payload.status)

        if payload.due_date is not None:
            invoice.due_date = payload.due_date
        if payload.notes is not None:
            invoice.notes = payload.notes
        if payload.legal_entity_id is not None:
            invoice.legal_entity_id = payload.legal_entity_id
        if payload.tax_profile_id is not None:
            invoice.tax_profile_id = payload.tax_profile_id

        invoice.updated_by_user_id = user.id
        self._refresh_overdue_status(invoice)
        self.db.flush()
        return self._to_invoice_response(invoice)

    def list_payments(
        self,
        *,
        status: PaymentStatus | None = None,
        party_id: uuid.UUID | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[PaymentResponse]:
        payments = self.repo.list_payments(
            self.tenant_id,
            status=status,
            party_id=party_id,
            skip=skip,
            limit=limit,
        )
        return [self._to_payment_response(p) for p in payments]

    def get_payment(self, payment_id: uuid.UUID) -> PaymentResponse:
        payment = self._get_payment_or_404(payment_id)
        return self._to_payment_response(payment)

    def create_payment(self, user: User, payload: PaymentCreate) -> PaymentResponse:
        if payload.party_id and not self.parties.get_party(self.tenant_id, payload.party_id):
            raise NotFoundError("Party not found")

        direction = payload.direction
        status = payload.status
        if payload.legacy_payment_type is not None:
            direction, mapped_status, _needs_review = map_legacy_payment_type(
                payload.legacy_payment_type
            )
            # Legacy type drives direction + recommended status; explicit status kept
            # only when caller did not rely on default completed for unknown types.
            status = mapped_status

        payment = self.repo.create_payment(
            tenant_id=self.tenant_id,
            party_id=payload.party_id,
            payment_number=self.repo.next_payment_number(self.tenant_id),
            amount=payload.amount,
            currency=payload.currency,
            payment_date=payload.payment_date,
            method=payload.method,
            status=status,
            direction=direction,
            reference_number=payload.reference_number,
            notes=payload.notes,
            created_by_user_id=user.id,
            updated_by_user_id=user.id,
        )
        return self._to_payment_response(payment)

    def allocate_payment(
        self,
        user: User,
        payment_id: uuid.UUID,
        payload: PaymentAllocateRequest,
    ) -> PaymentResponse:
        payment = self._get_payment_or_404(payment_id)
        if payment.status != PaymentStatus.COMPLETED:
            raise ConflictError("Only completed payments can be allocated")

        total_new = sum(item.amount for item in payload.allocations)
        available = payment.amount - payment.amount_allocated
        if total_new > available:
            raise ConflictError("Allocation exceeds unallocated payment amount")

        for item in payload.allocations:
            invoice = self._get_invoice_or_404(item.invoice_id)
            if invoice.status in (InvoiceStatus.DRAFT, InvoiceStatus.CANCELLED, InvoiceStatus.VOID):
                raise ConflictError("Cannot allocate payment to this invoice status")

            balance = invoice.total - invoice.amount_paid
            if item.amount > balance:
                raise ConflictError(
                    f"Allocation amount exceeds invoice balance for {invoice.invoice_number}"
                )

            existing = self.repo.get_allocation(
                self.tenant_id, payment.id, invoice.id
            )
            if existing:
                raise ConflictError(
                    f"Payment already allocated to invoice {invoice.invoice_number}"
                )

            self.repo.create_allocation(
                tenant_id=self.tenant_id,
                payment_id=payment.id,
                invoice_id=invoice.id,
                amount=item.amount,
                notes=item.notes,
            )
            invoice.amount_paid += item.amount
            self._update_invoice_payment_status(invoice)
            self._refresh_overdue_status(invoice)

        payment.amount_allocated += total_new
        payment.updated_by_user_id = user.id
        self.db.flush()
        self.db.refresh(payment)
        return self._to_payment_response(payment)

    def list_receivables(self) -> list[ReceivableResponse]:
        today = date.today()
        result: list[ReceivableResponse] = []
        for invoice in self.repo.list_receivable_invoices(self.tenant_id):
            balance = invoice.total - invoice.amount_paid
            if balance <= 0:
                continue
            is_overdue = (
                invoice.due_date is not None
                and invoice.due_date < today
                and invoice.status != InvoiceStatus.PAID
            )
            result.append(
                ReceivableResponse(
                    invoice_id=invoice.id,
                    invoice_number=invoice.invoice_number,
                    party_id=invoice.party_id,
                    status=invoice.status,
                    currency=invoice.currency,
                    total=invoice.total,
                    amount_paid=invoice.amount_paid,
                    balance_due=balance,
                    due_date=invoice.due_date,
                    is_overdue=is_overdue,
                )
            )
        return result

    def get_summary(self, currency: str = "RUB") -> FinanceSummaryResponse:
        today = date.today()
        receivables = self.list_receivables()
        outstanding = sum(r.balance_due for r in receivables)
        overdue = [r for r in receivables if r.is_overdue]

        return FinanceSummaryResponse(
            currency=currency,
            total_invoiced=Decimal(str(self.repo.sum_invoiced(self.tenant_id))),
            total_paid=Decimal(str(self.repo.sum_paid(self.tenant_id))),
            total_outstanding=outstanding,
            open_invoices_count=len(receivables),
            overdue_invoices_count=len(overdue),
            overdue_amount=sum((r.balance_due for r in overdue), Decimal("0")),
        )

    def _issue_invoice(self, invoice) -> None:
        if invoice.status != InvoiceStatus.DRAFT:
            raise ConflictError("Only draft invoices can be issued")
        now = datetime.now(UTC)
        invoice.status = InvoiceStatus.ISSUED
        invoice.issue_date = now.date()
        invoice.issued_at = now
        self._refresh_overdue_status(invoice)

    def _transition_status(self, invoice, new_status: InvoiceStatus) -> None:
        if new_status == InvoiceStatus.ISSUED and invoice.status == InvoiceStatus.DRAFT:
            self._issue_invoice(invoice)
            return
        if new_status in (InvoiceStatus.CANCELLED, InvoiceStatus.VOID):
            if invoice.amount_paid > 0:
                raise ConflictError("Cannot cancel invoice with payments")
        invoice.status = new_status
        self._refresh_overdue_status(invoice)

    def _update_invoice_payment_status(self, invoice) -> None:
        if invoice.amount_paid >= invoice.total:
            invoice.status = InvoiceStatus.PAID
        elif invoice.amount_paid > 0:
            invoice.status = InvoiceStatus.PARTIAL
        self._refresh_overdue_status(invoice)

    def _refresh_overdue_status(self, invoice) -> None:
        if invoice.status in (
            InvoiceStatus.PAID,
            InvoiceStatus.CANCELLED,
            InvoiceStatus.VOID,
            InvoiceStatus.DRAFT,
        ):
            return
        if invoice.due_date and invoice.due_date < date.today():
            if invoice.amount_paid < invoice.total:
                invoice.status = InvoiceStatus.OVERDUE

    def _get_invoice_or_404(self, invoice_id: uuid.UUID):
        invoice = self.repo.get_invoice(self.tenant_id, invoice_id)
        if not invoice:
            raise NotFoundError("Invoice not found")
        return invoice

    def _get_payment_or_404(self, payment_id: uuid.UUID):
        payment = self.repo.get_payment(self.tenant_id, payment_id)
        if not payment:
            raise NotFoundError("Payment not found")
        return payment

    def _to_invoice_response(self, invoice) -> InvoiceResponse:
        lines = [InvoiceLineResponse.model_validate(line) for line in invoice.lines]
        return InvoiceResponse(
            id=invoice.id,
            tenant_id=invoice.tenant_id,
            legal_entity_id=invoice.legal_entity_id,
            tax_profile_id=invoice.tax_profile_id,
            party_id=invoice.party_id,
            work_item_id=invoice.work_item_id,
            document_id=invoice.document_id,
            invoice_number=invoice.invoice_number,
            status=invoice.status,
            currency=invoice.currency,
            subtotal=invoice.subtotal,
            tax_amount=invoice.tax_amount,
            total=invoice.total,
            amount_paid=invoice.amount_paid,
            balance_due=invoice.total - invoice.amount_paid,
            issue_date=invoice.issue_date,
            due_date=invoice.due_date,
            issued_at=invoice.issued_at,
            notes=invoice.notes,
            lines=lines,
            created_at=invoice.created_at,
            updated_at=invoice.updated_at,
        )

    def _to_payment_response(self, payment) -> PaymentResponse:
        allocations = [
            PaymentAllocationResponse.model_validate(item) for item in payment.allocations
        ]
        return PaymentResponse(
            id=payment.id,
            tenant_id=payment.tenant_id,
            party_id=payment.party_id,
            payment_number=payment.payment_number,
            amount=payment.amount,
            currency=payment.currency,
            amount_allocated=payment.amount_allocated,
            unallocated_amount=payment.amount - payment.amount_allocated,
            payment_date=payment.payment_date,
            method=payment.method,
            status=payment.status,
            direction=getattr(payment, "direction", PaymentDirection.INCOMING),
            reference_number=payment.reference_number,
            notes=payment.notes,
            allocations=allocations,
            created_at=payment.created_at,
            updated_at=payment.updated_at,
        )
