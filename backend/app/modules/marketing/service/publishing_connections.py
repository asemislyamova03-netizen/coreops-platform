"""M8-B tenant-scoped publishing connection service (no HTTP routes)."""

from __future__ import annotations

import json
import uuid
from datetime import datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.enums import AuditAction
from app.modules.audit.recorder import AuditRecorder
from app.modules.marketing.enums import (
    MarketingPublishingConnectionStatus,
    MarketingPublishingProvider,
    MarketingPublishingTokenStatus,
)
from app.modules.marketing.exceptions import (
    MarketingPublishingConnectionDuplicateError,
    MarketingPublishingConnectionNotFoundError,
    MarketingPublishingConnectionValidationError,
)
from app.modules.marketing.models import MarketingPublishingConnection
from app.modules.marketing.repository import MarketingRepository
from app.modules.marketing.schemas import PublishingConnectionView
from app.modules.marketing.service.publishing_connection_validation import (
    normalize_scopes,
    validate_metadata_json,
)

_ENTITY_TYPE = "marketing_publishing_connection"
_HEALTHY_TOKEN_STATUSES = {
    MarketingPublishingTokenStatus.VALID,
    MarketingPublishingTokenStatus.EXPIRING,
}


class MarketingPublishingConnectionService:
    def __init__(self, db: Session, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.repo = MarketingRepository(db)

    def create_connection(
        self,
        *,
        provider: MarketingPublishingProvider,
        account_display_name: str,
        account_identifier: str | None = None,
        scopes_json: list[str] | None = None,
        metadata_json: dict | None = None,
        user_id: uuid.UUID | None = None,
    ) -> PublishingConnectionView:
        display_name = account_display_name.strip()
        if not display_name:
            raise MarketingPublishingConnectionValidationError("account_display_name_required")

        identifier = self._normalize_identifier(account_identifier)
        scopes = normalize_scopes(scopes_json)
        metadata = validate_metadata_json(metadata_json)

        row = self.repo.create_publishing_connection(
            tenant_id=self.tenant_id,
            provider=provider,
            account_display_name=display_name,
            account_identifier=identifier,
            status=MarketingPublishingConnectionStatus.NOT_CONNECTED,
            token_status=MarketingPublishingTokenStatus.NOT_CONFIGURED,
            scopes_json=scopes,
            metadata_json=metadata,
            created_by_user_id=user_id,
            updated_by_user_id=user_id,
        )
        try:
            self.db.flush()
        except IntegrityError as exc:
            self.db.rollback()
            raise MarketingPublishingConnectionDuplicateError() from exc

        self._audit(
            action=AuditAction.CREATE,
            summary=f"Publishing connection created: {provider.value}",
            entity_id=row.id,
            user_id=user_id,
            changes_json={
                "provider": provider.value,
                "account_display_name": display_name,
                "has_secret": False,
            },
        )
        return self._to_view(row)

    def get_connection(self, connection_id: uuid.UUID) -> PublishingConnectionView:
        row = self._get_or_404(connection_id)
        return self._to_view(row)

    def list_connections(
        self,
        *,
        provider: MarketingPublishingProvider | None = None,
        status: MarketingPublishingConnectionStatus | None = None,
        token_status: MarketingPublishingTokenStatus | None = None,
    ) -> list[PublishingConnectionView]:
        rows = self.repo.list_publishing_connections(
            self.tenant_id,
            provider=provider,
            status=status,
            token_status=token_status,
        )
        return [self._to_view(row) for row in rows]

    def update_metadata(
        self,
        connection_id: uuid.UUID,
        *,
        account_display_name: str | None = None,
        account_identifier: str | None = None,
        scopes_json: list[str] | None = None,
        metadata_json: dict | None = None,
        user_id: uuid.UUID | None = None,
    ) -> PublishingConnectionView:
        row = self._get_or_404(connection_id)
        changes: dict[str, object] = {}

        if account_display_name is not None:
            display_name = account_display_name.strip()
            if not display_name:
                raise MarketingPublishingConnectionValidationError("account_display_name_required")
            if row.account_display_name != display_name:
                changes["account_display_name"] = {"before": row.account_display_name, "after": display_name}
                row.account_display_name = display_name

        if account_identifier is not None:
            identifier = self._normalize_identifier(account_identifier)
            if row.account_identifier != identifier:
                changes["account_identifier"] = {
                    "before": row.account_identifier,
                    "after": identifier,
                }
                row.account_identifier = identifier

        if scopes_json is not None:
            scopes = normalize_scopes(scopes_json)
            if row.scopes_json != scopes:
                changes["scopes_count"] = {
                    "before": len(row.scopes_json or []),
                    "after": len(scopes),
                }
                changes["scopes_changed"] = True
                row.scopes_json = scopes

        if metadata_json is not None:
            metadata = validate_metadata_json(metadata_json)
            if row.metadata_json != metadata:
                keys_changed = sorted(
                    set((row.metadata_json or {}).keys()) ^ set(metadata.keys())
                )
                if not keys_changed and row.metadata_json != metadata:
                    keys_changed = sorted(metadata.keys())
                changes["metadata_keys_changed"] = keys_changed
                row.metadata_json = metadata

        if not changes:
            return self._to_view(row)

        row.updated_by_user_id = user_id
        try:
            self.db.flush()
        except IntegrityError as exc:
            self.db.rollback()
            raise MarketingPublishingConnectionDuplicateError() from exc

        self._audit(
            action=AuditAction.UPDATE,
            summary=f"Publishing connection metadata updated: {row.provider.value}",
            entity_id=row.id,
            user_id=user_id,
            changes_json=changes,
        )
        return self._to_view(row)

    def set_connection_status(
        self,
        connection_id: uuid.UUID,
        status: MarketingPublishingConnectionStatus,
        *,
        user_id: uuid.UUID | None = None,
    ) -> PublishingConnectionView:
        row = self._get_or_404(connection_id)
        if row.status == status:
            return self._to_view(row)

        if status == MarketingPublishingConnectionStatus.ACTIVE:
            self._assert_active_ready(row)
        if status == MarketingPublishingConnectionStatus.EXPIRED:
            raise MarketingPublishingConnectionValidationError(
                "expired_status_transition_requires_m8c_decision"
            )

        previous_status = row.status
        row.status = status
        row.updated_by_user_id = user_id
        self.db.flush()

        self._audit(
            action=AuditAction.UPDATE,
            summary=f"Publishing connection status changed: {row.provider.value}",
            entity_id=row.id,
            user_id=user_id,
            changes_json={
                "status": {"before": previous_status.value, "after": status.value},
                "has_secret": bool(row.secret_ref),
            },
        )
        return self._to_view(row)

    def set_token_status(
        self,
        connection_id: uuid.UUID,
        token_status: MarketingPublishingTokenStatus,
        *,
        expires_at: datetime | None = None,
        last_checked_at: datetime | None = None,
        last_error_code: str | None = None,
        last_error_message_redacted: str | None = None,
        user_id: uuid.UUID | None = None,
    ) -> PublishingConnectionView:
        row = self._get_or_404(connection_id)
        self._assert_token_status_allowed(row, token_status)

        changes: dict[str, object] = {}
        if row.token_status != token_status:
            changes["token_status"] = {
                "before": row.token_status.value,
                "after": token_status.value,
            }
            row.token_status = token_status

        if expires_at != row.expires_at:
            changes["expires_at"] = {
                "before": self._dt_iso(row.expires_at),
                "after": self._dt_iso(expires_at),
            }
            row.expires_at = expires_at

        if last_checked_at != row.last_checked_at:
            changes["last_checked_at"] = {
                "before": self._dt_iso(row.last_checked_at),
                "after": self._dt_iso(last_checked_at),
            }
            row.last_checked_at = last_checked_at

        if last_error_code != row.last_error_code:
            changes["last_error_code"] = {
                "before": row.last_error_code,
                "after": last_error_code,
            }
            row.last_error_code = last_error_code

        redacted = self._sanitize_redacted_message(last_error_message_redacted)
        if redacted != row.last_error_message_redacted:
            changes["last_error_message_redacted"] = {
                "before": row.last_error_message_redacted,
                "after": redacted,
            }
            row.last_error_message_redacted = redacted

        if not changes:
            return self._to_view(row)

        row.updated_by_user_id = user_id
        self.db.flush()

        self._audit(
            action=AuditAction.UPDATE,
            summary=f"Publishing connection token status updated: {row.provider.value}",
            entity_id=row.id,
            user_id=user_id,
            changes_json=changes,
        )
        return self._to_view(row)

    def _get_or_404(self, connection_id: uuid.UUID) -> MarketingPublishingConnection:
        row = self.repo.get_publishing_connection(self.tenant_id, connection_id)
        if row is None:
            raise MarketingPublishingConnectionNotFoundError()
        return row

    def _assert_active_ready(self, row: MarketingPublishingConnection) -> None:
        if not row.account_identifier or not row.account_identifier.strip():
            raise MarketingPublishingConnectionValidationError(
                "account_identifier_required_for_active"
            )

    def _assert_token_status_allowed(
        self,
        row: MarketingPublishingConnection,
        token_status: MarketingPublishingTokenStatus,
    ) -> None:
        if token_status in _HEALTHY_TOKEN_STATUSES and not row.secret_ref:
            raise MarketingPublishingConnectionValidationError(
                "secret_ref_required_for_healthy_token_status"
            )

    @staticmethod
    def _normalize_identifier(account_identifier: str | None) -> str | None:
        if account_identifier is None:
            return None
        value = account_identifier.strip()
        return value or None

    @staticmethod
    def _sanitize_redacted_message(message: str | None) -> str | None:
        if message is None:
            return None
        text = message.strip()
        if not text:
            return None
        if "secret_ref" in text.casefold():
            raise MarketingPublishingConnectionValidationError("redacted_message_forbidden_content")
        return text[:512]

    @staticmethod
    def _dt_iso(value: datetime | None) -> str | None:
        return value.isoformat() if value is not None else None

    def _to_view(self, row: MarketingPublishingConnection) -> PublishingConnectionView:
        return PublishingConnectionView(
            id=row.id,
            tenant_id=row.tenant_id,
            provider=row.provider,
            account_display_name=row.account_display_name,
            account_identifier=row.account_identifier,
            status=row.status,
            token_status=row.token_status,
            has_secret=bool(row.secret_ref),
            scopes_json=list(row.scopes_json or []),
            expires_at=row.expires_at,
            last_checked_at=row.last_checked_at,
            last_error_code=row.last_error_code,
            last_error_message_redacted=row.last_error_message_redacted,
            metadata_json=dict(row.metadata_json or {}),
            created_at=row.created_at,
            updated_at=row.updated_at,
            created_by_user_id=row.created_by_user_id,
            updated_by_user_id=row.updated_by_user_id,
        )

    def _audit(
        self,
        *,
        action: AuditAction,
        summary: str,
        entity_id: uuid.UUID,
        user_id: uuid.UUID | None,
        changes_json: dict[str, object],
    ) -> None:
        sanitized = self._sanitize_audit_payload(changes_json)
        AuditRecorder(self.db).audit_log(
            action=action,
            summary=summary,
            tenant_id=self.tenant_id,
            user_id=user_id,
            entity_type=_ENTITY_TYPE,
            entity_id=entity_id,
            changes_json=sanitized,
        )

    @classmethod
    def _sanitize_audit_payload(cls, payload: dict[str, object]) -> dict[str, object]:
        encoded = json.dumps(payload, default=str)
        if "secret_ref" in encoded.casefold():
            raise MarketingPublishingConnectionValidationError("audit_payload_forbidden_content")
        if "metadata_json" in encoded.casefold():
            raise MarketingPublishingConnectionValidationError("audit_payload_forbidden_metadata_values")
        if "scopes_json" in encoded.casefold():
            raise MarketingPublishingConnectionValidationError("audit_payload_forbidden_scope_values")
        return payload
