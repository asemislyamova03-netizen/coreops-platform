import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.enums import PartyStatus, PartyType
from app.modules.parties.models import Address, ContactMethod, Party


class PartyRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_parties(
        self,
        tenant_id: uuid.UUID,
        *,
        party_type: PartyType | None = None,
        status: PartyStatus | None = None,
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
