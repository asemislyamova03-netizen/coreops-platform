import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.modules.marketing.enums import MarketingMediaAssetStatus, MarketingPackStatus, MarketingTopicStatus
from app.modules.marketing.models import (
    MarketingContentTopic,
    MarketingMediaAsset,
    MarketingPublicationPack,
    MarketingPublicationText,
    MarketingPublishLog,
)


class MarketingRepository:
    def __init__(self, db: Session):
        self.db = db

    # --- Topics ---

    def list_topics(
        self,
        tenant_id: uuid.UUID,
        *,
        status: MarketingTopicStatus | None = None,
        rubric: str | None = None,
        search: str | None = None,
        exclude_archived: bool = True,
        skip: int = 0,
        limit: int = 50,
    ) -> list[MarketingContentTopic]:
        stmt = (
            select(MarketingContentTopic)
            .where(MarketingContentTopic.tenant_id == tenant_id)
            .order_by(
                MarketingContentTopic.priority.desc(),
                MarketingContentTopic.created_at.desc(),
            )
            .offset(skip)
            .limit(limit)
        )
        if status is not None:
            stmt = stmt.where(MarketingContentTopic.status == status)
        elif exclude_archived:
            stmt = stmt.where(MarketingContentTopic.status != MarketingTopicStatus.ARCHIVED)
        if rubric:
            stmt = stmt.where(MarketingContentTopic.rubric == rubric)
        if search:
            stmt = stmt.where(MarketingContentTopic.title.ilike(f"%{search}%"))
        return list(self.db.scalars(stmt).all())

    def get_topic(
        self,
        tenant_id: uuid.UUID,
        topic_id: uuid.UUID,
    ) -> MarketingContentTopic | None:
        stmt = select(MarketingContentTopic).where(
            MarketingContentTopic.tenant_id == tenant_id,
            MarketingContentTopic.id == topic_id,
        )
        return self.db.scalar(stmt)

    def create_topic(self, **kwargs) -> MarketingContentTopic:
        topic = MarketingContentTopic(**kwargs)
        self.db.add(topic)
        self.db.flush()
        return topic

    def count_approved_topics(self, tenant_id: uuid.UUID) -> int:
        stmt = select(MarketingContentTopic).where(
            MarketingContentTopic.tenant_id == tenant_id,
            MarketingContentTopic.status == MarketingTopicStatus.APPROVED,
        )
        return len(list(self.db.scalars(stmt).all()))

    def find_pack_for_topic_date(
        self,
        tenant_id: uuid.UUID,
        topic_id: uuid.UUID,
        planned_date: date,
    ) -> MarketingPublicationPack | None:
        stmt = select(MarketingPublicationPack).where(
            MarketingPublicationPack.tenant_id == tenant_id,
            MarketingPublicationPack.topic_id == topic_id,
            MarketingPublicationPack.planned_date == planned_date,
            MarketingPublicationPack.status != MarketingPackStatus.ARCHIVED,
        )
        return self.db.scalar(stmt)

    def list_active_packs_for_topic(
        self,
        tenant_id: uuid.UUID,
        topic_id: uuid.UUID,
    ) -> list[MarketingPublicationPack]:
        stmt = select(MarketingPublicationPack).where(
            MarketingPublicationPack.tenant_id == tenant_id,
            MarketingPublicationPack.topic_id == topic_id,
            MarketingPublicationPack.status != MarketingPackStatus.ARCHIVED,
        )
        return list(self.db.scalars(stmt).all())

    # --- Packs ---

    def list_packs(
        self,
        tenant_id: uuid.UUID,
        *,
        status: MarketingPackStatus | None = None,
        topic_id: uuid.UUID | None = None,
        planned_date: date | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[MarketingPublicationPack]:
        stmt = (
            select(MarketingPublicationPack)
            .where(MarketingPublicationPack.tenant_id == tenant_id)
            .options(selectinload(MarketingPublicationPack.topic))
            .order_by(MarketingPublicationPack.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        if status is not None:
            stmt = stmt.where(MarketingPublicationPack.status == status)
        if topic_id is not None:
            stmt = stmt.where(MarketingPublicationPack.topic_id == topic_id)
        if planned_date is not None:
            stmt = stmt.where(MarketingPublicationPack.planned_date == planned_date)
        return list(self.db.scalars(stmt).all())

    def get_pack(
        self,
        tenant_id: uuid.UUID,
        pack_id: uuid.UUID,
        *,
        with_relations: bool = False,
    ) -> MarketingPublicationPack | None:
        stmt = select(MarketingPublicationPack).where(
            MarketingPublicationPack.tenant_id == tenant_id,
            MarketingPublicationPack.id == pack_id,
        )
        if with_relations:
            stmt = stmt.options(
                selectinload(MarketingPublicationPack.topic),
                selectinload(MarketingPublicationPack.texts),
                selectinload(MarketingPublicationPack.media_assets),
                selectinload(MarketingPublicationPack.publish_logs),
            )
        return self.db.scalar(stmt)

    def get_pack_by_slug(
        self,
        tenant_id: uuid.UUID,
        slug: str,
    ) -> MarketingPublicationPack | None:
        stmt = select(MarketingPublicationPack).where(
            MarketingPublicationPack.tenant_id == tenant_id,
            MarketingPublicationPack.slug == slug,
        )
        return self.db.scalar(stmt)

    def create_pack(self, **kwargs) -> MarketingPublicationPack:
        pack = MarketingPublicationPack(**kwargs)
        self.db.add(pack)
        self.db.flush()
        return pack

    def create_text(self, **kwargs) -> MarketingPublicationText:
        text = MarketingPublicationText(**kwargs)
        self.db.add(text)
        self.db.flush()
        return text

    def list_pack_texts(
        self,
        tenant_id: uuid.UUID,
        pack_id: uuid.UUID,
    ) -> list[MarketingPublicationText]:
        stmt = (
            select(MarketingPublicationText)
            .where(
                MarketingPublicationText.tenant_id == tenant_id,
                MarketingPublicationText.pack_id == pack_id,
            )
            .order_by(MarketingPublicationText.channel)
        )
        return list(self.db.scalars(stmt).all())

    def get_pack_text(
        self,
        tenant_id: uuid.UUID,
        pack_id: uuid.UUID,
        channel,
    ) -> MarketingPublicationText | None:
        stmt = select(MarketingPublicationText).where(
            MarketingPublicationText.tenant_id == tenant_id,
            MarketingPublicationText.pack_id == pack_id,
            MarketingPublicationText.channel == channel,
        )
        return self.db.scalar(stmt)

    def list_pack_media(
        self,
        tenant_id: uuid.UUID,
        pack_id: uuid.UUID,
        *,
        include_archived: bool = False,
    ) -> list[MarketingMediaAsset]:
        stmt = (
            select(MarketingMediaAsset)
            .where(
                MarketingMediaAsset.tenant_id == tenant_id,
                MarketingMediaAsset.pack_id == pack_id,
            )
            .order_by(MarketingMediaAsset.created_at)
        )
        if not include_archived:
            stmt = stmt.where(MarketingMediaAsset.status != MarketingMediaAssetStatus.ARCHIVED)
        return list(self.db.scalars(stmt).all())

    def get_media_asset(
        self,
        tenant_id: uuid.UUID,
        asset_id: uuid.UUID,
    ) -> MarketingMediaAsset | None:
        stmt = select(MarketingMediaAsset).where(
            MarketingMediaAsset.tenant_id == tenant_id,
            MarketingMediaAsset.id == asset_id,
        )
        return self.db.scalar(stmt)

    def create_media_asset(self, **kwargs) -> MarketingMediaAsset:
        asset = MarketingMediaAsset(**kwargs)
        self.db.add(asset)
        self.db.flush()
        return asset

    def list_pack_logs(
        self,
        tenant_id: uuid.UUID,
        pack_id: uuid.UUID,
    ) -> list[MarketingPublishLog]:
        stmt = (
            select(MarketingPublishLog)
            .where(
                MarketingPublishLog.tenant_id == tenant_id,
                MarketingPublishLog.pack_id == pack_id,
            )
            .order_by(MarketingPublishLog.created_at.desc())
        )
        return list(self.db.scalars(stmt).all())


# Backward-compatible alias used by topics service
MarketingTopicRepository = MarketingRepository
