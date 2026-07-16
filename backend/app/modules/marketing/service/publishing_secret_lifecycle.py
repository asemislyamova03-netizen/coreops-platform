"""M8-C1a publishing secret lifecycle orchestrator (hardened).

Dedicated UnitOfWork:
  Each mutating operation opens its own Session via session_factory.
  Commit/rollback never touch a caller/request Session.

Vault side-effects are NOT atomic with DB. Pre-commit failures compensate
pending vault versions. Post-commit failures never delete a bound version.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Iterator

from sqlalchemy.orm import Session, sessionmaker

from app.core.enums import AuditAction
from app.core.provider_error_sanitizer import sanitize_provider_error
from app.core.secrets.plaintext import SecretPlaintext
from app.core.secrets.port import (
    SecretStoreMetadata,
    SecretVaultError,
    SecretVaultPort,
    SecretVersionState,
)
from app.core.secrets.ref import SecretRef, SecretRefValidationError, build_secret_ref, parse_secret_ref
from app.modules.audit.recorder import AuditRecorder
from app.modules.marketing.enums import (
    MarketingPublishingConnectionStatus,
    MarketingPublishingTokenStatus,
)
from app.modules.marketing.exceptions import (
    MarketingPublishingConnectionNotFoundError,
    MarketingPublishingConnectionValidationError,
    MarketingPublishingSecretLifecycleError,
)
from app.modules.marketing.models import MarketingPublishingConnection
from app.modules.marketing.repository import MarketingRepository
from app.modules.marketing.schemas import PublishingConnectionView
from app.modules.marketing.service.publishing_health import (
    HealthCheckResult,
    HealthCheckStatus,
    PublishingHealthCheckPort,
    UncheckedHealthCheckStub,
)

_ENTITY_TYPE = "marketing_publishing_connection"
SessionFactory = Callable[[], Session] | sessionmaker[Session]


class PublishingSecretLifecycleService:
    """Lifecycle orchestrator with dedicated Session per operation."""

    def __init__(
        self,
        tenant_id: uuid.UUID,
        *,
        session_factory: SessionFactory,
        vault: SecretVaultPort,
        health_check: PublishingHealthCheckPort | None = None,
    ):
        self.tenant_id = tenant_id
        self._session_factory = session_factory
        self.vault = vault
        self.health_check = health_check or UncheckedHealthCheckStub()

    @contextmanager
    def _uow(self) -> Iterator[Session]:
        db = self._session_factory()
        try:
            yield db
        finally:
            db.close()

    def bind_secret(
        self,
        *,
        connection_id: uuid.UUID,
        plaintext: SecretPlaintext,
        user_id: uuid.UUID | None = None,
    ) -> PublishingConnectionView:
        new_ref: SecretRef | None = None
        db_commit_succeeded = False
        with self._uow() as db:
            try:
                row = self._lock_or_404(db, connection_id)
                if row.secret_ref:
                    raise self._safe_error("secret_already_bound")

                version = 1
                self._cleanup_inactive_orphan_or_raise(
                    tenant_id=self.tenant_id,
                    connection_id=connection_id,
                    version=version,
                )
                new_ref = self.vault.store_secret(
                    tenant_id=self.tenant_id,
                    connection_id=connection_id,
                    version=version,
                    plaintext=plaintext,
                    metadata=SecretStoreMetadata(provider=row.provider.value),
                )
                health = self._run_health(row, new_ref)
                if health.status == HealthCheckStatus.UNHEALTHY:
                    self.vault.delete_version(new_ref)
                    new_ref = None
                    raise self._safe_error(health.error_code or "health_check_failed")

                row.secret_ref = new_ref.render()
                row.secret_version = new_ref.version
                row.secret_bound_at = datetime.now(UTC)
                row.token_status = MarketingPublishingTokenStatus.NOT_CONFIGURED
                row.last_error_code = None
                row.last_error_message_redacted = None
                if user_id is not None:
                    row.updated_by_user_id = user_id

                self._audit(
                    db,
                    action=AuditAction.UPDATE,
                    summary="Publishing connection secret bound",
                    entity_id=row.id,
                    user_id=user_id,
                    changes_json={
                        "operation": "bind_secret",
                        "result": "success",
                        "has_secret_before": False,
                        "has_secret_after": True,
                        "secret_version": new_ref.version,
                        "health_status": health.status.value,
                    },
                )
                db.commit()
                db_commit_succeeded = True
            except MarketingPublishingSecretLifecycleError:
                db.rollback()
                if not db_commit_succeeded and new_ref is not None:
                    self._safe_delete_pending(new_ref)
                raise
            except Exception:
                db.rollback()
                if not db_commit_succeeded and new_ref is not None:
                    self._safe_delete_pending(new_ref)
                raise self._safe_error("db_commit_failed") from None

        return self._post_commit_activate(
            connection_id=connection_id,
            bound_ref=new_ref,
            user_id=user_id,
            operation="bind_secret",
        )

    def rotate_secret(
        self,
        *,
        connection_id: uuid.UUID,
        plaintext: SecretPlaintext,
        user_id: uuid.UUID | None = None,
    ) -> PublishingConnectionView:
        new_ref: SecretRef | None = None
        old_ref: SecretRef | None = None
        old_version: int | None = None
        db_commit_succeeded = False
        with self._uow() as db:
            try:
                row = self._lock_or_404(db, connection_id)
                if not row.secret_ref or row.secret_version is None:
                    raise self._safe_error("secret_not_bound")

                try:
                    old_ref = parse_secret_ref(row.secret_ref)
                    old_ref.assert_ownership(
                        tenant_id=self.tenant_id, connection_id=connection_id
                    )
                except SecretRefValidationError:
                    raise self._safe_error("secret_ref_invalid") from None

                old_version = row.secret_version
                new_version = old_version + 1
                self._cleanup_inactive_orphan_or_raise(
                    tenant_id=self.tenant_id,
                    connection_id=connection_id,
                    version=new_version,
                )
                new_ref = self.vault.store_secret(
                    tenant_id=self.tenant_id,
                    connection_id=connection_id,
                    version=new_version,
                    plaintext=plaintext,
                    metadata=SecretStoreMetadata(provider=row.provider.value),
                )
                health = self._run_health(row, new_ref)
                if health.status == HealthCheckStatus.UNHEALTHY:
                    self.vault.delete_version(new_ref)
                    new_ref = None
                    raise self._safe_error(health.error_code or "health_check_failed")

                row.secret_ref = new_ref.render()
                row.secret_version = new_ref.version
                row.secret_bound_at = datetime.now(UTC)
                row.token_status = MarketingPublishingTokenStatus.NOT_CONFIGURED
                row.last_error_code = None
                row.last_error_message_redacted = None
                if user_id is not None:
                    row.updated_by_user_id = user_id

                self._audit(
                    db,
                    action=AuditAction.UPDATE,
                    summary="Publishing connection secret rotated",
                    entity_id=row.id,
                    user_id=user_id,
                    changes_json={
                        "operation": "rotate_secret",
                        "result": "success",
                        "has_secret_before": True,
                        "has_secret_after": True,
                        "secret_version": new_ref.version,
                        "previous_secret_version": old_version,
                        "health_status": health.status.value,
                    },
                )
                db.commit()
                db_commit_succeeded = True
            except MarketingPublishingSecretLifecycleError:
                db.rollback()
                if not db_commit_succeeded and new_ref is not None:
                    self._safe_delete_pending(new_ref)
                raise
            except Exception:
                db.rollback()
                if not db_commit_succeeded and new_ref is not None:
                    self._safe_delete_pending(new_ref)
                raise self._safe_error("db_commit_failed") from None

        view = self._post_commit_activate(
            connection_id=connection_id,
            bound_ref=new_ref,
            user_id=user_id,
            operation="rotate_secret",
            previous_version=old_version,
        )
        if old_ref is not None:
            self._post_commit_deactivate_previous(
                connection_id=connection_id,
                old_ref=old_ref,
                current_version=new_ref.version if new_ref else None,
                user_id=user_id,
            )
        return view

    def disconnect(
        self,
        *,
        connection_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
    ) -> PublishingConnectionView:
        with self._uow() as db:
            try:
                row = self._lock_or_404(db, connection_id)
                if not row.secret_ref and row.secret_version is None and row.secret_bound_at is None:
                    self._apply_disconnected_status(row, user_id=user_id)
                    self._audit(
                        db,
                        action=AuditAction.UPDATE,
                        summary="Publishing connection disconnect idempotent",
                        entity_id=row.id,
                        user_id=user_id,
                        changes_json={
                            "operation": "disconnect",
                            "result": "idempotent_noop",
                            "has_secret_before": False,
                            "has_secret_after": False,
                        },
                    )
                    db.commit()
                    return self._to_view(row)

                if not row.secret_ref:
                    raise self._safe_error("secret_ref_missing_inconsistent")

                try:
                    ref = parse_secret_ref(row.secret_ref)
                    ref.assert_ownership(
                        tenant_id=self.tenant_id, connection_id=connection_id
                    )
                except SecretRefValidationError:
                    raise self._safe_error("secret_ref_invalid") from None

                before_version = row.secret_version
                if self.vault.version_exists(ref):
                    try:
                        self.vault.deactivate_version(ref)
                    except SecretVaultError:
                        raise self._safe_error("vault_disconnect_failed") from None
                if not self.vault.confirm_inactive(ref):
                    sanitized = sanitize_provider_error(error_code="vault_revoke_failed")
                    row.last_error_code = sanitized.error_code
                    row.last_error_message_redacted = sanitized.message_redacted
                    self._audit(
                        db,
                        action=AuditAction.UPDATE,
                        summary="Publishing connection disconnect vault revoke failed",
                        entity_id=row.id,
                        user_id=user_id,
                        changes_json={
                            "operation": "disconnect",
                            "result": "vault_revoke_failed",
                            "recovery_code": sanitized.error_code,
                            "has_secret_before": True,
                            "has_secret_after": True,
                            "secret_version": before_version,
                        },
                    )
                    db.commit()
                    raise self._safe_error(sanitized.error_code)

                row.secret_ref = None
                row.secret_version = None
                row.secret_bound_at = None
                self._apply_disconnected_status(row, user_id=user_id)
                row.last_error_code = None
                row.last_error_message_redacted = None

                self._audit(
                    db,
                    action=AuditAction.UPDATE,
                    summary="Publishing connection secret disconnected",
                    entity_id=row.id,
                    user_id=user_id,
                    changes_json={
                        "operation": "disconnect",
                        "result": "success",
                        "has_secret_before": True,
                        "has_secret_after": False,
                        "previous_secret_version": before_version,
                    },
                )
                db.commit()
                return self._to_view(row)
            except MarketingPublishingSecretLifecycleError:
                db.rollback()
                raise
            except Exception:
                db.rollback()
                self._record_recovery_code(
                    connection_id=connection_id,
                    user_id=user_id,
                    operation="disconnect",
                    recovery_code="vault_recovery_required",
                    secret_version=None,
                )
                raise self._safe_error("db_commit_failed") from None

    def recover_bound_activation(
        self,
        *,
        connection_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
    ) -> PublishingConnectionView:
        """Idempotent: activate currently bound vault version without plaintext."""
        with self._uow() as db:
            try:
                row = self._lock_or_404(db, connection_id)
                if not row.secret_ref or row.secret_version is None:
                    raise self._safe_error("secret_not_bound")
                try:
                    ref = parse_secret_ref(row.secret_ref)
                    ref.assert_ownership(
                        tenant_id=self.tenant_id, connection_id=connection_id
                    )
                except SecretRefValidationError:
                    raise self._safe_error("secret_ref_invalid") from None

                state = self.vault.get_version_state(ref)
                if state == SecretVersionState.ACTIVE:
                    pass
                elif state in {SecretVersionState.PENDING, None}:
                    if state is None:
                        raise self._safe_error("vault_recovery_required")
                    self.vault.activate_version(ref)
                else:
                    raise self._safe_error("vault_recovery_required")

                # Never mark connection active / token valid from recovery.
                row.token_status = MarketingPublishingTokenStatus.NOT_CONFIGURED
                row.last_error_code = None
                row.last_error_message_redacted = None
                if user_id is not None:
                    row.updated_by_user_id = user_id
                self._audit(
                    db,
                    action=AuditAction.UPDATE,
                    summary="Publishing connection vault activation recovered",
                    entity_id=row.id,
                    user_id=user_id,
                    changes_json={
                        "operation": "recover_bound_activation",
                        "result": "success",
                        "has_secret_before": True,
                        "has_secret_after": True,
                        "secret_version": row.secret_version,
                    },
                )
                db.commit()
                return self._to_view(row)
            except MarketingPublishingSecretLifecycleError:
                db.rollback()
                raise
            except Exception:
                db.rollback()
                raise self._safe_error("vault_recovery_required") from None

    def recover_rotation_previous_deactivate(
        self,
        *,
        connection_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
    ) -> PublishingConnectionView:
        """Idempotent: ensure current bound version active and previous deactivated."""
        with self._uow() as db:
            try:
                row = self._lock_or_404(db, connection_id)
                if not row.secret_ref or row.secret_version is None or row.secret_version < 2:
                    raise self._safe_error("secret_not_bound")
                try:
                    current = parse_secret_ref(row.secret_ref)
                    current.assert_ownership(
                        tenant_id=self.tenant_id, connection_id=connection_id
                    )
                except SecretRefValidationError:
                    raise self._safe_error("secret_ref_invalid") from None

                previous = build_secret_ref(
                    tenant_id=self.tenant_id,
                    connection_id=connection_id,
                    version=row.secret_version - 1,
                )
                state = self.vault.get_version_state(current)
                if state == SecretVersionState.PENDING:
                    self.vault.activate_version(current)
                elif state not in {SecretVersionState.ACTIVE, None}:
                    if state is None:
                        raise self._safe_error("vault_recovery_required")

                if self.vault.version_exists(previous):
                    prev_state = self.vault.get_version_state(previous)
                    if prev_state != SecretVersionState.DEACTIVATED:
                        self.vault.deactivate_version(previous)

                row.last_error_code = None
                row.last_error_message_redacted = None
                if user_id is not None:
                    row.updated_by_user_id = user_id
                self._audit(
                    db,
                    action=AuditAction.UPDATE,
                    summary="Publishing connection rotation recovery completed",
                    entity_id=row.id,
                    user_id=user_id,
                    changes_json={
                        "operation": "recover_rotation",
                        "result": "success",
                        "has_secret_before": True,
                        "has_secret_after": True,
                        "secret_version": row.secret_version,
                        "previous_secret_version": previous.version,
                    },
                )
                db.commit()
                return self._to_view(row)
            except MarketingPublishingSecretLifecycleError:
                db.rollback()
                raise
            except Exception:
                db.rollback()
                raise self._safe_error("vault_recovery_required") from None

    def _post_commit_activate(
        self,
        *,
        connection_id: uuid.UUID,
        bound_ref: SecretRef | None,
        user_id: uuid.UUID | None,
        operation: str,
        previous_version: int | None = None,
    ) -> PublishingConnectionView:
        if bound_ref is None:
            raise self._safe_error("vault_recovery_required")
        try:
            state = self.vault.get_version_state(bound_ref)
            if state == SecretVersionState.ACTIVE:
                pass
            elif state == SecretVersionState.PENDING:
                self.vault.activate_version(bound_ref)
            else:
                raise SecretVaultError("secret_version_inactive")
        except SecretVaultError:
            self._record_recovery_code(
                connection_id=connection_id,
                user_id=user_id,
                operation=operation,
                recovery_code="vault_activation_required",
                secret_version=bound_ref.version,
                previous_version=previous_version,
            )
            raise self._safe_error("vault_activation_required") from None

        with self._uow() as db:
            row = self._lock_or_404(db, connection_id)
            return self._to_view(row)

    def _post_commit_deactivate_previous(
        self,
        *,
        connection_id: uuid.UUID,
        old_ref: SecretRef,
        current_version: int | None,
        user_id: uuid.UUID | None,
    ) -> None:
        try:
            if self.vault.version_exists(old_ref):
                if self.vault.get_version_state(old_ref) != SecretVersionState.DEACTIVATED:
                    self.vault.deactivate_version(old_ref)
        except SecretVaultError:
            self._record_recovery_code(
                connection_id=connection_id,
                user_id=user_id,
                operation="rotate_secret",
                recovery_code="vault_recovery_required",
                secret_version=current_version,
                previous_version=old_ref.version,
            )

    def _cleanup_inactive_orphan_or_raise(
        self,
        *,
        tenant_id: uuid.UUID,
        connection_id: uuid.UUID,
        version: int,
    ) -> None:
        ref = build_secret_ref(
            tenant_id=tenant_id, connection_id=connection_id, version=version
        )
        state = self.vault.get_version_state(ref)
        if state is None:
            return
        if state == SecretVersionState.ACTIVE:
            raise self._safe_error("vault_active_orphan")
        # PENDING or DEACTIVATED orphans may be deleted before retry store.
        self.vault.delete_version(ref)

    def _safe_delete_pending(self, ref: SecretRef) -> None:
        try:
            state = self.vault.get_version_state(ref)
            if state in {SecretVersionState.PENDING, SecretVersionState.DEACTIVATED, None}:
                if state is not None:
                    self.vault.delete_version(ref)
        except SecretVaultError:
            pass

    def _record_recovery_code(
        self,
        *,
        connection_id: uuid.UUID,
        user_id: uuid.UUID | None,
        operation: str,
        recovery_code: str,
        secret_version: int | None,
        previous_version: int | None = None,
    ) -> None:
        sanitized = sanitize_provider_error(error_code=recovery_code)
        try:
            with self._uow() as db:
                row = self._lock_or_404(db, connection_id)
                row.last_error_code = sanitized.error_code
                row.last_error_message_redacted = sanitized.message_redacted
                if user_id is not None:
                    row.updated_by_user_id = user_id
                payload: dict[str, object] = {
                    "operation": operation,
                    "result": "recovery_required",
                    "recovery_code": sanitized.error_code,
                    "has_secret_before": bool(row.secret_ref),
                    "has_secret_after": bool(row.secret_ref),
                }
                if secret_version is not None:
                    payload["secret_version"] = secret_version
                if previous_version is not None:
                    payload["previous_secret_version"] = previous_version
                self._audit(
                    db,
                    action=AuditAction.UPDATE,
                    summary="Publishing connection vault recovery required",
                    entity_id=row.id,
                    user_id=user_id,
                    changes_json=payload,
                )
                db.commit()
        except Exception:
            # Best-effort recovery audit; never raise raw internals.
            pass

    def _run_health(
        self,
        row: MarketingPublishingConnection,
        ref: SecretRef,
    ) -> HealthCheckResult:
        return self.health_check.check_connection_health(
            provider=row.provider,
            secret_ref=ref,
            scopes=list(row.scopes_json or []),
        )

    def _lock_or_404(self, db: Session, connection_id: uuid.UUID) -> MarketingPublishingConnection:
        row = MarketingRepository(db).get_publishing_connection_for_update(
            self.tenant_id, connection_id
        )
        if row is None:
            raise MarketingPublishingConnectionNotFoundError()
        return row

    @staticmethod
    def _apply_disconnected_status(
        row: MarketingPublishingConnection,
        *,
        user_id: uuid.UUID | None,
    ) -> None:
        row.status = MarketingPublishingConnectionStatus.NOT_CONNECTED
        row.token_status = MarketingPublishingTokenStatus.NOT_CONFIGURED
        if user_id is not None:
            row.updated_by_user_id = user_id

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
        db: Session,
        *,
        action: AuditAction,
        summary: str,
        entity_id: uuid.UUID,
        user_id: uuid.UUID | None,
        changes_json: dict[str, object],
    ) -> None:
        sanitized = self._sanitize_audit_payload(changes_json)
        AuditRecorder(db).audit_log(
            action=action,
            summary=summary,
            tenant_id=self.tenant_id,
            user_id=user_id,
            entity_type=_ENTITY_TYPE,
            entity_id=entity_id,
            changes_json=sanitized,
        )

    @staticmethod
    def _sanitize_audit_payload(payload: dict[str, object]) -> dict[str, object]:
        encoded = json.dumps(payload, default=str)
        lowered = encoded.casefold()
        if "secret_ref" in lowered:
            raise MarketingPublishingConnectionValidationError("audit_payload_forbidden_content")
        if "secret://" in lowered:
            raise MarketingPublishingConnectionValidationError("audit_payload_forbidden_content")
        if "bearer " in lowered:
            raise MarketingPublishingConnectionValidationError("audit_payload_forbidden_content")
        return payload

    @staticmethod
    def _safe_error(error_code: str) -> MarketingPublishingSecretLifecycleError:
        sanitized = sanitize_provider_error(error_code=error_code)
        return MarketingPublishingSecretLifecycleError(sanitized.error_code)
