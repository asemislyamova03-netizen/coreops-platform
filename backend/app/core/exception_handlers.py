from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    AuthenticationError,
    BootstrapCompletedError,
    ConflictError,
    CoreOpsError,
    FeatureNotEntitledError,
    ModuleDependencyError,
    ModuleDisabledError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitExceededError,
    UsageLimitExceededError,
)


def _error_response(status_code: int, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"detail": message})


async def core_ops_error_handler(_request: Request, exc: CoreOpsError) -> JSONResponse:
    if isinstance(exc, NotFoundError):
        return _error_response(404, exc.message)
    if isinstance(exc, ConflictError):
        return _error_response(409, exc.message)
    if isinstance(exc, AuthenticationError):
        return _error_response(401, exc.message)
    if isinstance(exc, (PermissionDeniedError, BootstrapCompletedError)):
        return _error_response(403, exc.message)
    if isinstance(exc, ModuleDisabledError):
        return _error_response(403, exc.message)
    if isinstance(exc, ModuleDependencyError):
        return _error_response(409, exc.message)
    if isinstance(exc, FeatureNotEntitledError):
        return _error_response(403, exc.message)
    if isinstance(exc, (UsageLimitExceededError, RateLimitExceededError)):
        return _error_response(429, exc.message)
    return _error_response(400, exc.message)
