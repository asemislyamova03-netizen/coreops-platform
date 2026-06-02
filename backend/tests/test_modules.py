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
