"""Tests for Core CRM E2 Party Match API."""

from app.modules.parties.matching import (
    normalize_email,
    normalize_phone_digits,
    normalize_telegram_user_id,
    normalize_telegram_username,
    phones_match,
    telegram_user_ids_match,
    telegram_usernames_match,
)

REGISTER_PAYLOAD = {
    "email": "owner@example.com",
    "password": "securepass123",
    "full_name": "Platform Owner",
    "company_name": "CoreOps Provider",
    "company_slug": "coreops-provider",
}


def _setup_tenant(client):
    client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    token = client.post(
        "/api/v1/auth/login",
        json={"email": REGISTER_PAYLOAD["email"], "password": REGISTER_PAYLOAD["password"]},
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    tenant_id = client.post(
        "/api/v1/tenants",
        json={
            "name": "Sales Match",
            "slug": "sales-match",
            "industry_template_code": "flexity_sales_basic",
        },
        headers=headers,
    ).json()["id"]

    return {**headers, "X-Tenant-ID": tenant_id}, tenant_id, headers


def test_normalize_helpers():
    assert normalize_email("  Ivan@Example.COM ") == "ivan@example.com"
    assert normalize_phone_digits("+7 (777) 123-45-67") == "77771234567"
    assert normalize_phone_digits("8 777 123 45 67") == "77771234567"
    assert normalize_phone_digits("12345") is None
    assert normalize_telegram_username("@Ivan_User") == "ivan_user"
    assert normalize_telegram_user_id(" 123456 ") == "123456"
    assert phones_match("+77771234567", "8 (777) 123-45-67")
    assert telegram_usernames_match("@Ivan", "ivan")
    assert telegram_user_ids_match("12345", "12345")
    assert not telegram_user_ids_match("ivan", "ivan")


def test_match_empty_payload_returns_422(client):
    tenant_headers, _, _ = _setup_tenant(client)
    response = client.post("/api/v1/parties/match", headers=tenant_headers, json={})
    assert response.status_code == 422


def test_match_blank_fields_returns_422(client):
    tenant_headers, _, _ = _setup_tenant(client)
    response = client.post(
        "/api/v1/parties/match",
        headers=tenant_headers,
        json={"name": "  ", "phone": "", "email": None},
    )
    assert response.status_code == 422


def test_match_phone_and_email_exact(client):
    tenant_headers, _, _ = _setup_tenant(client)

    created = client.post(
        "/api/v1/parties",
        headers=tenant_headers,
        json={
            "party_type": "person",
            "display_name": "Иван Петров",
            "contact_methods": [
                {"method_type": "phone", "value": "+7 777 111 22 33", "is_primary": True},
                {"method_type": "email", "value": "ivan@Example.com"},
            ],
        },
    )
    assert created.status_code == 201
    party_id = created.json()["id"]

    matched = client.post(
        "/api/v1/parties/match",
        headers=tenant_headers,
        json={"phone": "87771112233", "email": "IVAN@example.com"},
    )
    assert matched.status_code == 200
    body = matched.json()
    assert body["query_normalized"]["phone"] == "77771112233"
    assert body["query_normalized"]["email"] == "ivan@example.com"
    assert len(body["matches"]) == 1
    hit = body["matches"][0]
    assert hit["party_id"] == party_id
    assert hit["match_type"] == "exact"
    assert "phone" in hit["matched_on"]
    assert "email" in hit["matched_on"]
    assert hit["score"] >= 90
    assert len(hit["contact_methods"]) == 2


def test_match_telegram_username_and_user_id_metadata(client, db_session):
    import uuid

    from app.modules.parties.models import Party

    tenant_headers, tenant_id, _ = _setup_tenant(client)

    created = client.post(
        "/api/v1/parties",
        headers=tenant_headers,
        json={
            "party_type": "person",
            "display_name": "Telegram User",
            "contact_methods": [
                {"method_type": "telegram", "value": "@flexity_user", "is_primary": True}
            ],
            "metadata_json": {"telegram": {"user_id": "998877"}},
        },
    )
    assert created.status_code == 201
    party_id = created.json()["id"]

    # Ensure metadata persisted (create API stores metadata_json).
    party = db_session.get(Party, uuid.UUID(party_id))
    assert party is not None
    assert party.metadata_json.get("telegram", {}).get("user_id") == "998877"

    by_username = client.post(
        "/api/v1/parties/match",
        headers=tenant_headers,
        json={"telegram_username": "Flexity_User"},
    )
    assert by_username.status_code == 200
    assert by_username.json()["matches"][0]["party_id"] == party_id
    assert "telegram_username" in by_username.json()["matches"][0]["matched_on"]

    by_user_id = client.post(
        "/api/v1/parties/match",
        headers=tenant_headers,
        json={"telegram_user_id": "998877"},
    )
    assert by_user_id.status_code == 200
    assert by_user_id.json()["matches"][0]["party_id"] == party_id
    assert "telegram_user_id" in by_user_id.json()["matches"][0]["matched_on"]


def test_match_whatsapp(client):
    tenant_headers, _, _ = _setup_tenant(client)
    created = client.post(
        "/api/v1/parties",
        headers=tenant_headers,
        json={
            "party_type": "person",
            "display_name": "WA Contact",
            "contact_methods": [
                {"method_type": "whatsapp", "value": "+7 701 000 11 22", "is_primary": True}
            ],
        },
    )
    assert created.status_code == 201
    party_id = created.json()["id"]

    matched = client.post(
        "/api/v1/parties/match",
        headers=tenant_headers,
        json={"whatsapp": "87010001122"},
    )
    assert matched.status_code == 200
    hit = matched.json()["matches"][0]
    assert hit["party_id"] == party_id
    assert hit["match_type"] == "exact"
    assert "whatsapp" in hit["matched_on"]


def test_match_weak_name_only(client):
    tenant_headers, _, _ = _setup_tenant(client)
    client.post(
        "/api/v1/parties",
        headers=tenant_headers,
        json={"party_type": "person", "display_name": "Асем Ислямова"},
    )

    matched = client.post(
        "/api/v1/parties/match",
        headers=tenant_headers,
        json={"name": "асем"},
    )
    assert matched.status_code == 200
    body = matched.json()
    assert len(body["matches"]) >= 1
    assert body["matches"][0]["match_type"] == "weak"
    assert body["matches"][0]["matched_on"] == ["name"]
    assert body["matches"][0]["score"] == 30


def test_match_does_not_create_party(client):
    tenant_headers, _, _ = _setup_tenant(client)
    before = client.get("/api/v1/parties", headers=tenant_headers)
    assert before.status_code == 200
    count_before = len(before.json())

    matched = client.post(
        "/api/v1/parties/match",
        headers=tenant_headers,
        json={"phone": "+7 700 111 22 33"},
    )
    assert matched.status_code == 200
    assert matched.json()["matches"] == []

    after = client.get("/api/v1/parties", headers=tenant_headers)
    assert len(after.json()) == count_before


def test_match_tenant_isolation(client):
    tenant_a, _, owner_headers = _setup_tenant(client)
    created = client.post(
        "/api/v1/parties",
        headers=tenant_a,
        json={
            "party_type": "person",
            "display_name": "Private Contact",
            "contact_methods": [
                {"method_type": "email", "value": "secret@example.com", "is_primary": True}
            ],
        },
    )
    assert created.status_code == 201

    tenant_b_id = client.post(
        "/api/v1/tenants",
        json={"name": "Other Tenant", "slug": "other-match-tenant"},
        headers=owner_headers,
    ).json()["id"]
    # enable parties on second tenant via kindergarten or sales template
    client.post(
        f"/api/v1/tenants/{tenant_b_id}/modules/parties/enable",
        headers=owner_headers,
    )
    tenant_b = {**owner_headers, "X-Tenant-ID": tenant_b_id}

    matched = client.post(
        "/api/v1/parties/match",
        headers=tenant_b,
        json={"email": "secret@example.com"},
    )
    assert matched.status_code == 200
    assert matched.json()["matches"] == []


def test_match_two_parties_same_phone(client):
    tenant_headers, _, _ = _setup_tenant(client)
    for name in ("A One", "B Two"):
        created = client.post(
            "/api/v1/parties",
            headers=tenant_headers,
            json={
                "party_type": "person",
                "display_name": name,
                "contact_methods": [
                    {"method_type": "phone", "value": "+77770001122", "is_primary": True}
                ],
            },
        )
        assert created.status_code == 201

    matched = client.post(
        "/api/v1/parties/match",
        headers=tenant_headers,
        json={"phone": "87770001122"},
    )
    assert matched.status_code == 200
    assert len(matched.json()["matches"]) == 2
    assert all(hit["match_type"] == "exact" for hit in matched.json()["matches"])
