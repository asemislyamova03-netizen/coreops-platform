import uuid

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


def test_list_industry_templates_includes_kindergarten(client):
    headers = _auth(client)
    response = client.get("/api/v1/industry-templates", headers=headers)
    assert response.status_code == 200
    codes = {t["code"] for t in response.json()}
    assert "kindergarten_basic" in codes


def test_apply_template_to_tenant(client):
    headers = _auth(client)
    tenant_id = client.post(
        "/api/v1/tenants",
        json={"name": "Garden", "slug": "garden-school"},
        headers=headers,
    ).json()["id"]

    template_id = next(
        t["id"]
        for t in client.get("/api/v1/industry-templates", headers=headers).json()
        if t["code"] == "kindergarten_basic"
    )

    applied = client.post(
        f"/api/v1/tenants/{tenant_id}/apply-template/{template_id}",
        headers=headers,
    )
    assert applied.status_code == 200
    body = applied.json()
    assert body["template_code"] == "kindergarten_basic"
    assert "crm" in body["modules_enabled"]
    assert "parties" in body["modules_enabled"]
    assert body["pipelines_created"] == ["enrollment"]
    assert body["custom_fields_created"] == 7

    labels = client.get(f"/api/v1/tenants/{tenant_id}/labels", headers=headers)
    assert labels.status_code == 200
    assert labels.json()["entities"]["work_item"] == "Заявка"

    tenant_headers = {**headers, "X-Tenant-ID": tenant_id}
    catalog = client.get("/api/v1/catalog/items", headers=tenant_headers)
    assert catalog.status_code == 200
    items_by_sku = {item["sku"]: item for item in catalog.json()}
    assert set(items_by_sku) == {"edu-monthly", "registration-fee", "enrollment-fee"}
    assert items_by_sku["edu-monthly"]["base_price"] == "25000.00"
    assert items_by_sku["edu-monthly"]["currency"] == "KZT"


def test_pipelines_after_template_apply(client):
    headers = _auth(client)
    tenant_id = client.post(
        "/api/v1/tenants",
        json={
            "name": "Garden 2",
            "slug": "garden-school-2",
            "industry_template_code": "kindergarten_basic",
        },
        headers=headers,
    ).json()["id"]

    tenant_headers = {**headers, "X-Tenant-ID": tenant_id}
    pipelines = client.get("/api/v1/pipelines", headers=tenant_headers)
    assert pipelines.status_code == 200
    data = pipelines.json()
    assert len(data) == 1
    assert data[0]["code"] == "enrollment"
    assert len(data[0]["stages"]) == 9


def test_apply_template_idempotent_modules(client):
    headers = _auth(client)
    tenant_id = client.post(
        "/api/v1/tenants",
        json={"name": "Garden 3", "slug": "garden-school-3"},
        headers=headers,
    ).json()["id"]
    template_id = next(
        t["id"]
        for t in client.get("/api/v1/industry-templates", headers=headers).json()
        if t["code"] == "kindergarten_basic"
    )

    client.post(f"/api/v1/tenants/{tenant_id}/apply-template/{template_id}", headers=headers)
    second = client.post(
        f"/api/v1/tenants/{tenant_id}/apply-template/{template_id}",
        headers=headers,
    )
    assert second.status_code == 200
    assert second.json()["pipelines_created"] == []
    assert second.json()["custom_fields_created"] == 0

    tenant_headers = {**headers, "X-Tenant-ID": tenant_id}
    catalog = client.get("/api/v1/catalog/items", headers=tenant_headers)
    assert catalog.status_code == 200
    assert sorted(item["sku"] for item in catalog.json()) == [
        "edu-monthly",
        "enrollment-fee",
        "registration-fee",
    ]
