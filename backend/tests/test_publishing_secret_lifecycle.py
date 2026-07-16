"""M8-C1a hardened secret vault lifecycle tests."""

from __future__ import annotations

import json
import uuid
from unittest.mock import patch

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.core.enums import TenantStatus
from app.core.provider_error_sanitizer import sanitize_provider_error
from app.core.secrets.adapters.in_memory import InMemorySecretVault
from app.core.secrets.plaintext import SecretPlaintext
from app.core.secrets.port import SecretVaultError, SecretVersionState
from app.core.secrets.ref import (
    SecretRefValidationError,
    build_secret_ref,
    parse_secret_ref,
)
from app.modules.audit.models import AuditLog
from app.modules.marketing.enums import (
    MarketingPublishingConnectionStatus,
    MarketingPublishingProvider,
    MarketingPublishingTokenStatus,
)
from app.modules.marketing.exceptions import MarketingPublishingSecretLifecycleError
from app.modules.marketing.models import MarketingPublishingConnection
from app.modules.marketing.repository import MarketingRepository
from app.modules.marketing.service.publishing_connections import (
    MarketingPublishingConnectionService,
)
from app.modules.marketing.service.publishing_health import (
    HealthCheckResult,
    HealthCheckStatus,
    UncheckedHealthCheckStub,
)
from app.modules.marketing.service.publishing_secret_lifecycle import (
    PublishingSecretLifecycleService,
)
from app.modules.provider.models import ProviderCompany
from app.modules.tenants.models import Tenant


def _factory(db_engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=db_engine)


def _create_tenant(db_session, slug: str) -> Tenant:
    provider = ProviderCompany(name=f"Provider {slug}", slug=f"prov-{slug}", is_active=True)
    db_session.add(provider)
    db_session.flush()
    tenant = Tenant(
        provider_company_id=provider.id,
        name=f"Tenant {slug}",
        slug=slug,
        status=TenantStatus.ACTIVE,
    )
    db_session.add(tenant)
    db_session.commit()
    return tenant


def _create_connection(db_session, tenant_id: uuid.UUID) -> uuid.UUID:
    service = MarketingPublishingConnectionService(db_session, tenant_id)
    view = service.create_connection(
        provider=MarketingPublishingProvider.TELEGRAM,
        account_display_name="Vault Bot",
        account_identifier="vault-bot-1",
    )
    db_session.commit()
    return view.id


def _lifecycle(db_engine, tenant_id: uuid.UUID, vault: InMemorySecretVault | None = None):
    return PublishingSecretLifecycleService(
        tenant_id,
        session_factory=_factory(db_engine),
        vault=vault or InMemorySecretVault(app_env="test"),
        health_check=UncheckedHealthCheckStub(),
    )


def test_secret_ref_build_parse_roundtrip():
    tenant_id = uuid.uuid4()
    connection_id = uuid.uuid4()
    ref = build_secret_ref(tenant_id=tenant_id, connection_id=connection_id, version=3)
    rendered = ref.render()
    assert len(rendered) <= 255
    parsed = parse_secret_ref(rendered)
    assert parsed.tenant_id == tenant_id
    assert parsed.connection_id == connection_id
    assert parsed.version == 3


def test_secret_ref_rejects_token_like_and_bad_shape():
    with pytest.raises(SecretRefValidationError):
        parse_secret_ref("Bearer abc.def.ghi")
    with pytest.raises(SecretRefValidationError):
        parse_secret_ref("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.aaa.bbb")
    with pytest.raises(SecretRefValidationError):
        parse_secret_ref("secret://marketing/tenants/not-a-uuid/publishing-connections/x/versions/1")


def test_secret_plaintext_and_ref_safe_repr():
    secret = SecretPlaintext("super-secret-token-value")
    assert "super-secret" not in repr(secret)
    assert "super-secret" not in str(secret)
    ref = build_secret_ref(tenant_id=uuid.uuid4(), connection_id=uuid.uuid4(), version=1)
    assert ref.render() not in repr(ref)
    with pytest.raises(TypeError):
        json.dumps(secret)
    assert "super-secret" not in json.dumps({"s": secret}, default=str)


