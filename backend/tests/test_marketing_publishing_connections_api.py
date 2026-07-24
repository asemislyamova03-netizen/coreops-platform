"""M8-B HTTP API tests for Marketing publishing connections."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import app as fastapi_app
from app.modules.audit.models import AuditLog

BASE = "/api/v1/marketing/publishing-connections"
FORBIDDEN_KEYS = {
    "secret_ref",
    "secret_version",
    "secret_bound_at",
    "credentials_json",
    "secret",
    "token",
    "refresh_token",
}
SECRET_MARKERS = ("secret://", "bearer ", "bot_token", "sk-live")


def _register_and_login(client: TestClient, *, suffix: str) -> tuple[dict[str, str], str, str]:
    email = f"pc-{suffix}@example.com"
    password = "securepass123"
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": f"PC Owner {suffix}",
            "company_name": f"PC Provider {suffix}",
            "company_slug": f"pc-provider-{suffix}",
        },
    )
    assert reg.status_code == 201, reg.text
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    tenant = client.post(
        "/api/v1/tenants",
        json={"name": f"PC Tenant {suffix}", "slug": f"pc-tenant-{suffix}"},
        headers=headers,
    )
    assert tenant.status_code == 201, tenant.text
    tenant_id = tenant.json()["id"]
    headers = {**headers, "X-Tenant-ID": tenant_id}
    assert (
        client.post(
            f"/api/v1/tenants/{tenant_id}/modules/parties/enable", headers=headers
        ).status_code
        == 200
    )
    enable = client.post(
        f"/api/v1/tenants/{tenant_id}/modules/marketing/enable", headers=headers
    )
    assert enable.status_code == 200, enable.text
    return headers, tenant_id, email


def _assert_safe_payload(data: dict | list) -> None:
    rows = data if isinstance(data, list) else [data]
    for row in rows:
        assert isinstance(row, dict)
        for key in FORBIDDEN_KEYS:
            assert key not in row, f"forbidden key present: {key}"
        blob = str(row).casefold()
        for marker in SECRET_MARKERS:
            assert marker not in blob
        assert "has_secret" in row
        assert "status" in row
        assert "token_status" in row


def _create_connection(
    client: TestClient,
    headers: dict[str, str],
    *,
    identifier: str | None = "bot-account-1",
    display: str = "Demo Bot",
) -> dict:
    body = {
        "provider": "telegram",
        "account_display_name": display,
        "account_identifier": identifier,
        "scopes_json": ["messages"],
        "metadata_json": {"public_username": "demo_bot"},
    }
    resp = client.post(BASE, headers=headers, json=body)
    assert resp.status_code == 201, resp.text
    _assert_safe_payload(resp.json())
    return resp.json()


def test_owner_create_list_get(client: TestClient):
    headers, _, _ = _register_and_login(client, suffix="owner-crud")
    created = _create_connection(client, headers)
    listed = client.get(BASE, headers=headers)
    assert listed.status_code == 200
    _assert_safe_payload(listed.json())
    assert any(row["id"] == created["id"] for row in listed.json())
    got = client.get(f"{BASE}/{created['id']}", headers=headers)
    assert got.status_code == 200
    _assert_safe_payload(got.json())
    assert got.json()["has_secret"] is False


def test_admin_can_create(client: TestClient, db_session):
    from app.core.security import hash_password
    from app.modules.auth.models import User
    from app.modules.tenants.models import UserTenantMembership
    from app.core.enums import TenantRole

    headers, tenant_id, _ = _register_and_login(client, suffix="admin-create")
    admin = User(
        email="pc-admin-user@example.com",
        full_name="PC Admin",
        hashed_password=hash_password("securepass123"),
        is_active=True,
    )
    db_session.add(admin)
    db_session.flush()
    db_session.add(
        UserTenantMembership(
            tenant_id=uuid.UUID(tenant_id),
            user_id=admin.id,
            role=TenantRole.TENANT_ADMIN,
            is_active=True,
        )
    )
    db_session.commit()
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "pc-admin-user@example.com", "password": "securepass123"},
    )
    assert login.status_code == 200
    admin_headers = {
        "Authorization": f"Bearer {login.json()['access_token']}",
        "X-Tenant-ID": tenant_id,
    }
    created = _create_connection(client, admin_headers, identifier="admin-bot", display="Admin Bot")
    assert created["account_display_name"] == "Admin Bot"


def test_member_read_only_mutations_denied(client: TestClient, db_session):
    from app.core.security import hash_password
    from app.modules.auth.models import User
    from app.modules.tenants.models import UserTenantMembership
    from app.core.enums import TenantRole

    headers, tenant_id, _ = _register_and_login(client, suffix="member-ro")
    created = _create_connection(client, headers, identifier="member-bot")

    member = User(
        email="pc-member-user@example.com",
        full_name="PC Member",
        hashed_password=hash_password("securepass123"),
        is_active=True,
    )
    db_session.add(member)
    db_session.flush()
    db_session.add(
        UserTenantMembership(
            tenant_id=uuid.UUID(tenant_id),
            user_id=member.id,
            role=TenantRole.MEMBER,
            is_active=True,
        )
    )
    db_session.commit()
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "pc-member-user@example.com", "password": "securepass123"},
    )
    assert login.status_code == 200
    member_headers = {
        "Authorization": f"Bearer {login.json()['access_token']}",
        "X-Tenant-ID": tenant_id,
    }

    listed = client.get(BASE, headers=member_headers)
    assert listed.status_code == 200
    got = client.get(f"{BASE}/{created['id']}", headers=member_headers)
    assert got.status_code == 200

    denied = [
        client.post(
            BASE,
            headers=member_headers,
            json={
                "provider": "telegram",
                "account_display_name": "Nope",
                "account_identifier": "nope",
            },
        ),
        client.patch(
            f"{BASE}/{created['id']}",
            headers=member_headers,
            json={"account_display_name": "Nope"},
        ),
        client.post(
            f"{BASE}/{created['id']}/connect",
            headers=member_headers,
            json={"secret": "should-not-bind"},
        ),
        client.post(
            f"{BASE}/{created['id']}/rotate",
            headers=member_headers,
            json={"secret": "should-not-rotate"},
        ),
        client.post(f"{BASE}/{created['id']}/disconnect", headers=member_headers, json={}),
        client.post(f"{BASE}/{created['id']}/disable", headers=member_headers),
        client.post(f"{BASE}/{created['id']}/enable", headers=member_headers),
        client.post(f"{BASE}/{created['id']}/health-check", headers=member_headers),
    ]
    for resp in denied:
        assert resp.status_code == 403, resp.text


def test_unauthenticated_denied(client: TestClient):
    resp = client.get(BASE)
    assert resp.status_code in (401, 403)


def test_module_disabled_denied(client: TestClient):
    email = "pc-nomkt@example.com"
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "securepass123",
            "full_name": "No Mkt",
            "company_name": "No Mkt Co",
            "company_slug": "no-mkt-co",
        },
    )
    assert reg.status_code == 201, reg.text
    token = reg.json()["access_token"]
    tenant = client.post(
        "/api/v1/tenants",
        json={"name": "No Mkt Tenant", "slug": "no-mkt-tenant"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert tenant.status_code == 201, tenant.text
    tid = tenant.json()["id"]
    h = {"Authorization": f"Bearer {token}", "X-Tenant-ID": tid}
    resp = client.get(BASE, headers=h)
    assert resp.status_code == 403, resp.text


def test_cross_tenant_isolation(client: TestClient):
    headers, tenant_a, _ = _register_and_login(client, suffix="iso")
    tenant_b = client.post(
        "/api/v1/tenants",
        json={"name": "PC Tenant iso-b", "slug": "pc-tenant-iso-b"},
        headers=headers,
    )
    assert tenant_b.status_code == 201, tenant_b.text
    tid_b = tenant_b.json()["id"]
    assert (
        client.post(
            f"/api/v1/tenants/{tid_b}/modules/parties/enable", headers=headers
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/v1/tenants/{tid_b}/modules/marketing/enable", headers=headers
        ).status_code
        == 200
    )
    headers_a = {**headers, "X-Tenant-ID": tenant_a}
    headers_b = {**headers, "X-Tenant-ID": tid_b}
    created = _create_connection(client, headers_a, identifier="iso-bot")
    cross = client.get(f"{BASE}/{created['id']}", headers=headers_b)
    assert cross.status_code == 404
    assert cross.json()["detail"] == "publishing_connection_not_found"


def test_connect_rotate_disconnect_lifecycle(client: TestClient, db_session):
    headers, tenant_id, _ = _register_and_login(client, suffix="lifecycle")
    created = _create_connection(client, headers, identifier="life-bot")
    cid = created["id"]

    connect = client.post(
        f"{BASE}/{cid}/connect",
        headers=headers,
        json={"secret": "test-secret-material-v1"},
    )
    assert connect.status_code == 200, connect.text
    body = connect.json()
    _assert_safe_payload(body)
    assert body["has_secret"] is True
    assert body["token_status"] != "valid"

    rotate = client.post(
        f"{BASE}/{cid}/rotate",
        headers=headers,
        json={"secret": "test-secret-material-v2"},
    )
    assert rotate.status_code == 200, rotate.text
    _assert_safe_payload(rotate.json())
    assert rotate.json()["has_secret"] is True

    disconnect = client.post(f"{BASE}/{cid}/disconnect", headers=headers, json={})
    assert disconnect.status_code == 200, disconnect.text
    _assert_safe_payload(disconnect.json())
    assert disconnect.json()["has_secret"] is False
    assert disconnect.json()["token_status"] == "not_configured"

    again = client.post(f"{BASE}/{cid}/disconnect", headers=headers, json={})
    assert again.status_code == 200
    assert again.json()["has_secret"] is False

    # Audit must not contain secret material / secret_ref
    logs = (
        db_session.query(AuditLog)
        .filter(
            AuditLog.tenant_id == uuid.UUID(tenant_id),
            AuditLog.entity_type == "marketing_publishing_connection",
        )
        .all()
    )
    assert logs
    for entry in logs:
        blob = f"{entry.summary} {entry.changes_json}".casefold()
        assert "test-secret-material" not in blob
        assert "secret_ref" not in blob
        assert "secret://" not in blob


def test_connect_twice_conflicts(client: TestClient):
    headers, _, _ = _register_and_login(client, suffix="dbl-connect")
    created = _create_connection(client, headers, identifier="dbl-bot")
    cid = created["id"]
    first = client.post(
        f"{BASE}/{cid}/connect", headers=headers, json={"secret": "once-only-secret"}
    )
    assert first.status_code == 200
    second = client.post(
        f"{BASE}/{cid}/connect", headers=headers, json={"secret": "once-only-secret-2"}
    )
    assert second.status_code == 409
    assert "secret" not in str(second.json()).casefold() or "secret_already" in second.json()["detail"]
    # Ensure plaintext not echoed
    assert "once-only-secret" not in second.text


def test_duplicate_identifier_conflict(client: TestClient):
    headers, _, _ = _register_and_login(client, suffix="dup-id")
    _create_connection(client, headers, identifier="same-id")
    dup = client.post(
        BASE,
        headers=headers,
        json={
            "provider": "telegram",
            "account_display_name": "Other",
            "account_identifier": "same-id",
        },
    )
    assert dup.status_code == 409
    assert dup.json()["detail"] == "publishing_connection_duplicate"


def test_not_found(client: TestClient):
    headers, _, _ = _register_and_login(client, suffix="nf")
    missing = client.get(f"{BASE}/{uuid.uuid4()}", headers=headers)
    assert missing.status_code == 404


def test_health_check_stub_does_not_set_valid(client: TestClient):
    headers, _, _ = _register_and_login(client, suffix="health")
    created = _create_connection(client, headers, identifier="health-bot")
    resp = client.post(f"{BASE}/{created['id']}/health-check", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    _assert_safe_payload(body)
    assert body["token_status"] != "valid"
    assert body["last_error_code"] == "unchecked_health"
    assert body["last_checked_at"] is not None


def test_enable_disable(client: TestClient):
    headers, _, _ = _register_and_login(client, suffix="en-dis")
    created = _create_connection(client, headers, identifier="en-bot")
    enabled = client.post(f"{BASE}/{created['id']}/enable", headers=headers)
    assert enabled.status_code == 200, enabled.text
    assert enabled.json()["status"] == "active"
    disabled = client.post(f"{BASE}/{created['id']}/disable", headers=headers)
    assert disabled.status_code == 200
    assert disabled.json()["status"] == "disabled"


def test_production_like_vault_fail_closed(client: TestClient):
    headers, _, _ = _register_and_login(client, suffix="vault-prod")
    created = _create_connection(client, headers, identifier="prod-bot")
    get_settings.cache_clear()

    def _prod_settings() -> Settings:
        return Settings(app_env="production")

    fastapi_app.dependency_overrides[get_settings] = _prod_settings
    try:
        connect = client.post(
            f"{BASE}/{created['id']}/connect",
            headers=headers,
            json={"secret": "must-not-persist"},
        )
        assert connect.status_code == 503, connect.text
        assert connect.json()["detail"] == "secret_vault_unavailable"
        assert "must-not-persist" not in connect.text

        got = client.get(f"{BASE}/{created['id']}", headers=headers)
        assert got.status_code == 200
        assert got.json()["has_secret"] is False
    finally:
        fastapi_app.dependency_overrides.pop(get_settings, None)
        get_settings.cache_clear()


def test_no_destination_or_publish_routes_for_connections(client: TestClient):
    """Nested connection publish/dry-run stay absent; top-level destinations live in D2."""
    headers, _, _ = _register_and_login(client, suffix="no-dest")
    created = _create_connection(client, headers, identifier="nodest-bot")
    cid = created["id"]
    for path in (
        f"{BASE}/{cid}/destinations",
        f"{BASE}/{cid}/publish",
        f"{BASE}/{cid}/dry-run",
    ):
        assert client.get(path, headers=headers).status_code in (404, 405, 422)
        assert client.post(path, headers=headers, json={}).status_code in (404, 405, 422)


def test_view_schema_excludes_secret_ref():
    from app.modules.marketing.schemas import PublishingConnectionView

    fields = set(PublishingConnectionView.model_fields)
    assert "secret_ref" not in fields
    assert "has_secret" in fields
    assert "secret" not in fields
