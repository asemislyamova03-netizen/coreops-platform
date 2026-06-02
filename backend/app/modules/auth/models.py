from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.models import TimestampMixin, UUIDPrimaryKeyMixin


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    provider_staff: Mapped[list["ProviderStaff"]] = relationship(
        "ProviderStaff",
        back_populates="user",
        lazy="selectin",
    )
    tenant_memberships: Mapped[list["UserTenantMembership"]] = relationship(
        "UserTenantMembership",
        back_populates="user",
        lazy="selectin",
    )
