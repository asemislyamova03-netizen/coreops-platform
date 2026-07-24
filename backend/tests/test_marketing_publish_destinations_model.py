"""M8-D1 MarketingPublishDestination model / repository foundation tests."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.core.enums import TenantStatus
from app.modules.marketing.enums import (
    MarketingDestinationStatus,
    MarketingDestinationValidationStatus,
    MarketingPublishDestinationType,
    MarketingPublishingConnectionStatus,
    MarketingPublishingProvider,
    MarketingPublishingTokenStatus,
    destination_capability_enabled,
)
from app.modules.marketing.exceptions import (
    MarketingPublishDestinationHardDeleteForbiddenError,
    MarketingPublishDestinationValidationError,
    MarketingPublishingConnectionNotFoundError,
)
from app.modules.marketing.models import (
    MarketingPublishDestination,
    MarketingPublishingConnection,
)
from app.modules.marketing.repository import MarketingRepository
from app.modules.marketing.schemas import PublishDestinationView
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


def _create_connection(
    db_session,
    tenant_id: uuid.UUID,
    *,
    provider: MarketingPublishingProvider = MarketingPublishingProvider.TELEGRAM,
    display_name: str = "Bot",
) -> MarketingPublishingConnection:
    row = MarketingRepository(db_session).create_publishing_connection(
        tenant_id=tenant_id,
        provider=provider,
        account_display_name=display_name,
        account_identifier="@bot",
        status=MarketingPublishingConnectionStatus.NOT_CONNECTED,
        token_status=MarketingPublishingTokenStatus.NOT_CONFIGURED,
        scopes_json=[],
        metadata_json={},
        created_by_user_id=None,
        updated_by_user_id=None,
    )
    db_session.flush()
    return row


def _to_view(row: MarketingPublishDestination) -> PublishDestinationView:
    return PublishDestinationView.model_validate(row)


def test_destination_capability_tiktok_disabled():
    assert destination_capability_enabled(MarketingPublishDestinationType.TELEGRAM_CHAT) is True
    assert destination_capability_enabled(MarketingPublishDestinationType.TIKTOK_USER) is False


def test_create_read_list_publish_destination(db_session):
    tenant = _create_tenant(db_session, "m8d1-crud")
    conn = _create_connection(db_session, tenant.id)
    repo = MarketingRepository(db_session)

    row = repo.create_publish_destination(
        tenant_id=tenant.id,
        publishing_connection_id=conn.id,
        destination_type=MarketingPublishDestinationType.TELEGRAM_CHAT,
        external_id="-100123",
        display_name="Main channel",
        metadata_json={"note": "allow-list"},
    )
    db_session.flush()

    loaded = repo.get_publish_destination(tenant.id, row.id)
    assert loaded is not None
    assert loaded.external_id == "-100123"
    assert loaded.status == MarketingDestinationStatus.ENABLED
    assert loaded.validation_status == MarketingDestinationValidationStatus.UNCHECKED
    assert loaded.identity_locked_at is None
    assert loaded.provider == MarketingPublishingProvider.TELEGRAM

    listed = repo.list_publish_destinations_by_tenant(tenant.id)
    assert len(listed) == 1
    by_conn = repo.list_publish_destinations_by_connection(tenant.id, conn.id)
    assert len(by_conn) == 1


def test_same_tenant_connection_ok_cross_tenant_rejected(db_session):
    tenant_a = _create_tenant(db_session, "m8d1-a")
    tenant_b = _create_tenant(db_session, "m8d1-b")
    conn_a = _create_connection(db_session, tenant_a.id)
    repo = MarketingRepository(db_session)

    ok = repo.create_publish_destination(
        tenant_id=tenant_a.id,
        publishing_connection_id=conn_a.id,
        destination_type=MarketingPublishDestinationType.TELEGRAM_CHAT,
        external_id="chat-a",
        display_name="A",
    )
    db_session.flush()
    assert ok.tenant_id == tenant_a.id

    with pytest.raises(MarketingPublishingConnectionNotFoundError):
        repo.create_publish_destination(
            tenant_id=tenant_b.id,
            publishing_connection_id=conn_a.id,
            destination_type=MarketingPublishDestinationType.TELEGRAM_CHAT,
            external_id="chat-b",
            display_name="B",
        )


def test_composite_fk_rejects_mismatched_tenant_connection_insert(db_session):
    tenant_a = _create_tenant(db_session, "m8d1-cfk-a")
    tenant_b = _create_tenant(db_session, "m8d1-cfk-b")
    conn_a = _create_connection(db_session, tenant_a.id)
    db_session.commit()

    with pytest.raises(IntegrityError):
        db_session.execute(
            text(
                """
                INSERT INTO marketing_publish_destinations (
                    id, tenant_id, publishing_connection_id, provider, destination_type,
                    external_id, display_name, status, validation_status, metadata_json,
                    created_at, updated_at
                ) VALUES (
                    :id, :tenant_id, :conn_id, 'TELEGRAM', 'TELEGRAM_CHAT',
                    'bad-tenant', 'Bad', 'ENABLED', 'UNCHECKED', '{}',
                    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                )
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "tenant_id": str(tenant_b.id),
                "conn_id": str(conn_a.id),
            },
        )
        db_session.flush()
    db_session.rollback()


