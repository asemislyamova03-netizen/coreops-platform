REGISTER_PAYLOAD = {
    "email": "owner@example.com",
    "password": "securepass123",
    "full_name": "Platform Owner",
    "company_name": "CoreOps Provider",
    "company_slug": "coreops-provider",
}


def _integration_tenant(client):
    client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    token = client.post(
        "/api/v1/auth/login",
        json={"email": REGISTER_PAYLOAD["email"], "password": REGISTER_PAYLOAD["password"]},
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    tenant_id = client.post(
        "/api/v1/tenants",
        json={
            "name": "Integrations Tenant",
            "slug": "integrations-tenant",
            "plan_code": "enterprise",
        },
        headers=headers,
    ).json()["id"]

    provider_headers = {k: v for k, v in headers.items()}
    client.post(f"/api/v1/tenants/{tenant_id}/modules/integrations/enable", headers=provider_headers)

    return {**headers, "X-Tenant-ID": tenant_id}, provider_headers, tenant_id


def test_providers_and_bitrix_sync_flow(client):
    headers, _, _ = _integration_tenant(client)

    providers = client.get("/api/v1/integrations/providers", headers=headers)
    assert providers.status_code == 200
    codes = {p["code"] for p in providers.json()}
    assert "bitrix24" in codes

    connection = client.post(
        "/api/v1/integrations/connections",
        headers=headers,
        json={
            "provider_code": "bitrix24",
            "module_code": "crm",
            "name": "Bitrix mock",
            "credentials_json": {"portal_url": "https://demo.bitrix24.ru"},
        },
    )
    assert connection.status_code == 201
    conn_id = connection.json()["id"]
    assert connection.json()["has_credentials"] is True

    tested = client.post(f"/api/v1/integrations/connections/{conn_id}/test", headers=headers)
    assert tested.status_code == 200
    assert tested.json()["success"] is True

    synced = client.post(f"/api/v1/integrations/connections/{conn_id}/sync", headers=headers)
    assert synced.status_code == 200
    assert synced.json()["status"] == "completed"

    jobs = client.get("/api/v1/integrations/sync-jobs", headers=headers)
    assert jobs.status_code == 200
    assert len(jobs.json()) >= 1


def test_webhook_receive(client):
    response = client.post(
        "/api/v1/integrations/webhooks/bitrix24",
        json={"event_type": "ONCRMDEALUPDATE", "payload": {"ID": "123"}},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "processed"


def test_create_connection_with_unknown_provider_returns_404(client):
    headers, _, _ = _integration_tenant(client)
    response = client.post(
        "/api/v1/integrations/connections",
        headers=headers,
        json={
            "provider_code": "unknown_provider",
            "module_code": "crm",
            "name": "Unknown",
            "credentials_json": {},
        },
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_create_connection_with_unsupported_module_returns_409(client):
    headers, _, _ = _integration_tenant(client)
    response = client.post(
        "/api/v1/integrations/connections",
        headers=headers,
        json={
            "provider_code": "bitrix24",
            "module_code": "finance",
            "name": "Bitrix for finance",
            "credentials_json": {"portal_url": "https://demo.bitrix24.ru"},
        },
    )
    assert response.status_code == 409
    assert "does not support module" in response.json()["detail"]


def test_webhook_unknown_provider_returns_404(client):
    response = client.post(
        "/api/v1/integrations/webhooks/unknown_provider",
        json={"event_type": "PING", "payload": {}},
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
