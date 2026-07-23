import uuid
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, sessionmaker

from app.core.deps import get_db
from app.core.modules import require_module
from app.core.secrets.plaintext import SecretPlaintext
from app.core.secrets.port import SecretVaultPort
from app.core.tenancy import TenantContext
from app.modules.marketing.deps import (
    get_optional_secret_vault,
    get_publish_destination_service,
    get_publishing_connection_service,
    get_publishing_secret_lifecycle_service,
    require_marketing_connection_admin,
    require_marketing_destination_admin,
)
from app.modules.marketing.enums import (
    MarketingChannel,
    MarketingDestinationStatus,
    MarketingPackStatus,
    MarketingPublishDestinationType,
    MarketingPublishingConnectionStatus,
    MarketingPublishingProvider,
    MarketingPublishingTokenStatus,
    MarketingTopicStatus,
)
from app.modules.marketing.schemas import (
    ApproveRequest,
    HistoricalPublishRequest,
    HistoricalPublishResponse,
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
    PublishDestinationCreate,
    PublishDestinationUpdate,
    PublishDestinationView,
    PublishingConnectionCreate,
    PublishingConnectionDisconnect,
    PublishingConnectionSecretWrite,
    PublishingConnectionUpdate,
    PublishingConnectionView,
    RejectRequest,
    TakeTopicPackResponse,
    TakeTopicRequest,
    TopicCreate,
    TopicResponse,
    TopicUpdate,
)
from app.modules.marketing.service.approval import MarketingApprovalService
from app.modules.marketing.service.historical_publish import MarketingHistoricalPublishService
from app.modules.marketing.service.packs import MarketingPackService
from app.modules.marketing.service.media import MarketingMediaService
from app.modules.marketing.service.publish_destinations import (
    MarketingPublishDestinationService,
)
from app.modules.marketing.service.publishing_connections import (
    MarketingPublishingConnectionService,
)
from app.modules.marketing.service.publishing_secret_lifecycle import (
    PublishingSecretLifecycleService,
)
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


def _historical_publish_service(
    ctx: TenantContext,
    db: Session,
) -> MarketingHistoricalPublishService:
    return MarketingHistoricalPublishService(db, ctx.tenant.id)


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


@router.post(
    "/packs/{pack_id}/record-historical-publish",
    response_model=HistoricalPublishResponse,
)
def record_historical_publish(
    pack_id: uuid.UUID,
    payload: HistoricalPublishRequest,
    ctx: TenantContext = Depends(require_module("marketing")),
    db: Session = Depends(get_db),
) -> HistoricalPublishResponse:
    result = _historical_publish_service(ctx, db).record(ctx.user, pack_id, payload)
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


# --- M8-B publishing connections HTTP API ---


@router.get(
    "/publishing-connections",
    response_model=list[PublishingConnectionView],
)
def list_publishing_connections(
    provider: MarketingPublishingProvider | None = None,
    status_filter: MarketingPublishingConnectionStatus | None = Query(
        default=None, alias="status"
    ),
    token_status: MarketingPublishingTokenStatus | None = None,
    ctx: TenantContext = Depends(require_module("marketing")),
    svc: MarketingPublishingConnectionService = Depends(get_publishing_connection_service),
) -> list[PublishingConnectionView]:
    return svc.list_connections(
        provider=provider,
        status=status_filter,
        token_status=token_status,
    )


@router.get(
    "/publishing-connections/{connection_id}",
    response_model=PublishingConnectionView,
)
def get_publishing_connection(
    connection_id: uuid.UUID,
    ctx: TenantContext = Depends(require_module("marketing")),
    svc: MarketingPublishingConnectionService = Depends(get_publishing_connection_service),
) -> PublishingConnectionView:
    return svc.get_connection(connection_id)


@router.post(
    "/publishing-connections",
    response_model=PublishingConnectionView,
    status_code=status.HTTP_201_CREATED,
)
def create_publishing_connection(
    payload: PublishingConnectionCreate,
    ctx: TenantContext = Depends(require_marketing_connection_admin),
    db: Session = Depends(get_db),
    svc: MarketingPublishingConnectionService = Depends(get_publishing_connection_service),
) -> PublishingConnectionView:
    result = svc.create_connection(
        provider=payload.provider,
        account_display_name=payload.account_display_name,
        account_identifier=payload.account_identifier,
        scopes_json=payload.scopes_json,
        metadata_json=payload.metadata_json,
        user_id=ctx.user.id,
    )
    db.commit()
    return result


@router.patch(
    "/publishing-connections/{connection_id}",
    response_model=PublishingConnectionView,
)
def update_publishing_connection(
    connection_id: uuid.UUID,
    payload: PublishingConnectionUpdate,
    ctx: TenantContext = Depends(require_marketing_connection_admin),
    db: Session = Depends(get_db),
    svc: MarketingPublishingConnectionService = Depends(get_publishing_connection_service),
) -> PublishingConnectionView:
    result = svc.update_metadata(
        connection_id,
        account_display_name=payload.account_display_name,
        account_identifier=payload.account_identifier,
        scopes_json=payload.scopes_json,
        metadata_json=payload.metadata_json,
        user_id=ctx.user.id,
    )
    db.commit()
    return result


