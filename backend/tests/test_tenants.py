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


def test_add_tenant_membership_by_user_id_still_works(client, db_session):
    from app.core.security import hash_password
    from app.modules.auth.models import User

    headers = _auth_header(client)
    created = client.post(
        "/api/v1/tenants",
        json={"name": "By Id Tenant", "slug": "by-id-tenant"},
        headers=headers,
    )
    assert created.status_code == 201
    tenant_id = created.json()["id"]

    user = User(
        email="byid@example.com",
        full_name="By Id Member",
        hashed_password=hash_password("memberpass123"),
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    added = client.post(
        f"/api/v1/tenants/{tenant_id}/memberships",
        json={"user_id": str(user.id), "role": "member"},
        headers=headers,
    )
    assert added.status_code == 201
    assert added.json()["role"] == "member"


def test_add_tenant_membership_by_user_email(client, db_session):
    from app.core.security import hash_password
    from app.modules.auth.models import User

    headers = _auth_header(client)
    created = client.post(
        "/api/v1/tenants",
        json={"name": "By Email Tenant", "slug": "by-email-tenant"},
        headers=headers,
    )
    assert created.status_code == 201
    tenant_id = created.json()["id"]

    user = User(
        email="byemail@example.com",
        full_name="By Email Member",
        hashed_password=hash_password("memberpass123"),
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    added = client.post(
        f"/api/v1/tenants/{tenant_id}/memberships",
        json={"user_email": "byemail@example.com", "role": "tenant_admin"},
        headers=headers,
    )
    assert added.status_code == 201
    assert added.json()["role"] == "tenant_admin"


def test_add_tenant_membership_invalid_payload_cases(client):
    headers = _auth_header(client)
    created = client.post(
        "/api/v1/tenants",
        json={"name": "Invalid Payload Tenant", "slug": "invalid-payload-tenant"},
        headers=headers,
    )
    assert created.status_code == 201
    tenant_id = created.json()["id"]

    both_missing = client.post(
        f"/api/v1/tenants/{tenant_id}/memberships",
        json={"role": "member"},
        headers=headers,
    )
    assert both_missing.status_code == 422

    both_present = client.post(
        f"/api/v1/tenants/{tenant_id}/memberships",
        json={
            "user_id": created.json()["id"],
            "user_email": "owner@example.com",
            "role": "member",
        },
        headers=headers,
    )
    assert both_present.status_code == 422


def test_add_tenant_membership_unknown_email_returns_404(client):
    headers = _auth_header(client)
    created = client.post(
        "/api/v1/tenants",
        json={"name": "Unknown Email Tenant", "slug": "unknown-email-tenant"},
        headers=headers,
    )
    assert created.status_code == 201
    tenant_id = created.json()["id"]

    missing = client.post(
        f"/api/v1/tenants/{tenant_id}/memberships",
        json={"user_email": "missing@example.com", "role": "member"},
        headers=headers,
    )
    assert missing.status_code == 404


def test_add_tenant_membership_duplicate_returns_409(client, db_session):
    from app.core.security import hash_password
    from app.modules.auth.models import User

    headers = _auth_header(client)
    created = client.post(
        "/api/v1/tenants",
        json={"name": "Duplicate Tenant", "slug": "duplicate-tenant"},
        headers=headers,
    )
    assert created.status_code == 201
    tenant_id = created.json()["id"]

    user = User(
        email="duplicate@example.com",
        full_name="Duplicate Member",
        hashed_password=hash_password("memberpass123"),
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    first = client.post(
        f"/api/v1/tenants/{tenant_id}/memberships",
        json={"user_email": "duplicate@example.com", "role": "member"},
        headers=headers,
    )
    assert first.status_code == 201

    second = client.post(
        f"/api/v1/tenants/{tenant_id}/memberships",
        json={"user_email": "duplicate@example.com", "role": "member"},
        headers=headers,
    )
    assert second.status_code == 409


def test_create_tenant_user_success(client, db_session):
    headers = _auth_header(client)
    created = client.post(
        "/api/v1/tenants",
        json={"name": "Onboard Tenant", "slug": "onboard-tenant"},
        headers=headers,
    )
    assert created.status_code == 201
    tenant_id = created.json()["id"]

    temp_password = "securepass123"
    response = client.post(
        f"/api/v1/tenants/{tenant_id}/users",
        json={
            "email": "client@example.com",
            "full_name": "Client User",
            "temporary_password": temp_password,
            "role": "tenant_admin",
        },
        headers=headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["user"]["email"] == "client@example.com"
    assert data["user"]["full_name"] == "Client User"
    assert data["user"]["is_active"] is True
    assert "hashed_password" not in data["user"]
    assert "temporary_password" not in data
    assert data["membership"]["role"] == "tenant_admin"
    assert data["membership"]["membership_is_active"] is True

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "client@example.com", "password": temp_password},
    )
    assert login.status_code == 200
    assert "access_token" in login.json()


def test_create_tenant_user_duplicate_email_returns_409(client):
    headers = _auth_header(client)
    created = client.post(
        "/api/v1/tenants",
        json={"name": "Dup User Tenant", "slug": "dup-user-tenant"},
        headers=headers,
    )
    assert created.status_code == 201
    tenant_id = created.json()["id"]

    payload = {
        "email": "dupcreate@example.com",
        "full_name": "First User",
        "temporary_password": "securepass123",
        "role": "member",
    }
    first = client.post(f"/api/v1/tenants/{tenant_id}/users", json=payload, headers=headers)
    assert first.status_code == 201

    second = client.post(f"/api/v1/tenants/{tenant_id}/users", json=payload, headers=headers)
    assert second.status_code == 409


def test_create_tenant_user_requires_provider_owner(client, db_session):
    from app.core.security import hash_password
    from app.modules.auth.models import User

    owner_headers = _auth_header(client)
    created = client.post(
        "/api/v1/tenants",
        json={"name": "Owner Only Tenant", "slug": "owner-only-tenant"},
        headers=owner_headers,
    )
    assert created.status_code == 201
    tenant_id = created.json()["id"]

    outsider_password = "outsiderpass123"
    outsider = User(
        email="tenantonly@example.com",
        full_name="Tenant Only User",
        hashed_password=hash_password(outsider_password),
        is_active=True,
    )
    db_session.add(outsider)
    db_session.commit()

    outsider_headers = _login_header(
        client,
        email="tenantonly@example.com",
        password=outsider_password,
    )

    forbidden = client.post(
        f"/api/v1/tenants/{tenant_id}/users",
        json={
            "email": "newuser@example.com",
            "full_name": "New User",
            "temporary_password": "securepass123",
            "role": "member",
        },
        headers=outsider_headers,
    )
    assert forbidden.status_code == 403


def test_create_tenant_user_rejects_disallowed_roles(client):
    headers = _auth_header(client)
    created = client.post(
        "/api/v1/tenants",
        json={"name": "Role Guard Tenant", "slug": "role-guard-tenant"},
        headers=headers,
    )
    assert created.status_code == 201
    tenant_id = created.json()["id"]

    for role in ("tenant_owner", "provider_owner"):
        response = client.post(
            f"/api/v1/tenants/{tenant_id}/users",
            json={
                "email": f"{role}@example.com",
                "full_name": "Blocked Role",
                "temporary_password": "securepass123",
                "role": role,
            },
            headers=headers,
        )
        assert response.status_code == 422
