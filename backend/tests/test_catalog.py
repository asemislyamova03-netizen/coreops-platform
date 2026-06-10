REGISTER_PAYLOAD = {
    "email": "owner@example.com",
    "password": "securepass123",
    "full_name": "Platform Owner",
    "company_name": "CoreOps Provider",
    "company_slug": "coreops-provider",
}


def _catalog_tenant(client):
    client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    token = client.post(
        "/api/v1/auth/login",
        json={"email": REGISTER_PAYLOAD["email"], "password": REGISTER_PAYLOAD["password"]},
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    tenant_id = client.post(
        "/api/v1/tenants",
        json={
            "name": "Catalog Tenant",
            "slug": "catalog-tenant",
            "industry_template_code": "kindergarten_basic",
            "plan_code": "business",
        },
        headers=headers,
    ).json()["id"]

    return {**headers, "X-Tenant-ID": tenant_id}


def test_catalog_item_and_price_list(client):
    headers = _catalog_tenant(client)

    unit = client.post(
        "/api/v1/catalog/units",
        headers=headers,
        json={"code": "month", "name": "Месяц", "symbol": "мес"},
    )
    assert unit.status_code == 201

    service = client.post(
        "/api/v1/catalog/items",
        headers=headers,
        json={
            "item_type": "subscription_service",
            "name": "Дополнительные занятия (месяц)",
            "sku": "extra-classes-monthly",
            "unit_id": unit.json()["id"],
            "base_price": "15000.00",
            "currency": "RUB",
        },
    )
    assert service.status_code == 201
    item_id = service.json()["id"]

    fee = client.post(
        "/api/v1/catalog/items",
        headers=headers,
        json={
            "item_type": "fee",
            "name": "Материальный взнос",
            "sku": "materials-fee",
            "base_price": "5000",
            "currency": "RUB",
        },
    )
    assert fee.status_code == 201

    listed = client.get(
        "/api/v1/catalog/items?item_type=subscription_service",
        headers=headers,
    )
    assert listed.status_code == 200
    assert any(item["id"] == item_id for item in listed.json())

    price_list = client.post(
        "/api/v1/catalog/price-lists",
        headers=headers,
        json={"code": "default_2025", "name": "Основной прайс", "currency": "RUB"},
    )
    assert price_list.status_code == 201
    pl_id = price_list.json()["id"]

    pl_item = client.post(
        f"/api/v1/catalog/price-lists/{pl_id}/items",
        headers=headers,
        json={"catalog_item_id": item_id, "price": "14500.00"},
    )
    assert pl_item.status_code == 201

    fetched = client.get(f"/api/v1/catalog/price-lists/{pl_id}", headers=headers)
    assert fetched.status_code == 200
    assert len(fetched.json()["items"]) == 1
    assert fetched.json()["items"][0]["price"] == "14500.00"


def test_catalog_module_guard(client):
    headers = _catalog_tenant(client)
    tenant_id = headers["X-Tenant-ID"]
    provider_headers = {k: v for k, v in headers.items() if k != "X-Tenant-ID"}

    client.post(
        f"/api/v1/tenants/{tenant_id}/modules/catalog/disable",
        headers=provider_headers,
    )

    blocked = client.get("/api/v1/catalog/items", headers=headers)
    assert blocked.status_code == 403


def test_duplicate_sku(client):
    headers = _catalog_tenant(client)
    payload = {
        "item_type": "product",
        "name": "Товар A",
        "sku": "sku-a",
        "base_price": "100",
        "currency": "RUB",
    }
    assert client.post("/api/v1/catalog/items", headers=headers, json=payload).status_code == 201
    dup = client.post("/api/v1/catalog/items", headers=headers, json=payload)
    assert dup.status_code == 409
