import uuid

from sqlalchemy.orm import Session

from app.core.enums import AuditAction
from app.core.exceptions import NotFoundError
from app.modules.audit.recorder import AuditRecorder
from app.modules.module_registry.repository import ModuleRegistryRepository
from app.modules.process_overlay.constants import (
    ENTITY_PROCESS_DEFINITION_VERSION,
    ENTITY_TENANT_PROCESS_CONFIGURATION,
    MAX_PUBLISH_REASON_LENGTH,
)
from app.modules.process_overlay.exceptions import (
    ProcessDefinitionImmutableError,
    ProcessOverlayTenantIsolationError,
    ProcessOverlayValidationError,
)
from app.modules.process_overlay.policy_schema import (
    PolicySnapshotV1,
    parse_policy_snapshot,
    validate_policy_against_pipeline,
)
from app.modules.process_overlay.repository import ProcessOverlayRepository
from app.modules.process_overlay.schemas import (
    ProcessDefinitionVersionResponse,
    PublishDefinitionVersionRequest,
    TenantProcessConfigurationResponse,
)
from app.modules.workflows.repository import WorkflowRepository


class ProcessOverlayPublicationService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ProcessOverlayRepository(db)
        self.workflows = WorkflowRepository(db)
        self.modules = ModuleRegistryRepository(db)
        self.audit = AuditRecorder(db)

    def publish_definition_version(
        self,
        *,
        tenant_id: uuid.UUID,
        configuration_id: uuid.UUID,
        request: PublishDefinitionVersionRequest,
        actor_user_id: uuid.UUID,
    ) -> ProcessDefinitionVersionResponse:
        reason = request.publish_reason.strip()
        if not reason:
            raise ProcessOverlayValidationError("publish_reason must be non-empty")
        if len(reason) > MAX_PUBLISH_REASON_LENGTH:
            raise ProcessOverlayValidationError("publish_reason exceeds maximum length")

        config = self.repo.get_configuration(tenant_id, configuration_id)
        if config is None:
            raise NotFoundError("Tenant process configuration not found")

        template = self.repo.get_template_by_id(config.process_template_id)
        if template is None:
            raise NotFoundError("Process template not found")

        pipeline = self.workflows.get_pipeline(tenant_id, config.pipeline_id)
        if pipeline is None:
            raise ProcessOverlayTenantIsolationError(
                "Configuration pipeline not found for tenant"
            )

        policy = request.policy
        if isinstance(policy, dict):
            policy = parse_policy_snapshot(policy)
        elif not isinstance(policy, PolicySnapshotV1):
            policy = PolicySnapshotV1.model_validate(policy)

        validate_policy_against_pipeline(
            policy,
            pipeline_code=pipeline.code,
            pipeline_stage_codes={stage.code for stage in pipeline.stages},
            process_template_code=template.code,
        )
        self._validate_module_requirements(policy.module_requirements)

        version_number = self.repo.max_version_number(config.id) + 1
        version = self.repo.insert_definition_version(
            tenant_id=tenant_id,
            tenant_process_configuration_id=config.id,
            version_number=version_number,
            pipeline_id=pipeline.id,
            pipeline_code=pipeline.code,
            stage_codes_json=list(policy.stage_codes),
            policy_snapshot_json=policy.model_dump(),
            module_requirements_json=list(policy.module_requirements),
            published_by_user_id=actor_user_id,
            publish_reason=reason,
        )

        self.audit.audit_log(
            tenant_id=tenant_id,
            user_id=actor_user_id,
            action=AuditAction.CREATE,
            entity_type=ENTITY_PROCESS_DEFINITION_VERSION,
            entity_id=version.id,
            summary="Process definition version published",
            changes_json={
                "configuration_id": str(config.id),
                "version_number": version_number,
                "pipeline_code": pipeline.code,
            },
        )
        self.db.flush()
        return ProcessDefinitionVersionResponse.model_validate(version)

    def set_active_definition_version(
        self,
        *,
        tenant_id: uuid.UUID,
        configuration_id: uuid.UUID,
        version_id: uuid.UUID,
        actor_user_id: uuid.UUID | None = None,
    ) -> TenantProcessConfigurationResponse:
        config = self.repo.get_configuration(tenant_id, configuration_id)
        if config is None:
            raise NotFoundError("Tenant process configuration not found")

        version = self.repo.get_definition_version_for_configuration(
            tenant_id,
            configuration_id,
            version_id,
        )
        if version is None:
            raise ProcessOverlayValidationError(
                "Definition version does not belong to this configuration or tenant",
                errors=["version_id"],
            )

        if version.tenant_id != tenant_id:
            raise ProcessOverlayTenantIsolationError(
                "Definition version belongs to another tenant"
            )
        if version.tenant_process_configuration_id != config.id:
            raise ProcessOverlayValidationError(
                "Definition version belongs to another configuration",
                errors=["configuration_id"],
            )

        pipeline = self.workflows.get_pipeline(tenant_id, config.pipeline_id)
        if pipeline is None or pipeline.id != version.pipeline_id:
            raise ProcessOverlayTenantIsolationError(
                "Version pipeline is not consistent with tenant configuration"
            )

        config.active_definition_version_id = version.id
        config.updated_by_user_id = actor_user_id
        self.db.flush()

        self.audit.audit_log(
            tenant_id=tenant_id,
            user_id=actor_user_id,
            action=AuditAction.UPDATE,
            entity_type=ENTITY_TENANT_PROCESS_CONFIGURATION,
            entity_id=config.id,
            summary="Active process definition version set",
            changes_json={"active_definition_version_id": str(version.id)},
        )
        self.db.flush()
        return TenantProcessConfigurationResponse.model_validate(config)

    def guard_definition_version_immutable(self, version_id: uuid.UUID, tenant_id: uuid.UUID) -> None:
        version = self.repo.get_definition_version(tenant_id, version_id)
        if version is None:
            raise NotFoundError("Process definition version not found")
        self.repo.assert_definition_version_immutable(version)

    def _validate_module_requirements(self, module_requirements: list[str]) -> None:
        for module_code in module_requirements:
            if self.modules.get_definition(module_code) is None:
                raise ProcessOverlayValidationError(
                    f"Unknown module requirement '{module_code}'",
                    errors=[module_code],
                )
