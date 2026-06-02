class CoreOpsError(Exception):
    """Base application error."""

    def __init__(self, message: str = "An error occurred"):
        self.message = message
        super().__init__(message)


class NotFoundError(CoreOpsError):
    """Resource not found."""


class ConflictError(CoreOpsError):
    """Resource conflict (duplicate, already exists)."""


class AuthenticationError(CoreOpsError):
    """Invalid credentials or token."""


class PermissionDeniedError(CoreOpsError):
    """Action not allowed for the current principal."""


class BootstrapCompletedError(CoreOpsError):
    """Platform bootstrap already completed."""


class ModuleDisabledError(CoreOpsError):
    """Requested module is not enabled for the tenant."""


class ModuleDependencyError(CoreOpsError):
    """Module cannot be enabled because required modules are missing."""


class FeatureNotEntitledError(CoreOpsError):
    """Tenant subscription does not include this feature."""


class UsageLimitExceededError(CoreOpsError):
    """Tenant has exceeded a plan usage limit."""
