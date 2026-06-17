import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.enums import TenantRole, TenantStatus
from app.modules.tenants.models import Tenant, UserTenantMembership


class TenantRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, tenant_id: uuid.UUID) -> Tenant | None:
        stmt = (
            select(Tenant)
            .where(Tenant.id == tenant_id)
            .options(selectinload(Tenant.memberships))
        )
        return self.db.scalar(stmt)

    def list_for_provider(self, provider_company_id: uuid.UUID) -> list[Tenant]:
        stmt = (
            select(Tenant)
            .where(Tenant.provider_company_id == provider_company_id)
            .order_by(Tenant.created_at.desc())
        )
        return list(self.db.scalars(stmt).all())

    def list_for_user(self, user_id: uuid.UUID) -> list[Tenant]:
        stmt = (
            select(Tenant)
            .join(UserTenantMembership)
            .where(
                UserTenantMembership.user_id == user_id,
                UserTenantMembership.is_active.is_(True),
            )
            .order_by(Tenant.created_at.desc())
        )
        return list(self.db.scalars(stmt).all())

    def get_by_provider_and_slug(
        self,
        provider_company_id: uuid.UUID,
        slug: str,
    ) -> Tenant | None:
        stmt = select(Tenant).where(
            Tenant.provider_company_id == provider_company_id,
            Tenant.slug == slug,
        )
        return self.db.scalar(stmt)

    def create(
        self,
        *,
        provider_company_id: uuid.UUID,
        name: str,
        slug: str,
        status: TenantStatus = TenantStatus.TRIAL,
    ) -> Tenant:
        tenant = Tenant(
            provider_company_id=provider_company_id,
            name=name,
            slug=slug,
            status=status,
        )
        self.db.add(tenant)
        self.db.flush()
        return tenant

    def create_membership(
        self,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        role: TenantRole,
    ) -> UserTenantMembership:
        membership = UserTenantMembership(
            tenant_id=tenant_id,
            user_id=user_id,
            role=role,
        )
        self.db.add(membership)
        self.db.flush()
        return membership

    def get_membership(
        self,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> UserTenantMembership | None:
        stmt = select(UserTenantMembership).where(
            UserTenantMembership.tenant_id == tenant_id,
            UserTenantMembership.user_id == user_id,
        )
        return self.db.scalar(stmt)

    def list_memberships(self, tenant_id: uuid.UUID) -> list[UserTenantMembership]:
        stmt = (
            select(UserTenantMembership)
            .where(UserTenantMembership.tenant_id == tenant_id)
            .options(selectinload(UserTenantMembership.user))
            .order_by(UserTenantMembership.created_at.asc())
        )
        return list(self.db.scalars(stmt).all())
