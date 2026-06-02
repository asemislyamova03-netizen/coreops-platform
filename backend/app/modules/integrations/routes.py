import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.core.enums import SyncJobType
from app.core.modules import require_module
from app.core.tenancy import TenantContext, get_tenant_context
from app.modules.auth.models import User
from app.modules.integrations.schemas import (
    ConnectionTestResponse,
    ExternalReferenceCreate,
    ExternalReferenceResponse,
    IntegrationConnectionCreate,
    IntegrationConnectionResponse,
    IntegrationConnectionUpdate,
    IntegrationProviderResponse,
    SyncJobDetailResponse,
    SyncJobResponse,
    WebhookPayload,
    WebhookReceiveResponse,
)
from app.modules.integrations.service import IntegrationService

providers_router = APIRouter(prefix="/integrations/providers", tags=["integrations"])
connections_router = APIRouter(prefix="/integrations/connections", tags=["integrations"])
sync_router = APIRouter(prefix="/integrations/sync-jobs", tags=["integrations"])
references_router = APIRouter(prefix="/integrations/external-references", tags=["integrations"])
webhooks_router = APIRouter(prefix="/integrations/webhooks", tags=["integrations"])


def _tenant_service(ctx: TenantContext, db: Session) -> IntegrationService:
    return IntegrationService(db, ctx.tenant.id)


@providers_router.get("", response_model=list[IntegrationProviderResponse])
def list_providers(
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[IntegrationProviderResponse]:
    return IntegrationService(db).list_providers()


@connections_router.get("", response_model=list[IntegrationConnectionResponse])
def list_connections(
    module_code: str | None = None,
    provider_code: str | None = None,
    ctx: TenantContext = Depends(require_module("integrations")),
    db: Session = Depends(get_db),
) -> list[IntegrationConnectionResponse]:
    return _tenant_service(ctx, db).list_connections(
        module_code=module_code,
        provider_code=provider_code,
    )


@connections_router.post("", response_model=IntegrationConnectionResponse, status_code=201)
def create_connection(
    payload: IntegrationConnectionCreate,
    ctx: TenantContext = Depends(require_module("integrations")),
    db: Session = Depends(get_db),
) -> IntegrationConnectionResponse:
    result = _tenant_service(ctx, db).create_connection(payload)
    db.commit()
    return result


@connections_router.get("/{connection_id}", response_model=IntegrationConnectionResponse)
def get_connection(
    connection_id: uuid.UUID,
    ctx: TenantContext = Depends(require_module("integrations")),
    db: Session = Depends(get_db),
) -> IntegrationConnectionResponse:
    return _tenant_service(ctx, db).get_connection(connection_id)


@connections_router.patch("/{connection_id}", response_model=IntegrationConnectionResponse)
def update_connection(
    connection_id: uuid.UUID,
    payload: IntegrationConnectionUpdate,
    ctx: TenantContext = Depends(require_module("integrations")),
    db: Session = Depends(get_db),
) -> IntegrationConnectionResponse:
    result = _tenant_service(ctx, db).update_connection(connection_id, payload)
    db.commit()
    return result


@connections_router.post("/{connection_id}/test", response_model=ConnectionTestResponse)
def test_connection(
    connection_id: uuid.UUID,
    ctx: TenantContext = Depends(require_module("integrations")),
    db: Session = Depends(get_db),
) -> ConnectionTestResponse:
    result = _tenant_service(ctx, db).test_connection(connection_id)
    db.commit()
    return result


@connections_router.post("/{connection_id}/sync", response_model=SyncJobDetailResponse)
def sync_connection(
    connection_id: uuid.UUID,
    job_type: SyncJobType = SyncJobType.INCREMENTAL,
    ctx: TenantContext = Depends(require_module("integrations")),
    db: Session = Depends(get_db),
) -> SyncJobDetailResponse:
    result = _tenant_service(ctx, db).run_sync(connection_id, job_type=job_type)
    db.commit()
    return result


@sync_router.get("", response_model=list[SyncJobResponse])
def list_sync_jobs(
    connection_id: uuid.UUID | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    ctx: TenantContext = Depends(require_module("integrations")),
    db: Session = Depends(get_db),
) -> list[SyncJobResponse]:
    return _tenant_service(ctx, db).list_sync_jobs(connection_id=connection_id, limit=limit)


@sync_router.get("/{job_id}", response_model=SyncJobDetailResponse)
def get_sync_job(
    job_id: uuid.UUID,
    ctx: TenantContext = Depends(require_module("integrations")),
    db: Session = Depends(get_db),
) -> SyncJobDetailResponse:
    return _tenant_service(ctx, db).get_sync_job(job_id)


@references_router.get("", response_model=list[ExternalReferenceResponse])
def list_external_references(
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
    provider_code: str | None = None,
    ctx: TenantContext = Depends(require_module("integrations")),
    db: Session = Depends(get_db),
) -> list[ExternalReferenceResponse]:
    return _tenant_service(ctx, db).list_external_references(
        entity_type=entity_type,
        entity_id=entity_id,
        provider_code=provider_code,
    )


@references_router.post("", response_model=ExternalReferenceResponse, status_code=201)
def create_external_reference(
    payload: ExternalReferenceCreate,
    ctx: TenantContext = Depends(require_module("integrations")),
    db: Session = Depends(get_db),
) -> ExternalReferenceResponse:
    result = _tenant_service(ctx, db).create_external_reference(payload)
    db.commit()
    return result


@webhooks_router.post("/{provider_code}", response_model=WebhookReceiveResponse)
def receive_webhook(
    provider_code: str,
    payload: WebhookPayload,
    db: Session = Depends(get_db),
) -> WebhookReceiveResponse:
    result = IntegrationService(db).receive_webhook(
        provider_code,
        event_type=payload.event_type,
        payload=payload.payload,
        tenant_id=payload.tenant_id,
    )
    db.commit()
    return result
