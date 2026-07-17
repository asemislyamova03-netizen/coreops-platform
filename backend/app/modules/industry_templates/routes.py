import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db, require_provider_owner
from app.modules.auth.models import User
from app.modules.industry_templates.schemas import (
    ApplyTemplateResponse,
    IndustryTemplateCreate,
    IndustryTemplateResponse,
    IndustryTemplateUpdate,
    LeadSourceResponse,
)
from app.modules.industry_templates.service import IndustryTemplateService

router = APIRouter(prefix="/industry-templates", tags=["industry-templates"])
tenant_template_router = APIRouter(tags=["industry-templates"])


@router.get("", response_model=list[IndustryTemplateResponse])
def list_industry_templates(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[IndustryTemplateResponse]:
    templates = IndustryTemplateService(db).list_templates()
    return [IndustryTemplateResponse.model_validate(t) for t in templates]


@router.post("", response_model=IndustryTemplateResponse, status_code=201)
def create_industry_template(
    payload: IndustryTemplateCreate,
    _: User = Depends(require_provider_owner),
    db: Session = Depends(get_db),
) -> IndustryTemplateResponse:
    template = IndustryTemplateService(db).create_template(payload)
    return IndustryTemplateResponse.model_validate(template)


@router.get("/{template_id}", response_model=IndustryTemplateResponse)
def get_industry_template(
    template_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> IndustryTemplateResponse:
    template = IndustryTemplateService(db).get_template(template_id)
    return IndustryTemplateResponse.model_validate(template)


@router.patch("/{template_id}", response_model=IndustryTemplateResponse)
def update_industry_template(
    template_id: uuid.UUID,
    payload: IndustryTemplateUpdate,
    _: User = Depends(require_provider_owner),
    db: Session = Depends(get_db),
) -> IndustryTemplateResponse:
    template = IndustryTemplateService(db).update_template(template_id, payload)
    return IndustryTemplateResponse.model_validate(template)


@tenant_template_router.post(
    "/tenants/{tenant_id}/apply-template/{template_id}",
    response_model=ApplyTemplateResponse,
)
def apply_industry_template(
    tenant_id: uuid.UUID,
    template_id: uuid.UUID,
    current_user: User = Depends(require_provider_owner),
    db: Session = Depends(get_db),
) -> ApplyTemplateResponse:
    result = IndustryTemplateService(db).apply_to_tenant(
        current_user, tenant_id, template_id
    )
    db.commit()
    return result


@tenant_template_router.get("/tenants/{tenant_id}/labels")
def get_tenant_labels(
    tenant_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return IndustryTemplateService(db).get_tenant_labels(current_user, tenant_id)


@tenant_template_router.get(
    "/tenants/{tenant_id}/lead-sources",
    response_model=list[LeadSourceResponse],
)
def get_tenant_lead_sources(
    tenant_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[LeadSourceResponse]:
    return IndustryTemplateService(db).get_tenant_lead_sources(current_user, tenant_id)
