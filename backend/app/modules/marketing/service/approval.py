import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.modules.auth.models import User
from app.modules.marketing.enums import (
    ALLOWED_MEDIA_MIME_TYPES,
    DEFAULT_PACK_CHANNELS,
    MarketingApprovalStatus,
    MarketingChannel,
    MarketingPackStatus,
    MarketingPreflightStatus,
    MarketingTopicStatus,
)
from app.modules.marketing.exceptions import (
    MarketingInvalidPackStateError,
    MarketingPreflightNotPassedError,
)
from app.modules.marketing.models import MarketingPublicationPack
from app.modules.marketing.repository import MarketingRepository
from app.modules.marketing.schemas import (
    ApproveRequest,
    PackDetailResponse,
    PreflightCheckItem,
    PreflightIssue,
    PreflightRequest,
    PreflightResponse,
    RejectRequest,
)
from app.modules.marketing.service.packs import MarketingPackService
from app.modules.marketing.service.preflight_rules import (
    PREFLIGHT_REPORT_VERSION,
    append_topic_context_rules,
    build_media_checks,
    build_social_channel_checks,
)

_TELEGRAM_MAX_CHARS = 4096
_PREFLIGHT_ALLOWED_STATUSES = {
    MarketingPackStatus.DRAFT,
    MarketingPackStatus.PREFLIGHT_FAILED,
    MarketingPackStatus.READY_FOR_APPROVAL,
}


