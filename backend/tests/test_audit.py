REGISTER_PAYLOAD = {
    "email": "owner@example.com",
    "password": "securepass123",
    "full_name": "Platform Owner",
    "company_name": "CoreOps Provider",
    "company_slug": "coreops-provider",
}


def test_login_creates_security_event(client):
    client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    client.post(
        "/api/v1/auth/login",
        json={"email": REGISTER_PAYLOAD["email"], "password": REGISTER_PAYLOAD["password"]},
    )

    token = client.post(
        "/api/v1/auth/login",
        json={"email": REGISTER_PAYLOAD["email"], "password": REGISTER_PAYLOAD["password"]},
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    events = client.get("/api/v1/audit/security-events?event_type=login_success", headers=headers)
    assert events.status_code == 200
    assert len(events.json()) >= 1


def test_party_read_creates_data_access_log(client):
    client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    token = client.post(
        "/api/v1/auth/login",
        json={"email": REGISTER_PAYLOAD["email"], "password": REGISTER_PAYLOAD["password"]},
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    tenant_id = client.post(
        "/api/v1/tenants",
        json={
            "name": "Audit Tenant",
            "slug": "audit-tenant",
            "industry_template_code": "kindergarten_basic",
            "plan_code": "business",
        },
        headers=headers,
    ).json()["id"]
    tenant_headers = {**headers, "X-Tenant-ID": tenant_id}

    party = client.post(
        "/api/v1/parties",
        headers=tenant_headers,
        json={
            "party_type": "person",
            "display_name": "Родитель Аудит",
            "party_role": "guardian",
        },
    )
    assert party.status_code == 201
    party_id = party.json()["id"]

    fetched = client.get(f"/api/v1/parties/{party_id}", headers=tenant_headers)
    assert fetched.status_code == 200

    access_logs = client.get("/api/v1/audit/data-access", headers=tenant_headers)
    assert access_logs.status_code == 200
    assert any(log["entity_type"] == "party" and log["entity_id"] == party_id for log in access_logs.json())


def test_ai_approval_writes_audit_log(client):
    client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    token = client.post(
        "/api/v1/auth/login",
        json={"email": REGISTER_PAYLOAD["email"], "password": REGISTER_PAYLOAD["password"]},
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    tenant_id = client.post(
        "/api/v1/tenants",
        json={
            "name": "Audit AI Tenant",
            "slug": "audit-ai-tenant",
            "industry_template_code": "kindergarten_basic",
            "plan_code": "enterprise",
        },
        headers=headers,
    ).json()["id"]
    tenant_headers = {**headers, "X-Tenant-ID": tenant_id}

    agent_id = client.get("/api/v1/ai/agents", headers=tenant_headers).json()[0]["id"]
    client.post(
        "/api/v1/ai/tasks",
        headers=tenant_headers,
        json={"agent_id": agent_id, "title": "Task", "run_mock": True},
    )
    proposal_id = client.get(
        "/api/v1/ai/action-proposals?status=pending", headers=tenant_headers
    ).json()[0]["id"]
    client.post(f"/api/v1/ai/action-proposals/{proposal_id}/approve", headers=tenant_headers)

    logs = client.get(
        f"/api/v1/audit/logs?tenant_id={tenant_id}&action=approve",
        headers=headers,
    )
    assert logs.status_code == 200
    assert any(log["ai_proposal_id"] == proposal_id for log in logs.json())
