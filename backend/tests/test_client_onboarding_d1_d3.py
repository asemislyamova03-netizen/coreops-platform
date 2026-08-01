"""Tests for generic client self-service onboarding D1–D3."""

from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
from sqlalchemy import func, select

from app.core.config import get_settings
from app.core.enums import ModuleStatus, SecurityEventType, TenantRole
from app.modules.audit.models import SecurityEvent
from app.modules.auth.models import User
from app.modules.module_registry.models import TenantModule
from app.modules.provider.models import ProviderStaff
from app.modules.provider.repository import ProviderRepository
from app.modules.tenants.models import Tenant, UserTenantMembership

# Production security_events.event_type is VARCHAR(15) (Alembic 0011 max label).
SECURITY_EVENT_TYPE_DB_LIMIT = 15
HOST_PROVIDER_SLUG = "flexity-host"
SIGNUP_PATH = "/api/v1/client-onboarding/signup"


@pytest.fixture
def onboarding_settings(monkeypatch):
    monkeypatch.setenv("CLIENT_SELF_SERVICE_ONBOARDING_ENABLED", "true")
    monkeypatch.setenv("CLIENT_ONBOARDING_PROVIDER_SLUG", HOST_PROVIDER_SLUG)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def host_provider(db_session, onboarding_settings):
    company = ProviderRepository(db_session).create_company(
        name="Flexity Host",
        slug=HOST_PROVIDER_SLUG,
    )
    db_session.commit()
    return company


def _payload(**overrides):
    base = {
        "full_name": "Client Owner",
        "email": f"client-{uuid.uuid4().hex[:8]}@example.com",
        "password": "securepass123",
        "tenant_name": "Client Org",
        "tenant_slug": f"client-{uuid.uuid4().hex[:8]}",
    }
    base.update(overrides)
    return base


def _signup(client, payload=None, key=None, **header_extra):
    body = payload or _payload()
    headers = {"Idempotency-Key": key or str(uuid.uuid4()), **header_extra}
    return client.post(SIGNUP_PATH, json=body, headers=headers), body, headers["Idempotency-Key"]


def test_signup_feature_flag_off(client, host_provider, monkeypatch):
    monkeypatch.setenv("CLIENT_SELF_SERVICE_ONBOARDING_ENABLED", "false")
    get_settings.cache_clear()
    response, _, _ = _signup(client)
    assert response.status_code == 403


def test_signup_provider_not_configured(client, monkeypatch):
    monkeypatch.setenv("CLIENT_SELF_SERVICE_ONBOARDING_ENABLED", "true")
    monkeypatch.setenv("CLIENT_ONBOARDING_PROVIDER_SLUG", "missing-provider")
    get_settings.cache_clear()
    response, _, _ = _signup(client)
    assert response.status_code == 503


def test_signup_provider_slug_empty_fails_closed(client, host_provider, monkeypatch):
    monkeypatch.setenv("CLIENT_SELF_SERVICE_ONBOARDING_ENABLED", "true")
    monkeypatch.delenv("CLIENT_ONBOARDING_PROVIDER_SLUG", raising=False)
    monkeypatch.setenv("CLIENT_ONBOARDING_PROVIDER_SLUG", "")
    get_settings.cache_clear()
    # Empty string should fail closed even if a provider exists in DB.
    response, _, _ = _signup(client)
    assert response.status_code == 503


def test_signup_requires_idempotency_key(client, host_provider, onboarding_settings):
    response = client.post(SIGNUP_PATH, json=_payload())
    assert response.status_code == 400
    assert "Idempotency-Key" in response.json()["detail"]


