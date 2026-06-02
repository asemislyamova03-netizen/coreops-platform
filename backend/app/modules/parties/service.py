import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.modules.auth.models import User
from app.modules.parties.custom_fields import CustomFieldService
from app.modules.parties.models import ENTITY_PARTY
from app.modules.parties.repository import PartyRepository
from app.modules.parties.schemas import PartyCreate, PartyResponse, PartyUpdate


class PartyService:
    def __init__(self, db: Session, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.parties = PartyRepository(db)
        self.custom_fields = CustomFieldService(db, tenant_id)

    def list_parties(
        self,
        *,
        party_type=None,
        status=None,
        search: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[PartyResponse]:
        rows = self.parties.list_parties(
            self.tenant_id,
            party_type=party_type,
            status=status,
            search=search,
            skip=skip,
            limit=limit,
        )
        return [self._to_response(party) for party in rows]

    def get_party(self, party_id: uuid.UUID) -> PartyResponse:
        party = self._get_party_or_404(party_id)
        return self._to_response(party)

    def create_party(self, user: User, payload: PartyCreate) -> PartyResponse:
        applies_to = {"party_role": payload.party_role} if payload.party_role else None
        custom_values = self.custom_fields.validate_and_prepare(
            ENTITY_PARTY,
            payload.custom_fields,
            applies_to=applies_to,
        )

        party = self.parties.create_party(
            tenant_id=self.tenant_id,
            party_type=payload.party_type,
            display_name=payload.display_name,
            status=payload.status,
            metadata_json=self._build_metadata(payload.metadata_json, payload.party_role),
            created_by_user_id=user.id,
            updated_by_user_id=user.id,
        )

        self._replace_contact_methods(party.id, payload.contact_methods)
        self._replace_addresses(party.id, payload.addresses)

        if custom_values:
            self.custom_fields.upsert_values(ENTITY_PARTY, party.id, custom_values)

        self.db.flush()
        return self.get_party(party.id)

    def update_party(
        self,
        user: User,
        party_id: uuid.UUID,
        payload: PartyUpdate,
    ) -> PartyResponse:
        party = self._get_party_or_404(party_id)

        if payload.party_type is not None:
            party.party_type = payload.party_type
        if payload.display_name is not None:
            party.display_name = payload.display_name
        if payload.status is not None:
            party.status = payload.status
        if payload.metadata_json is not None or payload.party_role is not None:
            role = payload.party_role
            if role is None and party.metadata_json:
                role = party.metadata_json.get("party_role")
            meta = payload.metadata_json if payload.metadata_json is not None else party.metadata_json
            party.metadata_json = self._build_metadata(meta, role)

        if payload.contact_methods is not None:
            for method in list(party.contact_methods):
                self.db.delete(method)
            self.db.flush()
            self._replace_contact_methods(party.id, payload.contact_methods)

        if payload.addresses is not None:
            for address in list(party.addresses):
                self.db.delete(address)
            self.db.flush()
            self._replace_addresses(party.id, payload.addresses)

        if payload.custom_fields is not None:
            role = payload.party_role or party.metadata_json.get("party_role")
            applies_to = {"party_role": role} if role else None
            custom_values = self.custom_fields.validate_and_prepare(
                ENTITY_PARTY,
                payload.custom_fields,
                applies_to=applies_to,
            )
            self.custom_fields.upsert_values(ENTITY_PARTY, party.id, custom_values)

        party.updated_by_user_id = user.id
        self.db.flush()
        return self.get_party(party.id)

    def delete_party(self, party_id: uuid.UUID) -> None:
        party = self._get_party_or_404(party_id)
        self.parties.delete_party(party)
        self.db.flush()

    def list_custom_field_definitions(self, entity_type: str = ENTITY_PARTY):
        return self.custom_fields.list_definitions(entity_type)

    def _get_party_or_404(self, party_id: uuid.UUID):
        party = self.parties.get_party(self.tenant_id, party_id)
        if not party:
            raise NotFoundError("Party not found")
        return party

    def _replace_contact_methods(self, party_id: uuid.UUID, methods) -> None:
        for item in methods:
            self.parties.add_contact_method(
                tenant_id=self.tenant_id,
                party_id=party_id,
                method_type=item.method_type,
                value=item.value,
                label=item.label,
                is_primary=item.is_primary,
            )

    def _replace_addresses(self, party_id: uuid.UUID, addresses) -> None:
        for item in addresses:
            self.parties.add_address(
                tenant_id=self.tenant_id,
                party_id=party_id,
                address_type=item.address_type,
                country=item.country,
                city=item.city,
                line1=item.line1,
                line2=item.line2,
                postal_code=item.postal_code,
                is_primary=item.is_primary,
            )

    def _build_metadata(self, metadata: dict, party_role: str | None) -> dict:
        result = dict(metadata or {})
        if party_role:
            result["party_role"] = party_role
        return result

    def _to_response(self, party) -> PartyResponse:
        custom = self.custom_fields.get_values_map(ENTITY_PARTY, party.id)
        return PartyResponse(
            id=party.id,
            tenant_id=party.tenant_id,
            party_type=party.party_type,
            display_name=party.display_name,
            status=party.status,
            metadata_json=party.metadata_json,
            contact_methods=party.contact_methods,
            addresses=party.addresses,
            custom_fields=custom,
            created_at=party.created_at,
            updated_at=party.updated_at,
            created_by_user_id=party.created_by_user_id,
            updated_by_user_id=party.updated_by_user_id,
        )