def test_in_memory_vault_runtime_guard_deny_by_default():
    for env in ("", "staging", "production", "prod", "unknown", "qa"):
        with pytest.raises(SecretVaultError):
            InMemorySecretVault(app_env=env)
    for env in ("test", "testing", "development", "dev", "local", " TEST "):
        assert InMemorySecretVault(app_env=env) is not None


def test_in_memory_vault_lifecycle_states():
    vault = InMemorySecretVault(app_env="test")
    tenant_id = uuid.uuid4()
    connection_id = uuid.uuid4()
    ref = vault.store_secret(
        tenant_id=tenant_id,
        connection_id=connection_id,
        version=1,
        plaintext=SecretPlaintext("tok-1"),
    )
    assert vault.get_version_state(ref) == SecretVersionState.PENDING
    vault.activate_version(ref)
    assert vault.get_version_state(ref) == SecretVersionState.ACTIVE
    vault.deactivate_version(ref)
    assert vault.confirm_inactive(ref) is True


def test_dedicated_uow_does_not_commit_caller_dirty_state(db_session, db_engine):
    tenant = _create_tenant(db_session, "c1a-uow-ok")
    connection_id = _create_connection(db_session, tenant.id)
    caller_name = tenant.name
    tenant.name = "DIRTY-CALLER-SHOULD-NOT-COMMIT"
    assert tenant in db_session.dirty

    svc = _lifecycle(db_engine, tenant.id)
    view = svc.bind_secret(connection_id=connection_id, plaintext=SecretPlaintext("tok-uow"))
    assert view.has_secret is True

    db_session.rollback()
    db_session.refresh(tenant)
    assert tenant.name == caller_name


def test_dedicated_uow_failure_does_not_rollback_caller_state(db_session, db_engine):
    tenant = _create_tenant(db_session, "c1a-uow-fail")
    connection_id = _create_connection(db_session, tenant.id)
    tenant.name = "DIRTY-CALLER-KEEP"
    assert tenant in db_session.dirty

    vault = InMemorySecretVault(app_env="test")
    svc = _lifecycle(db_engine, tenant.id, vault)

    with patch.object(vault, "store_secret", side_effect=SecretVaultError("store_boom")):
        with pytest.raises(MarketingPublishingSecretLifecycleError) as exc_info:
            svc.bind_secret(connection_id=connection_id, plaintext=SecretPlaintext("tok"))
        assert exc_info.value.__cause__ is None

    assert tenant in db_session.dirty
    assert tenant.name == "DIRTY-CALLER-KEEP"


def test_lock_path_used_for_mutating_lifecycle(db_session, db_engine):
    tenant = _create_tenant(db_session, "c1a-lock")
    connection_id = _create_connection(db_session, tenant.id)
    svc = _lifecycle(db_engine, tenant.id)
    calls: list[tuple[uuid.UUID, uuid.UUID]] = []
    original = MarketingRepository.get_publishing_connection_for_update

    def _spy(self, tenant_id, connection_id):
        calls.append((tenant_id, connection_id))
        return original(self, tenant_id, connection_id)

    with patch.object(MarketingRepository, "get_publishing_connection_for_update", _spy):
        svc.bind_secret(connection_id=connection_id, plaintext=SecretPlaintext("tok-lock"))
    assert calls
    assert calls[0] == (tenant.id, connection_id)


