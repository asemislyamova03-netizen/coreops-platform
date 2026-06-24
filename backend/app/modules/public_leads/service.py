from __future__ import annotations

import logging
import uuid

from fastapi import Request
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.entitlements import EntitlementService
from app.core.enums import (
    AuditAction,
    ContactMethodType,
    PartyStatus,
    PartyType,
    TenantStatus,
    WorkItemParticipantRole,
    WorkItemStatus,
)
from app.core.exceptions import CoreOpsError, PermissionDeniedError
from app.core.modules import ModuleGuard
from app.modules.audit.recorder import AuditRecorder
from app.modules.auth.models import User
from app.modules.parties.models import Party
from app.modules.parties.repository import PartyRepository
from app.modules.public_leads.notifications import (
    PublicLeadTelegramConfig,
    PublicLeadTelegramNotifier,
)
from app.modules.public_leads.schemas import PublicLeadCreate, PublicLeadResponse
from app.modules.tenants.models import Tenant
from app.modules.workflows.models import Pipeline, PipelineStage
from app.modules.workflows.repository import WorkflowRepository

logger = logging.getLogger(__name__)


class PublicLeadConfigError(CoreOpsError):
    """Public lead capture is unavailable because runtime config is invalid."""


class PublicLeadService:
    def __init__(
        self,
        db: Session,
        settings: Settings,
        *,
        notifier: PublicLeadTelegramNotifier | None = None,
    ):
        self.db = db
        self.settings = settings
        self.parties = PartyRepository(db)
        self.workflows = WorkflowRepository(db)
        self.notifier = notifier or PublicLeadTelegramNotifier(
            PublicLeadTelegramConfig(
                bot_token=settings.public_leads_telegram_bot_token,
                chat_id=settings.public_leads_telegram_chat_id,
            )
        )

    def create_lead(
        self,
        payload: PublicLeadCreate,
        *,
        origin: str | None,
        request: Request | None = None,
    ) -> PublicLeadResponse:
        self._assert_enabled()
        self._assert_origin_allowed(origin)
        tenant_id, pipeline_id, stage_id, user_id = self._required_ids()
        user = self._assert_runtime_targets(tenant_id, pipeline_id, stage_id, user_id)
        self._assert_modules_and_features(tenant_id)

        try:
            party = self._create_party(payload, tenant_id=tenant_id, user_id=user.id)
            work_item = self._create_work_item(
                payload,
                tenant_id=tenant_id,
                pipeline_id=pipeline_id,
                stage_id=stage_id,
                user_id=user.id,
                party_id=party.id,
            )
            AuditRecorder(self.db).audit_log(
                action=AuditAction.CREATE,
                summary="Created public inbound lead",
                tenant_id=tenant_id,
                user_id=user.id,
                entity_type="work_item",
                entity_id=work_item.id,
                request=request,
                metadata_json={"source": "public_demo_form", "party_id": str(party.id)},
            )
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        try:
            self.notifier.send(payload, work_item_id=str(work_item.id))
        except Exception:
            logger.exception("Public lead Telegram notification failed")

        return PublicLeadResponse(party_id=party.id, work_item_id=work_item.id)

    def _assert_enabled(self) -> None:
        if not self.settings.public_leads_enabled:
            raise PermissionDeniedError("Public lead capture is disabled")

    def _assert_origin_allowed(self, origin: str | None) -> None:
        if not origin:
            return
        normalized = origin.rstrip("/")
        allowed = self.settings.public_leads_allowed_origin_list
        if normalized not in allowed:
            raise PermissionDeniedError("Origin is not allowed")

    def _required_ids(self) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID]:
        values = (
            self.settings.public_leads_target_tenant_id,
            self.settings.public_leads_pipeline_id,
            self.settings.public_leads_stage_id,
            self.settings.public_leads_created_by_user_id,
        )
        if not all(values):
            raise PublicLeadConfigError("Public lead target IDs are not configured")
        try:
            return tuple(uuid.UUID(str(value)) for value in values)  # type: ignore[return-value]
        except ValueError as exc:
            raise PublicLeadConfigError("Public lead target IDs are invalid") from exc

    def _assert_runtime_targets(
        self,
        tenant_id: uuid.UUID,
        pipeline_id: uuid.UUID,
        stage_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> User:
        tenant = self.db.get(Tenant, tenant_id)
        if not tenant or tenant.status not in {TenantStatus.ACTIVE, TenantStatus.TRIAL}:
            raise PublicLeadConfigError("Public lead target tenant is invalid")

        pipeline = self.db.get(Pipeline, pipeline_id)
        if not pipeline or pipeline.tenant_id != tenant_id:
            raise PublicLeadConfigError("Public lead target pipeline is invalid")

        stage = self.db.get(PipelineStage, stage_id)
        if not stage or stage.pipeline_id != pipeline_id:
            raise PublicLeadConfigError("Public lead target stage is invalid")

        user = self.db.get(User, user_id)
        if not user or not user.is_active:
            raise PublicLeadConfigError("Public lead created-by user is invalid")
        return user

    def _assert_modules_and_features(self, tenant_id: uuid.UUID) -> None:
        guard = ModuleGuard(self.db, tenant_id)
        guard.assert_enabled("parties")
        guard.assert_enabled("crm")
        EntitlementService(self.db, tenant_id).assert_feature("crm.work_items.create")

    def _create_party(
        self,
        payload: PublicLeadCreate,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Party:
        metadata = {
            "party_role": "lead",
            "source": "public_demo_form",
            "source_page": payload.source_page,
            "company": payload.company,
            "preferred_channel": payload.preferred_channel,
            "process_area": payload.process_area,
            "message": payload.message,
            "utm_source": payload.utm_source,
            "utm_medium": payload.utm_medium,
            "utm_campaign": payload.utm_campaign,
            "utm_content": payload.utm_content,
            "utm_term": payload.utm_term,
            "referrer": payload.referrer,
            "consent_accepted": payload.consent_accepted,
        }
        party = self.parties.create_party(
            tenant_id=tenant_id,
            party_type=PartyType.PERSON,
            display_name=payload.name,
            status=PartyStatus.ACTIVE,
            metadata_json={
                key: value for key, value in metadata.items() if value not in (None, "")
            },
            created_by_user_id=user_id,
            updated_by_user_id=user_id,
        )
        if payload.email:
            self.parties.add_contact_method(
                tenant_id=tenant_id,
                party_id=party.id,
                method_type=ContactMethodType.EMAIL,
                value=str(payload.email),
                label="public_form",
                is_primary=True,
            )
        if payload.phone:
            self.parties.add_contact_method(
                tenant_id=tenant_id,
                party_id=party.id,
                method_type=ContactMethodType.PHONE,
                value=payload.phone,
                label="public_form",
                is_primary=payload.email is None,
            )
        return party

    def _create_work_item(
        self,
        payload: PublicLeadCreate,
        *,
        tenant_id: uuid.UUID,
        pipeline_id: uuid.UUID,
        stage_id: uuid.UUID,
        user_id: uuid.UUID,
        party_id: uuid.UUID,
    ):
        item = self.workflows.create_work_item(
            tenant_id=tenant_id,
            pipeline_id=pipeline_id,
            stage_id=stage_id,
            work_item_type="demo_request",
            title=f"Demo request: {payload.name}",
            description=self._build_description(payload),
            primary_party_id=party_id,
            status=WorkItemStatus.OPEN,
            source="public_demo_form",
            custom_fields_json=self._custom_fields(payload),
            created_by_user_id=user_id,
            updated_by_user_id=user_id,
        )
        self.workflows.add_participant(
            tenant_id=tenant_id,
            work_item_id=item.id,
            party_id=party_id,
            role=WorkItemParticipantRole.CLIENT,
        )
        return item

    def _build_description(self, payload: PublicLeadCreate) -> str:
        lines = [
            f"Source page: {payload.source_page}",
            f"Preferred channel: {payload.preferred_channel or ''}",
            f"Process area: {payload.process_area or ''}",
            "",
            payload.message or "",
        ]
        return "\n".join(lines).strip()

    def _custom_fields(self, payload: PublicLeadCreate) -> dict:
        return {
            key: value
            for key, value in {
                "source_page": payload.source_page,
                "utm_source": payload.utm_source,
                "utm_medium": payload.utm_medium,
                "utm_campaign": payload.utm_campaign,
                "utm_content": payload.utm_content,
                "utm_term": payload.utm_term,
                "referrer": payload.referrer,
                "preferred_channel": payload.preferred_channel,
                "process_area": payload.process_area,
                "company": payload.company,
                "message": payload.message,
            }.items()
            if value not in (None, "")
        }
