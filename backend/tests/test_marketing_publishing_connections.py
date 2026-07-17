"""M8-B publishing connection service and tenant isolation tests."""

from __future__ import annotations

import json
import uuid

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from app.core.enums import TenantStatus
from app.modules.audit.models import AuditLog
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
from app.modules.marketing.repository import MarketingRepository
from app.modules.marketing.models import MarketingPublishingConnection
from app.modules.marketing.service.publishing_connections import MarketingPublishingConnectionService
from app.modules.provider.models import ProviderCompany
from app.modules.tenants.models import Tenant


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


def _service(db_session, tenant_id: uuid.UUID) -> MarketingPublishingConnectionService:
    return MarketingPublishingConnectionService(db_session, tenant_id)


def _set_secret_ref_direct(db_session, tenant_id: uuid.UUID, connection_id: uuid.UUID, secret_ref: str) -> None:
    from datetime import UTC, datetime

    row = MarketingRepository(db_session).get_publishing_connection(tenant_id, connection_id)
    assert row is not None
    row.secret_ref = secret_ref
    row.secret_version = 1
    row.secret_bound_at = datetime.now(UTC)
    db_session.flush()


def test_create_connection_defaults_and_has_secret_false(db_session):
    tenant = _create_tenant(db_session, "m8b-create")
    service = _service(db_session, tenant.id)

    view = service.create_connection(
        provider=MarketingPublishingProvider.TELEGRAM,
        account_display_name="Asem Telegram Bot",
    )

    assert view.provider == MarketingPublishingProvider.TELEGRAM
    assert view.status == MarketingPublishingConnectionStatus.NOT_CONNECTED
    assert view.token_status == MarketingPublishingTokenStatus.NOT_CONFIGURED
    assert view.has_secret is False
    assert "secret_ref" not in view.model_dump()


def test_scopes_normalization_dedupes_and_sorts(db_session):
    tenant = _create_tenant(db_session, "m8b-scopes")
    service = _service(db_session, tenant.id)

    view = service.create_connection(
        provider=MarketingPublishingProvider.INSTAGRAM,
        account_display_name="IG Account",
        scopes_json=[" publish ", "publish", "read"],
    )

    assert view.scopes_json == ["publish", "read"]


def test_rejects_token_like_scope(db_session):
    tenant = _create_tenant(db_session, "m8b-token-scope")
    service = _service(db_session, tenant.id)

    with pytest.raises(MarketingPublishingConnectionValidationError):
        service.create_connection(
            provider=MarketingPublishingProvider.TELEGRAM,
            account_display_name="Bot",
            scopes_json=["012345678901234567890123456789012345678901234567890"],
        )


def test_rejects_token_like_metadata_key(db_session):
    tenant = _create_tenant(db_session, "m8b-meta-key")
    service = _service(db_session, tenant.id)

    with pytest.raises(MarketingPublishingConnectionValidationError):
        service.create_connection(
            provider=MarketingPublishingProvider.TELEGRAM,
            account_display_name="Bot",
            metadata_json={"access_token": "label-only"},
        )


def test_rejects_unknown_metadata_key(db_session):
    tenant = _create_tenant(db_session, "m8b-meta-unknown")
    service = _service(db_session, tenant.id)
    with pytest.raises(MarketingPublishingConnectionValidationError):
        service.create_connection(
            provider=MarketingPublishingProvider.TELEGRAM,
            account_display_name="Bot",
            metadata_json={"label": "ok-but-unknown"},
        )


def test_rejects_nested_metadata(db_session):
    tenant = _create_tenant(db_session, "m8b-meta-nested")
    service = _service(db_session, tenant.id)
    with pytest.raises(MarketingPublishingConnectionValidationError):
        service.create_connection(
            provider=MarketingPublishingProvider.TELEGRAM,
            account_display_name="Bot",
            metadata_json={"public_username": {"nested": "value"}},
        )


