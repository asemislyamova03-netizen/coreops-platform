"""Marketing publishing-connection HTTP dependencies (M8-B)."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings
from app.core.deps import get_db
from app.core.enums import TenantRole
from app.core.exceptions import PermissionDeniedError
from app.core.modules import require_module
from app.core.permissions import get_provider_staff, user_has_any_tenant_role
from app.core.secrets.adapters.in_memory import InMemorySecretVault
from app.core.secrets.port import SecretVaultPort
from app.core.tenancy import TenantContext, get_tenant_context
from app.modules.marketing.service.publishing_connections import (
    MarketingPublishingConnectionService,
)
from app.modules.marketing.service.publishing_secret_lifecycle import (
    PublishingSecretLifecycleService,
)

_IN_MEMORY_VAULT_ENVS = frozenset({"test", "testing", "development", "dev", "local"})
_CONNECTION_ADMIN_ROLES = frozenset(
    {TenantRole.TENANT_OWNER, TenantRole.TENANT_ADMIN}
)


def require_marketing_connection_admin(
    ctx: TenantContext = Depends(require_module("marketing")),
) -> TenantContext:
    """OWNER/ADMIN membership, or provider staff for the same provider company."""
    staff = get_provider_staff(ctx.user)
    if staff and staff.provider_company_id == ctx.tenant.provider_company_id:
        return ctx
    if user_has_any_tenant_role(ctx.user, ctx.tenant.id, _CONNECTION_ADMIN_ROLES):
        return ctx
    raise PermissionDeniedError(
        "Insufficient permissions for publishing connection management"
    )


def resolve_secret_vault(
    request: Request,
    settings: Settings,
) -> SecretVaultPort | None:
    """Return InMemory vault only in allow-listed envs; else None (fail-closed)."""
    env = (settings.app_env or "").strip().lower()
    if env not in _IN_MEMORY_VAULT_ENVS:
        return None

    existing = getattr(request.app.state, "marketing_secret_vault", None)
    if isinstance(existing, InMemorySecretVault):
        return existing

    vault = InMemorySecretVault(app_env=env)
    request.app.state.marketing_secret_vault = vault
    return vault


def get_secret_vault(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> SecretVaultPort:
    """Require a vault for connect/rotate. No silent InMemory fallback in production."""
    vault = resolve_secret_vault(request, settings)
    if vault is None:
        raise HTTPException(status_code=503, detail="secret_vault_unavailable")
    return vault


def get_optional_secret_vault(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> SecretVaultPort | None:
    """Vault when available; None outside allow-listed envs (no InMemory fallback)."""
    return resolve_secret_vault(request, settings)


def get_publishing_connection_service(
    ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
) -> MarketingPublishingConnectionService:
    return MarketingPublishingConnectionService(db, ctx.tenant.id)


def get_publishing_secret_lifecycle_service(
    ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
    vault: SecretVaultPort = Depends(get_secret_vault),
) -> PublishingSecretLifecycleService:
    factory = sessionmaker(autocommit=False, autoflush=False, bind=db.get_bind())
    return PublishingSecretLifecycleService(
        ctx.tenant.id,
        session_factory=factory,
        vault=vault,
    )