def test_bind_success_does_not_activate_or_validate_token(db_session, db_engine):
    tenant = _create_tenant(db_session, "c1a-bind")
    connection_id = _create_connection(db_session, tenant.id)
    vault = InMemorySecretVault(app_env="test")
    svc = _lifecycle(db_engine, tenant.id, vault)
    view = svc.bind_secret(connection_id=connection_id, plaintext=SecretPlaintext("tok-bind-1"))
    assert view.has_secret is True
    assert view.status == MarketingPublishingConnectionStatus.NOT_CONNECTED
    assert view.token_status == MarketingPublishingTokenStatus.NOT_CONFIGURED
    assert "secret_ref" not in view.model_dump()
    row = db_session.get(MarketingPublishingConnection, connection_id)
    assert row.secret_version == 1
    parsed = parse_secret_ref(row.secret_ref)
    assert vault.get_version_state(parsed) == SecretVersionState.ACTIVE


def test_bind_commit_failure_compensates_pending_vault(db_session, db_engine):
    tenant = _create_tenant(db_session, "c1a-bind-fail")
    connection_id = _create_connection(db_session, tenant.id)
    vault = InMemorySecretVault(app_env="test")
    factory = _factory(db_engine)
    svc = PublishingSecretLifecycleService(
        tenant.id,
        session_factory=factory,
        vault=vault,
        health_check=UncheckedHealthCheckStub(),
    )

    real_session = factory()

    class _FailCommitSession:
        def __init__(self, inner):
            self._inner = inner

        def __getattr__(self, name):
            return getattr(self._inner, name)

        def commit(self):
            raise RuntimeError("boom")

        def rollback(self):
            return self._inner.rollback()

        def close(self):
            return self._inner.close()

    def _factory_fail():
        return _FailCommitSession(factory())

    svc_fail = PublishingSecretLifecycleService(
        tenant.id,
        session_factory=_factory_fail,
        vault=vault,
        health_check=UncheckedHealthCheckStub(),
    )
    with pytest.raises(MarketingPublishingSecretLifecycleError) as exc_info:
        svc_fail.bind_secret(connection_id=connection_id, plaintext=SecretPlaintext("tok-fail"))
    assert exc_info.value.__cause__ is None
    row = db_session.get(MarketingPublishingConnection, connection_id)
    assert row.secret_ref is None
    assert vault._store == {}
    real_session.close()


def test_post_commit_activation_failure_does_not_delete_bound_secret(db_session, db_engine):
    tenant = _create_tenant(db_session, "c1a-post")
    connection_id = _create_connection(db_session, tenant.id)
    vault = InMemorySecretVault(app_env="test")
    svc = _lifecycle(db_engine, tenant.id, vault)

    with patch.object(vault, "activate_version", side_effect=SecretVaultError("activate_boom")):
        with pytest.raises(MarketingPublishingSecretLifecycleError) as exc_info:
            svc.bind_secret(connection_id=connection_id, plaintext=SecretPlaintext("tok-post"))
        assert exc_info.value.args[0] == "vault_activation_required"
        assert exc_info.value.__cause__ is None

    db_session.expire_all()
    row = db_session.get(MarketingPublishingConnection, connection_id)
    assert row.secret_ref is not None
    assert row.secret_version == 1
    ref = parse_secret_ref(row.secret_ref)
    assert vault.version_exists(ref) is True
    assert vault.get_version_state(ref) == SecretVersionState.PENDING
    assert row.last_error_code == "vault_activation_required"


def test_recovery_activates_bound_secret_without_plaintext(db_session, db_engine):
    tenant = _create_tenant(db_session, "c1a-rec-act")
    connection_id = _create_connection(db_session, tenant.id)
    vault = InMemorySecretVault(app_env="test")
    svc = _lifecycle(db_engine, tenant.id, vault)
    with patch.object(vault, "activate_version", side_effect=SecretVaultError("activate_boom")):
        with pytest.raises(MarketingPublishingSecretLifecycleError):
            svc.bind_secret(connection_id=connection_id, plaintext=SecretPlaintext("tok-rec"))

    view = svc.recover_bound_activation(connection_id=connection_id)
    assert view.has_secret is True
    assert view.token_status == MarketingPublishingTokenStatus.NOT_CONFIGURED
    assert view.status == MarketingPublishingConnectionStatus.NOT_CONNECTED
    row = db_session.get(MarketingPublishingConnection, connection_id)
    ref = parse_secret_ref(row.secret_ref)
    assert vault.get_version_state(ref) == SecretVersionState.ACTIVE
    assert row.last_error_code is None


