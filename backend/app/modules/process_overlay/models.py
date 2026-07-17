import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    JSON,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    event,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.models import AuditUserMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.modules.process_overlay.enums import ProcessOverlayActivationState
from app.modules.process_overlay.exceptions import ProcessDefinitionImmutableError


class ProcessTemplate(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "process_templates"

    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_pipeline_code: Mapped[str] = mapped_column(String(64), nullable=False)
    default_policy_blueprint_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    required_module_codes_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)


class TenantProcessConfiguration(Base, UUIDPrimaryKeyMixin, TimestampMixin, AuditUserMixin):
    __tablename__ = "tenant_process_configurations"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "process_template_id",
            name="uq_tenant_process_config_tenant_template",
        ),
        UniqueConstraint(
            "tenant_id",
            "pipeline_id",
            name="uq_tenant_process_config_tenant_pipeline",
        ),
        ForeignKeyConstraint(
            ["id", "active_definition_version_id"],
            [
                "process_definition_versions.tenant_process_configuration_id",
                "process_definition_versions.id",
            ],
            name="fk_tenant_process_config_active_version",
            ondelete="RESTRICT",
            use_alter=True,
        ),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    process_template_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("process_templates.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    pipeline_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("pipelines.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    activation_state: Mapped[ProcessOverlayActivationState] = mapped_column(
        Enum(
            ProcessOverlayActivationState,
            name="process_overlay_activation_state",
            native_enum=False,
        ),
        default=ProcessOverlayActivationState.INACTIVE,
        nullable=False,
    )
    active_definition_version_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        nullable=True,
        index=True,
    )

    process_template: Mapped["ProcessTemplate"] = relationship("ProcessTemplate")
    definition_versions: Mapped[list["ProcessDefinitionVersion"]] = relationship(
        "ProcessDefinitionVersion",
        back_populates="configuration",
        foreign_keys="ProcessDefinitionVersion.tenant_process_configuration_id",
        lazy="selectin",
    )


class ProcessDefinitionVersion(Base, UUIDPrimaryKeyMixin):
    """Immutable published snapshot. No updated_at — append-only."""

    __tablename__ = "process_definition_versions"
    __table_args__ = (
        UniqueConstraint(
            "tenant_process_configuration_id",
            "version_number",
            name="uq_process_def_version_config_number",
        ),
        UniqueConstraint(
            "tenant_process_configuration_id",
            "id",
            name="uq_process_def_version_config_id",
        ),
        CheckConstraint("version_number > 0", name="ck_process_def_version_number_positive"),
        CheckConstraint(
            "length(trim(publish_reason)) > 0",
            name="ck_process_def_version_publish_reason_nonempty",
        ),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_process_configuration_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tenant_process_configurations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    version_number: Mapped[int] = mapped_column(nullable=False)
    pipeline_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("pipelines.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    pipeline_code: Mapped[str] = mapped_column(String(64), nullable=False)
    stage_codes_json: Mapped[list] = mapped_column(JSON, nullable=False)
    policy_snapshot_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    module_requirements_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    published_by_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    publish_reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    configuration: Mapped["TenantProcessConfiguration"] = relationship(
        "TenantProcessConfiguration",
        back_populates="definition_versions",
        foreign_keys=[tenant_process_configuration_id],
    )


@event.listens_for(ProcessDefinitionVersion, "before_update", propagate=True)
def _prevent_process_definition_version_update(_mapper, _connection, _target) -> None:
    raise ProcessDefinitionImmutableError("Published process definition versions are immutable")