def test_rejects_wrong_metadata_types(db_session):
    tenant = _create_tenant(db_session, "m8b-meta-type")
    service = _service(db_session, tenant.id)
    with pytest.raises(MarketingPublishingConnectionValidationError):
        service.create_connection(
            provider=MarketingPublishingProvider.TELEGRAM,
            account_display_name="Bot",
            metadata_json={"is_verified": "true"},
        )


def test_accepts_typed_metadata_allow_list(db_session):
    tenant = _create_tenant(db_session, "m8b-meta-allowed")
    service = _service(db_session, tenant.id)
    view = service.create_connection(
        provider=MarketingPublishingProvider.TELEGRAM,
        account_display_name="Bot",
        metadata_json={
            "public_username": "  asem_bot  ",
            "account_type": "  bot  ",
            "is_verified": True,
        },
    )
    assert view.metadata_json == {
        "public_username": "asem_bot",
        "account_type": "bot",
        "is_verified": True,
    }


def test_active_requires_account_identifier(db_session):
    tenant = _create_tenant(db_session, "m8b-active-id")
    service = _service(db_session, tenant.id)

    created = service.create_connection(
        provider=MarketingPublishingProvider.TELEGRAM,
        account_display_name="Draft Bot",
    )

    with pytest.raises(MarketingPublishingConnectionValidationError):
        service.set_connection_status(
            created.id,
            MarketingPublishingConnectionStatus.ACTIVE,
        )


def test_status_and_token_status_are_independent(db_session):
    tenant = _create_tenant(db_session, "m8b-axes")
    service = _service(db_session, tenant.id)

    created = service.create_connection(
        provider=MarketingPublishingProvider.TELEGRAM,
        account_display_name="Bot",
        account_identifier="@asem_bot",
    )

    disabled = service.set_connection_status(
        created.id,
        MarketingPublishingConnectionStatus.DISABLED,
    )
    assert disabled.status == MarketingPublishingConnectionStatus.DISABLED
    assert disabled.token_status == MarketingPublishingTokenStatus.NOT_CONFIGURED

    _set_secret_ref_direct(db_session, tenant.id, created.id, "vault/tenant/telegram/asem")
    rebound = service.get_connection(created.id)
    assert rebound.has_secret is True
    assert rebound.status == MarketingPublishingConnectionStatus.DISABLED


def test_disabled_does_not_clear_secret_ref(db_session):
    tenant = _create_tenant(db_session, "m8b-disable-secret")
    service = _service(db_session, tenant.id)

    created = service.create_connection(
        provider=MarketingPublishingProvider.TELEGRAM,
        account_display_name="Bot",
        account_identifier="@asem_bot",
    )
    _set_secret_ref_direct(db_session, tenant.id, created.id, "vault/tenant/telegram/asem")
    bound = service.get_connection(created.id)
    disabled = service.set_connection_status(
        created.id,
        MarketingPublishingConnectionStatus.DISABLED,
    )

    assert bound.has_secret is True
    assert disabled.has_secret is True


def test_healthy_token_status_requires_secret_ref(db_session):
    tenant = _create_tenant(db_session, "m8b-healthy")
    service = _service(db_session, tenant.id)

    created = service.create_connection(
        provider=MarketingPublishingProvider.TELEGRAM,
        account_display_name="Bot",
        account_identifier="@asem_bot",
    )

    with pytest.raises(MarketingPublishingConnectionValidationError):
        service.set_token_status(created.id, MarketingPublishingTokenStatus.VALID)


def test_partial_unique_allows_multiple_null_identifiers(db_session):
    tenant = _create_tenant(db_session, "m8b-null-dup")
    service = _service(db_session, tenant.id)

    first = service.create_connection(
        provider=MarketingPublishingProvider.TELEGRAM,
        account_display_name="Draft A",
    )
    second = service.create_connection(
        provider=MarketingPublishingProvider.TELEGRAM,
        account_display_name="Draft B",
    )

    assert first.account_identifier is None
    assert second.account_identifier is None


