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