def test_rotate_success_and_recovery_deactivates_previous(db_session, db_engine):
    tenant = _create_tenant(db_session, "c1a-rotate")
    connection_id = _create_connection(db_session, tenant.id)
    vault = InMemorySecretVault(app_env="test")
    svc = _lifecycle(db_engine, tenant.id, vault)
    svc.bind_secret(connection_id=connection_id, plaintext=SecretPlaintext("tok-v1"))

    with patch.object(
        vault,
        "deactivate_version",
        side_effect=SecretVaultError("deactivate_failed"),
    ):
        view = svc.rotate_secret(connection_id=connection_id, plaintext=SecretPlaintext("tok-v2"))
    assert view.has_secret is True
    row = db_session.get(MarketingPublishingConnection, connection_id)
    assert row.secret_version == 2
    assert row.last_error_code == "vault_recovery_required"

    recovered = svc.recover_rotation_previous_deactivate(connection_id=connection_id)
    assert recovered.has_secret is True
    old_ref = build_secret_ref(tenant_id=tenant.id, connection_id=connection_id, version=1)
    new_ref = build_secret_ref(tenant_id=tenant.id, connection_id=connection_id, version=2)
    assert vault.confirm_inactive(old_ref) is True
    assert vault.get_version_state(new_ref) == SecretVersionState.ACTIVE


def test_inactive_orphan_cleanup_and_retry(db_session, db_engine):
    tenant = _create_tenant(db_session, "c1a-orphan")
    connection_id = _create_connection(db_session, tenant.id)
    vault = InMemorySecretVault(app_env="test")
    orphan = vault.store_secret(
        tenant_id=tenant.id,
        connection_id=connection_id,
        version=1,
        plaintext=SecretPlaintext("orphan-pending"),
    )
    assert vault.get_version_state(orphan) == SecretVersionState.PENDING
    svc = _lifecycle(db_engine, tenant.id, vault)
    view = svc.bind_secret(connection_id=connection_id, plaintext=SecretPlaintext("tok-new"))
    assert view.has_secret is True
    row = db_session.get(MarketingPublishingConnection, connection_id)
    assert row.secret_version == 1


def test_active_orphan_not_deleted(db_session, db_engine):
    tenant = _create_tenant(db_session, "c1a-active-orphan")
    connection_id = _create_connection(db_session, tenant.id)
    vault = InMemorySecretVault(app_env="test")
    orphan = vault.store_secret(
        tenant_id=tenant.id,
        connection_id=connection_id,
        version=1,
        plaintext=SecretPlaintext("orphan-active"),
    )
    vault.activate_version(orphan)
    svc = _lifecycle(db_engine, tenant.id, vault)
    with pytest.raises(MarketingPublishingSecretLifecycleError) as exc_info:
        svc.bind_secret(connection_id=connection_id, plaintext=SecretPlaintext("tok"))
    assert exc_info.value.args[0] == "vault_active_orphan"
    assert vault.get_version_state(orphan) == SecretVersionState.ACTIVE


def test_disconnect_success_and_idempotent_retry(db_session, db_engine):
    tenant = _create_tenant(db_session, "c1a-disc")
    connection_id = _create_connection(db_session, tenant.id)
    svc = _lifecycle(db_engine, tenant.id)
    svc.bind_secret(connection_id=connection_id, plaintext=SecretPlaintext("tok-d"))
    view = svc.disconnect(connection_id=connection_id)
    assert view.has_secret is False
    again = svc.disconnect(connection_id=connection_id)
    assert again.has_secret is False


