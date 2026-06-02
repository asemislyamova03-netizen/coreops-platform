from app.core.enums import ProviderRole, TenantRole
from app.modules.auth.models import User
from app.modules.provider.models import ProviderStaff
from app.modules.tenants.models import UserTenantMembership


def user_has_provider_role(user: User, role: ProviderRole) -> bool:
    return any(staff.role == role for staff in user.provider_staff)


def user_is_provider_owner(user: User) -> bool:
    return user_has_provider_role(user, ProviderRole.PROVIDER_OWNER)


def user_has_tenant_role(
    user: User,
    tenant_id,
    role: TenantRole,
) -> bool:
    return any(
        m.tenant_id == tenant_id and m.role == role and m.is_active
        for m in user.tenant_memberships
    )


def user_is_tenant_owner(user: User, tenant_id) -> bool:
    return user_has_tenant_role(user, tenant_id, TenantRole.TENANT_OWNER)


def get_provider_staff(user: User) -> ProviderStaff | None:
    if not user.provider_staff:
        return None
    return user.provider_staff[0]


def user_belongs_to_provider(user: User, provider_company_id) -> bool:
    return any(s.provider_company_id == provider_company_id for s in user.provider_staff)
