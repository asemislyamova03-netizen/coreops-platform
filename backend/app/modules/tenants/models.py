import uuid

from sqlalchemy import JSON, Boolean, Enum, ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.enums import TenantRole, TenantStatus
from app.core.models import TimestampMixin, UUIDPrimaryKeyMixin


class Tenant(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "tenants"
    __table_args__ = (
        UniqueConstraint("provider_company_id", "slug", name="uq_tenant_provider_slug"),
    )

    provider_company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("provider_companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    industry_template_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("industry_templates.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[TenantStatus] = mapped_column(
        Enum(TenantStatus, name="tenant_status", native_enum=False),
        default=TenantStatus.TRIAL,
        nullable=False,
    )

    provider_company: Mapped["ProviderCompany"] = relationship(
        "ProviderCompany",
        back_populates="tenants",
    )
    memberships: Mapped[list["UserTenantMembership"]] = relationship(
        "UserTenantMembership",
        back_populates="tenant",
        lazy="selectin",
    )
    modules: Mapped[list["TenantModule"]] = relationship(
        "TenantModule",
        back_populates="tenant",
        lazy="selectin",
    )
    settings: Mapped["TenantSettings | None"] = relationship(
        "TenantSettings",
        back_populates="tenant",
        uselist=False,
        lazy="selectin",
    )


class TenantSettings(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "tenant_settings"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    labels_config: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    industry_config_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="settings")


class UserTenantMembership(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "user_tenant_memberships"
    __table_args__ = (
        UniqueConstraint("tenant_id", "user_id", name="uq_tenant_user_membership"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[TenantRole] = mapped_column(
        Enum(TenantRole, name="tenant_role", native_enum=False),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="memberships")
    user: Mapped["User"] = relationship("User", back_populates="tenant_memberships")
