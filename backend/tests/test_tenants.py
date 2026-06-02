REGISTER_PAYLOAD = {
    "email": "owner@example.com",
    "password": "securepass123",
    "full_name": "Platform Owner",
    "company_name": "CoreOps Provider",
    "company_slug": "coreops-provider",
}


def _auth_header(client) -> dict[str, str]:
    reg = client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    token = reg.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_create_and_list_tenants(client):
    headers = _auth_header(client)

    created = client.post(
        "/api/v1/tenants",
        json={"name": "Demo Client", "slug": "demo-client"},
        headers=headers,
    )
    assert created.status_code == 201
    tenant = created.json()
    assert tenant["slug"] == "demo-client"
    assert tenant["status"] == "trial"

    listed = client.get("/api/v1/tenants", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1


def test_get_tenant_by_id(client):
    headers = _auth_header(client)
    created = client.post(
        "/api/v1/tenants",
        json={"name": "Acme", "slug": "acme"},
        headers=headers,
    )
    tenant_id = created.json()["id"]

    fetched = client.get(f"/api/v1/tenants/{tenant_id}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["name"] == "Acme"


def test_create_tenant_requires_provider_owner(client):
    headers = _auth_header(client)
    # No Authorization
    response = client.post("/api/v1/tenants", json={"name": "X", "slug": "x"})
    assert response.status_code == 401