def test_successful_complete_signup(client, db_session, host_provider, onboarding_settings):
    response, payload, _ = _signup(client)
    assert response.status_code == 201, response.text
    data = response.json()

    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == payload["email"].lower()
    assert data["tenant"]["slug"] == payload["tenant_slug"]
    assert data["tenant"]["role"] == "tenant_owner"
    assert data["tenant"]["default_branch_id"]
    assert data["modules_enabled"] == ["parties", "marketing"]
    assert data["redirect_path"] == f"/workspace/{payload['tenant_slug']}/marketing/guide"
    assert "password" not in data
    assert "hashed_password" not in response.text

    user = db_session.scalar(select(User).where(User.email == payload["email"].lower()))
    assert user is not None
    staff = db_session.scalar(select(ProviderStaff).where(ProviderStaff.user_id == user.id))
    assert staff is None

    membership = db_session.scalar(
        select(UserTenantMembership).where(
            UserTenantMembership.user_id == user.id,
            UserTenantMembership.tenant_id == uuid.UUID(data["tenant"]["id"]),
        )
    )
    assert membership is not None
    assert membership.role == TenantRole.TENANT_OWNER

    tenant = db_session.get(Tenant, uuid.UUID(data["tenant"]["id"]))
    assert tenant is not None
    assert tenant.default_branch_id is not None
    assert tenant.provider_company_id == host_provider.id

    active = {
        row.module_code
        for row in db_session.scalars(
            select(TenantModule).where(TenantModule.tenant_id == tenant.id)
        ).all()
        if row.status in {ModuleStatus.ENABLED, ModuleStatus.TRIAL}
    }
    assert active == {"parties", "marketing"}

    me = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {data['access_token']}"},
    )
    assert me.status_code == 200
    me_body = me.json()
    assert me_body["provider"] is None
    assert len(me_body["tenants"]) == 1
    assert me_body["tenants"][0]["role"] == "tenant_owner"


def test_security_event_type_labels_fit_varchar15():
    """Guard production VARCHAR(15) on security_events.event_type (names + values)."""
    for member in SecurityEventType:
        assert len(member.name) <= SECURITY_EVENT_TYPE_DB_LIMIT, member.name
        assert len(member.value) <= SECURITY_EVENT_TYPE_DB_LIMIT, member.value
    assert SecurityEventType.CLIENT_ONB_DONE.value == "client_onb_done"
    assert len(SecurityEventType.CLIENT_ONB_DONE.value) == 15
    assert len(SecurityEventType.CLIENT_ONB_DONE.name) == 15


def test_signup_writes_client_onb_done_security_event(
    client, db_session, host_provider, onboarding_settings
):
    response, payload, _ = _signup(client)
    assert response.status_code == 201, response.text
    data = response.json()
    user_id = uuid.UUID(data["user"]["id"])
    tenant_id = uuid.UUID(data["tenant"]["id"])

    events = list(
        db_session.scalars(
            select(SecurityEvent).where(
                SecurityEvent.event_type == SecurityEventType.CLIENT_ONB_DONE,
                SecurityEvent.user_id == user_id,
                SecurityEvent.tenant_id == tenant_id,
            )
        ).all()
    )
    assert len(events) == 1
    event = events[0]
    assert event.event_type == SecurityEventType.CLIENT_ONB_DONE
    assert event.event_type.value == "client_onb_done"
    assert len(event.event_type.value) <= SECURITY_EVENT_TYPE_DB_LIMIT
    assert len(event.event_type.name) <= SECURITY_EVENT_TYPE_DB_LIMIT
    assert event.email == payload["email"].lower()
    details = event.details_json or {}
    blob = str(details).lower()
    assert "password" not in blob
    assert "token" not in blob
    assert "access_token" not in details
    assert "refresh_token" not in details
    assert "securepass" not in blob


def test_signup_rolls_back_when_security_event_flush_fails(
    client, db_session, host_provider, onboarding_settings
):
    """Atomicity: security_event failure must not leave partial onboarding rows."""
    payload = _payload()
    with patch(
        "app.modules.client_onboarding.service.AuditRecorder.security_event",
        side_effect=RuntimeError("security event boom"),
    ):
        with pytest.raises(RuntimeError, match="security event boom"):
            client.post(
                SIGNUP_PATH,
                json=payload,
                headers={"Idempotency-Key": str(uuid.uuid4())},
            )
    assert (
        db_session.scalar(select(User).where(User.email == payload["email"].lower())) is None
    )
    assert (
        db_session.scalar(select(Tenant).where(Tenant.slug == payload["tenant_slug"])) is None
    )
    assert (
        db_session.scalar(
            select(SecurityEvent).where(SecurityEvent.email == payload["email"].lower())
        )
        is None
    )


