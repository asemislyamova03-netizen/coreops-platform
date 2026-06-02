from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.core.permissions import get_provider_staff
from app.modules.auth.models import User
from app.modules.tenants.models import Tenant
from app.modules.tenants.repository import TenantRepository


@dataclass
class TenantContext:
    tenant: Tenant
    user: User


def get_tenant_context(
    tenant_id: uuid.UUID | None = None,
    x_tenant_id: Annotated[str | None, Header(alias="X-Tenant-ID")] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TenantContext:
    resolved_id = tenant_id
    if resolved_id is None and x_tenant_id:
        resolved_id = uuid.UUID(x_tenant_id)
    if resolved_id is None:
        raise PermissionDeniedError(
            "Tenant context required: use path tenant_id or X-Tenant-ID header"
        )

    tenant = TenantRepository(db).get_by_id(resolved_id)
    if not tenant:
        raise NotFoundError("Tenant not found")

    staff = get_provider_staff(current_user)
    if staff and staff.provider_company_id == tenant.provider_company_id:
        return TenantContext(tenant=tenant, user=current_user)

    if any(
        m.tenant_id == tenant.id and m.is_active for m in current_user.tenant_memberships
    ):
        return TenantContext(tenant=tenant, user=current_user)

    raise PermissionDeniedError("No access to this tenant")
