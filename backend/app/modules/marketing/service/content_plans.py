"""M7.5-B Marketing Content Plan service (persistence/API only)."""

from __future__ import annotations

import re
import uuid
from datetime import date

from sqlalchemy.orm import Session

from app.modules.auth.models import User
from app.modules.marketing.enums import (
    MarketingContentPlanItemStatus,
    MarketingContentPlanSource,
    MarketingContentPlanStatus,
    MarketingRubricStatus,
)
from app.modules.marketing.exceptions import (
    MarketingContentPlanImmutableError,
    MarketingContentPlanItemDuplicateLineKeyError,
    MarketingContentPlanItemNotFoundError,
    MarketingContentPlanNotFoundError,
    MarketingContentPlanValidationError,
    MarketingGuideNotFoundError,
    MarketingRubricNotFoundError,
    MarketingRubricNotSelectableError,
)
from app.modules.marketing.models import MarketingContentPlan, MarketingContentPlanItem
from app.modules.marketing.repository import MarketingRepository
from app.modules.marketing.schemas import (
    ContentPlanCreate,
    ContentPlanItemCreate,
    ContentPlanItemResponse,
    ContentPlanItemUpdate,
    ContentPlanResponse,
    ContentPlanUpdate,
)

_SECRETISH_KEY = re.compile(
    r"(secret|token|password|api[_-]?key|bearer|credential)",
    re.IGNORECASE,
)


def _assert_metadata_safe(extra: dict) -> None:
    def walk(obj: object, path: str = "") -> None:
        if isinstance(obj, dict):
            for key, value in obj.items():
                key_s = str(key)
                if _SECRETISH_KEY.search(key_s):
                    raise MarketingContentPlanValidationError("metadata_json_forbidden_key")
                walk(value, f"{path}.{key_s}" if path else key_s)
        elif isinstance(obj, list):
            for idx, item in enumerate(obj):
                walk(item, f"{path}[{idx}]")

    walk(extra)


def _assert_period(period_start: date, period_end: date) -> None:
    if period_start > period_end:
        raise MarketingContentPlanValidationError("invalid_period")


def _assert_date_in_period(
    planned_date: date,
    period_start: date,
    period_end: date,
) -> None:
    if planned_date < period_start or planned_date > period_end:
        raise MarketingContentPlanValidationError("planned_date_out_of_period")


