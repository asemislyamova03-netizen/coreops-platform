import uuid
from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.modules.auth.models import User
from app.modules.marketing.enums import MarketingTopicStatus
from app.modules.marketing.exceptions import (
    MarketingPackSlugExistsError,
    MarketingTopicDuplicateBlockedError,
    MarketingTopicNotApprovedError,
)
from app.modules.marketing.models import MarketingContentTopic
from app.modules.marketing.repository import MarketingRepository
from app.modules.marketing.schemas import (
    PackTextStubResponse,
    TakeTopicPackResponse,
    TakeTopicRequest,
    TopicCreate,
    TopicResponse,
    TopicUpdate,
)
from app.modules.marketing.service.pack_factory import create_draft_pack_with_texts
from app.modules.marketing.service.slugify import slugify
from app.modules.marketing.topic_metadata import (
    build_topic_metadata_for_create,
    build_topic_metadata_for_update,
    extract_editorial_fields,
)


class MarketingTopicService:
    def __init__(self, db: Session, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.repo = MarketingRepository(db)

    def list_topics(
        self,
        *,
        status: MarketingTopicStatus | None = None,
        rubric: str | None = None,
        search: str | None = None,
        include_archived: bool = False,
        skip: int = 0,
        limit: int = 50,
    ) -> list[TopicResponse]:
        rows = self.repo.list_topics(
            self.tenant_id,
            status=status,
            rubric=rubric,
            search=search,
            exclude_archived=not include_archived,
            skip=skip,
            limit=limit,
        )
        return [self._to_response(row) for row in rows]

    def get_topic(self, topic_id: uuid.UUID) -> TopicResponse:
        topic = self._get_topic_or_404(topic_id)
        return self._to_response(topic)

    def create_topic(self, user: User, payload: TopicCreate) -> TopicResponse:
        metadata = build_topic_metadata_for_create(payload)
        topic = self.repo.create_topic(
            tenant_id=self.tenant_id,
            legacy_topic_id=payload.legacy_topic_id,
            title=payload.title,
            rubric=payload.rubric,
            angle=payload.angle,
            source=payload.source,
            status=payload.status,
            priority=payload.priority,
            reusable=payload.reusable,
            recommended_channels=payload.recommended_channels,
            slug_hint=payload.slug_hint,
            metadata_json=metadata,
            created_by_user_id=user.id,
            updated_by_user_id=user.id,
        )
        return self._to_response(topic)

    def update_topic(
        self,
        user: User,
        topic_id: uuid.UUID,
        payload: TopicUpdate,
    ) -> TopicResponse:
        topic = self._get_topic_or_404(topic_id)
        for field in (
            "title",
            "rubric",
            "angle",
            "source",
            "status",
            "priority",
            "reusable",
            "recommended_channels",
            "legacy_topic_id",
            "slug_hint",
        ):
            value = getattr(payload, field)
            if value is not None:
                setattr(topic, field, value)
        merged_metadata = build_topic_metadata_for_update(topic.metadata_json, payload)
        if merged_metadata is not None:
            topic.metadata_json = merged_metadata
        topic.updated_by_user_id = user.id
        self.db.flush()
        return self._to_response(topic)

    def archive_topic(self, user: User, topic_id: uuid.UUID) -> TopicResponse:
        topic = self._get_topic_or_404(topic_id)
        topic.status = MarketingTopicStatus.ARCHIVED
        topic.updated_by_user_id = user.id
        self.db.flush()
        return self._to_response(topic)

    def mark_used(self, user: User, topic_id: uuid.UUID) -> TopicResponse:
        topic = self._get_topic_or_404(topic_id)
        now = datetime.now(UTC)
        topic.used_count += 1
        topic.last_used_at = now
        if not topic.reusable:
            topic.status = MarketingTopicStatus.USED
        topic.updated_by_user_id = user.id
        self.db.flush()
        return self._to_response(topic)

    def take_topic(
        self,
        user: User,
        topic_id: uuid.UUID,
        payload: TakeTopicRequest,
    ) -> TakeTopicPackResponse:
        topic = self._get_topic_or_404(topic_id)
        if topic.status != MarketingTopicStatus.APPROVED:
            raise MarketingTopicNotApprovedError()

        self._assert_take_allowed(topic)

        planned_date = payload.planned_date or date.today()
        slug = payload.slug or topic.slug_hint or slugify(topic.title)
        if self.repo.get_pack_by_slug(self.tenant_id, slug):
            raise MarketingPackSlugExistsError()

        existing = self.repo.find_pack_for_topic_date(
            self.tenant_id,
            topic.id,
            planned_date,
        )
        if existing:
            raise MarketingTopicDuplicateBlockedError(
                f"pack already exists for topic on {planned_date.isoformat()}"
            )

        pack, texts = create_draft_pack_with_texts(
            self.repo,
            tenant_id=self.tenant_id,
            user=user,
            title=topic.title,
            slug=slug,
            planned_date=planned_date,
            topic=topic,
            source=payload.source,
        )

        self.db.refresh(pack)
        return TakeTopicPackResponse(
            id=pack.id,
            tenant_id=pack.tenant_id,
            topic_id=pack.topic_id,
            slug=pack.slug,
            pack_dir_name=pack.pack_dir_name,
            title=pack.title,
            planned_date=pack.planned_date,
            status=pack.status.value,
            approval_status=pack.approval_status.value,
            publish_status=pack.publish_status.value,
            source=pack.source,
            texts=[
                PackTextStubResponse(
                    id=t.id,
                    channel=t.channel,
                    text=t.text,
                    status=t.status.value,
                    char_count=t.char_count,
                    version=t.version,
                )
                for t in texts
            ],
        )

    def _assert_take_allowed(self, topic: MarketingContentTopic) -> None:
        if not topic.reusable and topic.used_count > 0:
            raise MarketingTopicDuplicateBlockedError("topic already used and not reusable")

        active_packs = self.repo.list_active_packs_for_topic(self.tenant_id, topic.id)
        if active_packs and not topic.reusable:
            raise MarketingTopicDuplicateBlockedError(
                f"{len(active_packs)} active pack(s) exist for this topic"
            )

    def _get_topic_or_404(self, topic_id: uuid.UUID) -> MarketingContentTopic:
        topic = self.repo.get_topic(self.tenant_id, topic_id)
        if topic is None:
            raise NotFoundError("Topic not found")
        return topic

    def _to_response(self, topic: MarketingContentTopic) -> TopicResponse:
        duplicate_status, duplicate_detail = self._duplicate_status(topic)
        editorial = extract_editorial_fields(topic.metadata_json)
        return TopicResponse(
            id=topic.id,
            tenant_id=topic.tenant_id,
            legacy_topic_id=topic.legacy_topic_id,
            title=topic.title,
            rubric=topic.rubric,
            angle=topic.angle,
            source=topic.source,
            status=topic.status,
            priority=topic.priority,
            reusable=topic.reusable,
            recommended_channels=topic.recommended_channels,
            used_count=topic.used_count,
            last_used_at=topic.last_used_at,
            slug_hint=topic.slug_hint,
            metadata_json=topic.metadata_json or {},
            audience=editorial["audience"],
            pain=editorial["pain"],
            insight=editorial["insight"],
            source_ref=editorial["source_ref"],
            cta=editorial["cta"],
            funnel_stage=editorial["funnel_stage"],
            notes=editorial["notes"],
            planned_date=editorial["planned_date"],
            created_at=topic.created_at,
            updated_at=topic.updated_at,
            duplicate_status=duplicate_status,
            duplicate_detail=duplicate_detail,
        )

    def _duplicate_status(
        self,
        topic: MarketingContentTopic,
    ) -> tuple[str | None, str | None]:
        if topic.status == MarketingTopicStatus.ARCHIVED:
            return "blocked", "topic is archived"
        if not topic.reusable and topic.used_count > 0:
            return "blocked", "topic already used and not reusable"
        active = self.repo.list_active_packs_for_topic(self.tenant_id, topic.id)
        if active:
            return "warning", f"{len(active)} active pack(s) linked to topic"
        return "ok", None