def test_provider_module_role_injection_rejected(client, host_provider, onboarding_settings):
    payload = _payload()
    payload["provider_slug"] = "evil"
    payload["module_codes"] = ["crm", "finance"]
    payload["role"] = "provider_owner"
    response = client.post(
        SIGNUP_PATH,
        json=payload,
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    assert response.status_code == 422


def test_duplicate_email(client, host_provider, onboarding_settings):
    first, payload, _ = _signup(client)
    assert first.status_code == 201
    second, _, _ = _signup(
        client,
        payload={**payload, "tenant_slug": f"other-{uuid.uuid4().hex[:6]}"},
    )
    assert second.status_code == 409
    assert "Email" in second.json()["detail"]


def test_duplicate_tenant_slug(client, host_provider, onboarding_settings):
    first, payload, _ = _signup(client)
    assert first.status_code == 201
    second, _, _ = _signup(
        client,
        payload={
            **payload,
            "email": f"other-{uuid.uuid4().hex[:8]}@example.com",
        },
    )
    assert second.status_code == 409
    assert "slug" in second.json()["detail"].lower()


def test_idempotent_replay(client, host_provider, onboarding_settings):
    key = str(uuid.uuid4())
    payload = _payload()
    first = client.post(SIGNUP_PATH, json=payload, headers={"Idempotency-Key": key})
    assert first.status_code == 201
    second = client.post(SIGNUP_PATH, json=payload, headers={"Idempotency-Key": key})
    assert second.status_code == 201
    assert second.json()["user"]["id"] == first.json()["user"]["id"]
    assert second.json()["tenant"]["id"] == first.json()["tenant"]["id"]
    assert second.json()["access_token"]
    assert second.json()["refresh_token"]
    assert second.json()["modules_enabled"] == ["parties", "marketing"]
    # Tokens are re-issued; JWT may match if minted in the same second.
    assert "password" not in second.text


def test_same_key_different_payload(client, host_provider, onboarding_settings):
    key = str(uuid.uuid4())
    first, payload, _ = _signup(client, key=key)
    assert first.status_code == 201
    altered = {**payload, "tenant_name": "Different Name"}
    second = client.post(SIGNUP_PATH, json=altered, headers={"Idempotency-Key": key})
    assert second.status_code == 409
    assert "Idempotency-Key" in second.json()["detail"]


def test_duplicate_submission_different_keys_same_email(
    client, db_session, host_provider, onboarding_settings
):
    """Second submit with a new Idempotency-Key but same email must conflict safely."""
    payload = _payload()
    first = client.post(
        SIGNUP_PATH,
        json=payload,
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    assert first.status_code == 201
    second = client.post(
        SIGNUP_PATH,
        json=payload,
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    assert second.status_code == 409
    users = db_session.scalar(
        select(func.count()).select_from(User).where(User.email == payload["email"].lower())
    )
    assert users == 1


def test_integrity_error_maps_to_conflict_and_rolls_back(
    client, db_session, host_provider, onboarding_settings
):
    from sqlalchemy.exc import IntegrityError

    payload = _payload()

    def boom(*_args, **_kwargs):
        raise IntegrityError("INSERT", {}, Exception("uq_users_email"))

    with patch(
        "app.modules.client_onboarding.service.UserRepository.create",
        side_effect=boom,
    ):
        response, _, _ = _signup(client, payload=payload)
    assert response.status_code == 409
    assert (
        db_session.scalar(select(User).where(User.email == payload["email"].lower())) is None
    )


def test_rollback_on_branch_failure(client, db_session, host_provider, onboarding_settings):
    payload = _payload()
    with patch(
        "app.modules.client_onboarding.service.BranchService.ensure_default_branch",
        side_effect=RuntimeError("branch boom"),
    ):
        with pytest.raises(RuntimeError, match="branch boom"):
            client.post(
                SIGNUP_PATH,
                json=payload,
                headers={"Idempotency-Key": str(uuid.uuid4())},
            )
    assert (
        db_session.scalar(select(User).where(User.email == payload["email"].lower())) is None
    )
    assert (
        db_session.scalar(select(Tenant).where(Tenant.slug == payload["tenant_slug"])) is None
    )


def test_rollback_on_membership_failure(client, db_session, host_provider, onboarding_settings):
    payload = _payload()
    with patch(
        "app.modules.client_onboarding.service.TenantRepository.create_membership",
        side_effect=RuntimeError("membership boom"),
    ):
        with pytest.raises(RuntimeError, match="membership boom"):
            client.post(
                SIGNUP_PATH,
                json=payload,
                headers={"Idempotency-Key": str(uuid.uuid4())},
            )
    assert (
        db_session.scalar(select(User).where(User.email == payload["email"].lower())) is None
    )


def test_rollback_on_missing_module_definition(
    client, db_session, host_provider, onboarding_settings
):
    payload = _payload()
    with patch(
        "app.modules.client_onboarding.service.ModuleRegistryRepository.get_definition",
        return_value=None,
    ):
        response, _, _ = _signup(client, payload=payload)
    assert response.status_code == 503
    assert (
        db_session.scalar(select(User).where(User.email == payload["email"].lower())) is None
    )


def test_rollback_on_module_enable_failure(
    client, db_session, host_provider, onboarding_settings
):
    payload = _payload()
    with patch(
        "app.modules.client_onboarding.service.ModuleRegistryService.enable_modules_ordered",
        side_effect=RuntimeError("enable boom"),
    ):
        with pytest.raises(RuntimeError, match="enable boom"):
            client.post(
                SIGNUP_PATH,
                json=payload,
                headers={"Idempotency-Key": str(uuid.uuid4())},
            )
    assert (
        db_session.scalar(select(User).where(User.email == payload["email"].lower())) is None
    )
    assert (
        db_session.scalar(select(Tenant).where(Tenant.slug == payload["tenant_slug"])) is None
    )


def test_tenant_isolation_between_clients(client, host_provider, onboarding_settings):
    a, payload_a, _ = _signup(client)
    b, payload_b, _ = _signup(client)
    assert a.status_code == 201 and b.status_code == 201
    assert a.json()["tenant"]["id"] != b.json()["tenant"]["id"]

    headers_a = {
        "Authorization": f"Bearer {a.json()['access_token']}",
        "X-Tenant-ID": a.json()["tenant"]["id"],
    }
    headers_b = {
        "Authorization": f"Bearer {b.json()['access_token']}",
        "X-Tenant-ID": b.json()["tenant"]["id"],
    }
    # Each client can read own marketing guides list (empty).
    own = client.get("/api/v1/marketing/guides", headers=headers_a)
    assert own.status_code == 200
    # Cross-tenant header with other user's token should be denied.
    cross = client.get("/api/v1/marketing/guides", headers={
        "Authorization": headers_a["Authorization"],
        "X-Tenant-ID": b.json()["tenant"]["id"],
    })
    assert cross.status_code in {403, 404}
    _ = headers_b, payload_a, payload_b


def test_login_still_works_after_signup(client, host_provider, onboarding_settings):
    response, payload, _ = _signup(client)
    assert response.status_code == 201
    login = client.post(
        "/api/v1/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )
    assert login.status_code == 200
    assert login.json()["access_token"]


def test_bootstrap_register_still_works(client):
    # Regression: existing auth bootstrap path untouched (no onboarding settings required).
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "owner@example.com",
            "password": "securepass123",
            "full_name": "Platform Owner",
            "company_name": "CoreOps Provider",
            "company_slug": "coreops-provider",
        },
    )
    assert response.status_code == 201