def test_partial_unique_blocks_duplicate_non_null_identifier(db_session):
    tenant = _create_tenant(db_session, "m8b-dup")
    service = _service(db_session, tenant.id)

    service.create_connection(
        provider=MarketingPublishingProvider.TELEGRAM,
        account_display_name="Bot A",
        account_identifier="@same_bot",
    )

    with pytest.raises(MarketingPublishingConnectionDuplicateError):
        service.create_connection(
            provider=MarketingPublishingProvider.TELEGRAM,
            account_display_name="Bot B",
            account_identifier="@same_bot",
        )


def test_tenant_isolation_read_and_update(db_session):
    tenant_a = _create_tenant(db_session, "m8b-tenant-a")
    tenant_b = _create_tenant(db_session, "m8b-tenant-b")
    service_a = _service(db_session, tenant_a.id)
    service_b = _service(db_session, tenant_b.id)

    created = service_a.create_connection(
        provider=MarketingPublishingProvider.TELEGRAM,
        account_display_name="Tenant A Bot",
        account_identifier="@tenant_a_bot",
    )

    assert service_b.list_connections() == []

    with pytest.raises(MarketingPublishingConnectionNotFoundError):
        service_b.get_connection(created.id)

    with pytest.raises(MarketingPublishingConnectionNotFoundError):
        service_b.set_connection_status(
            created.id,
            MarketingPublishingConnectionStatus.DISABLED,
        )


def test_audit_never_contains_secret_ref(db_session):
    tenant = _create_tenant(db_session, "m8b-audit")
    service = _service(db_session, tenant.id)

    created = service.create_connection(
        provider=MarketingPublishingProvider.TELEGRAM,
        account_display_name="Audit Bot",
        account_identifier="@audit_bot",
    )
    _set_secret_ref_direct(db_session, tenant.id, created.id, "vault/tenant/telegram/audit-bot-ref")
    service.update_metadata(
        created.id,
        metadata_json={"public_username": "audit_bot", "account_type": "bot", "is_verified": True},
        scopes_json=["publish", "read"],
    )

    logs = list(
        db_session.scalars(
            select(AuditLog).where(
                AuditLog.tenant_id == tenant.id,
                AuditLog.entity_type == "marketing_publishing_connection",
            )
        ).all()
    )
    assert logs

    for log in logs:
        payload = json.dumps(
            {
                "summary": log.summary,
                "changes_json": log.changes_json,
                "metadata_json": log.metadata_json,
            }
        )
        assert "secret_ref" not in payload.casefold()
        assert "vault/tenant/telegram/audit-bot-ref" not in payload
        assert "\"public_username\": \"audit_bot\"" not in payload
        assert "\"scopes_json\"" not in payload

    metadata_log = next(log for log in logs if "metadata_keys_changed" in log.changes_json)
    assert metadata_log.changes_json["metadata_keys_changed"] == [
        "account_type",
        "is_verified",
        "public_username",
    ]
    assert metadata_log.changes_json["scopes_changed"] is True
    assert "scopes_count" in metadata_log.changes_json


def test_active_connection_is_not_publish_authorization(db_session):
    tenant = _create_tenant(db_session, "m8b-no-publish-ready")
    service = _service(db_session, tenant.id)

    created = service.create_connection(
        provider=MarketingPublishingProvider.TELEGRAM,
        account_display_name="Ready Bot",
        account_identifier="@ready_bot",
    )
    _set_secret_ref_direct(db_session, tenant.id, created.id, "vault/tenant/telegram/ready")
    service.set_token_status(created.id, MarketingPublishingTokenStatus.VALID)
    active = service.set_connection_status(
        created.id,
        MarketingPublishingConnectionStatus.ACTIVE,
    )

    dumped = active.model_dump()
    assert active.status == MarketingPublishingConnectionStatus.ACTIVE
    assert active.token_status == MarketingPublishingTokenStatus.VALID
    assert "publish_ready" not in dumped
    assert "publish_authorized" not in dumped
    assert "allow_list" not in dumped


