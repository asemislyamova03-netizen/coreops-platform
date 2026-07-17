import uuid

from sqlalchemy.orm import Session

from app.modules.branches.repository import BranchRepository
from app.modules.tenants.repository import TenantRepository


class BranchService:
    """E3a baseline service for default branch provisioning."""

    def __init__(self, db: Session):
        self.db = db
        self.branches = BranchRepository(db)
        self.tenants = TenantRepository(db)

    def ensure_default_branch(self, tenant_id: uuid.UUID) -> uuid.UUID:
        existing = self.branches.get_default(tenant_id)
        if existing:
            tenant = self.tenants.get_by_id(tenant_id)
            if tenant and tenant.default_branch_id is None:
                tenant.default_branch_id = existing.id
                self.db.flush()
            return existing.id

        branch = self.branches.create(
            tenant_id=tenant_id,
            code="main",
            name="Main branch",
            is_default=True,
            is_active=True,
        )
        tenant = self.tenants.get_by_id(tenant_id)
        if tenant:
            tenant.default_branch_id = branch.id
        self.db.flush()
        return branch.id
