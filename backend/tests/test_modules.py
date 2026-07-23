REGISTER_PAYLOAD = {
    "email": "owner@example.com",
    "password": "securepass123",
    "full_name": "Platform Owner",
    "company_name": "CoreOps Provider",
    "company_slug": "coreops-provider",
}


def _auth(client) -> dict[str, str]:
    client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    token = client.post(
        "/api/v1/auth/login",
        json={"email": REGISTER_PAYLOAD["email"], "password": REGISTER_PAYLOAD["password"]},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_tenant(client, headers, slug: str = "demo-client") -> str:
    response = client.post(
        "/api/v1/tenants",
        json={"name": "Demo", "slug": slug},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_module_registry_list(client):
    headers = _auth(client)
    response = client.get("/api/v1/modules/registry", headers=headers)
    assert response.status_code == 200
    codes = {item["code"] for item in response.json()}
    assert "crm" in codes
    assert "parties" in codes
    crm = next(item for item in response.json() if item["code"] == "crm")
    assert "parties" in (crm.get("dependencies_json") or {}).get("required", [])


def test_provision_tenant_modules_on_create(client):
    headers = _auth(client)
    tenant_id = _create_tenant(client, headers, slug="mod-tenant")

    response = client.get(f"/api/v1/tenants/{tenant_id}/modules", headers=headers)
    assert response.status_code == 200
    modules = response.json()
    assert len(modules) >= 8
    assert all(m["status"] == "disabled" for m in modules)


def test_enable_module_with_dependency_check(client):
    headers = _auth(client)
    tenant_id = _create_tenant(client, headers, slug="dep-tenant")

    crm_enable = client.post(
        f"/api/v1/tenants/{tenant_id}/modules/crm/enable",
        headers=headers,
    )
    assert crm_enable.status_code == 409

    parties_enable = client.post(
        f"/api/v1/tenants/{tenant_id}/modules/parties/enable",
        headers=headers,
    )
    assert parties_enable.status_code == 200

    crm_enable = client.post(
        f"/api/v1/tenants/{tenant_id}/modules/crm/enable",
        headers=headers,
    )
    assert crm_enable.status_code == 200
    assert crm_enable.json()["status"] == "enabled"


def test_enable_module_is_idempotent(client):
    headers = _auth(client)
    tenant_id = _create_tenant(client, headers, slug="idem-enable")

    first = client.post(
        f"/api/v1/tenants/{tenant_id}/modules/parties/enable",
        headers=headers,
    )
    assert first.status_code == 200
    first_body = first.json()

    second = client.post(
        f"/api/v1/tenants/{tenant_id}/modules/parties/enable",
        headers=headers,
    )
    assert second.status_code == 200
    second_body = second.json()
    assert second_body["status"] == "enabled"
    assert second_body["id"] == first_body["id"]
    assert second_body["mode"] == first_body["mode"]


def test_disable_required_dependency_returns_409(client):
    headers = _auth(client)
    tenant_id = _create_tenant(client, headers, slug="dep-disable")

    assert (
        client.post(
            f"/api/v1/tenants/{tenant_id}/modules/parties/enable",
            headers=headers,
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/v1/tenants/{tenant_id}/modules/crm/enable",
            headers=headers,
        ).status_code
        == 200
    )

    blocked = client.post(
        f"/api/v1/tenants/{tenant_id}/modules/parties/disable",
        headers=headers,
    )
    assert blocked.status_code == 409
    detail = blocked.json().get("detail", "")
    assert "parties" in detail
    assert "crm" in detail

    # Safe ordering: disable dependent first, then dependency.
    assert (
        client.post(
            f"/api/v1/tenants/{tenant_id}/modules/crm/disable",
            headers=headers,
        ).status_code
        == 200
    )
    allowed = client.post(
        f"/api/v1/tenants/{tenant_id}/modules/parties/disable",
        headers=headers,
    )
    assert allowed.status_code == 200
    assert allowed.json()["status"] == "disabled"


def test_disable_retains_settings_and_party_data(client, db_session):
    import uuid

    from app.modules.parties.models import Party

    headers = _auth(client)
    tenant_id = _create_tenant(client, headers, slug="retain-data")
    tenant_headers = {**headers, "X-Tenant-ID": tenant_id}

    assert (
        client.post(
            f"/api/v1/tenants/{tenant_id}/modules/parties/enable",
            headers=headers,
        ).status_code
        == 200
    )

    patched = client.patch(
        f"/api/v1/tenants/{tenant_id}/modules/parties",
        headers=headers,
        json={"settings_json": {"slice1_marker": "keep-me"}},
    )
    assert patched.status_code == 200
    assert patched.json()["settings_json"]["slice1_marker"] == "keep-me"

    created = client.post(
        "/api/v1/parties",
        headers=tenant_headers,
        json={
            "party_type": "person",
            "display_name": "Retain Party",
            "party_role": "client",
        },
    )
    assert created.status_code == 201
    party_id = created.json()["id"]

    disabled = client.post(
        f"/api/v1/tenants/{tenant_id}/modules/parties/disable",
        headers=headers,
    )
    assert disabled.status_code == 200
    assert disabled.json()["status"] == "disabled"
    assert disabled.json()["settings_json"]["slice1_marker"] == "keep-me"

    party = db_session.get(Party, uuid.UUID(party_id))
    assert party is not None
    assert str(party.tenant_id) == tenant_id
    assert party.display_name == "Retain Party"


def test_tenant_modules_isolation_and_provider_permission(client, db_session):
    from app.core.security import hash_password
    from app.modules.auth.models import User

    headers = _auth(client)
    tenant_a = _create_tenant(client, headers, slug="tenant-a-mods")
    tenant_b = _create_tenant(client, headers, slug="tenant-b-mods")

    assert (
        client.post(
            f"/api/v1/tenants/{tenant_a}/modules/parties/enable",
            headers=headers,
        ).status_code
        == 200
    )

    # Same provider: tenant B module state remains independent.
    modules_b = client.get(f"/api/v1/tenants/{tenant_b}/modules", headers=headers)
    assert modules_b.status_code == 200
    parties_b = next(m for m in modules_b.json() if m["module_code"] == "parties")
    assert parties_b["status"] == "disabled"

    # Non-provider user cannot manage modules (provider-owner permission regression).
    outsider = User(
        email="outsider-mods@example.com",
        full_name="Outsider Mods",
        hashed_password=hash_password("outsiderpass123"),
        is_active=True,
    )
    db_session.add(outsider)
    db_session.commit()
    outsider_token = client.post(
        "/api/v1/auth/login",
        json={"email": "outsider-mods@example.com", "password": "outsiderpass123"},
    ).json()["access_token"]
    outsider_headers = {"Authorization": f"Bearer {outsider_token}"}

    forbidden_list = client.get(
        f"/api/v1/tenants/{tenant_a}/modules",
        headers=outsider_headers,
    )
    assert forbidden_list.status_code == 403
    forbidden_enable = client.post(
        f"/api/v1/tenants/{tenant_a}/modules/crm/enable",
        headers=outsider_headers,
    )
    assert forbidden_enable.status_code == 403
    forbidden_disable = client.post(
        f"/api/v1/tenants/{tenant_a}/modules/parties/disable",
        headers=outsider_headers,
    )
    assert forbidden_disable.status_code == 403


def test_set_external_mode(client):
    headers = _auth(client)
    tenant_id = _create_tenant(client, headers, slug="ext-tenant")
    tenant_headers = {**headers, "X-Tenant-ID": tenant_id}

    client.post(f"/api/v1/tenants/{tenant_id}/modules/parties/enable", headers=headers)
    client.post(f"/api/v1/tenants/{tenant_id}/modules/crm/enable", headers=headers)
    client.post(f"/api/v1/tenants/{tenant_id}/modules/integrations/enable", headers=headers)

    connection = client.post(
        "/api/v1/integrations/connections",
        headers=tenant_headers,
        json={
            "provider_code": "bitrix24",
            "module_code": "crm",
            "name": "Bitrix CRM",
            "credentials_json": {"portal_url": "https://demo.bitrix24.ru"},
        },
    )
    assert connection.status_code == 201
    conn_id = connection.json()["id"]
    test_result = client.post(
        f"/api/v1/integrations/connections/{conn_id}/test",
        headers=tenant_headers,
    )
    assert test_result.status_code == 200
    assert test_result.json()["success"] is True

    response = client.patch(
        f"/api/v1/tenants/{tenant_id}/modules/crm/mode",
        json={"mode": "external", "external_provider_code": "bitrix24"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["mode"] == "external"
    assert response.json()["external_provider_code"] == "bitrix24"


def test_require_module_guard(client):
    headers = _auth(client)
    tenant_id = _create_tenant(client, headers, slug="guard-tenant")

    blocked = client.get(
        f"/api/v1/tenants/{tenant_id}/modules/crm/access-check",
        headers=headers,
    )
    assert blocked.status_code == 403

    client.post(f"/api/v1/tenants/{tenant_id}/modules/parties/enable", headers=headers)
    client.post(f"/api/v1/tenants/{tenant_id}/modules/crm/enable", headers=headers)

    allowed = client.get(
        f"/api/v1/tenants/{tenant_id}/modules/crm/access-check",
        headers=headers,
    )
    assert allowed.status_code == 200
    assert allowed.json()["access"] == "granted"