@router.post(
    "/publishing-connections/{connection_id}/connect",
    response_model=PublishingConnectionView,
)
def connect_publishing_connection(
    connection_id: uuid.UUID,
    payload: PublishingConnectionSecretWrite,
    ctx: TenantContext = Depends(require_marketing_connection_admin),
    lifecycle: PublishingSecretLifecycleService = Depends(
        get_publishing_secret_lifecycle_service
    ),
) -> PublishingConnectionView:
    # Secret material is write-only; never log or echo payload.secret.
    return lifecycle.bind_secret(
        connection_id=connection_id,
        plaintext=SecretPlaintext(payload.secret),
        user_id=ctx.user.id,
    )


@router.post(
    "/publishing-connections/{connection_id}/rotate",
    response_model=PublishingConnectionView,
)
def rotate_publishing_connection(
    connection_id: uuid.UUID,
    payload: PublishingConnectionSecretWrite,
    ctx: TenantContext = Depends(require_marketing_connection_admin),
    lifecycle: PublishingSecretLifecycleService = Depends(
        get_publishing_secret_lifecycle_service
    ),
) -> PublishingConnectionView:
    return lifecycle.rotate_secret(
        connection_id=connection_id,
        plaintext=SecretPlaintext(payload.secret),
        user_id=ctx.user.id,
    )


@router.post(
    "/publishing-connections/{connection_id}/disconnect",
    response_model=PublishingConnectionView,
)
def disconnect_publishing_connection(
    connection_id: uuid.UUID,
    payload: PublishingConnectionDisconnect | None = None,
    ctx: TenantContext = Depends(require_marketing_connection_admin),
    db: Session = Depends(get_db),
    svc: MarketingPublishingConnectionService = Depends(get_publishing_connection_service),
    vault: SecretVaultPort | None = Depends(get_optional_secret_vault),
) -> PublishingConnectionView:
    _ = payload  # optional non-secret reason; not logged
    current = svc.get_connection(connection_id)
    if vault is None:
        if current.has_secret:
            raise HTTPException(status_code=503, detail="secret_vault_unavailable")
        # No vault and no secret: idempotent disconnect via metadata service.
        result = svc.set_connection_status(
            connection_id,
            MarketingPublishingConnectionStatus.NOT_CONNECTED,
            user_id=ctx.user.id,
        )
        db.commit()
        return result

    factory = sessionmaker(autocommit=False, autoflush=False, bind=db.get_bind())
    lifecycle = PublishingSecretLifecycleService(
        ctx.tenant.id,
        session_factory=factory,
        vault=vault,
    )
    return lifecycle.disconnect(connection_id=connection_id, user_id=ctx.user.id)


@router.post(
    "/publishing-connections/{connection_id}/disable",
    response_model=PublishingConnectionView,
)
def disable_publishing_connection(
    connection_id: uuid.UUID,
    ctx: TenantContext = Depends(require_marketing_connection_admin),
    db: Session = Depends(get_db),
    svc: MarketingPublishingConnectionService = Depends(get_publishing_connection_service),
) -> PublishingConnectionView:
    result = svc.set_connection_status(
        connection_id,
        MarketingPublishingConnectionStatus.DISABLED,
        user_id=ctx.user.id,
    )
    db.commit()
    return result


@router.post(
    "/publishing-connections/{connection_id}/enable",
    response_model=PublishingConnectionView,
)
def enable_publishing_connection(
    connection_id: uuid.UUID,
    ctx: TenantContext = Depends(require_marketing_connection_admin),
    db: Session = Depends(get_db),
    svc: MarketingPublishingConnectionService = Depends(get_publishing_connection_service),
) -> PublishingConnectionView:
    result = svc.set_connection_status(
        connection_id,
        MarketingPublishingConnectionStatus.ACTIVE,
        user_id=ctx.user.id,
    )
    db.commit()
    return result


@router.post(
    "/publishing-connections/{connection_id}/health-check",
    response_model=PublishingConnectionView,
)
def health_check_publishing_connection(
    connection_id: uuid.UUID,
    ctx: TenantContext = Depends(require_marketing_connection_admin),
    db: Session = Depends(get_db),
    svc: MarketingPublishingConnectionService = Depends(get_publishing_connection_service),
) -> PublishingConnectionView:
    """Stamp last_checked_at via stub; must never invent token_status=valid."""
    current = svc.get_connection(connection_id)
    result = svc.set_token_status(
        connection_id,
        token_status=current.token_status,
        expires_at=current.expires_at,
        last_checked_at=datetime.now(timezone.utc),
        last_error_code="unchecked_health",
        last_error_message_redacted=current.last_error_message_redacted,
        user_id=ctx.user.id,
    )
    db.commit()
    return result


