import uuid
from datetime import UTC, datetime

from sqlalchemy import func, inspect, select
from sqlalchemy.orm import Session

from app.modules.process_overlay.enums import ProcessOverlayActivationState, ProcessRunState
from app.modules.process_overlay.exceptions import ProcessDefinitionImmutableError
from app.modules.process_overlay.models import (
    ProcessDefinitionVersion,
    ProcessRun,
    ProcessTemplate,
    TenantProcessConfiguration,
)


class ProcessOverlayRepository:
    def __init__(self, db: Session):
        self.db = db

    # --- ProcessTemplate (platform catalog) ---

    def get_template_by_code(self, code: str) -> ProcessTemplate | None:
        stmt = select(ProcessTemplate).where(ProcessTemplate.code == code)
        return self.db.scalar(stmt)

    def get_template_by_id(self, template_id: uuid.UUID) -> ProcessTemplate | None:
        return self.db.get(ProcessTemplate, template_id)

    def list_templates(self, *, active_only: bool = True) -> list[ProcessTemplate]:
        stmt = select(ProcessTemplate).order_by(ProcessTemplate.code)
        if active_only:
            stmt = stmt.where(ProcessTemplate.is_active.is_(True))
        return list(self.db.scalars(stmt).all())

    def upsert_template(self, **kwargs) -> ProcessTemplate:
        existing = self.get_template_by_code(kwargs["code"])
        if existing:
            for key, value in kwargs.items():
                setattr(existing, key, value)
            self.db.flush()
            return existing
        template = ProcessTemplate(**kwargs)
        self.db.add(template)
        self.db.flush()
        return template

    # --- TenantProcessConfiguration ---

    def get_configuration(
        self,
        tenant_id: uuid.UUID,
        configuration_id: uuid.UUID,
    ) -> TenantProcessConfiguration | None:
        stmt = select(TenantProcessConfiguration).where(
            TenantProcessConfiguration.tenant_id == tenant_id,
            TenantProcessConfiguration.id == configuration_id,
        )
        return self.db.scalar(stmt)

    def get_configuration_by_pipeline(
        self,
        tenant_id: uuid.UUID,
        pipeline_id: uuid.UUID,
    ) -> TenantProcessConfiguration | None:
        """Return the tenant's process config for a pipeline, if any (unique pair)."""
        stmt = select(TenantProcessConfiguration).where(
            TenantProcessConfiguration.tenant_id == tenant_id,
            TenantProcessConfiguration.pipeline_id == pipeline_id,
        )
        return self.db.scalar(stmt)

    def list_configurations(self, tenant_id: uuid.UUID) -> list[TenantProcessConfiguration]:
        stmt = (
            select(TenantProcessConfiguration)
            .where(TenantProcessConfiguration.tenant_id == tenant_id)
            .order_by(TenantProcessConfiguration.created_at)
        )
        return list(self.db.scalars(stmt).all())

    def create_configuration(
        self,
        *,
        tenant_id: uuid.UUID,
        process_template_id: uuid.UUID,
        pipeline_id: uuid.UUID,
        created_by_user_id: uuid.UUID | None = None,
    ) -> TenantProcessConfiguration:
        config = TenantProcessConfiguration(
            tenant_id=tenant_id,
            process_template_id=process_template_id,
            pipeline_id=pipeline_id,
            activation_state=ProcessOverlayActivationState.INACTIVE,
            active_definition_version_id=None,
            created_by_user_id=created_by_user_id,
            updated_by_user_id=created_by_user_id,
        )
        self.db.add(config)
        self.db.flush()
        return config

    def save_configuration_state(
        self,
        config: TenantProcessConfiguration,
        *,
        activation_state: ProcessOverlayActivationState,
        active_definition_version_id: uuid.UUID | None,
        updated_by_user_id: uuid.UUID | None,
    ) -> TenantProcessConfiguration:
        config.activation_state = activation_state
        config.active_definition_version_id = active_definition_version_id
        config.updated_by_user_id = updated_by_user_id
        self.db.flush()
        return config

    # --- ProcessDefinitionVersion (append-only) ---

    def get_definition_version(
        self,
        tenant_id: uuid.UUID,
        version_id: uuid.UUID,
    ) -> ProcessDefinitionVersion | None:
        stmt = select(ProcessDefinitionVersion).where(
            ProcessDefinitionVersion.tenant_id == tenant_id,
            ProcessDefinitionVersion.id == version_id,
        )
        return self.db.scalar(stmt)

    def get_definition_version_for_configuration(
        self,
        tenant_id: uuid.UUID,
        configuration_id: uuid.UUID,
        version_id: uuid.UUID,
    ) -> ProcessDefinitionVersion | None:
        stmt = select(ProcessDefinitionVersion).where(
            ProcessDefinitionVersion.tenant_id == tenant_id,
            ProcessDefinitionVersion.tenant_process_configuration_id == configuration_id,
            ProcessDefinitionVersion.id == version_id,
        )
        return self.db.scalar(stmt)

    def max_version_number(self, configuration_id: uuid.UUID) -> int:
        stmt = select(func.max(ProcessDefinitionVersion.version_number)).where(
            ProcessDefinitionVersion.tenant_process_configuration_id == configuration_id
        )
        value = self.db.scalar(stmt)
        return int(value or 0)

    def insert_definition_version(
        self,
        *,
        tenant_id: uuid.UUID,
        tenant_process_configuration_id: uuid.UUID,
        version_number: int,
        pipeline_id: uuid.UUID,
        pipeline_code: str,
        stage_codes_json: list[str],
        policy_snapshot_json: dict,
        module_requirements_json: list[str],
        published_by_user_id: uuid.UUID,
        publish_reason: str,
    ) -> ProcessDefinitionVersion:
        version = ProcessDefinitionVersion(
            tenant_id=tenant_id,
            tenant_process_configuration_id=tenant_process_configuration_id,
            version_number=version_number,
            pipeline_id=pipeline_id,
            pipeline_code=pipeline_code,
            stage_codes_json=stage_codes_json,
            policy_snapshot_json=policy_snapshot_json,
            module_requirements_json=module_requirements_json,
            published_at=datetime.now(UTC),
            published_by_user_id=published_by_user_id,
            publish_reason=publish_reason,
        )
        self.db.add(version)
        self.db.flush()
        return version

    def assert_definition_version_immutable(self, version: ProcessDefinitionVersion) -> None:
        state = inspect(version)
        if not state.persistent:
            return
        if state.attrs.policy_snapshot_json.history.has_changes():
            raise ProcessDefinitionImmutableError("policy_snapshot_json is immutable after publish")
        if state.attrs.version_number.history.has_changes():
            raise ProcessDefinitionImmutableError("version_number is immutable after publish")
        if state.attrs.tenant_process_configuration_id.history.has_changes():
            raise ProcessDefinitionImmutableError(
                "tenant_process_configuration_id is immutable after publish"
            )

    # --- ProcessRun (E1b runtime binding) ---

    def get_run(self, tenant_id: uuid.UUID, run_id: uuid.UUID) -> ProcessRun | None:
        stmt = select(ProcessRun).where(
            ProcessRun.tenant_id == tenant_id,
            ProcessRun.id == run_id,
        )
        return self.db.scalar(stmt)

    def get_active_run_for_work_item(
        self,
        tenant_id: uuid.UUID,
        work_item_id: uuid.UUID,
    ) -> ProcessRun | None:
        stmt = select(ProcessRun).where(
            ProcessRun.tenant_id == tenant_id,
            ProcessRun.work_item_id == work_item_id,
            ProcessRun.run_state == ProcessRunState.ACTIVE,
        )
        return self.db.scalar(stmt)

    def create_run(
        self,
        *,
        tenant_id: uuid.UUID,
        tenant_process_configuration_id: uuid.UUID,
        process_definition_version_id: uuid.UUID,
        work_item_id: uuid.UUID,
        started_by_user_id: uuid.UUID,
        current_stage_code: str | None = None,
        started_at: datetime | None = None,
    ) -> ProcessRun:
        run = ProcessRun(
            tenant_id=tenant_id,
            tenant_process_configuration_id=tenant_process_configuration_id,
            process_definition_version_id=process_definition_version_id,
            work_item_id=work_item_id,
            run_state=ProcessRunState.ACTIVE,
            started_at=started_at or datetime.now(UTC),
            started_by_user_id=started_by_user_id,
            completed_at=None,
            completed_by_user_id=None,
            completion_reason=None,
            current_stage_code=current_stage_code,
        )
        self.db.add(run)
        self.db.flush()
        return run

    def update_run_lifecycle(
        self,
        run: ProcessRun,
        *,
        run_state: ProcessRunState,
        completed_at: datetime,
        completed_by_user_id: uuid.UUID,
        completion_reason: str | None,
    ) -> ProcessRun:
        """Update terminal lifecycle fields only. Never mutates process_definition_version_id."""
        run.run_state = run_state
        run.completed_at = completed_at
        run.completed_by_user_id = completed_by_user_id
        run.completion_reason = completion_reason
        self.db.flush()
        return run