class MarketingApprovalService:
    def __init__(self, db: Session, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.repo = MarketingRepository(db)
        self._packs = MarketingPackService(db, tenant_id)

    def run_preflight(
        self,
        user: User,
        pack_id: uuid.UUID,
        payload: PreflightRequest | None = None,
    ) -> PreflightResponse:
        options = payload or PreflightRequest()
        pack = self._get_pack_or_404(pack_id, with_relations=True)
        self._assert_preflight_allowed(pack)

        texts = self.repo.list_pack_texts(self.tenant_id, pack_id)
        media = self.repo.list_pack_media(self.tenant_id, pack_id, include_archived=False)
        text_by_channel = {row.channel: row for row in texts}

        target_channels = options.channels or list(DEFAULT_PACK_CHANNELS)
        errors: list[PreflightIssue] = []
        warnings: list[PreflightIssue] = []
        checks: list[PreflightCheckItem] = []
        channel_eligibility: dict[str, bool] = {}

        # Pack metadata (M6)
        meta_ok = bool(pack.title and pack.slug and pack.planned_date)
        checks.append(
            PreflightCheckItem(
                code="pack_metadata_complete",
                passed=meta_ok,
                message=None if meta_ok else "title, slug and planned_date are required",
            )
        )
        if not meta_ok:
            errors.append(
                PreflightIssue(
                    code="pack_metadata_incomplete",
                    message="Pack metadata incomplete (title, slug, planned_date)",
                )
            )

        # Required text rows exist (M6)
        for channel in DEFAULT_PACK_CHANNELS:
            exists = channel in text_by_channel
            checks.append(
                PreflightCheckItem(
                    code=f"{channel.value}_row_exists",
                    passed=exists,
                    channel=channel.value,
                )
            )
            if not exists:
                errors.append(
                    PreflightIssue(
                        code="channel_text_missing",
                        message=f"No text row for channel {channel.value}",
                        channel=channel.value,
                    )
                )

        non_empty_channels: list[MarketingChannel] = []
        for channel in target_channels:
            row = text_by_channel.get(channel)
            has_text = bool(row and row.text.strip())
            channel_eligibility[channel.value] = has_text
            checks.append(
                PreflightCheckItem(
                    code=f"{channel.value}_text_present",
                    passed=has_text,
                    channel=channel.value,
                    message=None if has_text else "text is empty",
                )
            )
            if has_text:
                non_empty_channels.append(channel)
                if channel == MarketingChannel.TELEGRAM and row and row.char_count > _TELEGRAM_MAX_CHARS:
                    warnings.append(
                        PreflightIssue(
                            code="telegram_text_too_long",
                            message=f"Telegram text exceeds {_TELEGRAM_MAX_CHARS} characters",
                            channel="telegram",
                        )
                    )
                    checks.append(
                        PreflightCheckItem(
                            code="telegram_length_limit",
                            passed=False,
                            channel="telegram",
                            message="char_count > 4096",
                        )
                    )

        if not non_empty_channels:
            errors.append(
                PreflightIssue(
                    code="no_publishable_text",
                    message="At least one channel must have non-empty text",
                )
            )
            checks.append(
                PreflightCheckItem(
                    code="at_least_one_channel_text",
                    passed=False,
                    message="all channel texts are empty",
                )
            )
        else:
            checks.append(
                PreflightCheckItem(
                    code="at_least_one_channel_text",
                    passed=True,
                )
            )

        insights_row = text_by_channel.get(MarketingChannel.INSIGHTS)
        if insights_row and not insights_row.text.strip():
            warnings.append(
                PreflightIssue(
                    code="insights_text_empty",
                    message="Insights text is empty (allowed for MVP)",
                    channel="insights",
                )
            )

        # Topic linked + editorial context (M7-C1)
        topic_context_summary = append_topic_context_rules(
            pack_topic_id=pack.topic_id,
            topic=pack.topic,
            errors=errors,
            warnings=warnings,
            checks=checks,
        )
        if pack.topic_id is not None and pack.topic is not None:
            if pack.topic.status != MarketingTopicStatus.APPROVED:
                errors.append(
                    PreflightIssue(
                        code="topic_not_approved",
                        message="Linked topic is not approved",
                    )
                )
                checks.append(
                    PreflightCheckItem(
                        code="topic_approved",
                        passed=False,
                        message=f"status={pack.topic.status.value}",
                    )
                )
            else:
                checks.append(PreflightCheckItem(code="topic_approved", passed=True))

        # Social length rules (M7-C1)
        channel_checks = build_social_channel_checks(
            text_by_channel=text_by_channel,
            errors=errors,
            warnings=warnings,
            checks=checks,
        )

        # Media MIME (M6 hard) + missing media warning (M7-C1)
        for asset in media:
            mime_ok = asset.mime_type.lower() in ALLOWED_MEDIA_MIME_TYPES
            checks.append(
                PreflightCheckItem(
                    code=f"media_mime_{asset.id}",
                    passed=mime_ok,
                    message=None if mime_ok else f"invalid mime: {asset.mime_type}",
                )
            )
            if not mime_ok:
                errors.append(
                    PreflightIssue(
                        code="media_invalid_mime",
                        message=f"Media asset has invalid mime type: {asset.mime_type}",
                    )
                )
            if asset.width and asset.height and (asset.width != 1080 or asset.height != 1080):
                warnings.append(
                    PreflightIssue(
                        code="media_not_1080",
                        message=f"Media {asset.file_name} is not 1080x1080",
                    )
                )

        media_checks = build_media_checks(media=media, warnings=warnings, checks=checks)

        now = datetime.now(UTC)
        has_errors = len(errors) > 0
        passed = not has_errors
        if has_errors:
            result_status = "failed"
            pack.preflight_status = MarketingPreflightStatus.FAILED
            pack.status = MarketingPackStatus.PREFLIGHT_FAILED
        else:
            result_status = "warning" if warnings else "passed"
            pack.preflight_status = MarketingPreflightStatus.PASSED
            pack.status = MarketingPackStatus.READY_FOR_APPROVAL

        report = {
            "version": PREFLIGHT_REPORT_VERSION,
            "passed": passed,
            "status": result_status,
            "checked_at": now.isoformat(),
            "errors": [e.model_dump() for e in errors],
            "blockers": [e.model_dump() for e in errors],
            "warnings": [w.model_dump() for w in warnings],
            "checks": [c.model_dump() for c in checks],
            "checklist": [c.model_dump() for c in checks],
            "channel_eligibility": channel_eligibility,
            "topic_context_summary": topic_context_summary,
            "channel_checks": channel_checks,
            "media_checks": media_checks,
        }
        pack.preflight_at = now
        pack.preflight_report_json = report
        pack.updated_by_user_id = user.id
        self.db.flush()

        return PreflightResponse(
            pack_id=pack.id,
            status=result_status,
            checked_at=now,
            errors=errors,
            warnings=warnings,
            checks=checks,
            channel_eligibility=channel_eligibility,
            pack_status=pack.status,
            preflight_status=pack.preflight_status,
            approval_status=pack.approval_status,
            version=PREFLIGHT_REPORT_VERSION,
            passed=passed,
            blockers=list(errors),
            checklist=list(checks),
            topic_context_summary=topic_context_summary,
            channel_checks=channel_checks,
            media_checks=media_checks,
        )

    def approve_pack(
        self,
        user: User,
        pack_id: uuid.UUID,
        payload: ApproveRequest | None = None,
    ) -> PackDetailResponse:
        _ = payload
        pack = self._get_pack_or_404(pack_id, with_relations=True)

        if pack.preflight_status != MarketingPreflightStatus.PASSED:
            raise MarketingPreflightNotPassedError()

        if pack.status != MarketingPackStatus.READY_FOR_APPROVAL:
            raise MarketingInvalidPackStateError(
                f"Pack must be ready_for_approval to approve (current: {pack.status.value})"
            )

        now = datetime.now(UTC)
        pack.approval_status = MarketingApprovalStatus.APPROVED
        pack.status = MarketingPackStatus.APPROVED
        pack.approved_at = now
        pack.approved_by_user_id = user.id
        pack.updated_by_user_id = user.id
        self.db.flush()
        return self._packs._to_detail(pack)

    def reject_pack(
        self,
        user: User,
        pack_id: uuid.UUID,
        payload: RejectRequest | None = None,
    ) -> PackDetailResponse:
        pack = self._get_pack_or_404(pack_id, with_relations=True)

        allowed_reject_statuses = {
            MarketingPackStatus.READY_FOR_APPROVAL,
            MarketingPackStatus.APPROVED,
        }
        if pack.status not in allowed_reject_statuses:
            raise MarketingInvalidPackStateError(
                f"Pack cannot be rejected from status {pack.status.value}"
            )

        meta = dict(pack.metadata_json or {})
        if payload and payload.reason:
            meta["reject_reason"] = payload.reason
            meta["rejected_at"] = datetime.now(UTC).isoformat()
        pack.metadata_json = meta
        pack.approval_status = MarketingApprovalStatus.REJECTED
        pack.status = MarketingPackStatus.DRAFT
        pack.approved_at = None
        pack.approved_by_user_id = None
        pack.updated_by_user_id = user.id
        self.db.flush()
        return self._packs._to_detail(pack)

    def _assert_preflight_allowed(self, pack: MarketingPublicationPack) -> None:
        if pack.status in _PREFLIGHT_ALLOWED_STATUSES:
            return
        if pack.approval_status == MarketingApprovalStatus.REJECTED and pack.status == MarketingPackStatus.DRAFT:
            return
        forbidden = {
            MarketingPackStatus.APPROVED,
            MarketingPackStatus.PUBLISHING,
            MarketingPackStatus.PUBLISHED,
            MarketingPackStatus.SCHEDULED,
            MarketingPackStatus.ARCHIVED,
        }
        if pack.status in forbidden:
            raise MarketingInvalidPackStateError(
                f"Preflight not allowed for pack status {pack.status.value}"
            )

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
