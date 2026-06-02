import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, JSON, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.enums import (
    AddressType,
    ContactMethodType,
    PartyStatus,
    PartyType,
)
from app.core.models import AuditUserMixin, TimestampMixin, UUIDPrimaryKeyMixin

ENTITY_PARTY = "party"


class CustomFieldDefinition(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "custom_field_definitions"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "entity_type",
            "field_key",
            name="uq_custom_field_tenant_entity_key",
        ),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    field_key: Mapped[str] = mapped_column(String(64), nullable=False)
    field_type: Mapped[str] = mapped_column(String(32), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    applies_to_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    options_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    is_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sort_order: Mapped[int] = mapped_column(default=0, nullable=False)
    source_template_code: Mapped[str | None] = mapped_column(String(64), nullable=True)


class Party(Base, UUIDPrimaryKeyMixin, TimestampMixin, AuditUserMixin):
    __tablename__ = "parties"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    party_type: Mapped[PartyType] = mapped_column(
        Enum(PartyType, name="party_type", native_enum=False),
        nullable=False,
    )
    display_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    status: Mapped[PartyStatus] = mapped_column(
        Enum(PartyStatus, name="party_status", native_enum=False),
        default=PartyStatus.ACTIVE,
        nullable=False,
    )
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    contact_methods: Mapped[list["ContactMethod"]] = relationship(
        "ContactMethod",
        back_populates="party",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    addresses: Mapped[list["Address"]] = relationship(
        "Address",
        back_populates="party",
        lazy="selectin",
        cascade="all, delete-orphan",
    )


class ContactMethod(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "contact_methods"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    party_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("parties.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    method_type: Mapped[ContactMethodType] = mapped_column(
        Enum(ContactMethodType, name="contact_method_type", native_enum=False),
        nullable=False,
    )
    value: Mapped[str] = mapped_column(String(320), nullable=False)
    label: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    party: Mapped["Party"] = relationship("Party", back_populates="contact_methods")


class Address(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "addresses"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    party_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("parties.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    address_type: Mapped[AddressType] = mapped_column(
        Enum(AddressType, name="address_type", native_enum=False),
        default=AddressType.ACTUAL,
        nullable=False,
    )
    country: Mapped[str | None] = mapped_column(String(2), nullable=True)
    city: Mapped[str | None] = mapped_column(String(128), nullable=True)
    line1: Mapped[str | None] = mapped_column(String(255), nullable=True)
    line2: Mapped[str | None] = mapped_column(String(255), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    party: Mapped["Party"] = relationship("Party", back_populates="addresses")


class CustomFieldValue(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "custom_field_values"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "entity_type",
            "entity_id",
            "field_key",
            name="uq_custom_field_value_entity_key",
        ),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    entity_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    field_key: Mapped[str] = mapped_column(String(64), nullable=False)
    value_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
