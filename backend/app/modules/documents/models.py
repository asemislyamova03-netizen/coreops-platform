import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.enums import DocumentFileType, DocumentStatus, SignatureStatus
from app.core.models import AuditUserMixin, TimestampMixin, UUIDPrimaryKeyMixin


class DocumentTemplate(Base, UUIDPrimaryKeyMixin, TimestampMixin, AuditUserMixin):
    __tablename__ = "document_templates"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_document_template_tenant_code"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    document_type: Mapped[str] = mapped_column(String(64), default="contract", nullable=False)
    body_template: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    fields: Mapped[list["DocumentField"]] = relationship(
        "DocumentField",
        back_populates="template",
        lazy="selectin",
        cascade="all, delete-orphan",
    )


class DocumentField(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "document_fields"
    __table_args__ = (
        UniqueConstraint("template_id", "field_key", name="uq_document_field_template_key"),
    )

    template_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("document_templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    field_key: Mapped[str] = mapped_column(String(64), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    field_type: Mapped[str] = mapped_column(String(32), default="string", nullable=False)
    is_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    default_value: Mapped[str | None] = mapped_column(Text, nullable=True)

    template: Mapped["DocumentTemplate"] = relationship("DocumentTemplate", back_populates="fields")


class DocumentInstance(Base, UUIDPrimaryKeyMixin, TimestampMixin, AuditUserMixin):
    __tablename__ = "document_instances"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("document_templates.id", ondelete="SET NULL"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, name="document_status", native_enum=False),
        default=DocumentStatus.DRAFT,
        nullable=False,
        index=True,
    )
    rendered_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    context_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    party_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    work_item_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True, index=True)

    template: Mapped["DocumentTemplate | None"] = relationship("DocumentTemplate", lazy="joined")
    files: Mapped[list["DocumentFile"]] = relationship(
        "DocumentFile",
        back_populates="document",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    signature_requests: Mapped[list["SignatureRequest"]] = relationship(
        "SignatureRequest",
        back_populates="document",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    audit_trail: Mapped[list["DocumentAuditTrail"]] = relationship(
        "DocumentAuditTrail",
        back_populates="document",
        lazy="selectin",
        cascade="all, delete-orphan",
    )


class DocumentFile(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "document_files"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("document_instances.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_type: Mapped[DocumentFileType] = mapped_column(
        Enum(DocumentFileType, name="document_file_type", native_enum=False),
        nullable=False,
    )
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), default="text/plain", nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    document: Mapped["DocumentInstance"] = relationship("DocumentInstance", back_populates="files")


class SignatureRequest(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "signature_requests"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("document_instances.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[SignatureStatus] = mapped_column(
        Enum(SignatureStatus, name="signature_status", native_enum=False),
        default=SignatureStatus.PENDING,
        nullable=False,
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    document: Mapped["DocumentInstance"] = relationship(
        "DocumentInstance",
        back_populates="signature_requests",
    )


class DocumentAuditTrail(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "document_audit_trail"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("document_instances.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    details_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    document: Mapped["DocumentInstance"] = relationship(
        "DocumentInstance",
        back_populates="audit_trail",
    )