# --- end M8-B publishing connections HTTP API ---


# --- M8-D2 publish destinations HTTP API ---


@router.get(
    "/publish-destinations",
    response_model=list[PublishDestinationView],
)
def list_publish_destinations(
    status_filter: MarketingDestinationStatus | None = Query(
        default=None, alias="status"
    ),
    publishing_connection_id: uuid.UUID | None = None,
    destination_type: MarketingPublishDestinationType | None = None,
    include_archived: bool = False,
    ctx: TenantContext = Depends(require_module("marketing")),
    svc: MarketingPublishDestinationService = Depends(get_publish_destination_service),
) -> list[PublishDestinationView]:
    return svc.list_destinations(
        status=status_filter,
        publishing_connection_id=publishing_connection_id,
        destination_type=destination_type,
        include_archived=include_archived,
    )


@router.get(
    "/publish-destinations/{destination_id}",
    response_model=PublishDestinationView,
)
def get_publish_destination(
    destination_id: uuid.UUID,
    ctx: TenantContext = Depends(require_module("marketing")),
    svc: MarketingPublishDestinationService = Depends(get_publish_destination_service),
) -> PublishDestinationView:
    return svc.get_destination(destination_id)


@router.post(
    "/publish-destinations",
    response_model=PublishDestinationView,
    status_code=status.HTTP_201_CREATED,
)
def create_publish_destination(
    payload: PublishDestinationCreate,
    ctx: TenantContext = Depends(require_marketing_destination_admin),
    db: Session = Depends(get_db),
    svc: MarketingPublishDestinationService = Depends(get_publish_destination_service),
) -> PublishDestinationView:
    result = svc.create_destination(
        publishing_connection_id=payload.publishing_connection_id,
        destination_type=payload.destination_type,
        external_id=payload.external_id,
        display_name=payload.display_name,
        metadata_json=payload.metadata_json,
        user_id=ctx.user.id,
    )
    db.commit()
    return result


@router.patch(
    "/publish-destinations/{destination_id}",
    response_model=PublishDestinationView,
)
def update_publish_destination(
    destination_id: uuid.UUID,
    payload: PublishDestinationUpdate,
    ctx: TenantContext = Depends(require_marketing_destination_admin),
    db: Session = Depends(get_db),
    svc: MarketingPublishDestinationService = Depends(get_publish_destination_service),
) -> PublishDestinationView:
    result = svc.update_destination(
        destination_id,
        display_name=payload.display_name,
        external_id=payload.external_id,
        metadata_json=payload.metadata_json,
        user_id=ctx.user.id,
    )
    db.commit()
    return result


@router.post(
    "/publish-destinations/{destination_id}/disable",
    response_model=PublishDestinationView,
)
def disable_publish_destination(
    destination_id: uuid.UUID,
    ctx: TenantContext = Depends(require_marketing_destination_admin),
    db: Session = Depends(get_db),
    svc: MarketingPublishDestinationService = Depends(get_publish_destination_service),
) -> PublishDestinationView:
    result = svc.disable_destination(destination_id, user_id=ctx.user.id)
    db.commit()
    return result


@router.post(
    "/publish-destinations/{destination_id}/enable",
    response_model=PublishDestinationView,
)
def enable_publish_destination(
    destination_id: uuid.UUID,
    ctx: TenantContext = Depends(require_marketing_destination_admin),
    db: Session = Depends(get_db),
    svc: MarketingPublishDestinationService = Depends(get_publish_destination_service),
) -> PublishDestinationView:
    result = svc.enable_destination(destination_id, user_id=ctx.user.id)
    db.commit()
    return result


@router.post(
    "/publish-destinations/{destination_id}/validate",
    response_model=PublishDestinationView,
)
def validate_publish_destination(
    destination_id: uuid.UUID,
    ctx: TenantContext = Depends(require_marketing_destination_admin),
    db: Session = Depends(get_db),
    svc: MarketingPublishDestinationService = Depends(get_publish_destination_service),
) -> PublishDestinationView:
    """Structural validation only — never invents provider VALID without adapter."""
    result = svc.validate_destination(destination_id, user_id=ctx.user.id)
    db.commit()
    return result


@router.post(
    "/publish-destinations/{destination_id}/archive",
    response_model=PublishDestinationView,
)
def archive_publish_destination(
    destination_id: uuid.UUID,
    ctx: TenantContext = Depends(require_marketing_destination_admin),
    db: Session = Depends(get_db),
    svc: MarketingPublishDestinationService = Depends(get_publish_destination_service),
) -> PublishDestinationView:
    result = svc.archive_destination(destination_id, user_id=ctx.user.id)
    db.commit()
    return result


# --- end M8-D2 publish destinations HTTP API ---