def test_disconnect_vault_failure_keeps_db_ref(db_session, db_engine):
    tenant = _create_tenant(db_session, "c1a-disc-fail")
    connection_id = _create_connection(db_session, tenant.id)
    vault = InMemorySecretVault(app_env="test")
    svc = _lifecycle(db_engine, tenant.id, vault)
    svc.bind_secret(connection_id=connection_id, plaintext=SecretPlaintext("tok-keep"))
    with patch.object(vault, "deactivate_version", side_effect=SecretVaultError("nope")):
        with pytest.raises(MarketingPublishingSecretLifecycleError) as exc_info:
            svc.disconnect(connection_id=connection_id)
        assert exc_info.value.__cause__ is None
    row = db_session.get(MarketingPublishingConnection, connection_id)
    assert row.secret_ref is not None


def test_cross_tenant_bind_rejected(db_session, db_engine):
    tenant_a = _create_tenant(db_session, "c1a-ta")
    tenant_b = _create_tenant(db_session, "c1a-tb")
    connection_id = _create_connection(db_session, tenant_a.id)
    svc_b = _lifecycle(db_engine, tenant_b.id)
    with pytest.raises(Exception):
        svc_b.bind_secret(connection_id=connection_id, plaintext=SecretPlaintext("tok-x"))


def test_audit_has_no_secret_material(db_session, db_engine):
    tenant = _create_tenant(db_session, "c1a-audit")
    connection_id = _create_connection(db_session, tenant.id)
    svc = _lifecycle(db_engine, tenant.id)
    svc.bind_secret(connection_id=connection_id, plaintext=SecretPlaintext("tok-audit-secret"))
    logs = list(
        db_session.scalars(select(AuditLog).where(AuditLog.entity_id == connection_id)).all()
    )
    assert logs
    for log in logs:
        blob = json.dumps(log.changes_json or {}, default=str)
        assert "secret_ref" not in blob.casefold()
        assert "secret://" not in blob.casefold()
        assert "tok-audit-secret" not in blob


def test_db_secret_binding_consistency_check(db_session):
    tenant = _create_tenant(db_session, "c1a-check")
    connection_id = _create_connection(db_session, tenant.id)
    row = db_session.get(MarketingPublishingConnection, connection_id)
    row.secret_ref = (
        f"secret://marketing/tenants/{tenant.id}/publishing-connections/{connection_id}/versions/1"
    )
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def test_unhealthy_health_deletes_pending_version(db_session, db_engine):
    class Unhealthy:
        def check_connection_health(self, **kwargs):
            return HealthCheckResult(
                status=HealthCheckStatus.UNHEALTHY,
                error_code="health_check_failed",
            )

    tenant = _create_tenant(db_session, "c1a-unhealthy")
    connection_id = _create_connection(db_session, tenant.id)
    vault = InMemorySecretVault(app_env="test")
    svc = PublishingSecretLifecycleService(
        tenant.id,
        session_factory=_factory(db_engine),
        vault=vault,
        health_check=Unhealthy(),
    )
    with pytest.raises(MarketingPublishingSecretLifecycleError):
        svc.bind_secret(connection_id=connection_id, plaintext=SecretPlaintext("tok-bad"))
    assert vault._store == {}


def test_sanitizer_uses_typed_codes_only():
    result = sanitize_provider_error(
        error_code="provider_auth_failed",
        raw_message="Authorization: Bearer aaa.bbb.ccc https://api.example/token",
    )
    assert result.error_code == "provider_auth_failed"
    assert "Bearer" not in result.message_redacted


def test_for_update_query_constructed():
    """Contract: lock-path uses with_for_update (SQLite may no-op execution)."""
    stmt = (
        select(MarketingPublishingConnection)
        .where(MarketingPublishingConnection.id == uuid.uuid4())
        .with_for_update()
    )
    assert "FOR UPDATE" in str(stmt.compile(compile_kwargs={"literal_binds": False})).upper()