def test_uniqueness_among_non_archived(db_session):
    tenant = _create_tenant(db_session, "m8d1-uniq")
    conn = _create_connection(db_session, tenant.id)
    repo = MarketingRepository(db_session)

    first = repo.create_publish_destination(
        tenant_id=tenant.id,
        publishing_connection_id=conn.id,
        destination_type=MarketingPublishDestinationType.TELEGRAM_CHAT,
        external_id="dup-id",
        display_name="One",
    )
    db_session.commit()
    first_id = first.id
    conn_id = conn.id

    repo.create_publish_destination(
        tenant_id=tenant.id,
        publishing_connection_id=conn_id,
        destination_type=MarketingPublishDestinationType.TELEGRAM_CHAT,
        external_id="dup-id",
        display_name="Two",
    )
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()

    first = repo.get_publish_destination(tenant.id, first_id)
    assert first is not None
    repo.archive_publish_destination(tenant.id, first.id)
    db_session.commit()

    replacement = repo.create_publish_destination(
        tenant_id=tenant.id,
        publishing_connection_id=conn_id,
        destination_type=MarketingPublishDestinationType.TELEGRAM_CHAT,
        external_id="dup-id",
        display_name="Replacement",
    )
    db_session.flush()
    assert replacement.id != first_id
    assert replacement.status == MarketingDestinationStatus.ENABLED


def test_disable_enable_archive_lifecycle(db_session):
    tenant = _create_tenant(db_session, "m8d1-life")
    conn = _create_connection(db_session, tenant.id)
    repo = MarketingRepository(db_session)
    row = repo.create_publish_destination(
        tenant_id=tenant.id,
        publishing_connection_id=conn.id,
        destination_type=MarketingPublishDestinationType.TELEGRAM_CHAT,
        external_id="life-1",
        display_name="Life",
    )
    db_session.flush()

    repo.disable_publish_destination(tenant.id, row.id)
    db_session.flush()
    assert row.status == MarketingDestinationStatus.DISABLED

    repo.enable_publish_destination(tenant.id, row.id)
    db_session.flush()
    assert row.status == MarketingDestinationStatus.ENABLED

    repo.archive_publish_destination(tenant.id, row.id)
    db_session.flush()
    assert row.status == MarketingDestinationStatus.ARCHIVED

    with pytest.raises(MarketingPublishDestinationValidationError):
        repo.enable_publish_destination(tenant.id, row.id)


