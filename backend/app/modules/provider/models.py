import uuid

from sqlalchemy import Enum, ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.enums import ProviderRole
from app.core.models import TimestampMixin, UUIDPrimaryKeyMixin


class ProviderCompany(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "provider_companies"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    staff: Mapped[list["ProviderStaff"]] = relationship(
        "ProviderStaff",
        back_populates="provider_company",
        lazy="selectin",
    )
    tenants: Mapped[list["Tenant"]] = relationship(
        "Tenant",
        back_populates="provider_company",
        lazy="selectin",
    )


class ProviderStaff(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "provider_staff"
    __table_args__ = (
        UniqueConstraint("provider_company_id", "user_id", name="uq_provider_staff_user"),
    )

    provider_company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("provider_companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[ProviderRole] = mapped_column(
        Enum(ProviderRole, name="provider_role", native_enum=False),
        nullable=False,
    )

    provider_company: Mapped["ProviderCompany"] = relationship(
        "ProviderCompany",
        back_populates="staff",
    )
    user: Mapped["User"] = relationship("User", back_populates="provider_staff")
