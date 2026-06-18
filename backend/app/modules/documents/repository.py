import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.enums import DocumentStatus
from app.modules.documents.models import (
    DocumentAuditTrail,
    DocumentField,
    DocumentFile,
    DocumentInstance,
    DocumentTemplate,
    SignatureRequest,
)


class DocumentRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_templates(
        self,
        tenant_id: uuid.UUID,
        *,
        active_only: bool = True,
    ) -> list[DocumentTemplate]:
        stmt = (
            select(DocumentTemplate)
            .where(DocumentTemplate.tenant_id == tenant_id)
            .options(selectinload(DocumentTemplate.fields))
            .order_by(DocumentTemplate.name)
        )
        if active_only:
            stmt = stmt.where(DocumentTemplate.is_active.is_(True))
        return list(self.db.scalars(stmt).all())

    def get_template(
        self,
        tenant_id: uuid.UUID,
        template_id: uuid.UUID,
    ) -> DocumentTemplate | None:
        stmt = (
            select(DocumentTemplate)
            .where(
                DocumentTemplate.tenant_id == tenant_id,
                DocumentTemplate.id == template_id,
            )
            .options(selectinload(DocumentTemplate.fields))
        )
        return self.db.scalar(stmt)

    def get_template_by_code(
        self,
        tenant_id: uuid.UUID,
        code: str,
    ) -> DocumentTemplate | None:
        stmt = select(DocumentTemplate).where(
            DocumentTemplate.tenant_id == tenant_id,
            DocumentTemplate.code == code,
        )
        return self.db.scalar(stmt)

    def create_template(self, **kwargs) -> DocumentTemplate:
        template = DocumentTemplate(**kwargs)
        self.db.add(template)
        self.db.flush()
        return template

    def create_field(self, **kwargs) -> DocumentField:
        field = DocumentField(**kwargs)
        self.db.add(field)
        self.db.flush()
        return field

    def list_documents(
        self,
        tenant_id: uuid.UUID,
        *,
        status: DocumentStatus | None = None,
        party_id: uuid.UUID | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[DocumentInstance]:
        stmt = (
            select(DocumentInstance)
            .where(DocumentInstance.tenant_id == tenant_id)
            .options(
                selectinload(DocumentInstance.files),
                selectinload(DocumentInstance.signature_requests),
                selectinload(DocumentInstance.audit_trail),
            )
            .order_by(DocumentInstance.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        if status:
            stmt = stmt.where(DocumentInstance.status == status)
        if party_id:
            stmt = stmt.where(DocumentInstance.party_id == party_id)
        return list(self.db.scalars(stmt).all())

    def get_document(
        self,
        tenant_id: uuid.UUID,
        document_id: uuid.UUID,
    ) -> DocumentInstance | None:
        stmt = (
            select(DocumentInstance)
            .where(
                DocumentInstance.tenant_id == tenant_id,
                DocumentInstance.id == document_id,
            )
            .options(
                selectinload(DocumentInstance.files),
                selectinload(DocumentInstance.signature_requests),
                selectinload(DocumentInstance.audit_trail),
                selectinload(DocumentInstance.template),
            )
        )
        return self.db.scalar(stmt)

    def create_document(self, **kwargs) -> DocumentInstance:
        doc = DocumentInstance(**kwargs)
        self.db.add(doc)
        self.db.flush()
        return doc

    def create_file(self, **kwargs) -> DocumentFile:
        file = DocumentFile(**kwargs)
        self.db.add(file)
        self.db.flush()
        return file

    def create_signature_request(self, **kwargs) -> SignatureRequest:
        req = SignatureRequest(**kwargs)
        self.db.add(req)
        self.db.flush()
        return req

    def create_audit(self, **kwargs) -> DocumentAuditTrail:
        entry = DocumentAuditTrail(**kwargs)
        self.db.add(entry)
        self.db.flush()
        return entry
