import uuid

from sqlalchemy.orm import Session

from app.core.enums import ProviderRole, TenantRole
from app.core.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from app.core.permissions import get_provider_staff, user_is_provider_owner
from app.modules.auth.models import User
from app.modules.auth.repository import UserRepository
from app.modules.provider.repository import ProviderRepository
from app.modules.industry_templates.repository import IndustryTemplateRepository
from app.modules.industry_templates.service import IndustryTemplateService
from app.modules.module_registry.service import ModuleRegistryService
from app.modules.subscriptions.service import SubscriptionService
from app.modules.tenants.repository import TenantRepository
from app.modules.tenants.schemas import TenantCreate, TenantUpdate


class TenantService:
    def __init__(self, db: Session):
        self.db = db
        self.tenants = TenantRepository(db)
        self.users = UserRepository(db)
        self.providers = ProviderRepository(db)

    def list_accessible(self, user: User) -> list:
        staff = get_provider_staff(user)
        if staff and user_is_provider_owner(user):
            return self.tenants.list_for_provider(staff.provider_company_id)
        return self.tenants.list_for_user(user.id)

    def get_accessible(self, user: User, tenant_id: uuid.UUID):
        tenant = self.tenants.get_by_id(tenant_id)
        if not tenant:
            raise NotFoundError("Tenant not found")
        self._ensure_access(user, tenant)
        return tenant

    def create(self, user: User, payload: TenantCreate):
        staff = get_provider_staff(user)
        if not staff or staff.role != ProviderRole.PROVIDER_OWNER:
            raise PermissionDeniedError("Only provider owner can create tenants")

        if self.tenants.get_by_provider_and_slug(staff.provider_company_id, payload.slug):
            raise ConflictError("Tenant slug already exists for this provider")

        tenant = self.tenants.create(
            provider_company_id=staff.provider_company_id,
            name=payload.name,
            slug=payload.slug,
            status=payload.status,
        )

        owner_user_id = payload.owner_user_id
        if payload.owner_email and not owner_user_id:
            owner = self.users.get_by_email(payload.owner_email)
            if owner:
                owner_user_id = owner.id

        if owner_user_id:
            self._assign_membership(tenant.id, owner_user_id, TenantRole.TENANT_OWNER)

        ModuleRegistryService(self.db).provision_tenant_modules(tenant.id)
        if payload.plan_code:
            SubscriptionService(self.db).assign_plan(user, tenant.id, payload.plan_code)

        if payload.industry_template_code:
            template = IndustryTemplateRepository(self.db).get_by_code(
                payload.industry_template_code
            )
            if not template:
                raise NotFoundError(
                    f"Industry template '{payload.industry_template_code}' not found"
                )
            IndustryTemplateService(self.db).apply_to_tenant(user, tenant.id, template.id)

        self.db.commit()
        self.db.refresh(tenant)
        self.db.refresh(tenant)
        return tenant

    def update(self, user: User, tenant_id: uuid.UUID, payload: TenantUpdate):
        tenant = self.get_accessible(user, tenant_id)
        staff = get_provider_staff(user)
        if not staff or staff.provider_company_id != tenant.provider_company_id:
            if not any(
                m.tenant_id == tenant_id and m.role == TenantRole.TENANT_OWNER
                for m in user.tenant_memberships
            ):
                raise PermissionDeniedError("Insufficient permissions to update tenant")

        if payload.name is not None:
            tenant.name = payload.name
        if payload.status is not None:
            tenant.status = payload.status

        self.db.commit()
        self.db.refresh(tenant)
        return tenant

    def add_membership(
        self,
        user: User,
        tenant_id: uuid.UUID,
        member_user_id: uuid.UUID,
        role: TenantRole,
    ):
        tenant = self.get_accessible(user, tenant_id)
        staff = get_provider_staff(user)
        if not staff or staff.provider_company_id != tenant.provider_company_id:
            raise PermissionDeniedError("Only provider staff can assign tenant members")

        member = self.users.get_by_id(member_user_id)
        if not member:
            raise NotFoundError("User not found")

        return self._assign_membership(tenant_id, member_user_id, role)

    def _assign_membership(
        self,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        role: TenantRole,
    ):
        existing = self.tenants.get_membership(tenant_id, user_id)
        if existing:
            raise ConflictError("User is already a member of this tenant")

        membership = self.tenants.create_membership(
            tenant_id=tenant_id,
            user_id=user_id,
            role=role,
        )
        self.db.flush()
        return membership

    def _ensure_access(self, user: User, tenant) -> None:
        staff = get_provider_staff(user)
        if staff and staff.provider_company_id == tenant.provider_company_id:
            return
        if any(m.tenant_id == tenant.id and m.is_active for m in user.tenant_memberships):
            return
        raise PermissionDeniedError("No access to this tenant")