def test_expired_transition_blocked_pending_m8c_decision(db_session):
    tenant = _create_tenant(db_session, "m8b-expired")
    service = _service(db_session, tenant.id)
    created = service.create_connection(
        provider=MarketingPublishingProvider.TELEGRAM,
        account_display_name="Bot",
        account_identifier="@bot",
    )
    with pytest.raises(MarketingPublishingConnectionValidationError):
        service.set_connection_status(created.id, MarketingPublishingConnectionStatus.EXPIRED)


def test_db_check_active_requires_identifier(db_session):
    tenant = _create_tenant(db_session, "m8b-db-active-check")
    with pytest.raises(IntegrityError):
        db_session.execute(
            text(
                """
                INSERT INTO marketing_publishing_connections
                (id, tenant_id, provider, account_display_name, account_identifier, status, token_status, scopes_json, metadata_json, created_at, updated_at)
                VALUES (:id, :tenant_id, :provider, :display, :identifier, :status, :token_status, :scopes_json, :metadata_json, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "tenant_id": str(tenant.id),
                "provider": "TELEGRAM",
                "display": "Raw Bot",
                "identifier": "   ",
                "status": "ACTIVE",
                "token_status": "NOT_CONFIGURED",
                "scopes_json": "[]",
                "metadata_json": "{}",
            },
        )


def test_db_check_valid_requires_secret_ref(db_session):
    tenant = _create_tenant(db_session, "m8b-db-token-check")
    with pytest.raises(IntegrityError):
        db_session.execute(
            text(
                """
                INSERT INTO marketing_publishing_connections
                (id, tenant_id, provider, account_display_name, account_identifier, status, token_status, scopes_json, metadata_json, created_at, updated_at)
                VALUES (:id, :tenant_id, :provider, :display, :identifier, :status, :token_status, :scopes_json, :metadata_json, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "tenant_id": str(tenant.id),
                "provider": "TELEGRAM",
                "display": "Raw Bot",
                "identifier": "@raw_bot",
                "status": "NOT_CONNECTED",
                "token_status": "VALID",
                "scopes_json": "[]",
                "metadata_json": "{}",
            },
        )


def test_db_check_invalid_enum_value_rejected(db_session):
    tenant = _create_tenant(db_session, "m8b-db-enum-check")
    with pytest.raises(IntegrityError):
        db_session.execute(
            text(
                """
                INSERT INTO marketing_publishing_connections
                (id, tenant_id, provider, account_display_name, account_identifier, status, token_status, scopes_json, metadata_json, created_at, updated_at)
                VALUES (:id, :tenant_id, :provider, :display, :identifier, :status, :token_status, :scopes_json, :metadata_json, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "tenant_id": str(tenant.id),
                "provider": "MASTODON",
                "display": "Raw Bot",
                "identifier": "@raw_bot",
                "status": "NOT_CONNECTED",
                "token_status": "NOT_CONFIGURED",
                "scopes_json": "[]",
                "metadata_json": "{}",
            },
        )


def test_public_service_contract_has_no_secret_ref_setter(db_session):
    tenant = _create_tenant(db_session, "m8b-no-secret-setter")
    service = _service(db_session, tenant.id)
    created = service.create_connection(
        provider=MarketingPublishingProvider.TELEGRAM,
        account_display_name="Bot",
        account_identifier="@bot",
    )
    assert not hasattr(service, "bind_secret_ref")
    assert not hasattr(service, "set_secret_ref")
    assert created.has_secret is False


def test_repository_create_rejects_secret_ref_kwarg(db_session):
    tenant = _create_tenant(db_session, "m8b-repo-contract")
    repo = MarketingRepository(db_session)
    with pytest.raises(TypeError):
        repo.create_publishing_connection(
            tenant_id=tenant.id,
            provider=MarketingPublishingProvider.TELEGRAM,
            account_display_name="Bot",
            account_identifier="@bot",
            status=MarketingPublishingConnectionStatus.NOT_CONNECTED,
            token_status=MarketingPublishingTokenStatus.NOT_CONFIGURED,
            scopes_json=[],
            metadata_json={},
            created_by_user_id=None,
            updated_by_user_id=None,
            secret_ref="vault/ref",
        )
