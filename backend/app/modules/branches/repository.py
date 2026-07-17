import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.branches.models import Branch


class BranchRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        *,
        tenant_id: uuid.UUID,
        code: str,
        name: str,
        is_active: bool = True,
        is_default: bool = False,
    ) -> Branch:
        branch = Branch(
            tenant_id=tenant_id,
            code=code,
            name=name,
            is_active=is_active,
            is_default=is_default,
        )
        self.db.add(branch)
        self.db.flush()
        return branch

    def get_default(self, tenant_id: uuid.UUID) -> Branch | None:
        stmt = (
            select(Branch)
            .where(
                Branch.tenant_id == tenant_id,
                Branch.is_default.is_(True),
            )
            .order_by(Branch.created_at.asc(), Branch.id.asc())
            .limit(1)
        )
        return self.db.scalar(stmt)
