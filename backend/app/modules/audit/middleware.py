import uuid

from fastapi import FastAPI, Request, Response

from app.core.enums import AuditAction
from app.modules.audit.recorder import AuditRecorder

MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def install_audit_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def audit_mutations(request: Request, call_next) -> Response:
        if request.method not in MUTATING_METHODS:
            return await call_next(request)

        response = await call_next(request)
        if response.status_code >= 400:
            return response

        action = _resolve_action(request)
        if action is None:
            return response

        db = getattr(request.state, "db", None)
        if db is None:
            return response
        try:
            tenant_id = _state_uuid(request, "tenant_id")
            user_id = _state_uuid(request, "user_id")
            AuditRecorder(db).audit_log(
                action=action,
                summary=f"{request.method} {request.url.path}",
                tenant_id=tenant_id,
                user_id=user_id,
                entity_type=_entity_type_from_path(request.url.path),
                request=request,
            )
            db.commit()
        except Exception:
            db.rollback()

        return response


def _resolve_action(request: Request) -> AuditAction | None:
    method = request.method
    path = request.url.path
    if method == "POST":
        if path.endswith("/approve"):
            return AuditAction.APPROVE
        if path.endswith("/reject"):
            return AuditAction.REJECT
        if path.endswith("/execute"):
            return AuditAction.EXECUTE
        return AuditAction.CREATE
    if method in {"PUT", "PATCH"}:
        return AuditAction.UPDATE
    if method == "DELETE":
        return AuditAction.DELETE
    return None


def _entity_type_from_path(path: str) -> str | None:
    parts = [part for part in path.split("/") if part]
    if len(parts) < 3:
        return None
    if parts[0] == "api" and parts[1] == "v1":
        return parts[2].replace("-", "_")
    return parts[0].replace("-", "_")


def _state_uuid(request: Request, key: str) -> uuid.UUID | None:
    raw_value = getattr(request.state, key, None)
    if isinstance(raw_value, uuid.UUID):
        return raw_value
    if isinstance(raw_value, str) and raw_value:
        try:
            return uuid.UUID(raw_value)
        except ValueError:
            return None
    return None
