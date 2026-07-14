import uuid
from datetime import date

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.modules.auth.models import User
from app.modules.marketing.enums import MarketingPackStatus
from app.modules.marketing.exceptions import MarketingPackSlugExistsError
from app.modules.marketing.models import MarketingContentTopic, MarketingPublicationPack
from app.modules.marketing.repository import MarketingRepository
from app.modules.marketing.schemas import (
    PackCreate,
    PackDetailResponse,
    PackMediaAssetResponse,
    PackPublishLogResponse,
    PackSummaryResponse,
    PackTextResponse,
    PackUpdate,
    TopicSummaryInPack,
)
from app.modules.marketing.service.pack_factory import create_draft_pack_with_texts
from app.modules.marketing.service.slugify import slugify
from app.modules.marketing.topic_metadata import extract_editorial_fields

_PATCHABLE_STATUSES = {MarketingPackStatus.DRAFT, MarketingPackStatus.ARCHIVED}
_FORBIDDEN_PATCH_STATUSES = {
    MarketingPackStatus.APPROVED,
    MarketingPackStatus.PUBLISHED,
    MarketingPackStatus.PUBLISHING,
    MarketingPackStatus.SCHEDULED,
}


class MarketingPackService:
    def __init__(self, db: Session, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.repo = MarketingRepository(db)

    def list_packs(
        self,
        *,
        status: MarketingPackStatus | None = None,
        topic_id: uuid.UUID | None = None,
        planned_date: date | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[PackSummaryResponse]:
        rows = self.repo.list_packs(
            self.tenant_id,
            status=status,
            topic_id=topic_id,
            planned_date=planned_date,
            skip=skip,
            limit=limit,
        )
        return [self._to_summary(row) for row in rows]

    def create_pack(self, user: User, payload: PackCreate) -> PackDetailResponse:
        topic = None
        if payload.topic_id is not None:
            topic = self._get_topic_or_404(payload.topic_id)

        planned_date = payload.planned_date or date.today()
        slug = payload.slug or slugify(payload.title)
        if self.repo.get_pack_by_slug(self.tenant_id, slug):
            raise MarketingPackSlugExistsError()

        pack, texts = create_draft_pack_with_texts(
            self.repo,
            tenant_id=self.tenant_id,
            user=user,
            title=payload.title,
            slug=slug,
            planned_date=planned_date,
            topic=topic,
            topic_id=payload.topic_id,
            source=payload.source,
            metadata_json=payload.metadata_json,
        )
        self.db.refresh(pack)
        return self._to_detail(pack, texts=texts)

    def get_pack(self, pack_id: uuid.UUID) -> PackDetailResponse:
        pack = self._get_pack_or_404(pack_id, with_relations=True)
        return self._to_detail(pack)

    def update_pack(
        self,
        user: User,
        pack_id: uuid.UUID,
        payload: PackUpdate,
    ) -> PackDetailResponse:
        pack = self._get_pack_or_404(pack_id, with_relations=True)

        if payload.title is not None:
            pack.title = payload.title

        if payload.source is not None:
            pack.source = payload.source

        if payload.topic_id is not None:
            self._get_topic_or_404(payload.topic_id)
            pack.topic_id = payload.topic_id

        if payload.status is not None:
            self._apply_safe_status_change(pack, payload.status)

        pack.updated_by_user_id = user.id
        self.db.flush()
        self.db.refresh(pack)
        return self._to_detail(pack)

    def _apply_safe_status_change(
        self,
        pack: MarketingPublicationPack,
        new_status: MarketingPackStatus,
    ) -> None:
        if new_status in _FORBIDDEN_PATCH_STATUSES:
            raise ConflictError(
                f"Cannot set pack status to '{new_status.value}' via PATCH; use approval/publish flows"
            )
        if new_status not in _PATCHABLE_STATUSES:
            raise ConflictError(f"Pack status '{new_status.value}' is not allowed via PATCH")
        if pack.status in _FORBIDDEN_PATCH_STATUSES and new_status != MarketingPackStatus.ARCHIVED:
            raise ConflictError("Cannot change status of an approved or publishing pack except to archived")
        pack.status = new_status

    def _get_pack_or_404(
        self,
        pack_id: uuid.UUID,
        *,
        with_relations: bool = False,
    ) -> MarketingPublicationPack:
        pack = self.repo.get_pack(self.tenant_id, pack_id, with_relations=with_relations)
        if pack is None:
            raise NotFoundError("Pack not found")
        return pack

    def _get_topic_or_404(self, topic_id: uuid.UUID) -> MarketingContentTopic:
        topic = self.repo.get_topic(self.tenant_id, topic_id)
        if topic is None:
            raise NotFoundError("Topic not found")
        return topic

    def _topic_summary(self, topic: MarketingContentTopic) -> TopicSummaryInPack:
        editorial = extract_editorial_fields(topic.metadata_json)
        return TopicSummaryInPack(
            id=topic.id,
            legacy_topic_id=topic.legacy_topic_id,
            title=topic.title,
            rubric=topic.rubric,
            status=topic.status,
            angle=topic.angle,
            priority=topic.priority,
            audience=editorial["audience"],
            pain=editorial["pain"],
            insight=editorial["insight"],
            source_ref=editorial["source_ref"],
            cta=editorial["cta"],
            funnel_stage=editorial["funnel_stage"],
            notes=editorial["notes"],
            planned_date=editorial["planned_date"],
        )

    def _to_summary(self, pack: MarketingPublicationPack) -> PackSummaryResponse:
        topic_summary = None
        if pack.topic is not None:
            topic_summary = self._topic_summary(pack.topic)
        return PackSummaryResponse(
            id=pack.id,
            tenant_id=pack.tenant_id,
            topic_id=pack.topic_id,
            slug=pack.slug,
            pack_dir_name=pack.pack_dir_name,
            title=pack.title,
            planned_date=pack.planned_date,
            status=pack.status,
            preflight_status=pack.preflight_status,
            approval_status=pack.approval_status,
            publish_status=pack.publish_status,
            source=pack.source,
            created_by_user_id=pack.created_by_user_id,
            created_at=pack.created_at,
            updated_at=pack.updated_at,
            topic=topic_summary,
        )

    def _to_detail(
        self,
        pack: MarketingPublicationPack,
        *,
        texts: list | None = None,
    ) -> PackDetailResponse:
        summary = self._to_summary(pack)
        text_rows = texts if texts is not None else pack.texts
        media_rows = pack.media_assets if hasattr(pack, "media_assets") and pack.media_assets else []
        log_rows = pack.publish_logs if hasattr(pack, "publish_logs") and pack.publish_logs else []
        if not media_rows:
            media_rows = self.repo.list_pack_media(self.tenant_id, pack.id, include_archived=False)
        if not log_rows:
            log_rows = self.repo.list_pack_logs(self.tenant_id, pack.id)

        return PackDetailResponse(
            **summary.model_dump(),
            campaign_id=pack.campaign_id,
            plan_item_id=pack.plan_item_id,
            preflight_at=pack.preflight_at,
            preflight_report_json=pack.preflight_report_json or {},
            approved_at=pack.approved_at,
            approved_by_user_id=pack.approved_by_user_id,
            channel_config_json=pack.channel_config_json,
            legacy_git_path=pack.legacy_git_path,
            metadata_json=pack.metadata_json,
            texts=[PackTextResponse.model_validate(t) for t in text_rows],
            media_assets=[PackMediaAssetResponse.model_validate(m) for m in media_rows],
            publish_logs=[PackPublishLogResponse.model_validate(log) for log in log_rows],
        )
