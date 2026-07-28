"""HTTP coverage for WorkItem close/reopen disposition (ported from dirty M8 WC).

Base: origin/main. Product code unchanged. Assertions follow current API contracts:
POST /api/v1/work-items/{id}/close|reopen, DispositionCode literal, ConflictError 409.
"""

REGISTER_PAYLOAD = {
    "email": "owner@example.com",
    "password": "securepass123",
    "full_name": "Platform Owner",
    "company_name": "CoreOps Provider",
    "company_slug": "coreops-provider",
}


def _auth_headers(client) -> dict[str, str]:
    # Register may 409 on reuse within the same DB session; login still succeeds.
    client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    token = client.post(
        "/api/v1/auth/login",
        json={"email": REGISTER_PAYLOAD["email"], "password": REGISTER_PAYLOAD["password"]},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _flexity_sales_tenant(client):
    headers = _auth_headers(client)
    tenant_id = client.post(
        "/api/v1/tenants",
        json={
            "name": "Flexity Sales Disposition",
            "slug": "flexity-sales-disposition",
            "industry_template_code": "flexity_sales_basic",
            "plan_code": "business",
        },
        headers=headers,
    ).json()["id"]
    tenant_headers = {**headers, "X-Tenant-ID": tenant_id}
    return tenant_headers, tenant_id


def _kindergarten_tenant(client):
    headers = _auth_headers(client)
    tenant_id = client.post(
        "/api/v1/tenants",
        json={
            "name": "Garden Disposition",
            "slug": "garden-disposition",
            "industry_template_code": "kindergarten_basic",
            "plan_code": "business",
        },
        headers=headers,
    ).json()["id"]
    tenant_headers = {**headers, "X-Tenant-ID": tenant_id}
    return tenant_headers, tenant_id


def _create_flexity_sales_work_item(client, headers):
    pipeline = client.get("/api/v1/pipelines", headers=headers).json()[0]
    new_lead_stage = next(stage for stage in pipeline["stages"] if stage["code"] == "new_lead")
    rejected_stage = next(stage for stage in pipeline["stages"] if stage["code"] == "rejected")

    party = client.post(
        "/api/v1/parties",
        headers=headers,
        json={
            "party_type": "person",
            "display_name": "Тестовый лид",
            "party_role": "lead",
        },
    )
    assert party.status_code == 201

    work_item = client.post(
        "/api/v1/work-items",
        headers=headers,
        json={
            "pipeline_id": pipeline["id"],
            "stage_id": new_lead_stage["id"],
            "work_item_type": "lead",
            "title": "Лид для disposition",
            "primary_party_id": party.json()["id"],
            "source": "manual",
        },
    )
    assert work_item.status_code == 201
    return work_item.json(), pipeline, new_lead_stage, rejected_stage


def test_close_moves_work_item_to_rejected(client):
    headers, _ = _flexity_sales_tenant(client)
    item, pipeline, _, rejected_stage = _create_flexity_sales_work_item(client, headers)

    closed = client.post(
        f"/api/v1/work-items/{item['id']}/close",
        headers=headers,
        json={"disposition": "spam"},
    )
    assert closed.status_code == 200
    body = closed.json()
    assert body["stage_id"] == rejected_stage["id"]
    assert body["status"] == "lost"
    assert body["custom_fields"]["disposition"] == "spam"


def test_close_stores_optional_disposition_note(client):
    headers, _ = _flexity_sales_tenant(client)
    item, _, _, _ = _create_flexity_sales_work_item(client, headers)

    closed = client.post(
        f"/api/v1/work-items/{item['id']}/close",
        headers=headers,
        json={
            "disposition": "other",
            "disposition_note": "Случайный звонок",
        },
    )
    assert closed.status_code == 200
    body = closed.json()
    assert body["custom_fields"]["disposition"] == "other"
    assert body["custom_fields"]["disposition_note"] == "Случайный звонок"


def test_close_with_invalid_disposition_returns_validation_error(client):
    headers, _ = _flexity_sales_tenant(client)
    item, _, _, _ = _create_flexity_sales_work_item(client, headers)

    closed = client.post(
        f"/api/v1/work-items/{item['id']}/close",
        headers=headers,
        json={"disposition": "not_a_real_code"},
    )
    assert closed.status_code == 422


def test_close_returns_404_for_cross_tenant_work_item(client):
    headers_a, _ = _flexity_sales_tenant(client)
    item, _, _, _ = _create_flexity_sales_work_item(client, headers_a)

    auth = _auth_headers(client)
    tenant_b = client.post(
        "/api/v1/tenants",
        json={
            "name": "Flexity Sales B",
            "slug": "flexity-sales-disposition-b",
            "industry_template_code": "flexity_sales_basic",
            "plan_code": "business",
        },
        headers=auth,
    ).json()["id"]
    headers_b = {**auth, "X-Tenant-ID": tenant_b}

    closed = client.post(
        f"/api/v1/work-items/{item['id']}/close",
        headers=headers_b,
        json={"disposition": "spam"},
    )
    assert closed.status_code == 404


def test_close_returns_conflict_when_rejected_stage_missing(client):
    # kindergarten_basic has lost/enrolled terminals but no rejected stage.
    headers, _ = _kindergarten_tenant(client)
    pipeline = client.get("/api/v1/pipelines", headers=headers).json()[0]
    first_stage = min(pipeline["stages"], key=lambda stage: stage["sort_order"])

    work_item = client.post(
        "/api/v1/work-items",
        headers=headers,
        json={
            "pipeline_id": pipeline["id"],
            "stage_id": first_stage["id"],
            "work_item_type": "inquiry",
            "title": "Заявка без rejected",
        },
    )
    assert work_item.status_code == 201
    item_id = work_item.json()["id"]

    closed = client.post(
        f"/api/v1/work-items/{item_id}/close",
        headers=headers,
        json={"disposition": "spam"},
    )
    assert closed.status_code == 409
    assert "rejected" in closed.json()["detail"].lower()


def test_reopen_moves_work_item_to_new_lead_and_clears_disposition(client):
    headers, _ = _flexity_sales_tenant(client)
    item, _, new_lead_stage, _ = _create_flexity_sales_work_item(client, headers)

    closed = client.post(
        f"/api/v1/work-items/{item['id']}/close",
        headers=headers,
        json={"disposition": "duplicate", "disposition_note": "Повтор"},
    )
    assert closed.status_code == 200

    reopened = client.post(
        f"/api/v1/work-items/{item['id']}/reopen",
        headers=headers,
        json={},
    )
    assert reopened.status_code == 200
    body = reopened.json()
    assert body["stage_id"] == new_lead_stage["id"]
    assert body["status"] == "in_progress"
    assert body["custom_fields"].get("disposition") is None
    assert body["custom_fields"].get("disposition_note") is None


def test_reopen_returns_404_for_cross_tenant_work_item(client):
    headers_a, _ = _flexity_sales_tenant(client)
    item, _, _, _ = _create_flexity_sales_work_item(client, headers_a)

    closed = client.post(
        f"/api/v1/work-items/{item['id']}/close",
        headers=headers_a,
        json={"disposition": "spam"},
    )
    assert closed.status_code == 200

    auth = _auth_headers(client)
    tenant_b = client.post(
        "/api/v1/tenants",
        json={
            "name": "Flexity Sales Reopen B",
            "slug": "flexity-sales-reopen-b",
            "industry_template_code": "flexity_sales_basic",
            "plan_code": "business",
        },
        headers=auth,
    ).json()["id"]
    headers_b = {**auth, "X-Tenant-ID": tenant_b}

    reopened = client.post(
        f"/api/v1/work-items/{item['id']}/reopen",
        headers=headers_b,
        json={},
    )
    assert reopened.status_code == 404


def test_list_work_items_includes_rejected_lost_items(client):
    headers, _ = _flexity_sales_tenant(client)
    item, pipeline, _, rejected_stage = _create_flexity_sales_work_item(client, headers)

    closed = client.post(
        f"/api/v1/work-items/{item['id']}/close",
        headers=headers,
        json={"disposition": "spam"},
    )
    assert closed.status_code == 200

    listed = client.get(
        f"/api/v1/work-items?pipeline_id={pipeline['id']}&limit=200",
        headers=headers,
    )
    assert listed.status_code == 200
    body = listed.json()
    match = next(row for row in body if row["id"] == item["id"])
    assert match["stage_id"] == rejected_stage["id"]
    assert match["status"] == "lost"
    assert match["custom_fields"]["disposition"] == "spam"


def test_close_creates_activity(client):
    headers, _ = _flexity_sales_tenant(client)
    item, _, _, _ = _create_flexity_sales_work_item(client, headers)

    closed = client.post(
        f"/api/v1/work-items/{item['id']}/close",
        headers=headers,
        json={"disposition": "test"},
    )
    assert closed.status_code == 200

    detail = client.get(f"/api/v1/work-items/{item['id']}", headers=headers)
    assert detail.status_code == 200
    activities = detail.json()["activities"]
    assert any("закрыт" in activity["title"].lower() for activity in activities)
