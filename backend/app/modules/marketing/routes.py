import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.modules import require_module
from app.core.tenancy import TenantContext
from app.modules.marketing.enums import MarketingChannel, MarketingPackStatus, MarketingTopicStatus
from app.modules.marketing.schemas import (
    ApproveRequest,
    MarketingHealthResponse,
    MediaCreate,
    MediaUpdate,
    PackCreate,
    PackDetailResponse,
    PackMediaAssetResponse,
    PackSummaryResponse,
    PackTextResponse,
    PackTextUpsert,
    PackUpdate,
    PreflightRequest,
    PreflightResponse,
    RejectRequest,
    TakeTopicPackResponse,
    TakeTopicRequest,
    TopicCreate,
    TopicResponse,
    TopicUpdate,
)
from app.modules.marketing.service.approval import MarketingApprovalService
from app.modules.marketing.service.packs import MarketingPackService
from app.modules.marketing.service.media import MarketingMediaService
from app.modules.marketing.service.texts import MarketingTextService
from app.modules.marketing.service.topics import MarketingTopicService

router = APIRouter(prefix="/marketing", tags=["marketing"])


def _topic_service(ctx: TenantContext, db: Session) -> MarketingTopicService:
    return MarketingTopicService(db, ctx.tenant.id)


def _pack_service(ctx: TenantContext, db: Session) -> MarketingPackService:
    return MarketingPackService(db, ctx.tenant.id)


def _text_service(ctx: TenantContext, db: Session) -> MarketingTextService:
    return MarketingTextService(db, ctx.tenant.id)


def _media_service(ctx: TenantContext, db: Session) -> MarketingMediaService:
    return MarketingMediaService(db, ctx.tenant.id)


def _approval_service(ctx: TenantContext, db: Session) -> MarketingApprovalService:
    return MarketingApprovalService(db, ctx.tenant.id)


@router.get("/health", response_model=MarketingHealthResponse)
def marketing_health(
    ctx: TenantContext = Depends(require_module("marketing")),
) -> MarketingHealthResponse:
    return MarketingHealthResponse()


@router.get("/topics", response_model=list[TopicResponse])
def list_topics(
    status: MarketingTopicStatus | None = None,
    rubric: str | None = Query(default=None, max_length=128),
    search: str | None = Query(default=None, max_length=255),
    include_archived: bool = False,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    ctx: TenantContext = Depends(require_module("marketing")),
    db: Session = Depends(get_db),
) -> list[TopicResponse]:
    return _topic_service(ctx, db).list_topics(
        status=status,
        rubric=rubric,
        search=search,
        include_archived=include_archived,
        skip=skip,
        limit=limit,
    )


@router.post("/topics", response_model=TopicResponse, status_code=201)
def create_topic(
    payload: TopicCreate,
    ctx: TenantContext = Depends(require_module("marketing")),
    db: Session = Depends(get_db),
) -> TopicResponse:
    result = _topic_service(ctx, db).create_topic(ctx.user, payload)
    db.commit()
    return result


@router.get("/topics/{topic_id}", response_model=TopicResponse)
def get_topic(
    topic_id: uuid.UUID,
    ctx: TenantContext = Depends(require_module("marketing")),
    db: Session = Depends(get_db),
) -> TopicResponse:
    return _topic_service(ctx, db).get_topic(topic_id)


@router.patch("/topics/{topic_id}", response_model=TopicResponse)
def update_topic(
    topic_id: uuid.UUID,
    payload: TopicUpdate,
    ctx: TenantContext = Depends(require_module("marketing")),
    db: Session = Depends(get_db),
) -> TopicResponse:
    result = _topic_service(ctx, db).update_topic(ctx.user, topic_id, payload)
    db.commit()
    return result


@router.post("/topics/{topic_id}/take", response_model=TakeTopicPackResponse, status_code=201)
def take_topic(
    topic_id: uuid.UUID,
    payload: TakeTopicRequest | None = None,
    ctx: TenantContext = Depends(require_module("marketing")),
    db: Session = Depends(get_db),
) -> TakeTopicPackResponse:
    body = payload or TakeTopicRequest()
    result = _topic_service(ctx, db).take_topic(ctx.user, topic_id, body)
    db.commit()
    return result


@router.post("/topics/{topic_id}/archive", response_model=TopicResponse)
def archive_topic(
    topic_id: uuid.UUID,
    ctx: TenantContext = Depends(require_module("marketing")),
    db: Session = Depends(get_db),
) -> TopicResponse:
    result = _topic_service(ctx, db).archive_topic(ctx.user, topic_id)
    db.commit()
    return result


@router.post("/topics/{topic_id}/mark-used", response_model=TopicResponse)
def mark_topic_used(
    topic_id: uuid.UUID,
    ctx: TenantContext = Depends(require_module("marketing")),
    db: Session = Depends(get_db),
) -> TopicResponse:
    result = _topic_service(ctx, db).mark_used(ctx.user, topic_id)
    db.commit()
    return result


