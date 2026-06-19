REGISTER_PAYLOAD = {
    "email": "owner@example.com",
    "password": "securepass123",
    "full_name": "Platform Owner",
    "company_name": "CoreOps Provider",
    "company_slug": "coreops-provider",
}


def _setup_tenant_with_parties_module(client):
    client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    token = client.post(
        "/api/v1/auth/login",
        json={"email": REGISTER_PAYLOAD["email"], "password": REGISTER_PAYLOAD["password"]},
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    tenant_id = client.post(
        "/api/v1/tenants",
        json={
            "name": "Garden",
            "slug": "garden-parties",
            "industry_template_code": "kindergarten_basic",
        },
        headers=headers,
    ).json()["id"]

    tenant_headers = {**headers, "X-Tenant-ID": tenant_id}
    return tenant_headers, tenant_id


def test_parties_module_required(client):
    headers, tenant_id = _setup_tenant_with_parties_module(client)

    client.post(
        f"/api/v1/tenants/{tenant_id}/modules/parties/disable",
        headers=headers,
    )

    blocked = client.get("/api/v1/parties", headers=headers)
    assert blocked.status_code == 403

    client.post(
        f"/api/v1/tenants/{tenant_id}/modules/parties/enable",
        headers=headers,
    )
    allowed = client.get("/api/v1/parties", headers=headers)
    assert allowed.status_code == 200


def test_create_party_with_custom_fields(client):
    headers, _ = _setup_tenant_with_parties_module(client)

    created = client.post(
        "/api/v1/parties",
        headers=headers,
        json={
            "party_type": "person",
            "display_name": "Иван Петров",
            "party_role": "enrollee",
            "contact_methods": [
                {"method_type": "email", "value": "parent@example.com", "is_primary": True}
            ],
            "custom_fields": {
                "birth_date": "2020-05-15",
                "allergies": "нет",
                "group_name": "Солнышко",
            },
        },
    )
    assert created.status_code == 201
    body = created.json()
    assert body["display_name"] == "Иван Петров"
    assert body["custom_fields"]["group_name"] == "Солнышко"
    assert body["metadata_json"]["party_role"] == "enrollee"
    assert len(body["contact_methods"]) == 1

    party_id = body["id"]
    fetched = client.get(f"/api/v1/parties/{party_id}", headers=headers)
    assert fetched.status_code == 200

    listed = client.get("/api/v1/parties?search=Петров", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1


def test_list_parties_by_party_role(client):
    headers, _ = _setup_tenant_with_parties_module(client)

    guardian = client.post(
        "/api/v1/parties",
        headers=headers,
        json={
            "party_type": "person",
            "display_name": "Родитель Сидоров",
            "party_role": "guardian",
        },
    )
    assert guardian.status_code == 201

    enrollee = client.post(
        "/api/v1/parties",
        headers=headers,
        json={
            "party_type": "person",
            "display_name": "Ребёнок Сидоров",
            "party_role": "enrollee",
            "custom_fields": {
                "birth_date": "2020-05-15",
                "allergies": "нет",
                "group_name": "Солнышко",
            },
        },
    )
    assert enrollee.status_code == 201

    guardians = client.get("/api/v1/parties?party_role=guardian", headers=headers)
    assert guardians.status_code == 200
    names = {item["display_name"] for item in guardians.json()}
    assert "Родитель Сидоров" in names
    assert "Ребёнок Сидоров" not in names
    assert "Иван Петров" not in names


def test_custom_field_definitions_list(client):
    headers, _ = _setup_tenant_with_parties_module(client)
    response = client.get("/api/v1/parties/custom-field-definitions", headers=headers)
    assert response.status_code == 200
    keys = {item["field_key"] for item in response.json()}
    assert "birth_date" in keys
    assert "group_name" in keys


def test_required_custom_field_validation(client):
    headers, _ = _setup_tenant_with_parties_module(client)
    response = client.post(
        "/api/v1/parties",
        headers=headers,
        json={
            "party_type": "person",
            "display_name": "Без даты рождения",
            "party_role": "enrollee",
            "custom_fields": {"allergies": "нет"},
        },
    )
    assert response.status_code == 409


def test_update_and_delete_party(client):
    headers, _ = _setup_tenant_with_parties_module(client)
    created = client.post(
        "/api/v1/parties",
        headers=headers,
        json={
            "party_type": "person",
            "display_name": "Мария",
            "party_role": "enrollee",
            "custom_fields": {
                "birth_date": "2019-01-01",
                "allergies": "пыльца",
            },
        },
    )
    party_id = created.json()["id"]

    updated = client.patch(
        f"/api/v1/parties/{party_id}",
        headers=headers,
        json={"display_name": "Мария С.", "status": "inactive"},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "inactive"

    deleted = client.delete(f"/api/v1/parties/{party_id}", headers=headers)
    assert deleted.status_code == 204

    missing = client.get(f"/api/v1/parties/{party_id}", headers=headers)
    assert missing.status_code == 404
