REGISTER_PAYLOAD = {
    "email": "owner@example.com",
    "password": "securepass123",
    "full_name": "Platform Owner",
    "company_name": "CoreOps Provider",
    "company_slug": "coreops-provider",
}


def test_register_provider_owner(client):
    response = client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_register_bootstrap_once(client):
    client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    response = client.post("/api/v1/auth/register", json={
        **REGISTER_PAYLOAD,
        "email": "other@example.com",
        "company_slug": "other-company",
    })
    assert response.status_code == 403


def test_login_and_me(client):
    client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)

    login = client.post(
        "/api/v1/auth/login",
        json={"email": REGISTER_PAYLOAD["email"], "password": REGISTER_PAYLOAD["password"]},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    body = me.json()
    assert body["user"]["email"] == REGISTER_PAYLOAD["email"]
    assert body["provider"]["role"] == "provider_owner"
    assert body["provider"]["provider_company_name"] == REGISTER_PAYLOAD["company_name"]


def test_refresh_token(client):
    reg = client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    refresh_token = reg.json()["refresh_token"]

    refreshed = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert refreshed.status_code == 200
    assert refreshed.json()["access_token"]


def test_login_invalid_password(client):
    client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    response = client.post(
        "/api/v1/auth/login",
        json={"email": REGISTER_PAYLOAD["email"], "password": "wrong"},
    )
    assert response.status_code == 401