def test_identity_lock_monotonic_across_reset_disable_archive(db_session):
    tenant = _create_tenant(db_session, "m8d1-lock")
    conn = _create_connection(db_session, tenant.id)
    repo = MarketingRepository(db_session)
    row = repo.create_publish_destination(
        tenant_id=tenant.id,
        publishing_connection_id=conn.id,
        destination_type=MarketingPublishDestinationType.TELEGRAM_CHAT,
        external_id="ext-old",
        display_name="Ext",
    )
    db_session.flush()
    assert row.identity_locked_at is None

    # Editable before first VALID.
    repo.update_publish_destination_external_id(tenant.id, row.id, "ext-new")
    db_session.flush()
    assert row.external_id == "ext-new"

    row.apply_structural_validation(
        validation_status=MarketingDestinationValidationStatus.VALID,
    )
    db_session.flush()
    locked_at = row.identity_locked_at
    assert locked_at is not None
    assert row.validation_status == MarketingDestinationValidationStatus.VALID

    with pytest.raises(MarketingPublishDestinationValidationError):
        repo.update_publish_destination_external_id(tenant.id, row.id, "ext-locked")

    # Reset to UNCHECKED preserves lock and keeps external_id immutable.
    row.apply_structural_validation(
        validation_status=MarketingDestinationValidationStatus.UNCHECKED,
    )
    db_session.flush()
    assert row.validation_status == MarketingDestinationValidationStatus.UNCHECKED
    assert row.identity_locked_at == locked_at
    with pytest.raises(MarketingPublishDestinationValidationError):
        repo.update_publish_destination_external_id(tenant.id, row.id, "ext-after-reset")

    # disable / archive must not unlock
    repo.disable_publish_destination(tenant.id, row.id)
    db_session.flush()
    assert row.identity_locked_at == locked_at
    repo.enable_publish_destination(tenant.id, row.id)
    repo.archive_publish_destination(tenant.id, row.id)
    db_session.flush()
    assert row.identity_locked_at == locked_at


def test_tiktok_cannot_enable_or_mark_valid(db_session):
    tenant = _create_tenant(db_session, "m8d1-tt")
    conn = _create_connection(
        db_session,
        tenant.id,
        provider=MarketingPublishingProvider.TIKTOK,
        display_name="TT",
    )
    repo = MarketingRepository(db_session)
    row = repo.create_publish_destination(
        tenant_id=tenant.id,
        publishing_connection_id=conn.id,
        destination_type=MarketingPublishDestinationType.TIKTOK_USER,
        external_id="tt-user",
        display_name="TikTok reserved",
    )
    db_session.flush()
    assert row.status == MarketingDestinationStatus.DISABLED

    with pytest.raises(MarketingPublishDestinationValidationError):
        repo.enable_publish_destination(tenant.id, row.id)

    with pytest.raises(MarketingPublishDestinationValidationError):
        row.apply_structural_validation(
            validation_status=MarketingDestinationValidationStatus.VALID,
        )

    row.apply_structural_validation(
        validation_status=MarketingDestinationValidationStatus.UNAVAILABLE,
        validation_error_code="capability_disabled",
    )
    assert row.validation_status == MarketingDestinationValidationStatus.UNAVAILABLE
    assert row.identity_locked_at is None


def test_connection_delete_restrict_when_destination_exists(db_session):
    tenant = _create_tenant(db_session, "m8d1-fk")
    conn = _create_connection(db_session, tenant.id)
    repo = MarketingRepository(db_session)
    dest = repo.create_publish_destination(
        tenant_id=tenant.id,
        publishing_connection_id=conn.id,
        destination_type=MarketingPublishDestinationType.TELEGRAM_CHAT,
        external_id="fk-chat",
        display_name="FK",
    )
    db_session.commit()
    dest_id = dest.id
    conn_id = conn.id

    parent = db_session.get(MarketingPublishingConnection, conn_id)
    assert parent is not None
    db_session.delete(parent)
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()

    still = repo.get_publish_destination(tenant.id, dest_id)
    assert still is not None
    assert still.publishing_connection_id == conn_id
    remaining = db_session.get(MarketingPublishingConnection, conn_id)
    assert remaining is not None


