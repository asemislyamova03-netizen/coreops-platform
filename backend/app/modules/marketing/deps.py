"""Marketing publishing-connection HTTP dependencies (M8-B)."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings
from app.core.database import SessionLocal
from app.core.deps import get_db
from app.core.enums import TenantRole
from app.core.exceptions import PermissionDeniedError
from app.core.modules import require_module
from app.core.permissions import get_provider_staff, user_has_any_tenant_role
from app.core.secrets.adapters.envelope_pg import EnvelopePgSecretVault
from app.core.secrets.adapters.in_memory import InMemorySecretVault
from app.core.secrets.kek_provider import KekProvider, KekProviderError
from app.core.secrets.port import SecretVaultPort
from app.core.tenancy import TenantContext, get_tenant_context
from app.modules.marketing.service.publishing_connections import (
    MarketingPublishingConnectionService,
)
from app.modules.marketing.service.publish_destinations import (
    MarketingPublishDestinationService,
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


# Destination mutations reuse the same OWNER/ADMIN (+ provider staff) gate as connections.
require_marketing_destination_admin = require_marketing_connection_admin


def _build_in_memory_vault(request: Request, env: str) -> InMemorySecretVault:
    existing = getattr(request.app.state, "marketing_secret_vault", None)
    if isinstance(existing, InMemorySecretVault):
        return existing
    vault = InMemorySecretVault(app_env=env)
    request.app.state.marketing_secret_vault = vault
    return vault


def _build_envelope_vault(
    request: Request,
    settings: Settings,
) -> EnvelopePgSecretVault | None:
    existing = getattr(request.app.state, "marketing_secret_vault", None)
    if isinstance(existing, EnvelopePgSecretVault):
        return existing
    try:
        kek_provider = KekProvider.load_from_config(
            credential_path=settings.secret_kek_credential_path,
            credentials_dir=settings.secret_kek_credentials_dir,
            credential_name=settings.secret_kek_credential_name,
        )
    except KekProviderError:
        return None
    vault = EnvelopePgSecretVault(
        session_factory=SessionLocal,
        kek_provider=kek_provider,
        pending_ttl_seconds=settings.secret_envelope_pending_ttl_seconds,
    )
    request.app.state.marketing_secret_vault = vault
    return vault


def resolve_secret_vault(
    request: Request,
    settings: Settings,
) -> SecretVaultPort | None:
    """Select vault adapter explicitly; never silently fall back to InMemory outside allow-list."""
    env = (settings.app_env or "").strip().lower()
    adapter = (settings.secret_vault_adapter or "auto").strip().lower()
    existing = getattr(request.app.state, "marketing_secret_vault", None)

    if adapter == "in_memory":
        if env not in _IN_MEMORY_VAULT_ENVS:
            return None
        if isinstance(existing, InMemorySecretVault):
            return existing
        return _build_in_memory_vault(request, env)

    if adapter == "envelope_pg":
        if isinstance(existing, EnvelopePgSecretVault):
            return existing
        return _build_envelope_vault(request, settings)

    if adapter == "auto":
        if env in _IN_MEMORY_VAULT_ENVS:
            if isinstance(existing, InMemorySecretVault):
                return existing
            return _build_in_memory_vault(request, env)
        # staging/production/etc.: envelope only — ignore any cached InMemory
        if isinstance(existing, EnvelopePgSecretVault):
            return existing
        return _build_envelope_vault(request, settings)

    return None


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
    """Vault when available; None when adapter/KEK unavailable (no InMemory fallback)."""
    return resolve_secret_vault(request, settings)


def get_publishing_connection_service(
    ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
) -> MarketingPublishingConnectionService:
    return MarketingPublishingConnectionService(db, ctx.tenant.id)


def get_publish_destination_service(
    ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
) -> MarketingPublishDestinationService:
    return MarketingPublishDestinationService(db, ctx.tenant.id)


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
