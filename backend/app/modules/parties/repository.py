import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.enums import ContactMethodType, PartyStatus, PartyType
from app.modules.parties.models import Address, ContactMethod, Party
from app.modules.workflows.models import WorkItem


class PartyRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_parties(
        self,
        tenant_id: uuid.UUID,
        *,
        party_type: PartyType | None = None,
        status: PartyStatus | None = None,
        party_role: str | None = None,
        search: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Party]:
        stmt = (
            select(Party)
            .where(Party.tenant_id == tenant_id)
            .options(
                selectinload(Party.contact_methods),
                selectinload(Party.addresses),
            )
            .order_by(Party.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        if party_type:
            stmt = stmt.where(Party.party_type == party_type)
        if status:
            stmt = stmt.where(Party.status == status)
        if party_role:
            stmt = stmt.where(Party.metadata_json["party_role"].as_string() == party_role)
        if search:
            stmt = stmt.where(Party.display_name.ilike(f"%{search}%"))
        return list(self.db.scalars(stmt).all())

    def get_party(self, tenant_id: uuid.UUID, party_id: uuid.UUID) -> Party | None:
        stmt = (
            select(Party)
            .where(Party.tenant_id == tenant_id, Party.id == party_id)
            .options(
                selectinload(Party.contact_methods),
                selectinload(Party.addresses),
            )
        )
        return self.db.scalar(stmt)

    def list_parties_by_ids(
        self,
        tenant_id: uuid.UUID,
        party_ids: list[uuid.UUID],
    ) -> list[Party]:
        if not party_ids:
            return []
        stmt = (
            select(Party)
            .where(Party.tenant_id == tenant_id, Party.id.in_(party_ids))
            .options(
                selectinload(Party.contact_methods),
                selectinload(Party.addresses),
            )
        )
        return list(self.db.scalars(stmt).all())

    def list_contact_methods_by_types(
        self,
        tenant_id: uuid.UUID,
        method_types: list[ContactMethodType],
    ) -> list[ContactMethod]:
        if not method_types:
            return []
        stmt = (
            select(ContactMethod)
            .where(
                ContactMethod.tenant_id == tenant_id,
                ContactMethod.method_type.in_(method_types),
            )
            .options(selectinload(ContactMethod.party))
        )
        return list(self.db.scalars(stmt).all())

    def list_parties_with_telegram_metadata(self, tenant_id: uuid.UUID) -> list[Party]:
        """Candidates that may store telegram.user_id in metadata_json (not indexed)."""
        stmt = (
            select(Party)
            .where(Party.tenant_id == tenant_id)
            .options(
                selectinload(Party.contact_methods),
                selectinload(Party.addresses),
            )
        )
        parties = list(self.db.scalars(stmt).all())
        return [
            party
            for party in parties
            if isinstance(party.metadata_json, dict)
            and (
                isinstance(party.metadata_json.get("telegram"), dict)
                or party.metadata_json.get("telegram_user_id") is not None
            )
        ]

    def list_recent_work_items_for_party(
        self,
        tenant_id: uuid.UUID,
        party_id: uuid.UUID,
        *,
        limit: int = 3,
    ) -> list[WorkItem]:
        stmt = (
            select(WorkItem)
            .where(
                WorkItem.tenant_id == tenant_id,
                WorkItem.primary_party_id == party_id,
            )
            .order_by(WorkItem.updated_at.desc())
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def create_party(self, **kwargs) -> Party:
        party = Party(**kwargs)
        self.db.add(party)
        self.db.flush()
        return party

    def add_contact_method(self, **kwargs) -> ContactMethod:
        method = ContactMethod(**kwargs)
        self.db.add(method)
        self.db.flush()
        return method

    def add_address(self, **kwargs) -> Address:
        address = Address(**kwargs)
        self.db.add(address)
        self.db.flush()
        return address

    def delete_party(self, party: Party) -> None:
        self.db.delete(party)
