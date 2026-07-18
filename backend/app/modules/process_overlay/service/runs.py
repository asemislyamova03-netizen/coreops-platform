import uuid
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.enums import AuditAction
from app.core.exceptions import NotFoundError
from app.modules.audit.recorder import AuditRecorder
from app.modules.process_overlay.constants import ENTITY_PROCESS_RUN
from app.modules.process_overlay.enums import ProcessOverlayActivationState, ProcessRunState
from app.modules.process_overlay.exceptions import (
    ProcessOverlayActivationError,
    ProcessOverlayTenantIsolationError,
    ProcessOverlayValidationError,
    ProcessRunConflictError,
    ProcessRunStateError,
)
from app.modules.process_overlay.repository import ProcessOverlayRepository
from app.modules.process_overlay.schemas import ProcessRunResponse
from app.modules.workflows.repository import WorkflowRepository

_ACTIVE_RUN_CONFLICT_MESSAGE = "An active process run already exists for this work item"


class ProcessOverlayRunService:
    """Explicit ProcessRun lifecycle (E1b). Does not hook CRM create/move."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = ProcessOverlayRepository(db)
        self.workflows = WorkflowRepository(db)
        self.audit = AuditRecorder(db)

    def start_run(
        self,
        tenant_id: uuid.UUID,
        work_item_id: uuid.UUID,
        configuration_id: uuid.UUID,
        actor_user_id: uuid.UUID,
    ) -> ProcessRunResponse:
        config = self.repo.get_configuration(tenant_id, configuration_id)
        if config is None:
            raise NotFoundError("Tenant process configuration not found")

        if config.activation_state != ProcessOverlayActivationState.ACTIVE:
            raise ProcessOverlayActivationError("Overlay configuration is inactive")

        if config.active_definition_version_id is None:
            raise ProcessOverlayValidationError(
                "Cannot start process run without active definition version",
                errors=["active_definition_version_id"],
            )

        version = self.repo.get_definition_version_for_configuration(
            tenant_id,
            configuration_id,
            config.active_definition_version_id,
        )
        if version is None:
            raise ProcessOverlayValidationError(
                "Active definition version does not belong to this configuration",
                errors=["active_definition_version_id"],
            )
        if version.tenant_id != tenant_id or config.tenant_id != tenant_id:
            raise ProcessOverlayTenantIsolationError(
                "Configuration or definition version belongs to another tenant"
            )
        if version.tenant_process_configuration_id != config.id:
            raise ProcessOverlayValidationError(
                "Definition version belongs to another configuration",
                errors=["configuration_id"],
            )

        work_item = self.workflows.get_work_item(tenant_id, work_item_id)
        if work_item is None:
            raise NotFoundError("Work item not found")
        if work_item.pipeline_id != config.pipeline_id:
            raise ProcessOverlayValidationError(
                "Work item pipeline does not match process configuration pipeline",
                errors=["pipeline_id"],
            )

        existing = self.repo.get_active_run_for_work_item(tenant_id, work_item_id)
        if existing is not None:
            raise ProcessRunConflictError(_ACTIVE_RUN_CONFLICT_MESSAGE)

        stage = self.workflows.get_stage(tenant_id, work_item.stage_id)
        current_stage_code = stage.code if stage is not None else None

        try:
            with self.db.begin_nested():
                run = self.repo.create_run(
                    tenant_id=tenant_id,
                    tenant_process_configuration_id=config.id,
                    process_definition_version_id=config.active_definition_version_id,
                    work_item_id=work_item.id,
                    started_by_user_id=actor_user_id,
                    current_stage_code=current_stage_code,
                )

                self.audit.audit_log(
                    tenant_id=tenant_id,
                    user_id=actor_user_id,
                    action=AuditAction.CREATE,
                    entity_type=ENTITY_PROCESS_RUN,
                    entity_id=run.id,
                    summary="Process run started",
                    changes_json={
                        "event": "process_run.started",
                        "work_item_id": str(work_item.id),
                        "configuration_id": str(config.id),
                        "definition_version_id": str(version.id),
                        "version_number": version.version_number,
                    },
                )
                self.db.flush()
        except IntegrityError as exc:
            # Concurrent start hits uq_process_run_one_active_per_work_item.
            # begin_nested rolled back the savepoint; outer txn stays usable.
            raise ProcessRunConflictError(_ACTIVE_RUN_CONFLICT_MESSAGE) from exc

        # C2b1: optional first-contact Task automation (tenant config; same session).
        from app.modules.workflows.service.lead_automation import (
            maybe_create_process_run_first_contact_task,
        )

        maybe_create_process_run_first_contact_task(
            self.db,
            tenant_id=tenant_id,
            process_run_id=run.id,
            work_item_id=work_item.id,
            actor_user_id=actor_user_id,
        )

        return ProcessRunResponse.model_validate(run)

    def complete_run(
        self,
        tenant_id: uuid.UUID,
        process_run_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        *,
        reason: str | None = None,
    ) -> ProcessRunResponse:
        run = self._get_active_run_or_raise(tenant_id, process_run_id)
        completion_reason = reason.strip() if reason is not None else None
        if completion_reason == "":
            completion_reason = None

        self.repo.update_run_lifecycle(
            run,
            run_state=ProcessRunState.COMPLETED,
            completed_at=datetime.now(UTC),
            completed_by_user_id=actor_user_id,
            completion_reason=completion_reason,
        )

        changes: dict = {"event": "process_run.completed"}
        if completion_reason is not None:
            changes["completion_reason"] = completion_reason

        self.audit.audit_log(
            tenant_id=tenant_id,
            user_id=actor_user_id,
            action=AuditAction.UPDATE,
            entity_type=ENTITY_PROCESS_RUN,
            entity_id=run.id,
            summary="Process run completed",
            changes_json=changes,
        )
        self.db.flush()
        return ProcessRunResponse.model_validate(run)

    def cancel_run(
        self,
        tenant_id: uuid.UUID,
        process_run_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        *,
        reason: str,
    ) -> ProcessRunResponse:
        completion_reason = reason.strip() if reason is not None else ""
        if not completion_reason:
            raise ProcessOverlayValidationError(
                "cancel_run requires a non-empty reason",
                errors=["reason"],
            )

        run = self._get_active_run_or_raise(tenant_id, process_run_id)

        self.repo.update_run_lifecycle(
            run,
            run_state=ProcessRunState.CANCELLED,
            completed_at=datetime.now(UTC),
            completed_by_user_id=actor_user_id,
            completion_reason=completion_reason,
        )

        self.audit.audit_log(
            tenant_id=tenant_id,
            user_id=actor_user_id,
            action=AuditAction.UPDATE,
            entity_type=ENTITY_PROCESS_RUN,
            entity_id=run.id,
            summary="Process run cancelled",
            changes_json={
                "event": "process_run.cancelled",
                "completion_reason": completion_reason,
            },
        )
        self.db.flush()
        return ProcessRunResponse.model_validate(run)

    def _get_active_run_or_raise(self, tenant_id: uuid.UUID, process_run_id: uuid.UUID):
        run = self.repo.get_run(tenant_id, process_run_id)
        if run is None:
            raise NotFoundError("Process run not found")
        if run.run_state != ProcessRunState.ACTIVE:
            raise ProcessRunStateError(
                f"Process run must be active to change lifecycle (current={run.run_state.value})"
            )
        return run
