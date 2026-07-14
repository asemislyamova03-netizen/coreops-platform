import uuid
from datetime import date

from app.modules.auth.models import User
from app.modules.marketing.enums import (
    DEFAULT_PACK_CHANNELS,
    MarketingApprovalStatus,
    MarketingChannel,
    MarketingPackStatus,
    MarketingPreflightStatus,
    MarketingPublishStatus,
    MarketingTextStatus,
)
from app.modules.marketing.models import MarketingContentTopic, MarketingPublicationPack, MarketingPublicationText
from app.modules.marketing.repository import MarketingRepository


def resolve_pack_channels(topic: MarketingContentTopic | None) -> list[MarketingChannel]:
    if topic and topic.recommended_channels:
        resolved: list[MarketingChannel] = []
        for raw in topic.recommended_channels:
            try:
                resolved.append(MarketingChannel(str(raw).lower()))
            except ValueError:
                continue
        if resolved:
            return resolved
    return list(DEFAULT_PACK_CHANNELS)


def create_draft_pack_with_texts(
    repo: MarketingRepository,
    *,
    tenant_id: uuid.UUID,
    user: User,
    title: str,
    slug: str,
    planned_date: date,
    topic: MarketingContentTopic | None = None,
    topic_id: uuid.UUID | None = None,
    source: str = "console",
    pack_dir_name: str | None = None,
    metadata_json: dict | None = None,
    channels: list[MarketingChannel] | None = None,
) -> tuple[MarketingPublicationPack, list[MarketingPublicationText]]:
    resolved_topic_id = topic_id if topic_id is not None else (topic.id if topic else None)
    meta = dict(metadata_json or {})
    if topic and "topic_rubric" not in meta:
        meta["topic_rubric"] = topic.rubric

    pack = repo.create_pack(
        tenant_id=tenant_id,
        topic_id=resolved_topic_id,
        slug=slug,
        pack_dir_name=pack_dir_name or f"{planned_date.isoformat()}-{slug}",
        title=title,
        planned_date=planned_date,
        status=MarketingPackStatus.DRAFT,
        preflight_status=MarketingPreflightStatus.NOT_RUN,
        approval_status=MarketingApprovalStatus.DRAFT,
        publish_status=MarketingPublishStatus.NOT_STARTED,
        source=source,
        metadata_json=meta,
        created_by_user_id=user.id,
        updated_by_user_id=user.id,
    )

    channel_list = channels if channels is not None else resolve_pack_channels(topic)
    texts: list[MarketingPublicationText] = []
    for channel in channel_list:
        text_row = repo.create_text(
            tenant_id=tenant_id,
            pack_id=pack.id,
            channel=channel,
            text="",
            status=MarketingTextStatus.DRAFT,
            char_count=0,
            created_by_user_id=user.id,
            updated_by_user_id=user.id,
        )
        texts.append(text_row)

    return pack, texts
