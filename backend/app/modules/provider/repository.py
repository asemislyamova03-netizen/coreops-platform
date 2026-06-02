import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import ProviderRole
from app.modules.provider.models import ProviderCompany, ProviderStaff


class ProviderRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_company_by_id(self, company_id: uuid.UUID) -> ProviderCompany | None:
        return self.db.get(ProviderCompany, company_id)

    def get_company_by_slug(self, slug: str) -> ProviderCompany | None:
        stmt = select(ProviderCompany).where(ProviderCompany.slug == slug)
        return self.db.scalar(stmt)

    def create_company(self, *, name: str, slug: str) -> ProviderCompany:
        company = ProviderCompany(name=name, slug=slug)
        self.db.add(company)
        self.db.flush()
        return company

    def create_staff(
        self,
        *,
        provider_company_id: uuid.UUID,
        user_id: uuid.UUID,
        role: ProviderRole,
    ) -> ProviderStaff:
        staff = ProviderStaff(
            provider_company_id=provider_company_id,
            user_id=user_id,
            role=role,
        )
        self.db.add(staff)
        self.db.flush()
        return staff

    def get_staff_for_user(self, user_id: uuid.UUID) -> ProviderStaff | None:
        stmt = select(ProviderStaff).where(ProviderStaff.user_id == user_id)
        return self.db.scalar(stmt)