def test_tenant_delete_restrict_when_destination_exists(db_session):
    tenant = _create_tenant(db_session, "m8d1-tenant-fk")
    conn = _create_connection(db_session, tenant.id)
    repo = MarketingRepository(db_session)
    dest = repo.create_publish_destination(
        tenant_id=tenant.id,
        publishing_connection_id=conn.id,
        destination_type=MarketingPublishDestinationType.TELEGRAM_CHAT,
        external_id="tenant-fk",
        display_name="TenantFK",
    )
    db_session.commit()
    tenant_id = tenant.id
    dest_id = dest.id

    victim = db_session.get(Tenant, tenant_id)
    assert victim is not None
    db_session.delete(victim)
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()

    assert repo.get_publish_destination(tenant_id, dest_id) is not None
    assert db_session.get(Tenant, tenant_id) is not None


def test_hard_delete_forbidden(db_session):
    tenant = _create_tenant(db_session, "m8d1-nodel")
    conn = _create_connection(db_session, tenant.id)
    repo = MarketingRepository(db_session)
    row = repo.create_publish_destination(
        tenant_id=tenant.id,
        publishing_connection_id=conn.id,
        destination_type=MarketingPublishDestinationType.TELEGRAM_CHAT,
        external_id="no-del",
        display_name="NoDel",
    )
    db_session.flush()
    with pytest.raises(MarketingPublishDestinationHardDeleteForbiddenError):
        repo.delete_publish_destination(tenant.id, row.id)


def test_metadata_forbidden_nested_keys_rejected_allowed_passes(db_session):
    tenant = _create_tenant(db_session, "m8d1-meta")
    conn = _create_connection(db_session, tenant.id)
    repo = MarketingRepository(db_session)

    with pytest.raises(MarketingPublishDestinationValidationError) as exc_info:
        repo.create_publish_destination(
            tenant_id=tenant.id,
            publishing_connection_id=conn.id,
            destination_type=MarketingPublishDestinationType.TELEGRAM_CHAT,
            external_id="meta-bad",
            display_name="BadMeta",
            metadata_json={"labels": {"Access_Token": "SHOULD_NOT_APPEAR_IN_ERROR"}},
        )
    assert "SHOULD_NOT_APPEAR_IN_ERROR" not in str(exc_info.value)
    assert "metadata_json_forbidden_key" in str(exc_info.value)

    row = repo.create_publish_destination(
        tenant_id=tenant.id,
        publishing_connection_id=conn.id,
        destination_type=MarketingPublishDestinationType.TELEGRAM_CHAT,
        external_id="meta-ok",
        display_name="OkMeta",
        metadata_json={"public_label": "channel-main", "display_hint": "ok"},
    )
    db_session.flush()
    assert row.metadata_json == {"public_label": "channel-main", "display_hint": "ok"}

    with pytest.raises(MarketingPublishDestinationValidationError):
        repo.update_publish_destination_display(
            tenant.id,
            row.id,
            metadata_json={"nested": {"secret_ref": "nope"}},
        )


def test_view_serialization_has_no_secret_fields(db_session):
    tenant = _create_tenant(db_session, "m8d1-view")
    conn = _create_connection(db_session, tenant.id)
    conn.secret_ref = "vault/secret/should-not-leak"
    conn.secret_version = 1
    conn.secret_bound_at = datetime.now(UTC)
    db_session.flush()

    repo = MarketingRepository(db_session)
    row = repo.create_publish_destination(
        tenant_id=tenant.id,
        publishing_connection_id=conn.id,
        destination_type=MarketingPublishDestinationType.TELEGRAM_CHAT,
        external_id="view-chat",
        display_name="View",
    )
    db_session.flush()

    dumped = _to_view(row).model_dump()
    assert "secret_ref" not in dumped
    assert "token" not in dumped
    assert "access_token" not in dumped
    assert dumped["external_id"] == "view-chat"
    assert dumped["status"] == MarketingDestinationStatus.ENABLED
    assert dumped["publishing_connection_id"] == conn.id
    assert dumped["identity_locked_at"] is None


def test_marketing_models_include_destination(db_engine):
    from sqlalchemy import inspect

    inspector = inspect(db_engine)
    assert "marketing_publish_destinations" in set(inspector.get_table_names())
    assert "marketing_publishing_connections" in set(inspector.get_table_names())