class MarketingContentPlanService:
    def __init__(self, db: Session, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.repo = MarketingRepository(db)

    def list_plans(
        self,
        *,
        status: MarketingContentPlanStatus | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[ContentPlanResponse]:
        return [
            self._plan_response(row)
            for row in self.repo.list_content_plans(
                self.tenant_id,
                status=status,
                skip=skip,
                limit=limit,
            )
        ]

    def get_plan(self, plan_id: uuid.UUID) -> ContentPlanResponse:
        return self._plan_response(self._get_plan_or_404(plan_id))

    def create_plan(self, user: User, payload: ContentPlanCreate) -> ContentPlanResponse:
        _assert_period(payload.period_start, payload.period_end)
        _assert_metadata_safe(payload.metadata_json)
        guide_id = payload.guide_id
        guide_version: int | None = None
        if guide_id is not None:
            guide = self.repo.get_guide(self.tenant_id, guide_id)
            if guide is None:
                raise MarketingGuideNotFoundError()
            guide_version = guide.version
        else:
            active = self.repo.get_active_guide(self.tenant_id)
            if active is not None:
                guide_id = active.id
                guide_version = active.version

        plan = self.repo.create_content_plan(
            tenant_id=self.tenant_id,
            title=payload.title.strip(),
            period_start=payload.period_start,
            period_end=payload.period_end,
            status=MarketingContentPlanStatus.DRAFT,
            guide_id=guide_id,
            guide_version=guide_version,
            source=MarketingContentPlanSource.MANUAL,
            import_fingerprint=None,
            metadata_json=dict(payload.metadata_json),
            created_by_user_id=user.id,
            updated_by_user_id=user.id,
        )
        return self._plan_response(plan)

    def update_plan(
        self,
        user: User,
        plan_id: uuid.UUID,
        payload: ContentPlanUpdate,
    ) -> ContentPlanResponse:
        plan = self._get_plan_or_404(plan_id)
        self._require_draft_plan(plan)
        fields = payload.model_fields_set
        if "title" in fields and payload.title is not None:
            plan.title = payload.title.strip()
        period_start = plan.period_start
        period_end = plan.period_end
        if "period_start" in fields and payload.period_start is not None:
            period_start = payload.period_start
        if "period_end" in fields and payload.period_end is not None:
            period_end = payload.period_end
        _assert_period(period_start, period_end)
        plan.period_start = period_start
        plan.period_end = period_end
        if "guide_id" in fields:
            if payload.guide_id is None:
                plan.guide_id = None
                plan.guide_version = None
            else:
                guide = self.repo.get_guide(self.tenant_id, payload.guide_id)
                if guide is None:
                    raise MarketingGuideNotFoundError()
                plan.guide_id = guide.id
                plan.guide_version = guide.version
        if "metadata_json" in fields and payload.metadata_json is not None:
            _assert_metadata_safe(payload.metadata_json)
            plan.metadata_json = dict(payload.metadata_json)
        # Existing items must remain inside the (possibly new) period.
        for item in self.repo.list_content_plan_items(self.tenant_id, plan.id):
            if item.status == MarketingContentPlanItemStatus.CANCELLED:
                continue
            _assert_date_in_period(item.planned_date, plan.period_start, plan.period_end)
        plan.updated_by_user_id = user.id
        self.db.flush()
        return self._plan_response(plan)

    def approve_plan(self, user: User, plan_id: uuid.UUID) -> ContentPlanResponse:
        plan = self._get_plan_or_404(plan_id)
        self._require_draft_plan(plan)
        items = self.repo.list_content_plan_items(self.tenant_id, plan.id)
        non_cancelled = [
            item
            for item in items
            if item.status != MarketingContentPlanItemStatus.CANCELLED
        ]
        if not non_cancelled:
            raise MarketingContentPlanValidationError("approve_requires_items")
        for item in non_cancelled:
            if item.status == MarketingContentPlanItemStatus.DRAFT:
                item.status = MarketingContentPlanItemStatus.APPROVED
                item.updated_by_user_id = user.id
            elif item.status != MarketingContentPlanItemStatus.APPROVED:
                raise MarketingContentPlanValidationError("item_status_blocks_approve")
        plan.status = MarketingContentPlanStatus.APPROVED
        plan.updated_by_user_id = user.id
        self.db.flush()
        return self._plan_response(plan)

    def archive_plan(self, user: User, plan_id: uuid.UUID) -> ContentPlanResponse:
        plan = self._get_plan_or_404(plan_id)
        if plan.status == MarketingContentPlanStatus.ARCHIVED:
            return self._plan_response(plan)
        if plan.status not in (
            MarketingContentPlanStatus.DRAFT,
            MarketingContentPlanStatus.APPROVED,
        ):
            raise MarketingContentPlanValidationError("plan_archive_forbidden")
        plan.status = MarketingContentPlanStatus.ARCHIVED
        plan.updated_by_user_id = user.id
        self.db.flush()
        return self._plan_response(plan)

    def list_items(self, plan_id: uuid.UUID) -> list[ContentPlanItemResponse]:
        self._get_plan_or_404(plan_id)
        return [
            self._item_response(row)
            for row in self.repo.list_content_plan_items(self.tenant_id, plan_id)
        ]

    def create_item(
        self,
        user: User,
        plan_id: uuid.UUID,
        payload: ContentPlanItemCreate,
    ) -> ContentPlanItemResponse:
        plan = self._get_plan_or_404(plan_id)
        self._require_draft_plan(plan)
        _assert_date_in_period(payload.planned_date, plan.period_start, plan.period_end)
        self._require_active_rubric(payload.rubric_id)
        line_key = payload.line_key.strip() if payload.line_key else None
        if line_key:
            existing = self.repo.get_content_plan_item_by_line_key(
                self.tenant_id, plan.id, line_key
            )
            if existing is not None:
                raise MarketingContentPlanItemDuplicateLineKeyError()
        item = self.repo.create_content_plan_item(
            tenant_id=self.tenant_id,
            plan_id=plan.id,
            planned_date=payload.planned_date,
            rubric_id=payload.rubric_id,
            working_title=payload.working_title.strip(),
            angle=(payload.angle.strip() if payload.angle and payload.angle.strip() else None),
            channels=list(payload.channels),
            format=(payload.format.strip() if payload.format and payload.format.strip() else None),
            goal=(payload.goal.strip() if payload.goal and payload.goal.strip() else None),
            audience=(
                payload.audience.strip() if payload.audience and payload.audience.strip() else None
            ),
            cta=(payload.cta.strip() if payload.cta and payload.cta.strip() else None),
            pain=(payload.pain.strip() if payload.pain and payload.pain.strip() else None),
            insight=(
                payload.insight.strip() if payload.insight and payload.insight.strip() else None
            ),
            funnel_stage=(
                payload.funnel_stage.strip()
                if payload.funnel_stage and payload.funnel_stage.strip()
                else None
            ),
            notes=(payload.notes.strip() if payload.notes and payload.notes.strip() else None),
            status=MarketingContentPlanItemStatus.DRAFT,
            topic_id=None,
            external_line_key=line_key,
            sort_order=payload.sort_order,
            created_by_user_id=user.id,
            updated_by_user_id=user.id,
        )
        return self._item_response(item)

    def update_item(
        self,
        user: User,
        plan_id: uuid.UUID,
        item_id: uuid.UUID,
        payload: ContentPlanItemUpdate,
    ) -> ContentPlanItemResponse:
        plan = self._get_plan_or_404(plan_id)
        self._require_draft_plan(plan)
        item = self._get_item_or_404(plan_id, item_id)
        if item.status != MarketingContentPlanItemStatus.DRAFT:
            raise MarketingContentPlanImmutableError("item_not_draft")
        fields = payload.model_fields_set
        if "planned_date" in fields and payload.planned_date is not None:
            _assert_date_in_period(
                payload.planned_date, plan.period_start, plan.period_end
            )
            item.planned_date = payload.planned_date
        if "rubric_id" in fields and payload.rubric_id is not None:
            self._require_active_rubric(payload.rubric_id)
            item.rubric_id = payload.rubric_id
        if "working_title" in fields and payload.working_title is not None:
            item.working_title = payload.working_title.strip()
        if "channels" in fields and payload.channels is not None:
            item.channels = list(payload.channels)
        if "sort_order" in fields and payload.sort_order is not None:
            item.sort_order = payload.sort_order
        for field in (
            "angle",
            "format",
            "goal",
            "audience",
            "cta",
            "pain",
            "insight",
            "funnel_stage",
            "notes",
        ):
            if field in fields:
                value = getattr(payload, field)
                if isinstance(value, str):
                    setattr(item, field, value.strip() or None)
                else:
                    setattr(item, field, value)
        item.updated_by_user_id = user.id
        self.db.flush()
        return self._item_response(item)

    def cancel_item(
        self,
        user: User,
        plan_id: uuid.UUID,
        item_id: uuid.UUID,
    ) -> ContentPlanItemResponse:
        plan = self._get_plan_or_404(plan_id)
        self._require_draft_plan(plan)
        item = self._get_item_or_404(plan_id, item_id)
        if item.status == MarketingContentPlanItemStatus.CANCELLED:
            return self._item_response(item)
        if item.status != MarketingContentPlanItemStatus.DRAFT:
            raise MarketingContentPlanImmutableError("item_cancel_not_draft")
        item.status = MarketingContentPlanItemStatus.CANCELLED
        item.updated_by_user_id = user.id
        self.db.flush()
        return self._item_response(item)

    def _require_active_rubric(self, rubric_id: uuid.UUID) -> None:
        rubric = self.repo.get_rubric(self.tenant_id, rubric_id)
        if rubric is None:
            raise MarketingRubricNotFoundError()
        if rubric.status != MarketingRubricStatus.ACTIVE:
            raise MarketingRubricNotSelectableError()

    def _require_draft_plan(self, plan: MarketingContentPlan) -> None:
        if plan.status != MarketingContentPlanStatus.DRAFT:
            raise MarketingContentPlanImmutableError("plan_not_draft")

    def _get_plan_or_404(self, plan_id: uuid.UUID) -> MarketingContentPlan:
        plan = self.repo.get_content_plan(self.tenant_id, plan_id)
        if plan is None:
            raise MarketingContentPlanNotFoundError()
        return plan

    def _get_item_or_404(
        self,
        plan_id: uuid.UUID,
        item_id: uuid.UUID,
    ) -> MarketingContentPlanItem:
        item = self.repo.get_content_plan_item(self.tenant_id, plan_id, item_id)
        if item is None:
            raise MarketingContentPlanItemNotFoundError()
        return item

    def _plan_response(self, plan: MarketingContentPlan) -> ContentPlanResponse:
        return ContentPlanResponse.model_validate(plan)

    def _item_response(self, item: MarketingContentPlanItem) -> ContentPlanItemResponse:
        return ContentPlanItemResponse(
            id=item.id,
            tenant_id=item.tenant_id,
            plan_id=item.plan_id,
            planned_date=item.planned_date,
            rubric_id=item.rubric_id,
            working_title=item.working_title,
            angle=item.angle,
            channels=list(item.channels or []),
            format=item.format,
            goal=item.goal,
            audience=item.audience,
            cta=item.cta,
            pain=item.pain,
            insight=item.insight,
            funnel_stage=item.funnel_stage,
            notes=item.notes,
            status=item.status,
            topic_id=item.topic_id,
            line_key=item.external_line_key,
            sort_order=item.sort_order,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )
