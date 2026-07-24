"""M8-D2 HTTP API tests for Marketing publish destinations."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.modules.marketing.enums import MarketingDestinationValidationStatus
from app.modules.marketing.models import MarketingPublishDestination
from app.modules.marketing.repository import MarketingRepository

CONN_BASE = "/api/v1/marketing/publishing-connections"
DEST_BASE = "/api/v1/marketing/publish-destinations"
FORBIDDEN_KEYS = {
    "secret_ref",
    "secret_version",
    "secret_bound_at",
    "credentials_json",
    "credentials",
    "secret",
    "token",
    "access_token",
    "refresh_token",
    "ciphertext",
    "nonce",
    "wrapped_key",
}
SECRET_MARKERS = ("secret://", "bearer ", "bot_token", "sk-live", "ciphertext")


def _register_and_login(client: TestClient, *, suffix: str) -> tuple[dict[str, str], str]:
    email = f"pd-{suffix}@example.com"
    password = "securepass123"
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": f"PD Owner {suffix}",
            "company_name": f"PD Provider {suffix}",
            "company_slug": f"pd-provider-{suffix}",
        },
    )
    assert reg.status_code == 201, reg.text
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    tenant = client.post(
        "/api/v1/tenants",
        json={"name": f"PD Tenant {suffix}", "slug": f"pd-tenant-{suffix}"},
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
    return headers, tenant_id


def _assert_safe_payload(data: dict | list) -> None:
    rows = data if isinstance(data, list) else [data]
    for row in rows:
        assert isinstance(row, dict)
        for key in FORBIDDEN_KEYS:
            assert key not in row, f"forbidden key present: {key}"
        blob = str(row).casefold()
        for marker in SECRET_MARKERS:
            assert marker not in blob
        assert "publishing_connection_id" in row
        assert "external_id" in row
        assert "validation_status" in row
        assert "status" in row


def _create_connection(
    client: TestClient,
    headers: dict[str, str],
    *,
    provider: str = "telegram",
    identifier: str = "dest-bot-1",
    display: str = "Dest Bot",
) -> dict:
    resp = client.post(
        CONN_BASE,
        headers=headers,
        json={
            "provider": provider,
            "account_display_name": display,
            "account_identifier": identifier,
            "scopes_json": ["messages"],
            "metadata_json": {"public_username": "dest_bot"},
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_destination(
    client: TestClient,
    headers: dict[str, str],
    connection_id: str,
    *,
    destination_type: str = "telegram_chat",
    external_id: str = "-100111",
    display_name: str = "Main channel",
    metadata_json: dict | None = None,
) -> dict:
    body = {
        "publishing_connection_id": connection_id,
        "destination_type": destination_type,
        "external_id": external_id,
        "display_name": display_name,
        "metadata_json": metadata_json if metadata_json is not None else {"note": "ok"},
    }
    resp = client.post(DEST_BASE, headers=headers, json=body)
    assert resp.status_code == 201, resp.text
    _assert_safe_payload(resp.json())
    return resp.json()


def _member_headers(client: TestClient, db_session, tenant_id: str, *, suffix: str) -> dict[str, str]:
    from app.core.enums import TenantRole
    from app.core.security import hash_password
    from app.modules.auth.models import User
    from app.modules.tenants.models import UserTenantMembership

    member = User(
        email=f"pd-mem-{suffix}@example.com",
        full_name=f"PD Member {suffix}",
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
        json={"email": f"pd-mem-{suffix}@example.com", "password": "securepass123"},
    )
    assert login.status_code == 200
    return {
        "Authorization": f"Bearer {login.json()['access_token']}",
        "X-Tenant-ID": tenant_id,
    }


def test_owner_create_list_get(client: TestClient):
    headers, _ = _register_and_login(client, suffix="owner-crud")
    conn = _create_connection(client, headers)
    created = _create_destination(client, headers, conn["id"])
    listed = client.get(DEST_BASE, headers=headers)
    assert listed.status_code == 200
    _assert_safe_payload(listed.json())
    assert any(row["id"] == created["id"] for row in listed.json())
    got = client.get(f"{DEST_BASE}/{created['id']}", headers=headers)
    assert got.status_code == 200
    _assert_safe_payload(got.json())
    assert got.json()["external_id"] == "-100111"
    assert got.json()["status"] == "enabled"
    assert got.json()["validation_status"] == "unchecked"


def test_admin_can_mutate(client: TestClient, db_session):
    from app.core.enums import TenantRole
    from app.core.security import hash_password
    from app.modules.auth.models import User
    from app.modules.tenants.models import UserTenantMembership

    headers, tenant_id = _register_and_login(client, suffix="admin-mut")
    conn = _create_connection(client, headers, identifier="admin-dest-bot")
    created = _create_destination(client, headers, conn["id"], external_id="admin-chat")

    admin = User(
        email="pd-admin-user@example.com",
        full_name="PD Admin",
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
        json={"email": "pd-admin-user@example.com", "password": "securepass123"},
    )
    assert login.status_code == 200
    admin_headers = {
        "Authorization": f"Bearer {login.json()['access_token']}",
        "X-Tenant-ID": tenant_id,
    }
    patched = client.patch(
        f"{DEST_BASE}/{created['id']}",
        headers=admin_headers,
        json={"display_name": "Admin renamed"},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["display_name"] == "Admin renamed"


def test_member_read_only_mutations_denied(client: TestClient, db_session):
    headers, tenant_id = _register_and_login(client, suffix="member-ro")
    conn = _create_connection(client, headers, identifier="member-dest-bot")
    created = _create_destination(client, headers, conn["id"], external_id="member-chat")
    member_headers = _member_headers(client, db_session, tenant_id, suffix="ro")

    listed = client.get(DEST_BASE, headers=member_headers)
    assert listed.status_code == 200
    got = client.get(f"{DEST_BASE}/{created['id']}", headers=member_headers)
    assert got.status_code == 200

    denied = [
        client.post(
            DEST_BASE,
            headers=member_headers,
            json={
                "publishing_connection_id": conn["id"],
                "destination_type": "telegram_chat",
                "external_id": "nope",
                "display_name": "Nope",
            },
        ),
        client.patch(
            f"{DEST_BASE}/{created['id']}",
            headers=member_headers,
            json={"display_name": "Nope"},
        ),
        client.post(f"{DEST_BASE}/{created['id']}/disable", headers=member_headers),
        client.post(f"{DEST_BASE}/{created['id']}/enable", headers=member_headers),
        client.post(f"{DEST_BASE}/{created['id']}/validate", headers=member_headers),
        client.post(f"{DEST_BASE}/{created['id']}/archive", headers=member_headers),
    ]
    for resp in denied:
        assert resp.status_code == 403, resp.text


def test_owner_lifecycle_enable_disable_archive_validate(client: TestClient):
    headers, _ = _register_and_login(client, suffix="life")
    conn = _create_connection(client, headers, identifier="life-bot")
    created = _create_destination(client, headers, conn["id"], external_id="life-chat")
    did = created["id"]

    disabled = client.post(f"{DEST_BASE}/{did}/disable", headers=headers)
    assert disabled.status_code == 200, disabled.text
    assert disabled.json()["status"] == "disabled"

    enabled = client.post(f"{DEST_BASE}/{did}/enable", headers=headers)
    assert enabled.status_code == 200, enabled.text
    assert enabled.json()["status"] == "enabled"

    validated = client.post(f"{DEST_BASE}/{did}/validate", headers=headers)
    assert validated.status_code == 200, validated.text
    body = validated.json()
    _assert_safe_payload(body)
    assert body["validation_status"] == "unavailable"
    assert body["validation_error_code"] == "provider_adapter_unavailable"
    assert body["validation_status"] != "valid"

    archived = client.post(f"{DEST_BASE}/{did}/archive", headers=headers)
    assert archived.status_code == 200, archived.text
    assert archived.json()["status"] == "archived"


def test_cross_tenant_connection_and_destination_404(client: TestClient):
    headers, tenant_a = _register_and_login(client, suffix="iso")
    tenant_b = client.post(
        "/api/v1/tenants",
        json={"name": "PD Tenant iso-b", "slug": "pd-tenant-iso-b"},
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

    conn_a = _create_connection(client, headers_a, identifier="iso-a-bot")
    dest_a = _create_destination(client, headers_a, conn_a["id"], external_id="iso-a-chat")

    cross_get = client.get(f"{DEST_BASE}/{dest_a['id']}", headers=headers_b)
    assert cross_get.status_code == 404
    assert cross_get.json()["detail"] == "publish_destination_not_found"

    cross_create = client.post(
        DEST_BASE,
        headers=headers_b,
        json={
            "publishing_connection_id": conn_a["id"],
            "destination_type": "telegram_chat",
            "external_id": "stolen",
            "display_name": "Stolen",
        },
    )
    assert cross_create.status_code == 404
    assert cross_create.json()["detail"] == "publishing_connection_not_found"

    cross_patch = client.patch(
        f"{DEST_BASE}/{dest_a['id']}",
        headers=headers_b,
        json={"display_name": "Nope"},
    )
    assert cross_patch.status_code == 404


def test_redaction_no_secret_fields(client: TestClient, db_session):
    headers, tenant_id = _register_and_login(client, suffix="redact")
    conn = _create_connection(client, headers, identifier="redact-bot")
    # Bind a secret_ref on the connection row — destination responses must still stay clean.
    row = MarketingRepository(db_session).get_publishing_connection(
        uuid.UUID(tenant_id), uuid.UUID(conn["id"])
    )
    assert row is not None
    row.secret_ref = "vault/tenant/telegram/should-not-leak"
    row.secret_version = 1
    row.secret_bound_at = datetime.now(UTC)
    db_session.commit()

    created = _create_destination(client, headers, conn["id"], external_id="redact-chat")
    got = client.get(f"{DEST_BASE}/{created['id']}", headers=headers)
    assert got.status_code == 200
    _assert_safe_payload(got.json())
    blob = str(got.json()).casefold()
    assert "should-not-leak" not in blob
    assert "secret_ref" not in blob
    assert "vault/" not in blob


def test_tiktok_capability_disabled_via_api(client: TestClient):
    headers, _ = _register_and_login(client, suffix="tiktok")
    conn = _create_connection(
        client, headers, provider="tiktok", identifier="tt-account", display="TT Acc"
    )
    created = client.post(
        DEST_BASE,
        headers=headers,
        json={
            "publishing_connection_id": conn["id"],
            "destination_type": "tiktok_user",
            "external_id": "tt-user-1",
            "display_name": "TikTok reserved",
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["status"] == "disabled"
    did = body["id"]

    enable = client.post(f"{DEST_BASE}/{did}/enable", headers=headers)
    assert enable.status_code == 409
    assert "destination_capability_disabled" in enable.json()["detail"]

    validated = client.post(f"{DEST_BASE}/{did}/validate", headers=headers)
    assert validated.status_code == 200, validated.text
    assert validated.json()["validation_status"] == "unavailable"
    assert validated.json()["validation_error_code"] == "capability_disabled"
    assert validated.json()["validation_status"] != "valid"


def test_metadata_forbidden_keys_normalized_variants(client: TestClient):
    headers, _ = _register_and_login(client, suffix="meta-forbid")
    conn = _create_connection(client, headers, identifier="meta-bot")
    variants = [
        {"AccessToken": "x"},
        {"access-token": "x"},
        {"access_token": "x"},
        {"ACCESS.TOKEN": "x"},
        {"nested": {"secret_ref": "x"}},
        {"apiKey": "x"},
        {"bot-token": "x"},
    ]
    for meta in variants:
        resp = client.post(
            DEST_BASE,
            headers=headers,
            json={
                "publishing_connection_id": conn["id"],
                "destination_type": "telegram_chat",
                "external_id": f"meta-{uuid.uuid4().hex[:8]}",
                "display_name": "Meta",
                "metadata_json": meta,
            },
        )
        assert resp.status_code == 409, resp.text
        assert resp.json()["detail"] == "metadata_json_forbidden_key"
        assert "x" not in resp.text or "forbidden" in resp.text


def test_display_name_control_chars_and_length_rejected(client: TestClient):
    headers, _ = _register_and_login(client, suffix="disp")
    conn = _create_connection(client, headers, identifier="disp-bot")

    control = client.post(
        DEST_BASE,
        headers=headers,
        json={
            "publishing_connection_id": conn["id"],
            "destination_type": "telegram_chat",
            "external_id": "disp-ctrl",
            "display_name": "Bad\x00Name",
        },
    )
    assert control.status_code == 409
    assert control.json()["detail"] == "display_name_control_characters"

    too_long = client.post(
        DEST_BASE,
        headers=headers,
        json={
            "publishing_connection_id": conn["id"],
            "destination_type": "telegram_chat",
            "external_id": "disp-long",
            "display_name": "x" * 256,
        },
    )
    # Pydantic max_length → 422; domain path also rejects too_long if reached.
    assert too_long.status_code in (409, 422), too_long.text


def test_external_id_immutable_after_lock_via_api(client: TestClient, db_session):
    headers, tenant_id = _register_and_login(client, suffix="lock")
    conn = _create_connection(client, headers, identifier="lock-bot")
    created = _create_destination(client, headers, conn["id"], external_id="lock-chat")
    did = uuid.UUID(created["id"])

    # Lock identity via domain structural VALID (D1 path); HTTP validate never invents VALID.
    row = db_session.get(MarketingPublishDestination, did)
    assert row is not None
    row.apply_structural_validation(
        validation_status=MarketingDestinationValidationStatus.VALID,
    )
    db_session.commit()
    assert row.identity_locked_at is not None

    patched = client.patch(
        f"{DEST_BASE}/{created['id']}",
        headers=headers,
        json={"external_id": "should-fail"},
    )
    assert patched.status_code == 409
    assert patched.json()["detail"] == "external_id_immutable"


def test_no_hard_delete_route(client: TestClient):
    headers, _ = _register_and_login(client, suffix="nodel")
    conn = _create_connection(client, headers, identifier="nodel-bot")
    created = _create_destination(client, headers, conn["id"], external_id="nodel-chat")
    deleted = client.delete(f"{DEST_BASE}/{created['id']}", headers=headers)
    assert deleted.status_code in (404, 405)


def test_view_schema_excludes_secret_fields():
    from app.modules.marketing.schemas import PublishDestinationView

    fields = set(PublishDestinationView.model_fields)
    assert "secret_ref" not in fields
    assert "secret" not in fields
    assert "credentials_json" not in fields
    assert "token" not in fields
    assert "external_id" in fields
    assert "identity_locked_at" in fields


def test_same_provider_company_staff_can_mutate_destination(
    client: TestClient, db_session
):
    """Provider staff of the tenant's provider company may mutate without tenant OWNER/ADMIN."""
    from app.core.enums import ProviderRole
    from app.core.security import hash_password
    from app.modules.auth.models import User
    from app.modules.provider.models import ProviderStaff
    from app.modules.tenants.models import Tenant

    headers, tenant_id = _register_and_login(client, suffix="staff-ok")
    conn = _create_connection(client, headers, identifier="staff-ok-bot")
    created = _create_destination(
        client, headers, conn["id"], external_id="staff-ok-chat"
    )

    tenant = db_session.get(Tenant, uuid.UUID(tenant_id))
    assert tenant is not None
    staff_user = User(
        email="pd-same-company-staff@example.com",
        full_name="Same Company Staff",
        hashed_password=hash_password("securepass123"),
        is_active=True,
    )
    db_session.add(staff_user)
    db_session.flush()
    db_session.add(
        ProviderStaff(
            provider_company_id=tenant.provider_company_id,
            user_id=staff_user.id,
            role=ProviderRole.SUPPORT_MANAGER,
        )
    )
    db_session.commit()

    login = client.post(
        "/api/v1/auth/login",
        json={
            "email": "pd-same-company-staff@example.com",
            "password": "securepass123",
        },
    )
    assert login.status_code == 200, login.text
    staff_headers = {
        "Authorization": f"Bearer {login.json()['access_token']}",
        "X-Tenant-ID": tenant_id,
    }

    # require_module("marketing") still applies for staff.
    patched = client.patch(
        f"{DEST_BASE}/{created['id']}",
        headers=staff_headers,
        json={"display_name": "Staff renamed"},
    )
    assert patched.status_code == 200, patched.text
    _assert_safe_payload(patched.json())
    assert patched.json()["display_name"] == "Staff renamed"


