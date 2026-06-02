REGISTER_PAYLOAD = {
    "email": "owner@example.com",
    "password": "securepass123",
    "full_name": "Platform Owner",
    "company_name": "CoreOps Provider",
    "company_slug": "coreops-provider",
}


def _ai_tenant(client):
    client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    token = client.post(
        "/api/v1/auth/login",
        json={"email": REGISTER_PAYLOAD["email"], "password": REGISTER_PAYLOAD["password"]},
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    tenant_id = client.post(
        "/api/v1/tenants",
        json={
            "name": "AI Tenant",
            "slug": "ai-tenant",
            "industry_template_code": "kindergarten_basic",
            "plan_code": "enterprise",
        },
        headers=headers,
    ).json()["id"]

    return {**headers, "X-Tenant-ID": tenant_id}


def test_ai_agent_task_and_critical_approval_flow(client):
    headers = _ai_tenant(client)

    agents = client.get("/api/v1/ai/agents", headers=headers)
    assert agents.status_code == 200
    assert len(agents.json()) >= 1
    agent_id = agents.json()[0]["id"]

    task = client.post(
        "/api/v1/ai/tasks",
        headers=headers,
        json={
            "agent_id": agent_id,
            "title": "Review enrollment",
            "task_type": "enrollment",
            "run_mock": True,
        },
    )
    assert task.status_code == 201
    assert task.json()["status"] == "completed"
    assert task.json()["output_json"]["proposal_requires_approval"] is True

    proposals = client.get("/api/v1/ai/action-proposals?status=pending", headers=headers)
    assert proposals.status_code == 200
    assert len(proposals.json()) >= 1
    proposal_id = proposals.json()[0]["id"]
    assert proposals.json()[0]["is_critical"] is True

    blocked = client.post(
        f"/api/v1/ai/action-proposals/{proposal_id}/execute",
        headers=headers,
    )
    assert blocked.status_code == 403

    approved = client.post(
        f"/api/v1/ai/action-proposals/{proposal_id}/approve",
        headers=headers,
        json={"comment": "OK"},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"

    executed = client.post(
        f"/api/v1/ai/action-proposals/{proposal_id}/execute",
        headers=headers,
    )
    assert executed.status_code == 200
    assert executed.json()["status"] == "executed"

    usage = client.get("/api/v1/ai/usage/summary", headers=headers)
    assert usage.status_code == 200
    assert usage.json()["total_tokens"] > 0


def test_non_critical_proposal_execute_without_approval(client):
    headers = _ai_tenant(client)
    agent_id = client.get("/api/v1/ai/agents", headers=headers).json()[0]["id"]

    proposal = client.post(
        "/api/v1/ai/action-proposals",
        headers=headers,
        json={
            "agent_id": agent_id,
            "action_type": "other",
            "title": "Log note",
            "payload_json": {"note": "test"},
        },
    )
    assert proposal.status_code == 201
    assert proposal.json()["is_critical"] is False

    executed = client.post(
        f"/api/v1/ai/action-proposals/{proposal.json()['id']}/execute",
        headers=headers,
    )
    assert executed.status_code == 200
    assert executed.json()["status"] == "executed"
