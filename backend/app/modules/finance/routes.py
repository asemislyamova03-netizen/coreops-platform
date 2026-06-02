import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.entitlements import require_feature
from app.core.enums import InvoiceStatus, PaymentStatus
from app.core.modules import require_module
from app.core.tenancy import TenantContext
from app.modules.finance.schemas import (
    FinanceSummaryResponse,
    InvoiceCreate,
    InvoiceResponse,
    InvoiceUpdate,
    PaymentAllocateRequest,
    PaymentCreate,
    PaymentResponse,
    ReceivableResponse,
)
from app.modules.finance.service import FinanceService

invoices_router = APIRouter(prefix="/finance/invoices", tags=["finance"])
payments_router = APIRouter(prefix="/finance/payments", tags=["finance"])
finance_router = APIRouter(prefix="/finance", tags=["finance"])


def _service(ctx: TenantContext, db: Session) -> FinanceService:
    return FinanceService(db, ctx.tenant.id)


@invoices_router.get("", response_model=list[InvoiceResponse])
def list_invoices(
    status: InvoiceStatus | None = None,
    party_id: uuid.UUID | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    ctx: TenantContext = Depends(require_module("finance")),
    db: Session = Depends(get_db),
) -> list[InvoiceResponse]:
    return _service(ctx, db).list_invoices(
        status=status,
        party_id=party_id,
        skip=skip,
        limit=limit,
    )


@invoices_router.post("", response_model=InvoiceResponse, status_code=201)
def create_invoice(
    payload: InvoiceCreate,
    ctx: TenantContext = Depends(require_feature("finance.invoices.create")),
    db: Session = Depends(get_db),
) -> InvoiceResponse:
    result = _service(ctx, db).create_invoice(ctx.user, payload)
    db.commit()
    return result


@invoices_router.get("/{invoice_id}", response_model=InvoiceResponse)
def get_invoice(
    invoice_id: uuid.UUID,
    ctx: TenantContext = Depends(require_module("finance")),
    db: Session = Depends(get_db),
) -> InvoiceResponse:
    return _service(ctx, db).get_invoice(invoice_id)


@invoices_router.patch("/{invoice_id}", response_model=InvoiceResponse)
def update_invoice(
    invoice_id: uuid.UUID,
    payload: InvoiceUpdate,
    ctx: TenantContext = Depends(require_module("finance")),
    db: Session = Depends(get_db),
) -> InvoiceResponse:
    result = _service(ctx, db).update_invoice(ctx.user, invoice_id, payload)
    db.commit()
    return result


@payments_router.get("", response_model=list[PaymentResponse])
def list_payments(
    status: PaymentStatus | None = None,
    party_id: uuid.UUID | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    ctx: TenantContext = Depends(require_module("finance")),
    db: Session = Depends(get_db),
) -> list[PaymentResponse]:
    return _service(ctx, db).list_payments(
        status=status,
        party_id=party_id,
        skip=skip,
        limit=limit,
    )


@payments_router.post("", response_model=PaymentResponse, status_code=201)
def create_payment(
    payload: PaymentCreate,
    ctx: TenantContext = Depends(require_module("finance")),
    db: Session = Depends(get_db),
) -> PaymentResponse:
    result = _service(ctx, db).create_payment(ctx.user, payload)
    db.commit()
    return result


@payments_router.get("/{payment_id}", response_model=PaymentResponse)
def get_payment(
    payment_id: uuid.UUID,
    ctx: TenantContext = Depends(require_module("finance")),
    db: Session = Depends(get_db),
) -> PaymentResponse:
    return _service(ctx, db).get_payment(payment_id)


@payments_router.post("/{payment_id}/allocate", response_model=PaymentResponse)
def allocate_payment(
    payment_id: uuid.UUID,
    payload: PaymentAllocateRequest,
    ctx: TenantContext = Depends(require_module("finance")),
    db: Session = Depends(get_db),
) -> PaymentResponse:
    result = _service(ctx, db).allocate_payment(ctx.user, payment_id, payload)
    db.commit()
    return result


@finance_router.get("/receivables", response_model=list[ReceivableResponse])
def list_receivables(
    ctx: TenantContext = Depends(require_module("finance")),
    db: Session = Depends(get_db),
) -> list[ReceivableResponse]:
    return _service(ctx, db).list_receivables()


@finance_router.get("/summary", response_model=FinanceSummaryResponse)
def finance_summary(
    currency: str = Query(default="RUB", max_length=3),
    ctx: TenantContext = Depends(require_module("finance")),
    db: Session = Depends(get_db),
) -> FinanceSummaryResponse:
    return _service(ctx, db).get_summary(currency=currency)
