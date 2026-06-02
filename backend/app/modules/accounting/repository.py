import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.modules.accounting.models import LegalEntity, TaxProfile


class AccountingRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_legal_entities(self, tenant_id: uuid.UUID, *, active_only: bool = True) -> list[LegalEntity]:
        stmt = (
            select(LegalEntity)
            .where(LegalEntity.tenant_id == tenant_id)
            .options(selectinload(LegalEntity.tax_profiles))
            .order_by(LegalEntity.name)
        )
        if active_only:
            stmt = stmt.where(LegalEntity.is_active.is_(True))
        return list(self.db.scalars(stmt).all())

    def get_legal_entity(self, tenant_id: uuid.UUID, entity_id: uuid.UUID) -> LegalEntity | None:
        stmt = (
            select(LegalEntity)
            .where(LegalEntity.tenant_id == tenant_id, LegalEntity.id == entity_id)
            .options(selectinload(LegalEntity.tax_profiles))
        )
        return self.db.scalar(stmt)

    def create_legal_entity(self, **kwargs) -> LegalEntity:
        entity = LegalEntity(**kwargs)
        self.db.add(entity)
        self.db.flush()
        return entity

    def list_tax_profiles(
        self,
        tenant_id: uuid.UUID,
        *,
        legal_entity_id: uuid.UUID | None = None,
        active_only: bool = True,
    ) -> list[TaxProfile]:
        stmt = (
            select(TaxProfile)
            .where(TaxProfile.tenant_id == tenant_id)
            .order_by(TaxProfile.name)
        )
        if legal_entity_id:
            stmt = stmt.where(TaxProfile.legal_entity_id == legal_entity_id)
        if active_only:
            stmt = stmt.where(TaxProfile.is_active.is_(True))
        return list(self.db.scalars(stmt).all())

    def get_tax_profile(self, tenant_id: uuid.UUID, profile_id: uuid.UUID) -> TaxProfile | None:
        stmt = select(TaxProfile).where(
            TaxProfile.tenant_id == tenant_id,
            TaxProfile.id == profile_id,
        )
        return self.db.scalar(stmt)

    def get_tax_profile_by_code(self, tenant_id: uuid.UUID, code: str) -> TaxProfile | None:
        stmt = select(TaxProfile).where(
            TaxProfile.tenant_id == tenant_id,
            TaxProfile.code == code,
        )
        return self.db.scalar(stmt)

    def create_tax_profile(self, **kwargs) -> TaxProfile:
        profile = TaxProfile(**kwargs)
        self.db.add(profile)
        self.db.flush()
        return profile
