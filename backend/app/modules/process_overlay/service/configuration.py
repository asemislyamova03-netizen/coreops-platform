import uuid

from sqlalchemy.orm import Session

from app.core.enums import AuditAction
from app.core.exceptions import ConflictError, NotFoundError
from app.core.modules import ModuleGuard
from app.modules.audit.recorder import AuditRecorder
from app.modules.module_registry.repository import ModuleRegistryRepository
from app.modules.process_overlay.constants import (
    ENTITY_TENANT_PROCESS_CONFIGURATION,
    MAX_PUBLISH_REASON_LENGTH,
)
from app.modules.process_overlay.enums import ProcessOverlayActivationState
from app.modules.process_overlay.exceptions import (
    ProcessOverlayActivationError,
    ProcessOverlayTenantIsolationError,
    ProcessOverlayValidationError,
)
from app.modules.process_overlay.repository import ProcessOverlayRepository
from app.modules.process_overlay.schemas import TenantProcessConfigurationResponse
from app.modules.workflows.repository import WorkflowRepository


class ProcessOverlayConfigurationService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ProcessOverlayRepository(db)
        self.workflows = WorkflowRepository(db)
        self.modules = ModuleRegistryRepository(db)
        self.audit = AuditRecorder(db)

    def create_configuration(
        self,
        *,
        tenant_id: uuid.UUID,
        process_template_code: str,
        pipeline_id: uuid.UUID,
        actor_user_id: uuid.UUID | None = None,
    ) -> TenantProcessConfigurationResponse:
        template = self.repo.get_template_by_code(process_template_code)
        if template is None or not template.is_active:
            raise NotFoundError(f"Process template '{process_template_code}' not found")

        pipeline = self.workflows.get_pipeline(tenant_id, pipeline_id)
        if pipeline is None:
            raise ProcessOverlayTenantIsolationError(
                "Pipeline not found for tenant or belongs to another tenant"
            )
        if pipeline.code != template.default_pipeline_code:
            raise ProcessOverlayValidationError(
                "Pipeline code does not match process template default_pipeline_code",
                errors=[f"expected {template.default_pipeline_code}, got {pipeline.code}"],
            )

        existing_template = self.repo.list_configurations(tenant_id)
        for config in existing_template:
            if config.process_template_id == template.id:
                raise ConflictError("Tenant process configuration for this template already exists")
            if config.pipeline_id == pipeline_id:
                raise ConflictError("Tenant process configuration for this pipeline already exists")

        config = self.repo.create_configuration(
            tenant_id=tenant_id,
            process_template_id=template.id,
            pipeline_id=pipeline.id,
            created_by_user_id=actor_user_id,
        )
        self.audit.audit_log(
            tenant_id=tenant_id,
            user_id=actor_user_id,
            action=AuditAction.CREATE,
            entity_type=ENTITY_TENANT_PROCESS_CONFIGURATION,
            entity_id=config.id,
            summary="Tenant process configuration created",
            changes_json={
                "process_template_code": process_template_code,
                "pipeline_id": str(pipeline.id),
                "activation_state": ProcessOverlayActivationState.INACTIVE.value,
            },
        )
        self.db.flush()
        return TenantProcessConfigurationResponse.model_validate(config)

    def activate_configuration(
        self,
        *,
        tenant_id: uuid.UUID,
        configuration_id: uuid.UUID,
        actor_user_id: uuid.UUID | None = None,
    ) -> TenantProcessConfigurationResponse:
        config = self._get_configuration_or_raise(tenant_id, configuration_id)
        if config.activation_state == ProcessOverlayActivationState.ACTIVE:
            return TenantProcessConfigurationResponse.model_validate(config)

        if config.active_definition_version_id is None:
            raise ProcessOverlayActivationError(
                "Cannot activate configuration without active_definition_version_id"
            )

        version = self.repo.get_definition_version_for_configuration(
            tenant_id,
            configuration_id,
            config.active_definition_version_id,
        )
        if version is None:
            raise ProcessOverlayActivationError(
                "Active definition version does not belong to this configuration"
            )

        self._assert_configuration_pipeline_consistency(config, tenant_id)
        self._assert_module_requirements_met(tenant_id, version.module_requirements_json)

        config.activation_state = ProcessOverlayActivationState.ACTIVE
        config.updated_by_user_id = actor_user_id
        self.db.flush()

        self.audit.audit_log(
            tenant_id=tenant_id,
            user_id=actor_user_id,
            action=AuditAction.UPDATE,
            entity_type=ENTITY_TENANT_PROCESS_CONFIGURATION,
            entity_id=config.id,
            summary="Tenant process configuration activated",
            changes_json={
                "activation_state": ProcessOverlayActivationState.ACTIVE.value,
                "active_definition_version_id": str(version.id),
            },
        )
        self.db.flush()
        return TenantProcessConfigurationResponse.model_validate(config)

    def deactivate_configuration(
        self,
        *,
        tenant_id: uuid.UUID,
        configuration_id: uuid.UUID,
        actor_user_id: uuid.UUID | None = None,
    ) -> TenantProcessConfigurationResponse:
        config = self._get_configuration_or_raise(tenant_id, configuration_id)
        if config.activation_state == ProcessOverlayActivationState.INACTIVE:
            return TenantProcessConfigurationResponse.model_validate(config)

        config.activation_state = ProcessOverlayActivationState.INACTIVE
        config.updated_by_user_id = actor_user_id
        self.db.flush()

        self.audit.audit_log(
            tenant_id=tenant_id,
            user_id=actor_user_id,
            action=AuditAction.UPDATE,
            entity_type=ENTITY_TENANT_PROCESS_CONFIGURATION,
            entity_id=config.id,
            summary="Tenant process configuration deactivated",
            changes_json={"activation_state": ProcessOverlayActivationState.INACTIVE.value},
        )
        self.db.flush()
        return TenantProcessConfigurationResponse.model_validate(config)

    def get_configuration(
        self,
        tenant_id: uuid.UUID,
        configuration_id: uuid.UUID,
    ) -> TenantProcessConfigurationResponse:
        config = self._get_configuration_or_raise(tenant_id, configuration_id)
        return TenantProcessConfigurationResponse.model_validate(config)

    def _get_configuration_or_raise(
        self,
        tenant_id: uuid.UUID,
        configuration_id: uuid.UUID,
    ):
        config = self.repo.get_configuration(tenant_id, configuration_id)
        if config is None:
            raise NotFoundError("Tenant process configuration not found")
        return config

    def _assert_configuration_pipeline_consistency(
        self,
        config,
        tenant_id: uuid.UUID,
    ) -> None:
        pipeline = self.workflows.get_pipeline(tenant_id, config.pipeline_id)
        if pipeline is None:
            raise ProcessOverlayTenantIsolationError(
                "Configuration pipeline not found for tenant"
            )
        if not pipeline.stages:
            raise ProcessOverlayActivationError("Configuration pipeline has no stages")

    def _assert_module_requirements_met(
        self,
        tenant_id: uuid.UUID,
        module_requirements: list[str],
    ) -> None:
        guard = ModuleGuard(self.db, tenant_id)
        for module_code in module_requirements:
            definition = self.modules.get_definition(module_code)
            if definition is None:
                raise ProcessOverlayValidationError(
                    f"Unknown module requirement '{module_code}'",
                    errors=[module_code],
                )
            guard.assert_enabled(module_code)
