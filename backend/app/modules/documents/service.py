import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.enums import AuditAction, DocumentFileType, DocumentStatus, SignatureStatus
from app.modules.audit.recorder import AuditRecorder
from app.core.exceptions import ConflictError, NotFoundError
from app.modules.auth.models import User
from app.modules.documents.models import DocumentTemplate
from app.modules.documents.repository import DocumentRepository
from app.modules.documents.schemas import (
    DocumentGenerateRequest,
    DocumentImportCreate,
    DocumentResponse,
    DocumentTemplateCreate,
    DocumentTemplateResponse,
    DocumentTemplateUpdate,
    DocumentUpdate,
    LegacyContractImportInput,
    assess_legacy_contract_import,
)
from app.modules.documents import storage as file_storage
from app.modules.documents.template_engine import extract_placeholders, render_template


class DocumentService:
    def __init__(self, db: Session, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.repo = DocumentRepository(db)

    def list_templates(self, active_only: bool = True) -> list[DocumentTemplateResponse]:
        templates = self.repo.list_templates(self.tenant_id, active_only=active_only)
        return [DocumentTemplateResponse.model_validate(t) for t in templates]

    def get_template(self, template_id: uuid.UUID) -> DocumentTemplateResponse:
        template = self._get_template_or_404(template_id)
        return DocumentTemplateResponse.model_validate(template)

    def create_template(
        self,
        user: User,
        payload: DocumentTemplateCreate,
    ) -> DocumentTemplateResponse:
        if self.repo.get_template_by_code(self.tenant_id, payload.code):
            raise ConflictError("Document template code already exists")

        template = self.repo.create_template(
            tenant_id=self.tenant_id,
            code=payload.code,
            name=payload.name,
            description=payload.description,
            document_type=payload.document_type,
            body_template=payload.body_template,
            is_active=payload.is_active,
            created_by_user_id=user.id,
            updated_by_user_id=user.id,
        )
        for field_data in payload.fields:
            self.repo.create_field(
                template_id=template.id,
                field_key=field_data.field_key,
                label=field_data.label,
                field_type=field_data.field_type,
                is_required=field_data.is_required,
                default_value=field_data.default_value,
            )
        self.db.refresh(template)
        return DocumentTemplateResponse.model_validate(template)

    def update_template(
        self,
        user: User,
        template_id: uuid.UUID,
        payload: DocumentTemplateUpdate,
    ) -> DocumentTemplateResponse:
        template = self._get_template_or_404(template_id)
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(template, key, value)
        template.updated_by_user_id = user.id
        self.db.flush()
        self.db.refresh(template)
        return DocumentTemplateResponse.model_validate(template)

    def import_templates_from_config(
        self,
        user: User,
        templates_config: list[dict],
    ) -> int:
        created = 0
        for item in templates_config:
            code = item["code"]
            if self.repo.get_template_by_code(self.tenant_id, code):
                continue
            body = item.get("body_template") or _default_body_for_code(code)
            template = self.repo.create_template(
                tenant_id=self.tenant_id,
                code=code,
                name=item["name"],
                description=item.get("description"),
                document_type=item.get("document_type", "contract"),
                body_template=body,
                is_active=True,
                created_by_user_id=user.id,
                updated_by_user_id=user.id,
            )
            for field_data in item.get("fields", _default_fields_for_code(code)):
                self.repo.create_field(
                    template_id=template.id,
                    field_key=field_data["field_key"],
                    label=field_data["label"],
                    field_type=field_data.get("field_type", "string"),
                    is_required=field_data.get("is_required", False),
                    default_value=field_data.get("default_value"),
                )
            created += 1
        return created

    def list_documents(
        self,
        *,
        status: DocumentStatus | None = None,
        party_id: uuid.UUID | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[DocumentResponse]:
        docs = self.repo.list_documents(
            self.tenant_id,
            status=status,
            party_id=party_id,
            skip=skip,
            limit=limit,
        )
        return [DocumentResponse.model_validate(d) for d in docs]

    def get_document(self, document_id: uuid.UUID) -> DocumentResponse:
        doc = self._get_document_or_404(document_id)
        return DocumentResponse.model_validate(doc)

    def generate_document(
        self,
        user: User,
        payload: DocumentGenerateRequest,
    ) -> DocumentResponse:
        template = self._get_template_or_404(payload.template_id)
        if not template.is_active:
            raise ConflictError("Document template is not active")

        context = self._build_context(template, payload.context)
        try:
            rendered = render_template(template.body_template, context)
        except KeyError as exc:
            raise ConflictError(f"Missing placeholder value: {exc.args[0]}") from exc

        title = payload.title or template.name
        doc = self.repo.create_document(
            tenant_id=self.tenant_id,
            template_id=template.id,
            title=title,
            status=DocumentStatus.GENERATED,
            rendered_content=rendered,
            context_json=context,
            party_id=payload.party_id,
            work_item_id=payload.work_item_id,
            created_by_user_id=user.id,
            updated_by_user_id=user.id,
        )

        filename = f"{doc.id}.txt"
        storage_path, size = file_storage.save_text_file(
            self.tenant_id,
            doc.id,
            filename,
            rendered,
        )
        self.repo.create_file(
            tenant_id=self.tenant_id,
            document_id=doc.id,
            file_type=DocumentFileType.GENERATED,
            storage_path=storage_path,
            filename=filename,
            mime_type="text/plain",
            size_bytes=size,
        )
        self._audit(doc.id, user.id, "generated", {"template_code": template.code})
        AuditRecorder(self.db).audit_log(
            action=AuditAction.CREATE,
            summary=f"Document generated: {doc.title}",
            tenant_id=self.tenant_id,
            user_id=user.id,
            entity_type="document_instance",
            entity_id=doc.id,
            metadata_json={"template_code": template.code},
        )

        self.db.refresh(doc)
        return DocumentResponse.model_validate(doc)

    def import_document(
        self,
        user: User,
        payload: DocumentImportCreate,
    ) -> DocumentResponse:
        """
        Create a historical document/contract instance without template generation.
        Amount, external_ref and review flags live in context_json (no migration).
        """
        assessment = assess_legacy_contract_import(
            LegacyContractImportInput(
                legacy_status=payload.legacy_status,
                work_item_id=payload.work_item_id,
                amount=payload.amount,
            )
        )
        status = payload.status or assessment.target_status

        context: dict[str, str] = {
            "import_mode": "legacy_contract",
            "source_system": payload.source_system,
            "amount": str(payload.amount),
            "status_needs_review": str(assessment.status_needs_review).lower(),
            "link_needs_review": str(assessment.link_needs_review).lower(),
            "amount_needs_review": str(assessment.amount_needs_review).lower(),
        }
        if payload.external_ref:
            context["external_ref"] = payload.external_ref
            context["external_legacy_id"] = payload.external_ref
        if payload.legacy_status is not None:
            context["legacy_status"] = payload.legacy_status
        if payload.branch_id is not None:
            context["branch_id"] = str(payload.branch_id)
        context.update({k: str(v) for k, v in payload.extra_context.items()})

        doc = self.repo.create_document(
            tenant_id=self.tenant_id,
            template_id=None,
            title=payload.title,
            status=status,
            rendered_content=payload.rendered_content,
            context_json=context,
            party_id=payload.party_id,
            work_item_id=payload.work_item_id,
            created_by_user_id=user.id,
            updated_by_user_id=user.id,
        )
        self._audit(
            doc.id,
            user.id,
            "imported",
            {
                "source_system": payload.source_system,
                "external_ref": payload.external_ref,
                "amount": str(payload.amount),
                "link_needs_review": assessment.link_needs_review,
                "amount_needs_review": assessment.amount_needs_review,
                "status_needs_review": assessment.status_needs_review,
            },
        )
        AuditRecorder(self.db).audit_log(
            action=AuditAction.CREATE,
            summary=f"Document imported: {doc.title}",
            tenant_id=self.tenant_id,
            user_id=user.id,
            entity_type="document_instance",
            entity_id=doc.id,
            metadata_json={
                "import_mode": "legacy_contract",
                "source_system": payload.source_system,
                "external_ref": payload.external_ref,
            },
        )
        self.db.refresh(doc)
        return DocumentResponse.model_validate(doc)

    def update_document(
        self,
        user: User,
        document_id: uuid.UUID,
        payload: DocumentUpdate,
    ) -> DocumentResponse:
        doc = self._get_document_or_404(document_id)
        if payload.title is not None:
            doc.title = payload.title
        if payload.status is not None:
            old_status = doc.status
            doc.status = payload.status
            self._audit(
                doc.id,
                user.id,
                "status_changed",
                {"from": old_status.value, "to": payload.status.value},
            )
        doc.updated_by_user_id = user.id
        self.db.flush()
        self.db.refresh(doc)
        return DocumentResponse.model_validate(doc)

    def send_for_signature(self, user: User, document_id: uuid.UUID) -> DocumentResponse:
        doc = self._get_document_or_404(document_id)
        if doc.status not in (
            DocumentStatus.GENERATED,
            DocumentStatus.SENT_FOR_REVIEW,
        ):
            raise ConflictError("Document cannot be sent for signature in current status")

        now = datetime.now(UTC)
        doc.status = DocumentStatus.SENT_FOR_SIGNATURE
        doc.updated_by_user_id = user.id
        self.repo.create_signature_request(
            tenant_id=self.tenant_id,
            document_id=doc.id,
            status=SignatureStatus.SENT,
            sent_at=now,
        )
        self._audit(doc.id, user.id, "sent_for_signature", {})
        self.db.flush()
        self.db.refresh(doc)
        return DocumentResponse.model_validate(doc)

    def upload_signed_file(
        self,
        user: User,
        document_id: uuid.UUID,
        filename: str,
        content: bytes,
        mime_type: str = "application/octet-stream",
    ) -> DocumentResponse:
        doc = self._get_document_or_404(document_id)
        if doc.status not in (
            DocumentStatus.SENT_FOR_SIGNATURE,
            DocumentStatus.SENT_FOR_REVIEW,
            DocumentStatus.GENERATED,
        ):
            raise ConflictError("Document cannot accept signed file in current status")

        storage_path, size = file_storage.save_binary_file(
            self.tenant_id,
            doc.id,
            filename,
            content,
        )
        self.repo.create_file(
            tenant_id=self.tenant_id,
            document_id=doc.id,
            file_type=DocumentFileType.SIGNED,
            storage_path=storage_path,
            filename=filename,
            mime_type=mime_type,
            size_bytes=size,
        )

        now = datetime.now(UTC)
        doc.status = DocumentStatus.SIGNED
        doc.updated_by_user_id = user.id

        for req in doc.signature_requests:
            if req.status == SignatureStatus.SENT:
                req.status = SignatureStatus.SIGNED
                req.signed_at = now

        self._audit(doc.id, user.id, "signed", {"filename": filename})
        self.db.flush()
        self.db.refresh(doc)
        return DocumentResponse.model_validate(doc)

    def _build_context(
        self,
        template: DocumentTemplate,
        provided: dict[str, str],
    ) -> dict[str, str]:
        context = {k: str(v) for k, v in provided.items()}
        placeholders = extract_placeholders(template.body_template)
        for field in template.fields:
            if field.field_key in context:
                continue
            if field.default_value is not None:
                context[field.field_key] = field.default_value
            elif field.is_required and field.field_key in placeholders:
                raise ConflictError(f"Required field missing: {field.field_key}")
        missing = placeholders - set(context.keys())
        if missing:
            raise ConflictError(
                f"Missing placeholder values: {', '.join(sorted(missing))}"
            )
        return context

    def _audit(
        self,
        document_id: uuid.UUID,
        actor_user_id: uuid.UUID | None,
        action: str,
        details: dict,
    ) -> None:
        self.repo.create_audit(
            tenant_id=self.tenant_id,
            document_id=document_id,
            action=action,
            actor_user_id=actor_user_id,
            details_json=details,
        )

    def _get_template_or_404(self, template_id: uuid.UUID) -> DocumentTemplate:
        template = self.repo.get_template(self.tenant_id, template_id)
        if not template:
            raise NotFoundError("Document template not found")
        return template

    def _get_document_or_404(self, document_id: uuid.UUID):
        doc = self.repo.get_document(self.tenant_id, document_id)
        if not doc:
            raise NotFoundError("Document not found")
        return doc


def _default_body_for_code(code: str) -> str:
    bodies = {
        "parent_contract": (
            "ДОГОВОР № {{contract_number}}\n\n"
            "Законный представитель: {{guardian_name}}\n"
            "Ребёнок: {{child_name}}\n"
            "Дата: {{contract_date}}\n"
        ),
        "enrollment_application": (
            "ЗАЯВЛЕНИЕ НА ЗАЧИСЛЕНИЕ\n\n"
            "Ребёнок: {{child_name}}\n"
            "Законный представитель: {{guardian_name}}\n"
            "Дата: {{application_date}}\n"
        ),
    }
    return bodies.get(
        code,
        "Документ {{document_code}}\n\nСодержание: {{body}}\n",
    )


def _default_fields_for_code(code: str) -> list[dict]:
    if code == "parent_contract":
        return [
            {"field_key": "contract_number", "label": "Номер договора", "is_required": True},
            {"field_key": "guardian_name", "label": "Законный представитель", "is_required": True},
            {"field_key": "child_name", "label": "Ребёнок", "is_required": True},
            {"field_key": "contract_date", "label": "Дата договора", "is_required": True},
        ]
    if code == "enrollment_application":
        return [
            {"field_key": "child_name", "label": "Ребёнок", "is_required": True},
            {"field_key": "guardian_name", "label": "Законный представитель", "is_required": True},
            {"field_key": "application_date", "label": "Дата заявления", "is_required": True},
        ]
    return [{"field_key": "body", "label": "Текст", "is_required": True}]
