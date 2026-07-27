"""M7.5-A Marketing Rubric directory service."""

from __future__ import annotations

import re
import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.auth.models import User
from app.modules.marketing.enums import MarketingRubricStatus
from app.modules.marketing.exceptions import (
    MarketingRubricDuplicateError,
    MarketingRubricHardDeleteForbiddenError,
    MarketingRubricNotFoundError,
    MarketingRubricNotSelectableError,
    MarketingRubricValidationError,
)
from app.modules.marketing.models import MarketingRubric
from app.modules.marketing.repository import MarketingRepository
from app.modules.marketing.rubric_seed import DEFAULT_RUBRIC_SEED
from app.modules.marketing.schemas import (
    RubricCreate,
    RubricResponse,
    RubricSeedRequest,
    RubricSeedResponse,
    RubricUpdate,
)

_CODE_RE = re.compile(r"^[a-z][a-z0-9_]{1,62}$")


def normalize_rubric_code(code: str) -> str:
    return code.strip().casefold()


class MarketingRubricService:
    def __init__(self, db: Session, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.repo = MarketingRepository(db)

    def list_rubrics(
        self,
        *,
        status: MarketingRubricStatus | None = None,
        include_archived: bool = False,
    ) -> list[RubricResponse]:
        rows = self.repo.list_rubrics(
            self.tenant_id,
            status=status,
            include_archived=include_archived,
        )
        return [self._to_response(row) for row in rows]

    def get_rubric(self, rubric_id: uuid.UUID) -> RubricResponse:
        return self._to_response(self._get_or_404(rubric_id))

    def create_rubric(self, user: User, payload: RubricCreate) -> RubricResponse:
        code = normalize_rubric_code(payload.code)
        if not _CODE_RE.match(code):
            raise MarketingRubricValidationError("invalid_rubric_code")
        if self.repo.get_rubric_by_code(self.tenant_id, code) is not None:
            raise MarketingRubricDuplicateError()
        try:
            rubric = self.repo.create_rubric(
                tenant_id=self.tenant_id,
                code=code,
                name=payload.name.strip(),
                description=(payload.description.strip() if payload.description else None),
                content_instructions=(
                    payload.content_instructions.strip()
                    if payload.content_instructions
                    else None
                ),
                status=payload.status,
                sort_order=payload.sort_order,
                metadata_json=dict(payload.metadata_json),
                created_by_user_id=user.id,
                updated_by_user_id=user.id,
            )
        except IntegrityError as exc:
            raise MarketingRubricDuplicateError() from exc
        return self._to_response(rubric)

    def update_rubric(
        self,
        user: User,
        rubric_id: uuid.UUID,
        payload: RubricUpdate,
    ) -> RubricResponse:
        rubric = self._get_or_404(rubric_id)
        fields_set = payload.model_fields_set
        # code is immutable after create (historical topic.rubric string links).
        if "code" in fields_set and payload.code is not None:
            if normalize_rubric_code(payload.code) != rubric.code:
                raise MarketingRubricValidationError("rubric_code_immutable")
        if "name" in fields_set and payload.name is not None:
            if not payload.name.strip():
                raise MarketingRubricValidationError("name_required")
            rubric.name = payload.name.strip()
        if "description" in fields_set:
            rubric.description = (
                payload.description.strip()
                if isinstance(payload.description, str) and payload.description.strip()
                else None
            )
        if "content_instructions" in fields_set:
            rubric.content_instructions = (
                payload.content_instructions.strip()
                if isinstance(payload.content_instructions, str)
                and payload.content_instructions.strip()
                else None
            )
        if "sort_order" in fields_set and payload.sort_order is not None:
            rubric.sort_order = payload.sort_order
        if "metadata_json" in fields_set and payload.metadata_json is not None:
            rubric.metadata_json = dict(payload.metadata_json)
        if "status" in fields_set and payload.status is not None:
            rubric.status = payload.status
        rubric.updated_by_user_id = user.id
        self.db.flush()
        return self._to_response(rubric)

    def activate(self, user: User, rubric_id: uuid.UUID) -> RubricResponse:
        return self._set_status(user, rubric_id, MarketingRubricStatus.ACTIVE)

    def deactivate(self, user: User, rubric_id: uuid.UUID) -> RubricResponse:
        return self._set_status(user, rubric_id, MarketingRubricStatus.INACTIVE)

    def archive(self, user: User, rubric_id: uuid.UUID) -> RubricResponse:
        return self._set_status(user, rubric_id, MarketingRubricStatus.ARCHIVED)

    def delete_forbidden(self) -> None:
        raise MarketingRubricHardDeleteForbiddenError()

    def seed_defaults(
        self,
        user: User,
        payload: RubricSeedRequest,
    ) -> RubricSeedResponse:
        """Idempotent per-tenant seed. Does not run globally or on production auto."""
        created = 0
        skipped = 0
        updated = 0
        for row in DEFAULT_RUBRIC_SEED:
            existing = self.repo.get_rubric_by_code(self.tenant_id, row["code"])
            if existing is None:
                self.repo.create_rubric(
                    tenant_id=self.tenant_id,
                    code=row["code"],
                    name=row["name"],
                    description=row["description"],
                    content_instructions=row["content_instructions"],
                    status=MarketingRubricStatus.ACTIVE,
                    sort_order=row["sort_order"],
                    metadata_json={"seeded": True},
                    created_by_user_id=user.id,
                    updated_by_user_id=user.id,
                )
                created += 1
                continue
            skipped += 1
            if payload.force:
                existing.name = row["name"]
                existing.description = row["description"]
                existing.content_instructions = row["content_instructions"]
                existing.sort_order = row["sort_order"]
                existing.updated_by_user_id = user.id
                updated += 1
        self.db.flush()
        return RubricSeedResponse(created=created, skipped=skipped, updated=updated)

    def assert_code_selectable_for_new_topic(self, code: str) -> None:
        """Legacy free-text allowed; known inactive/archived codes are rejected."""
        normalized = normalize_rubric_code(code)
        row = self.repo.get_rubric_by_code(self.tenant_id, normalized)
        if row is None:
            # Also try exact code as stored (legacy non-slug titles).
            row = self.repo.get_rubric_by_code(self.tenant_id, code.strip())
        if row is None:
            return
        if row.status != MarketingRubricStatus.ACTIVE:
            raise MarketingRubricNotSelectableError()

    def _set_status(
        self,
        user: User,
        rubric_id: uuid.UUID,
        status: MarketingRubricStatus,
    ) -> RubricResponse:
        rubric = self._get_or_404(rubric_id)
        rubric.status = status
        rubric.updated_by_user_id = user.id
        self.db.flush()
        return self._to_response(rubric)

    def _get_or_404(self, rubric_id: uuid.UUID) -> MarketingRubric:
        rubric = self.repo.get_rubric(self.tenant_id, rubric_id)
        if rubric is None:
            raise MarketingRubricNotFoundError()
        return rubric

    def _to_response(self, rubric: MarketingRubric) -> RubricResponse:
        return RubricResponse(
            id=rubric.id,
            tenant_id=rubric.tenant_id,
            code=rubric.code,
            name=rubric.name,
            description=rubric.description,
            content_instructions=rubric.content_instructions,
            status=rubric.status,
            sort_order=rubric.sort_order,
            metadata_json=dict(rubric.metadata_json or {}),
            created_at=rubric.created_at,
            updated_at=rubric.updated_at,
        )
