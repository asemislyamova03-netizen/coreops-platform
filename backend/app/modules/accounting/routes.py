import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.modules import require_module
from app.core.tenancy import TenantContext
from app.modules.accounting.schemas import (
    LegalEntityCreate,
    LegalEntityResponse,
    LegalEntityUpdate,
    TaxProfileCreate,
    TaxProfileResponse,
    TaxProfileUpdate,
)
from app.modules.accounting.service import AccountingService

legal_entities_router = APIRouter(prefix="/accounting/legal-entities", tags=["accounting"])
tax_profiles_router = APIRouter(prefix="/accounting/tax-profiles", tags=["accounting"])


def _service(ctx: TenantContext, db: Session) -> AccountingService:
    return AccountingService(db, ctx.tenant.id)


@legal_entities_router.get("", response_model=list[LegalEntityResponse])
def list_legal_entities(
    active_only: bool = True,
    ctx: TenantContext = Depends(require_module("accounting")),
    db: Session = Depends(get_db),
) -> list[LegalEntityResponse]:
    return _service(ctx, db).list_legal_entities(active_only=active_only)


@legal_entities_router.post("", response_model=LegalEntityResponse, status_code=201)
def create_legal_entity(
    payload: LegalEntityCreate,
    ctx: TenantContext = Depends(require_module("accounting")),
    db: Session = Depends(get_db),
) -> LegalEntityResponse:
    result = _service(ctx, db).create_legal_entity(payload)
    db.commit()
    return result


@legal_entities_router.get("/{entity_id}", response_model=LegalEntityResponse)
def get_legal_entity(
    entity_id: uuid.UUID,
    ctx: TenantContext = Depends(require_module("accounting")),
    db: Session = Depends(get_db),
) -> LegalEntityResponse:
    return _service(ctx, db).get_legal_entity(entity_id)


@legal_entities_router.patch("/{entity_id}", response_model=LegalEntityResponse)
def update_legal_entity(
    entity_id: uuid.UUID,
    payload: LegalEntityUpdate,
    ctx: TenantContext = Depends(require_module("accounting")),
    db: Session = Depends(get_db),
) -> LegalEntityResponse:
    result = _service(ctx, db).update_legal_entity(entity_id, payload)
    db.commit()
    return result


@tax_profiles_router.get("", response_model=list[TaxProfileResponse])
def list_tax_profiles(
    legal_entity_id: uuid.UUID | None = None,
    active_only: bool = True,
    ctx: TenantContext = Depends(require_module("accounting")),
    db: Session = Depends(get_db),
) -> list[TaxProfileResponse]:
    return _service(ctx, db).list_tax_profiles(
        legal_entity_id=legal_entity_id,
        active_only=active_only,
    )


@tax_profiles_router.post("", response_model=TaxProfileResponse, status_code=201)
def create_tax_profile(
    payload: TaxProfileCreate,
    ctx: TenantContext = Depends(require_module("accounting")),
    db: Session = Depends(get_db),
) -> TaxProfileResponse:
    result = _service(ctx, db).create_tax_profile(payload)
    db.commit()
    return result


@tax_profiles_router.get("/{profile_id}", response_model=TaxProfileResponse)
def get_tax_profile(
    profile_id: uuid.UUID,
    ctx: TenantContext = Depends(require_module("accounting")),
    db: Session = Depends(get_db),
) -> TaxProfileResponse:
    return _service(ctx, db).get_tax_profile(profile_id)


@tax_profiles_router.patch("/{profile_id}", response_model=TaxProfileResponse)
def update_tax_profile(
    profile_id: uuid.UUID,
    payload: TaxProfileUpdate,
    ctx: TenantContext = Depends(require_module("accounting")),
    db: Session = Depends(get_db),
) -> TaxProfileResponse:
    result = _service(ctx, db).update_tax_profile(profile_id, payload)
    db.commit()
    return result
