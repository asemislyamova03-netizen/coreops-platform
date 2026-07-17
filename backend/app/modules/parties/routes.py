import uuid

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.enums import DataAccessType, PartyStatus, PartyType
from app.modules.audit.recorder import AuditRecorder
from app.core.modules import require_module
from app.core.tenancy import TenantContext
from app.modules.auth.models import User
from app.modules.parties.models import ENTITY_PARTY
from app.modules.parties.schemas import (
    CustomFieldDefinitionResponse,
    PartyCreate,
    PartyMatchRequest,
    PartyMatchResponse,
    PartyResponse,
    PartyUpdate,
)
from app.modules.parties.service import PartyService

router = APIRouter(prefix="/parties", tags=["parties"])


def _service(ctx: TenantContext, db: Session) -> PartyService:
    return PartyService(db, ctx.tenant.id)


@router.post("/match", response_model=PartyMatchResponse)
def match_parties(
    payload: PartyMatchRequest,
    ctx: TenantContext = Depends(require_module("parties")),
    db: Session = Depends(get_db),
) -> PartyMatchResponse:
    """Read-only party contact match. Does not create, link, or merge parties."""
    return _service(ctx, db).match_parties(payload)


@router.get("", response_model=list[PartyResponse])
def list_parties(
    party_type: PartyType | None = None,
    status: PartyStatus | None = None,
    party_role: str | None = Query(default=None, max_length=64),
    search: str | None = Query(default=None, max_length=255),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    ctx: TenantContext = Depends(require_module("parties")),
    db: Session = Depends(get_db),
) -> list[PartyResponse]:
    return _service(ctx, db).list_parties(
        party_type=party_type,
        status=status,
        party_role=party_role,
        search=search,
        skip=skip,
        limit=limit,
    )


@router.post("", response_model=PartyResponse, status_code=201)
def create_party(
    payload: PartyCreate,
    ctx: TenantContext = Depends(require_module("parties")),
    db: Session = Depends(get_db),
) -> PartyResponse:
    result = _service(ctx, db).create_party(ctx.user, payload)
    db.commit()
    return result


@router.get("/custom-field-definitions", response_model=list[CustomFieldDefinitionResponse])
def list_custom_field_definitions(
    entity_type: str = Query(default=ENTITY_PARTY),
    ctx: TenantContext = Depends(require_module("parties")),
    db: Session = Depends(get_db),
) -> list[CustomFieldDefinitionResponse]:
    definitions = _service(ctx, db).list_custom_field_definitions(entity_type)
    return [CustomFieldDefinitionResponse.model_validate(d) for d in definitions]


@router.get("/{party_id}", response_model=PartyResponse)
def get_party(
    party_id: uuid.UUID,
    request: Request,
    ctx: TenantContext = Depends(require_module("parties")),
    db: Session = Depends(get_db),
) -> PartyResponse:
    result = _service(ctx, db).get_party(party_id)
    AuditRecorder(db).data_access(
        tenant_id=ctx.tenant.id,
        user_id=ctx.user.id,
        entity_type="party",
        entity_id=party_id,
        access_type=DataAccessType.READ,
        resource_label=result.display_name,
        request=request,
    )
    db.commit()
    return result


@router.patch("/{party_id}", response_model=PartyResponse)
def update_party(
    party_id: uuid.UUID,
    payload: PartyUpdate,
    ctx: TenantContext = Depends(require_module("parties")),
    db: Session = Depends(get_db),
) -> PartyResponse:
    result = _service(ctx, db).update_party(ctx.user, party_id, payload)
    db.commit()
    return result


@router.delete("/{party_id}", status_code=204)
def delete_party(
    party_id: uuid.UUID,
    ctx: TenantContext = Depends(require_module("parties")),
    db: Session = Depends(get_db),
) -> None:
    _service(ctx, db).delete_party(party_id)
    db.commit()
