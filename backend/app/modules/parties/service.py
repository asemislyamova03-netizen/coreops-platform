import uuid
from collections import defaultdict

from sqlalchemy.orm import Session

from app.core.enums import ContactMethodType
from app.core.exceptions import NotFoundError
from app.modules.auth.models import User
from app.modules.parties.custom_fields import CustomFieldService
from app.modules.parties.matching import (
    emails_match,
    normalize_email,
    normalize_name,
    normalize_phone_digits,
    normalize_telegram_user_id,
    normalize_telegram_username,
    phones_match,
    score_for_matched_on,
    telegram_user_id_from_metadata,
    telegram_user_ids_match,
    telegram_usernames_match,
)
from app.modules.parties.models import ENTITY_PARTY
from app.modules.parties.repository import PartyRepository
from app.modules.parties.schemas import (
    PartyCreate,
    PartyMatchContactPreview,
    PartyMatchHit,
    PartyMatchNormalizedQuery,
    PartyMatchRequest,
    PartyMatchResponse,
    PartyMatchWorkItemPreview,
    PartyResponse,
    PartyUpdate,
)

EXACT_MATCH_LIMIT = 20
WEAK_MATCH_LIMIT = 5
RECENT_WORK_ITEMS_LIMIT = 3


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
        party_role: str | None = None,
        search: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[PartyResponse]:
        rows = self.parties.list_parties(
            self.tenant_id,
            party_type=party_type,
            status=status,
            party_role=party_role,
            search=search,
            skip=skip,
            limit=limit,
        )
        return [self._to_response(party) for party in rows]

    def get_party(self, party_id: uuid.UUID) -> PartyResponse:
        party = self._get_party_or_404(party_id)
        return self._to_response(party)

    def match_parties(self, payload: PartyMatchRequest) -> PartyMatchResponse:
        """Read-only party match. Does not create/link/merge parties."""
        query = PartyMatchNormalizedQuery(
            name=normalize_name(payload.name),
            phone=normalize_phone_digits(payload.phone),
            email=normalize_email(payload.email),
            telegram_username=normalize_telegram_username(payload.telegram_username),
            telegram_user_id=normalize_telegram_user_id(payload.telegram_user_id),
            whatsapp=normalize_phone_digits(payload.whatsapp),
        )

        exact_matched_on: dict[uuid.UUID, set[str]] = defaultdict(set)

        if query.email:
            for method in self.parties.list_contact_methods_by_types(
                self.tenant_id,
                [ContactMethodType.EMAIL],
            ):
                if emails_match(query.email, method.value):
                    exact_matched_on[method.party_id].add("email")

        if query.phone:
            for method in self.parties.list_contact_methods_by_types(
                self.tenant_id,
                [ContactMethodType.PHONE, ContactMethodType.MOBILE],
            ):
                if phones_match(query.phone, method.value):
                    exact_matched_on[method.party_id].add("phone")

        if query.whatsapp:
            for method in self.parties.list_contact_methods_by_types(
                self.tenant_id,
                [
                    ContactMethodType.WHATSAPP,
                    ContactMethodType.PHONE,
                    ContactMethodType.MOBILE,
                ],
            ):
                if phones_match(query.whatsapp, method.value):
                    exact_matched_on[method.party_id].add("whatsapp")

        if query.telegram_username:
            for method in self.parties.list_contact_methods_by_types(
                self.tenant_id,
                [ContactMethodType.TELEGRAM],
            ):
                if telegram_usernames_match(query.telegram_username, method.value):
                    exact_matched_on[method.party_id].add("telegram_username")

        if query.telegram_user_id:
            for method in self.parties.list_contact_methods_by_types(
                self.tenant_id,
                [ContactMethodType.TELEGRAM],
            ):
                if telegram_user_ids_match(query.telegram_user_id, method.value):
                    exact_matched_on[method.party_id].add("telegram_user_id")
            for party in self.parties.list_parties_with_telegram_metadata(self.tenant_id):
                meta_id = telegram_user_id_from_metadata(party.metadata_json)
                if telegram_user_ids_match(query.telegram_user_id, meta_id):
                    exact_matched_on[party.id].add("telegram_user_id")

        exact_ids = list(exact_matched_on.keys())[:EXACT_MATCH_LIMIT]
        exact_parties = {
            party.id: party
            for party in self.parties.list_parties_by_ids(self.tenant_id, exact_ids)
        }

        matches: list[PartyMatchHit] = []
        for party_id in exact_ids:
            party = exact_parties.get(party_id)
            if not party:
                continue
            matched_on = sorted(exact_matched_on[party_id])
            matches.append(
                self._build_match_hit(
                    party,
                    match_type="exact",
                    matched_on=matched_on,
                )
            )

        if query.name:
            # Name match is weak and done in Python so Cyrillic works on SQLite tests
            # and unnormalized display names stay reliable without migration.
            weak_rows = self.parties.list_parties(
                self.tenant_id,
                limit=200,
            )
            exact_set = set(exact_matched_on.keys())
            weak_added = 0
            for party in weak_rows:
                if party.id in exact_set:
                    continue
                if query.name not in party.display_name.lower():
                    continue
                matches.append(
                    self._build_match_hit(
                        party,
                        match_type="weak",
                        matched_on=["name"],
                    )
                )
                weak_added += 1
                if weak_added >= WEAK_MATCH_LIMIT:
                    break

        matches.sort(
            key=lambda hit: (
                0 if hit.match_type == "exact" else 1,
                -hit.score,
                hit.display_name.lower(),
            )
        )

        return PartyMatchResponse(matches=matches, query_normalized=query)

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

    def _build_match_hit(self, party, *, match_type: str, matched_on: list[str]) -> PartyMatchHit:
        recent = self.parties.list_recent_work_items_for_party(
            self.tenant_id,
            party.id,
            limit=RECENT_WORK_ITEMS_LIMIT,
        )
        return PartyMatchHit(
            party_id=party.id,
            display_name=party.display_name,
            party_type=party.party_type,
            status=party.status,
            match_type=match_type,  # type: ignore[arg-type]
            score=score_for_matched_on(matched_on, match_type=match_type),
            matched_on=matched_on,
            contact_methods=[
                PartyMatchContactPreview(
                    method_type=method.method_type,
                    value=method.value,
                    label=method.label,
                    is_primary=method.is_primary,
                )
                for method in party.contact_methods
            ],
            recent_work_items=[
                PartyMatchWorkItemPreview(
                    id=item.id,
                    title=item.title,
                    status=item.status.value if hasattr(item.status, "value") else str(item.status),
                    updated_at=item.updated_at,
                )
                for item in recent
            ],
        )

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
