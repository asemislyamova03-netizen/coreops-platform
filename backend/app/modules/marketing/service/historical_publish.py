import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.modules.auth.models import User
from app.modules.marketing.enums import MarketingPackStatus, MarketingPublishStatus
from app.modules.marketing.models import MarketingPublicationPack
from app.modules.marketing.repository import MarketingRepository
from app.modules.marketing.schemas import (
    HistoricalPublishChannelResult,
    HistoricalPublishRequest,
    HistoricalPublishResponse,
)

_DEFAULT_TARGET_SOCIAL_CHANNELS = {"telegram", "instagram"}


class MarketingHistoricalPublishService:
    """Record verified past publications without invoking an outbound publisher."""

    def __init__(self, db: Session, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.repo = MarketingRepository(db)

    def record(
        self,
        user: User,
        pack_id: uuid.UUID,
        payload: HistoricalPublishRequest,
    ) -> HistoricalPublishResponse:
        pack = self._get_pack_or_404(pack_id)
        if pack.status == MarketingPackStatus.PUBLISHING:
            raise ConflictError("Cannot record historical publish while pack is publishing")

        published_at = payload.published_at or datetime.now(UTC)
        published_at_date = published_at.date().isoformat()
        channel_results: list[HistoricalPublishChannelResult] = []
        logs_created = 0
        skipped_existing = 0

        for channel in payload.channels:
            existing = self.repo.find_historical_publish_log(
                self.tenant_id,
                pack.id,
                channel=channel,
                source=payload.source,
                evidence_ref=payload.evidence_ref,
                published_at_date=published_at_date,
            )
            if existing is not None:
                skipped_existing += 1
                channel_results.append(
                    HistoricalPublishChannelResult(
                        channel=channel,
                        status="existing",
                        log_id=existing.id,
                    )
                )
                continue

            log = self.repo.create_publish_log(
                tenant_id=self.tenant_id,
                pack_id=pack.id,
                queue_item_id=None,
                channel=channel,
                action="historical_record",
                status="recorded",
                external_url=payload.external_url,
                external_post_id=None,
                published_at=published_at,
                error_message=None,
                actor=str(user.id),
                created_at=datetime.now(UTC),
                metadata_json={
                    "source": payload.source,
                    "evidence_ref": payload.evidence_ref,
                    "published_at_date": published_at_date,
                    "note": payload.note,
                    "needs_review": payload.needs_review,
                },
            )
            logs_created += 1
            channel_results.append(
                HistoricalPublishChannelResult(
                    channel=channel,
                    status="created",
                    log_id=log.id,
                )
            )

        if payload.update_publish_status:
            pack.publish_status = self._rollup_publish_status(
                pack,
                target_channels=set(payload.target_social_channels or _DEFAULT_TARGET_SOCIAL_CHANNELS),
            )
            self.db.flush()

        return HistoricalPublishResponse(
            pack_id=pack.id,
            publish_status=pack.publish_status,
            pack_status=pack.status,
            approval_status=pack.approval_status,
            logs_created=logs_created,
            skipped_existing=skipped_existing,
            needs_review=payload.needs_review,
            channel_results=channel_results,
        )

    def _rollup_publish_status(
        self,
        pack: MarketingPublicationPack,
        *,
        target_channels: set[str],
    ) -> MarketingPublishStatus:
        historical_channels = {
            log.channel
            for log in self.repo.list_pack_logs(self.tenant_id, pack.id)
            if (
                log.action == "historical_record"
                and log.status == "recorded"
                and not (log.metadata_json or {}).get("needs_review", False)
            )
        }
        if not target_channels.issubset(historical_channels):
            return MarketingPublishStatus.PARTIAL
        return MarketingPublishStatus.PUBLISHED

    def _get_pack_or_404(self, pack_id: uuid.UUID) -> MarketingPublicationPack:
        pack = self.repo.get_pack(self.tenant_id, pack_id)
        if pack is None:
            raise NotFoundError("Pack not found")
        return pack