def test_foreign_provider_company_staff_denied_destination_mutation(
    client: TestClient, db_session
):
    """Unrelated provider-company staff must not mutate; tenant isolation preserved."""
    from app.core.enums import ProviderRole, TenantRole
    from app.core.security import hash_password
    from app.modules.auth.models import User
    from app.modules.provider.models import ProviderCompany, ProviderStaff
    from app.modules.tenants.models import UserTenantMembership

    headers, tenant_id = _register_and_login(client, suffix="staff-deny")
    conn = _create_connection(client, headers, identifier="staff-deny-bot")
    created = _create_destination(
        client, headers, conn["id"], external_id="staff-deny-chat"
    )

    other_company = ProviderCompany(name="Other Provider Co", slug="pd-other-provider")
    db_session.add(other_company)
    db_session.flush()

    # Case A: foreign staff with no tenant membership → tenant context denied.
    foreign_only = User(
        email="pd-foreign-staff-only@example.com",
        full_name="Foreign Staff Only",
        hashed_password=hash_password("securepass123"),
        is_active=True,
    )
    db_session.add(foreign_only)
    db_session.flush()
    db_session.add(
        ProviderStaff(
            provider_company_id=other_company.id,
            user_id=foreign_only.id,
            role=ProviderRole.SUPPORT_MANAGER,
        )
    )

    # Case B: foreign staff + MEMBER membership → can read, cannot mutate.
    foreign_member = User(
        email="pd-foreign-staff-member@example.com",
        full_name="Foreign Staff Member",
        hashed_password=hash_password("securepass123"),
        is_active=True,
    )
    db_session.add(foreign_member)
    db_session.flush()
    db_session.add(
        ProviderStaff(
            provider_company_id=other_company.id,
            user_id=foreign_member.id,
            role=ProviderRole.SUPPORT_MANAGER,
        )
    )
    db_session.add(
        UserTenantMembership(
            tenant_id=uuid.UUID(tenant_id),
            user_id=foreign_member.id,
            role=TenantRole.MEMBER,
            is_active=True,
        )
    )
    db_session.commit()

    login_a = client.post(
        "/api/v1/auth/login",
        json={
            "email": "pd-foreign-staff-only@example.com",
            "password": "securepass123",
        },
    )
    assert login_a.status_code == 200
    headers_a = {
        "Authorization": f"Bearer {login_a.json()['access_token']}",
        "X-Tenant-ID": tenant_id,
    }
    denied_tenant = client.patch(
        f"{DEST_BASE}/{created['id']}",
        headers=headers_a,
        json={"display_name": "Hijack"},
    )
    assert denied_tenant.status_code == 403, denied_tenant.text

    login_b = client.post(
        "/api/v1/auth/login",
        json={
            "email": "pd-foreign-staff-member@example.com",
            "password": "securepass123",
        },
    )
    assert login_b.status_code == 200
    headers_b = {
        "Authorization": f"Bearer {login_b.json()['access_token']}",
        "X-Tenant-ID": tenant_id,
    }
    # MEMBER + require_module: read still allowed.
    got = client.get(f"{DEST_BASE}/{created['id']}", headers=headers_b)
    assert got.status_code == 200, got.text
    denied_mut = client.patch(
        f"{DEST_BASE}/{created['id']}",
        headers=headers_b,
        json={"display_name": "Hijack"},
    )
    assert denied_mut.status_code == 403, denied_mut.text
