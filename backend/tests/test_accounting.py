import uuid


def _accounting_tenant(client) -> dict[str, str]:
    uid = uuid.uuid4().hex[:8]
    register_payload = {
        "email": f"accounting-{uid}@example.com",
        "password": "securepass123",
        "full_name": "Accounting Owner",
        "company_name": "Accounting Provider",
        "company_slug": f"accounting-provider-{uid}",
    }
    client.post("/api/v1/auth/register", json=register_payload)
    token = client.post(
        "/api/v1/auth/login",
        json={"email": register_payload["email"], "password": register_payload["password"]},
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    tenant_id = client.post(
        "/api/v1/tenants",
        json={
            "name": f"Accounting Tenant {uid}",
            "slug": f"accounting-tenant-{uid}",
            "plan_code": "enterprise",
        },
        headers=headers,
    ).json()["id"]

    provider_headers = {k: v for k, v in headers.items()}
    client.post(f"/api/v1/tenants/{tenant_id}/modules/accounting/enable", headers=provider_headers)
    return {**headers, "X-Tenant-ID": tenant_id}


def test_tax_profile_requires_existing_legal_entity(client):
    headers = _accounting_tenant(client)
    missing_entity = uuid.uuid4()
    response = client.post(
        "/api/v1/accounting/tax-profiles",
        headers=headers,
        json={
            "legal_entity_id": str(missing_entity),
            "code": "vat-20",
            "name": "VAT 20%",
            "tax_regime": "general",
        },
    )
    assert response.status_code == 404
    assert "legal entity not found" in response.json()["detail"].lower()


def test_tax_profile_code_must_be_unique_per_tenant(client):
    headers = _accounting_tenant(client)
    legal_entity = client.post(
        "/api/v1/accounting/legal-entities",
        headers=headers,
        json={"name": "ООО Учет", "country": "RU", "tax_number": "7700000010"},
    )
    assert legal_entity.status_code == 201
    legal_entity_id = legal_entity.json()["id"]

    payload = {
        "legal_entity_id": legal_entity_id,
        "code": "vat-main",
        "name": "Основной НДС",
        "tax_regime": "general",
    }
    created = client.post("/api/v1/accounting/tax-profiles", headers=headers, json=payload)
    assert created.status_code == 201

    duplicate = client.post("/api/v1/accounting/tax-profiles", headers=headers, json=payload)
    assert duplicate.status_code == 409
    assert "already exists" in duplicate.json()["detail"].lower()
