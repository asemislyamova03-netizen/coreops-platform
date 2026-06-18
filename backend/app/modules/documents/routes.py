import uuid

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.entitlements import require_feature
from app.core.enums import DocumentStatus
from app.core.modules import require_module
from app.core.tenancy import TenantContext
from app.modules.documents.schemas import (
    DocumentGenerateRequest,
    DocumentResponse,
    DocumentTemplateCreate,
    DocumentTemplateResponse,
    DocumentTemplateUpdate,
    DocumentUpdate,
)
from app.modules.documents.service import DocumentService

templates_router = APIRouter(prefix="/document-templates", tags=["documents"])
documents_router = APIRouter(prefix="/documents", tags=["documents"])


def _service(ctx: TenantContext, db: Session) -> DocumentService:
    return DocumentService(db, ctx.tenant.id)


@templates_router.get("", response_model=list[DocumentTemplateResponse])
def list_document_templates(
    active_only: bool = True,
    ctx: TenantContext = Depends(require_module("documents")),
    db: Session = Depends(get_db),
) -> list[DocumentTemplateResponse]:
    return _service(ctx, db).list_templates(active_only=active_only)


@templates_router.post("", response_model=DocumentTemplateResponse, status_code=201)
def create_document_template(
    payload: DocumentTemplateCreate,
    ctx: TenantContext = Depends(require_module("documents")),
    db: Session = Depends(get_db),
) -> DocumentTemplateResponse:
    result = _service(ctx, db).create_template(ctx.user, payload)
    db.commit()
    return result


@templates_router.get("/{template_id}", response_model=DocumentTemplateResponse)
def get_document_template(
    template_id: uuid.UUID,
    ctx: TenantContext = Depends(require_module("documents")),
    db: Session = Depends(get_db),
) -> DocumentTemplateResponse:
    return _service(ctx, db).get_template(template_id)


@templates_router.patch("/{template_id}", response_model=DocumentTemplateResponse)
def update_document_template(
    template_id: uuid.UUID,
    payload: DocumentTemplateUpdate,
    ctx: TenantContext = Depends(require_module("documents")),
    db: Session = Depends(get_db),
) -> DocumentTemplateResponse:
    result = _service(ctx, db).update_template(ctx.user, template_id, payload)
    db.commit()
    return result


@documents_router.get("", response_model=list[DocumentResponse])
def list_documents(
    status: DocumentStatus | None = None,
    party_id: uuid.UUID | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    ctx: TenantContext = Depends(require_module("documents")),
    db: Session = Depends(get_db),
) -> list[DocumentResponse]:
    return _service(ctx, db).list_documents(
        status=status,
        party_id=party_id,
        skip=skip,
        limit=limit,
    )


@documents_router.post("/generate", response_model=DocumentResponse, status_code=201)
def generate_document(
    payload: DocumentGenerateRequest,
    ctx: TenantContext = Depends(require_feature("documents.generate")),
    db: Session = Depends(get_db),
) -> DocumentResponse:
    result = _service(ctx, db).generate_document(ctx.user, payload)
    db.commit()
    return result


@documents_router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: uuid.UUID,
    ctx: TenantContext = Depends(require_module("documents")),
    db: Session = Depends(get_db),
) -> DocumentResponse:
    return _service(ctx, db).get_document(document_id)


@documents_router.patch("/{document_id}", response_model=DocumentResponse)
def update_document(
    document_id: uuid.UUID,
    payload: DocumentUpdate,
    ctx: TenantContext = Depends(require_module("documents")),
    db: Session = Depends(get_db),
) -> DocumentResponse:
    result = _service(ctx, db).update_document(ctx.user, document_id, payload)
    db.commit()
    return result


@documents_router.post("/{document_id}/send-for-signature", response_model=DocumentResponse)
def send_document_for_signature(
    document_id: uuid.UUID,
    ctx: TenantContext = Depends(require_module("documents")),
    db: Session = Depends(get_db),
) -> DocumentResponse:
    result = _service(ctx, db).send_for_signature(ctx.user, document_id)
    db.commit()
    return result


@documents_router.post("/{document_id}/upload-signed-file", response_model=DocumentResponse)
async def upload_signed_document_file(
    document_id: uuid.UUID,
    file: UploadFile = File(...),
    ctx: TenantContext = Depends(require_module("documents")),
    db: Session = Depends(get_db),
) -> DocumentResponse:
    content = await file.read()
    filename = file.filename or "signed.pdf"
    mime_type = file.content_type or "application/octet-stream"
    result = _service(ctx, db).upload_signed_file(
        ctx.user,
        document_id,
        filename,
        content,
        mime_type=mime_type,
    )
    db.commit()
    return result
