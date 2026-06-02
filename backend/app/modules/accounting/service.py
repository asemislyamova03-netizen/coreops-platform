import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.modules.accounting.repository import AccountingRepository
from app.modules.accounting.schemas import (
    LegalEntityCreate,
    LegalEntityResponse,
    LegalEntityUpdate,
    TaxProfileCreate,
    TaxProfileResponse,
    TaxProfileUpdate,
)


class AccountingService:
    def __init__(self, db: Session, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.repo = AccountingRepository(db)

    def list_legal_entities(self, active_only: bool = True) -> list[LegalEntityResponse]:
        entities = self.repo.list_legal_entities(self.tenant_id, active_only=active_only)
        return [LegalEntityResponse.model_validate(e) for e in entities]

    def get_legal_entity(self, entity_id: uuid.UUID) -> LegalEntityResponse:
        entity = self._get_legal_entity_or_404(entity_id)
        return LegalEntityResponse.model_validate(entity)

    def create_legal_entity(self, payload: LegalEntityCreate) -> LegalEntityResponse:
        entity = self.repo.create_legal_entity(
            tenant_id=self.tenant_id,
            **payload.model_dump(),
        )
        return LegalEntityResponse.model_validate(entity)

    def update_legal_entity(
        self,
        entity_id: uuid.UUID,
        payload: LegalEntityUpdate,
    ) -> LegalEntityResponse:
        entity = self._get_legal_entity_or_404(entity_id)
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(entity, key, value)
        self.db.flush()
        return LegalEntityResponse.model_validate(entity)

    def list_tax_profiles(
        self,
        *,
        legal_entity_id: uuid.UUID | None = None,
        active_only: bool = True,
    ) -> list[TaxProfileResponse]:
        profiles = self.repo.list_tax_profiles(
            self.tenant_id,
            legal_entity_id=legal_entity_id,
            active_only=active_only,
        )
        return [TaxProfileResponse.model_validate(p) for p in profiles]

    def get_tax_profile(self, profile_id: uuid.UUID) -> TaxProfileResponse:
        profile = self._get_tax_profile_or_404(profile_id)
        return TaxProfileResponse.model_validate(profile)

    def create_tax_profile(self, payload: TaxProfileCreate) -> TaxProfileResponse:
        if not self.repo.get_legal_entity(self.tenant_id, payload.legal_entity_id):
            raise NotFoundError("Legal entity not found")
        if self.repo.get_tax_profile_by_code(self.tenant_id, payload.code):
            raise ConflictError("Tax profile code already exists")

        profile = self.repo.create_tax_profile(
            tenant_id=self.tenant_id,
            **payload.model_dump(),
        )
        return TaxProfileResponse.model_validate(profile)

    def update_tax_profile(
        self,
        profile_id: uuid.UUID,
        payload: TaxProfileUpdate,
    ) -> TaxProfileResponse:
        profile = self._get_tax_profile_or_404(profile_id)
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(profile, key, value)
        self.db.flush()
        return TaxProfileResponse.model_validate(profile)

    def _get_legal_entity_or_404(self, entity_id: uuid.UUID):
        entity = self.repo.get_legal_entity(self.tenant_id, entity_id)
        if not entity:
            raise NotFoundError("Legal entity not found")
        return entity

    def _get_tax_profile_or_404(self, profile_id: uuid.UUID):
        profile = self.repo.get_tax_profile(self.tenant_id, profile_id)
        if not profile:
            raise NotFoundError("Tax profile not found")
        return profile
