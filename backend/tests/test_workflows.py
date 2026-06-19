REGISTER_PAYLOAD = {
    "email": "owner@example.com",
    "password": "securepass123",
    "full_name": "Platform Owner",
    "company_name": "CoreOps Provider",
    "company_slug": "coreops-provider",
}


def _crm_tenant(client):
    client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    token = client.post(
        "/api/v1/auth/login",
        json={"email": REGISTER_PAYLOAD["email"], "password": REGISTER_PAYLOAD["password"]},
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    tenant_id = client.post(
        "/api/v1/tenants",
        json={
            "name": "CRM Tenant",
            "slug": "crm-tenant",
            "industry_template_code": "kindergarten_basic",
            "plan_code": "business",
        },
        headers=headers,
    ).json()["id"]

    tenant_headers = {**headers, "X-Tenant-ID": tenant_id}
    return tenant_headers, tenant_id


def test_list_pipelines_after_template(client):
    headers, _ = _crm_tenant(client)
    pipelines = client.get("/api/v1/pipelines", headers=headers)
    assert pipelines.status_code == 200
    assert any(p["code"] == "enrollment" for p in pipelines.json())


def test_work_item_lifecycle(client):
    headers, _ = _crm_tenant(client)

    party = client.post(
        "/api/v1/parties",
        headers=headers,
        json={
            "party_type": "person",
            "display_name": "Родитель Иванова",
            "party_role": "guardian",
        },
    )
    assert party.status_code == 201
    party_id = party.json()["id"]

    pipeline = next(p for p in client.get("/api/v1/pipelines", headers=headers).json() if p["code"] == "enrollment")
    first_stage_id = min(pipeline["stages"], key=lambda s: s["sort_order"])["id"]

    work_item = client.post(
        "/api/v1/work-items",
        headers=headers,
        json={
            "pipeline_id": pipeline["id"],
            "stage_id": first_stage_id,
            "work_item_type": "inquiry",
            "title": "Заявка на поступление",
            "primary_party_id": party_id,
            "custom_fields": {"preferred_start_date": "2025-09-01"},
        },
    )
    assert work_item.status_code == 201
    item = work_item.json()
    assert item["title"] == "Заявка на поступление"
    assert item["custom_fields"]["preferred_start_date"] == "2025-09-01"

    second_stage = sorted(pipeline["stages"], key=lambda s: s["sort_order"])[1]
    moved = client.post(
        f"/api/v1/work-items/{item['id']}/move-stage",
        headers=headers,
        json={"stage_id": second_stage["id"]},
    )
    assert moved.status_code == 200
    assert moved.json()["stage_id"] == second_stage["id"]
    assert moved.json()["status"] == "in_progress"

    activity = client.post(
        f"/api/v1/work-items/{item['id']}/activities",
        headers=headers,
        json={"activity_type": "call", "title": "Звонок родителю"},
    )
    assert activity.status_code == 201

    task = client.post(
        f"/api/v1/work-items/{item['id']}/tasks",
        headers=headers,
        json={"title": "Подготовить договор"},
    )
    assert task.status_code == 201

    by_stage = client.get(
        f"/api/v1/work-items?stage_id={second_stage['id']}",
        headers=headers,
    )
    assert by_stage.status_code == 200
    assert len(by_stage.json()) >= 1

    by_party = client.get(
        f"/api/v1/work-items?primary_party_id={party_id}",
        headers=headers,
    )
    assert by_party.status_code == 200
    assert len(by_party.json()) == 1
    assert by_party.json()[0]["id"] == item["id"]

    detail = client.get(f"/api/v1/work-items/{item['id']}", headers=headers)
    assert detail.status_code == 200
    detail_body = detail.json()
    assert len(detail_body["activities"]) >= 1
    assert len(detail_body["tasks"]) >= 1


def test_crm_module_disabled_blocks_work_items(client):
    headers, tenant_id = _crm_tenant(client)
    provider_headers = {k: v for k, v in headers.items() if k != "X-Tenant-ID"}

    client.post(
        f"/api/v1/tenants/{tenant_id}/modules/crm/disable",
        headers=provider_headers,
    )

    blocked = client.get("/api/v1/work-items", headers=headers)
    assert blocked.status_code == 403
