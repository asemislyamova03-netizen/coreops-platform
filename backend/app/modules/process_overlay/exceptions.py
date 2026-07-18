import uuid

from app.core.exceptions import ConflictError, CoreOpsError, PermissionDeniedError


class ProcessOverlayError(CoreOpsError):
    """Base error for Process Overlay domain logic."""


class ProcessOverlayValidationError(ProcessOverlayError):
    """Policy or configuration input failed validation."""

    def __init__(self, message: str, *, errors: list[str] | None = None):
        super().__init__(message)
        self.errors = errors or []


class ProcessDefinitionImmutableError(ProcessOverlayError):
    """Published process definition versions cannot be mutated."""


class ProcessOverlayActivationError(ProcessOverlayError):
    """Configuration cannot be activated in the current state."""


class ProcessOverlayTenantIsolationError(PermissionDeniedError):
    """Cross-tenant resource reference rejected."""


class ProcessRunConflictError(ConflictError):
    """Process run conflicts with an existing active run or invariant."""


class ProcessRunStateError(ProcessOverlayError):
    """Process run lifecycle transition is not allowed from the current state."""


class ProcessTransitionDeniedError(ConflictError):
    """CRM stage transition denied by pinned Process Overlay policy (fail-closed)."""

    def __init__(
        self,
        message: str = "Process transition denied",
        *,
        code: str = "PROCESS_TRANSITION_DENIED",
        from_stage_code: str | None = None,
        to_stage_code: str | None = None,
        process_run_id: uuid.UUID | None = None,
        definition_version_id: uuid.UUID | None = None,
    ):
        super().__init__(message)
        self.code = code
        self.from_stage_code = from_stage_code
        self.to_stage_code = to_stage_code
        self.process_run_id = process_run_id
        self.definition_version_id = definition_version_id
