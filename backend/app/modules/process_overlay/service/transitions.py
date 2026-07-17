"""E1c: single shared Process Overlay transition guard for CRM stage writers."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.enums import AuditAction
from app.modules.audit.recorder import AuditRecorder
from app.modules.process_overlay.constants import (
    ENTITY_PROCESS_RUN,
    EVENT_PROCESS_TRANSITION_APPLIED,
)
from app.modules.process_overlay.exceptions import (
    ProcessOverlayValidationError,
    ProcessTransitionDeniedError,
)
from app.modules.process_overlay.models import ProcessDefinitionVersion, ProcessRun
from app.modules.process_overlay.policy_schema import parse_policy_snapshot
from app.modules.process_overlay.repository import ProcessOverlayRepository


@dataclass(frozen=True)
class TransitionGuardResult:
    """Outcome of evaluating overlay transition policy for a CRM stage change."""

    enforced: bool
    noop: bool = False
    run: ProcessRun | None = None
    version: ProcessDefinitionVersion | None = None


class ProcessOverlayTransitionGuard:
    """Edge-only allow/deny against pinned ProcessRun policy (fail-closed).

    Callers must run CRM tenant/pipeline validation first, and lock the WorkItem
    with SELECT FOR UPDATE before invoking this guard.
    """

    def __init__(self, db: Session):
        self.db = db
        self.repo = ProcessOverlayRepository(db)
        self.audit = AuditRecorder(db)

    def assert_transition_allowed(
        self,
        tenant_id: uuid.UUID,
        work_item,
        *,
        from_stage_code: str | None,
        to_stage_code: str | None,
        actor_user_id: uuid.UUID,
        via: str,
    ) -> TransitionGuardResult:
        """Evaluate pinned policy for a candidate stage transition.

        Same-stage is not a transition. No ACTIVE run → legacy CRM (not enforced).
        Denied transitions raise ProcessTransitionDeniedError with no deny audit.
        """
        del actor_user_id  # reserved for applied-audit callers / future conditions
        del via

        if from_stage_code is None or to_stage_code is None:
            raise ProcessTransitionDeniedError(
                "Process transition denied: stage code unresolved",
                from_stage_code=from_stage_code,
                to_stage_code=to_stage_code,
            )

        if from_stage_code == to_stage_code:
            return TransitionGuardResult(enforced=False, noop=True)

        run = self.repo.get_active_run_for_work_item_for_update(tenant_id, work_item.id)
        if run is None:
            return TransitionGuardResult(enforced=False)

        version = self.repo.get_definition_version(
            tenant_id,
            run.process_definition_version_id,
        )
        if version is None:
            raise ProcessTransitionDeniedError(
                "Process transition denied: pinned definition version missing",
                from_stage_code=from_stage_code,
                to_stage_code=to_stage_code,
                process_run_id=run.id,
                definition_version_id=run.process_definition_version_id,
            )
        if version.tenant_id != tenant_id:
            raise ProcessTransitionDeniedError(
                "Process transition denied: definition version tenant mismatch",
                from_stage_code=from_stage_code,
                to_stage_code=to_stage_code,
                process_run_id=run.id,
                definition_version_id=version.id,
            )
        if version.tenant_process_configuration_id != run.tenant_process_configuration_id:
            raise ProcessTransitionDeniedError(
                "Process transition denied: definition version configuration mismatch",
                from_stage_code=from_stage_code,
                to_stage_code=to_stage_code,
                process_run_id=run.id,
                definition_version_id=version.id,
            )
        if version.pipeline_id != work_item.pipeline_id:
            raise ProcessTransitionDeniedError(
                "Process transition denied: process pipeline mismatch",
                from_stage_code=from_stage_code,
                to_stage_code=to_stage_code,
                process_run_id=run.id,
                definition_version_id=version.id,
            )

        try:
            policy = parse_policy_snapshot(version.policy_snapshot_json)
        except ProcessOverlayValidationError as exc:
            raise ProcessTransitionDeniedError(
                "Process transition denied: invalid pinned policy",
                from_stage_code=from_stage_code,
                to_stage_code=to_stage_code,
                process_run_id=run.id,
                definition_version_id=version.id,
            ) from exc

        edges = {(t.from_stage_code, t.to_stage_code) for t in policy.transitions}
        if (from_stage_code, to_stage_code) not in edges:
            raise ProcessTransitionDeniedError(
                f"Process transition denied: {from_stage_code} -> {to_stage_code}",
                from_stage_code=from_stage_code,
                to_stage_code=to_stage_code,
                process_run_id=run.id,
                definition_version_id=version.id,
            )

        return TransitionGuardResult(enforced=True, run=run, version=version)

    def record_applied_transition(
        self,
        *,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        result: TransitionGuardResult,
        work_item_id: uuid.UUID,
        from_stage_code: str,
        to_stage_code: str,
        via: str,
    ) -> None:
        """Sync current_stage_code and write process_transition.applied exactly once."""
        if not result.enforced or result.noop or result.run is None or result.version is None:
            return

        self.repo.update_run_current_stage_code(
            result.run,
            current_stage_code=to_stage_code,
        )
        self.audit.audit_log(
            tenant_id=tenant_id,
            user_id=actor_user_id,
            action=AuditAction.UPDATE,
            entity_type=ENTITY_PROCESS_RUN,
            entity_id=result.run.id,
            summary="Process transition applied",
            changes_json={
                "event": EVENT_PROCESS_TRANSITION_APPLIED,
                "work_item_id": str(work_item_id),
                "process_run_id": str(result.run.id),
                "definition_version_id": str(result.version.id),
                "from_stage_code": from_stage_code,
                "to_stage_code": to_stage_code,
                "via": via,
            },
        )