@router.get("/packs", response_model=list[PackSummaryResponse])
def list_packs(
    status: MarketingPackStatus | None = None,
    topic_id: uuid.UUID | None = None,
    planned_date: date | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    ctx: TenantContext = Depends(require_module("marketing")),
    db: Session = Depends(get_db),
) -> list[PackSummaryResponse]:
    return _pack_service(ctx, db).list_packs(
        status=status,
        topic_id=topic_id,
        planned_date=planned_date,
        skip=skip,
        limit=limit,
    )


@router.post("/packs", response_model=PackDetailResponse, status_code=201)
def create_pack(
    payload: PackCreate,
    ctx: TenantContext = Depends(require_module("marketing")),
    db: Session = Depends(get_db),
) -> PackDetailResponse:
    result = _pack_service(ctx, db).create_pack(ctx.user, payload)
    db.commit()
    return result


@router.get("/packs/{pack_id}", response_model=PackDetailResponse)
def get_pack(
    pack_id: uuid.UUID,
    ctx: TenantContext = Depends(require_module("marketing")),
    db: Session = Depends(get_db),
) -> PackDetailResponse:
    return _pack_service(ctx, db).get_pack(pack_id)


@router.patch("/packs/{pack_id}", response_model=PackDetailResponse)
def update_pack(
    pack_id: uuid.UUID,
    payload: PackUpdate,
    ctx: TenantContext = Depends(require_module("marketing")),
    db: Session = Depends(get_db),
) -> PackDetailResponse:
    result = _pack_service(ctx, db).update_pack(ctx.user, pack_id, payload)
    db.commit()
    return result


@router.post("/packs/{pack_id}/preflight", response_model=PreflightResponse)
def run_pack_preflight(
    pack_id: uuid.UUID,
    payload: PreflightRequest | None = None,
    ctx: TenantContext = Depends(require_module("marketing")),
    db: Session = Depends(get_db),
) -> PreflightResponse:
    result = _approval_service(ctx, db).run_preflight(ctx.user, pack_id, payload)
    db.commit()
    return result


@router.post("/packs/{pack_id}/approve", response_model=PackDetailResponse)
def approve_pack(
    pack_id: uuid.UUID,
    payload: ApproveRequest | None = None,
    ctx: TenantContext = Depends(require_module("marketing")),
    db: Session = Depends(get_db),
) -> PackDetailResponse:
    result = _approval_service(ctx, db).approve_pack(ctx.user, pack_id, payload)
    db.commit()
    return result


@router.post("/packs/{pack_id}/reject", response_model=PackDetailResponse)
def reject_pack(
    pack_id: uuid.UUID,
    payload: RejectRequest | None = None,
    ctx: TenantContext = Depends(require_module("marketing")),
    db: Session = Depends(get_db),
) -> PackDetailResponse:
    result = _approval_service(ctx, db).reject_pack(ctx.user, pack_id, payload)
    db.commit()
    return result


@router.get("/packs/{pack_id}/texts", response_model=list[PackTextResponse])
def list_pack_texts(
    pack_id: uuid.UUID,
    ctx: TenantContext = Depends(require_module("marketing")),
    db: Session = Depends(get_db),
) -> list[PackTextResponse]:
    return _text_service(ctx, db).list_pack_texts(pack_id)


@router.put("/packs/{pack_id}/texts/{channel}", response_model=PackTextResponse)
def upsert_pack_text(
    pack_id: uuid.UUID,
    channel: MarketingChannel,
    payload: PackTextUpsert,
    ctx: TenantContext = Depends(require_module("marketing")),
    db: Session = Depends(get_db),
) -> PackTextResponse:
    result = _text_service(ctx, db).upsert_pack_text(ctx.user, pack_id, channel, payload)
    db.commit()
    return result


@router.get("/packs/{pack_id}/media", response_model=list[PackMediaAssetResponse])
def list_pack_media(
    pack_id: uuid.UUID,
    ctx: TenantContext = Depends(require_module("marketing")),
    db: Session = Depends(get_db),
) -> list[PackMediaAssetResponse]:
    return _media_service(ctx, db).list_pack_media(pack_id)


@router.post("/packs/{pack_id}/media", response_model=PackMediaAssetResponse, status_code=201)
def attach_pack_media(
    pack_id: uuid.UUID,
    payload: MediaCreate,
    ctx: TenantContext = Depends(require_module("marketing")),
    db: Session = Depends(get_db),
) -> PackMediaAssetResponse:
    result = _media_service(ctx, db).attach_media(ctx.user, pack_id, payload)
    db.commit()
    return result


@router.patch("/media/{asset_id}", response_model=PackMediaAssetResponse)
def update_media_asset(
    asset_id: uuid.UUID,
    payload: MediaUpdate,
    ctx: TenantContext = Depends(require_module("marketing")),
    db: Session = Depends(get_db),
) -> PackMediaAssetResponse:
    result = _media_service(ctx, db).update_media(ctx.user, asset_id, payload)
    db.commit()
    return result


@router.delete("/media/{asset_id}", response_model=PackMediaAssetResponse)
def archive_media_asset(
    asset_id: uuid.UUID,
    ctx: TenantContext = Depends(require_module("marketing")),
    db: Session = Depends(get_db),
) -> PackMediaAssetResponse:
    result = _media_service(ctx, db).archive_media(ctx.user, asset_id)
    db.commit()
    return result
