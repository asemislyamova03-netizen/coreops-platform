import uuid

from sqlalchemy import JSON, Boolean, Enum, ForeignKey, Numeric, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.enums import TaxRegime
from app.core.models import TimestampMixin, UUIDPrimaryKeyMixin


class LegalEntity(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "legal_entities"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_legal_entity_tenant_name"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    legal_form: Mapped[str | None] = mapped_column(String(64), nullable=True)
    country: Mapped[str] = mapped_column(String(2), default="RU", nullable=False)
    registration_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tax_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    residency_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    base_currency: Mapped[str] = mapped_column(String(3), default="RUB", nullable=False)
    bank_details_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    tax_profiles: Mapped[list["TaxProfile"]] = relationship(
        "TaxProfile",
        back_populates="legal_entity",
        lazy="selectin",
        cascade="all, delete-orphan",
    )


class TaxProfile(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "tax_profiles"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_tax_profile_tenant_code"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    legal_entity_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("legal_entities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    country: Mapped[str] = mapped_column(String(2), default="RU", nullable=False)
    tax_regime: Mapped[TaxRegime] = mapped_column(
        Enum(TaxRegime, name="tax_regime", native_enum=False),
        default=TaxRegime.GENERAL,
        nullable=False,
    )
    default_vat_rate: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    config_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    legal_entity: Mapped["LegalEntity"] = relationship("LegalEntity", back_populates="tax_profiles")
