import uuid

from sqlalchemy import Enum, ForeignKey, JSON, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.enums import ModuleMode, ModuleStatus
from app.core.models import TimestampMixin, UUIDPrimaryKeyMixin


class ModuleDefinition(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "module_definitions"

    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_mode: Mapped[ModuleMode] = mapped_column(
        Enum(ModuleMode, name="module_mode", native_enum=False),
        default=ModuleMode.INTERNAL,
        nullable=False,
    )
    dependencies_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)


class TenantModule(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "tenant_modules"
    __table_args__ = (UniqueConstraint("tenant_id", "module_code", name="uq_tenant_module"),)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    module_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[ModuleStatus] = mapped_column(
        Enum(ModuleStatus, name="module_status", native_enum=False),
        default=ModuleStatus.DISABLED,
        nullable=False,
    )
    mode: Mapped[ModuleMode] = mapped_column(
        Enum(ModuleMode, name="module_mode", native_enum=False),
        default=ModuleMode.DISABLED,
        nullable=False,
    )
    external_provider_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    settings_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="modules")
