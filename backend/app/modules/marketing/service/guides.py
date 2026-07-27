"""M7.5-A Marketing Guide service."""

from __future__ import annotations

import re
import uuid

from sqlalchemy.orm import Session

from app.modules.auth.models import User
from app.modules.marketing.enums import MarketingGuideStatus
from app.modules.marketing.exceptions import (
    MarketingGuideNotFoundError,
    MarketingGuideValidationError,
)
from app.modules.marketing.models import MarketingGuide
from app.modules.marketing.repository import MarketingRepository
from app.modules.marketing.schemas import (
    GuideCreate,
    GuideResponse,
    GuideUpdate,
)

_SECRETISH_KEY = re.compile(
    r"(secret|token|password|api[_-]?key|bearer|credential)",
    re.IGNORECASE,
)


def _assert_extra_json_safe(extra: dict) -> None:
    def walk(obj: object, path: str = "") -> None:
        if isinstance(obj, dict):
            for key, value in obj.items():
                key_s = str(key)
                if _SECRETISH_KEY.search(key_s):
                    raise MarketingGuideValidationError("extra_json_forbidden_key")
                walk(value, f"{path}.{key_s}" if path else key_s)
        elif isinstance(obj, list):
            for idx, item in enumerate(obj):
                walk(item, f"{path}[{idx}]")

    walk(extra)


class MarketingGuideService:
    def __init__(self, db: Session, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.repo = MarketingRepository(db)

    def list_guides(self) -> list[GuideResponse]:
        return [self._to_response(row) for row in self.repo.list_guides(self.tenant_id)]

    def get_active(self) -> GuideResponse:
        guide = self.repo.get_active_guide(self.tenant_id)
        if guide is None:
            raise MarketingGuideNotFoundError()
        return self._to_response(guide)

    def get_guide(self, guide_id: uuid.UUID) -> GuideResponse:
        return self._to_response(self._get_or_404(guide_id))

    def create_draft(self, user: User, payload: GuideCreate) -> GuideResponse:
        _assert_extra_json_safe(payload.extra_json)
        version = self.repo.max_guide_version(self.tenant_id) + 1
        guide = self.repo.create_guide(
            tenant_id=self.tenant_id,
            version=version,
            status=MarketingGuideStatus.DRAFT,
            business_name=payload.business_name.strip(),
            business_summary=payload.business_summary.strip(),
            products_services=payload.products_services.strip(),
            audiences=payload.audiences.strip(),
            goals=payload.goals.strip(),
            channels=list(payload.channels),
            default_frequency=payload.default_frequency.strip(),
            tone_rules=(payload.tone_rules.strip() if payload.tone_rules else None),
            constraints=(payload.constraints.strip() if payload.constraints else None),
            sources_notes=(payload.sources_notes.strip() if payload.sources_notes else None),
            extra_json=dict(payload.extra_json),
            created_by_user_id=user.id,
            updated_by_user_id=user.id,
        )
        if payload.activate:
            return self.activate(user, guide.id)
        return self._to_response(guide)

    def update_guide(
        self,
        user: User,
        guide_id: uuid.UUID,
        payload: GuideUpdate,
    ) -> GuideResponse:
        guide = self._get_or_404(guide_id)
        if guide.status == MarketingGuideStatus.SUPERSEDED:
            raise MarketingGuideValidationError("guide_superseded_immutable")
        fields_set = payload.model_fields_set
        if "extra_json" in fields_set and payload.extra_json is not None:
            _assert_extra_json_safe(payload.extra_json)
            guide.extra_json = dict(payload.extra_json)
        for field in (
            "business_name",
            "business_summary",
            "products_services",
            "audiences",
            "goals",
            "default_frequency",
        ):
            if field in fields_set:
                value = getattr(payload, field)
                if value is None or not str(value).strip():
                    raise MarketingGuideValidationError(f"{field}_required")
                setattr(guide, field, str(value).strip())
        if "channels" in fields_set and payload.channels is not None:
            guide.channels = list(payload.channels)
        for field in ("tone_rules", "constraints", "sources_notes"):
            if field in fields_set:
                value = getattr(payload, field)
                setattr(guide, field, value.strip() if isinstance(value, str) and value.strip() else None)
        guide.updated_by_user_id = user.id
        self.db.flush()
        return self._to_response(guide)

    def activate(self, user: User, guide_id: uuid.UUID) -> GuideResponse:
        guide = self._get_or_404(guide_id)
        if guide.status == MarketingGuideStatus.SUPERSEDED:
            raise MarketingGuideValidationError("guide_superseded_immutable")
        if guide.status == MarketingGuideStatus.ACTIVE:
            return self._to_response(guide)

        # Supersede first, then activate — SQLite partial unique needs ordered flushes.
        for active in self.repo.list_active_guides_for_update(self.tenant_id):
            if active.id == guide.id:
                continue
            active.status = MarketingGuideStatus.SUPERSEDED
            active.updated_by_user_id = user.id
        self.db.flush()

        guide.status = MarketingGuideStatus.ACTIVE
        guide.updated_by_user_id = user.id
        self.db.flush()
        return self._to_response(guide)

    def _get_or_404(self, guide_id: uuid.UUID) -> MarketingGuide:
        guide = self.repo.get_guide(self.tenant_id, guide_id)
        if guide is None:
            raise MarketingGuideNotFoundError()
        return guide

    def _to_response(self, guide: MarketingGuide) -> GuideResponse:
        return GuideResponse(
            id=guide.id,
            tenant_id=guide.tenant_id,
            version=guide.version,
            status=guide.status,
            business_name=guide.business_name,
            business_summary=guide.business_summary,
            products_services=guide.products_services,
            audiences=guide.audiences,
            goals=guide.goals,
            channels=list(guide.channels or []),
            default_frequency=guide.default_frequency,
            tone_rules=guide.tone_rules,
            constraints=guide.constraints,
            sources_notes=guide.sources_notes,
            extra_json=dict(guide.extra_json or {}),
            created_at=guide.created_at,
            updated_at=guide.updated_at,
        )
