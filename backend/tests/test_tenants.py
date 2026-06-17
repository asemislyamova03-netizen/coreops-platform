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


def _login_header(client, email: str, password: str) -> dict[str, str]:
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
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


def test_list_tenant_memberships_returns_assigned_membership(client):
    headers = _auth_header(client)
    me = client.get("/api/v1/auth/me", headers=headers)
    user_id = me.json()["user"]["id"]

    created = client.post(
        "/api/v1/tenants",
        json={"name": "Membership Demo", "slug": "membership-demo", "owner_user_id": user_id},
        headers=headers,
    )
    assert created.status_code == 201
    tenant_id = created.json()["id"]

    memberships = client.get(f"/api/v1/tenants/{tenant_id}/memberships", headers=headers)
    assert memberships.status_code == 200
    data = memberships.json()
    assert len(data) == 1
    assert data[0]["email"] == REGISTER_PAYLOAD["email"]
    assert data[0]["role"] == "tenant_owner"
    assert data[0]["membership_is_active"] is True


def test_list_tenant_memberships_denies_user_without_access(client, db_session):
    from app.core.security import hash_password
    from app.modules.auth.models import User

    owner_headers = _auth_header(client)
    created = client.post(
        "/api/v1/tenants",
        json={"name": "Restricted", "slug": "restricted"},
        headers=owner_headers,
    )
    assert created.status_code == 201
    tenant_id = created.json()["id"]

    outsider_password = "outsiderpass123"
    outsider = User(
        email="outsider@example.com",
        full_name="Outsider User",
        hashed_password=hash_password(outsider_password),
        is_active=True,
    )
    db_session.add(outsider)
    db_session.commit()

    outsider_headers = _login_header(
        client,
        email="outsider@example.com",
        password=outsider_password,
    )

    forbidden = client.get(f"/api/v1/tenants/{tenant_id}/memberships", headers=outsider_headers)
    assert forbidden.status_code == 403
