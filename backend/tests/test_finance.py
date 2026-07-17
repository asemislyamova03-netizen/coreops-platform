import uuid


def _finance_tenant(client) -> tuple[dict[str, str], str]:
    uid = uuid.uuid4().hex[:8]
    register_payload = {
        "email": f"finance-{uid}@example.com",
        "password": "securepass123",
        "full_name": "Finance Owner",
        "company_name": "Finance Provider",
        "company_slug": f"finance-provider-{uid}",
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
            "name": f"Finance Tenant {uid}",
            "slug": f"finance-tenant-{uid}",
            "industry_template_code": "kindergarten_basic",
            "plan_code": "business",
        },
        headers=headers,
    ).json()["id"]

    tenant_headers = {**headers, "X-Tenant-ID": tenant_id}
    return tenant_headers, tenant_id


def _create_party(client, headers: dict[str, str]) -> str:
    response = client.post(
        "/api/v1/parties",
        headers=headers,
        json={
            "party_type": "person",
            "display_name": "Финансовый клиент",
            "party_role": "guardian",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def _create_invoice(client, headers: dict[str, str], party_id: str, issue: bool = True) -> str:
    response = client.post(
        "/api/v1/finance/invoices",
        headers=headers,
        json={
            "party_id": party_id,
            "lines": [{"description": "Абонемент", "quantity": "1", "unit_price": "12000"}],
            "issue": issue,
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def _create_payment(
    client,
    headers: dict[str, str],
    party_id: str,
    amount: str,
    status: str = "completed",
) -> str:
    response = client.post(
        "/api/v1/finance/payments",
        headers=headers,
        json={
            "party_id": party_id,
            "amount": amount,
            "currency": "RUB",
            "payment_date": "2025-09-15",
            "status": status,
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_allocate_payment_requires_completed_status(client):
    headers, _ = _finance_tenant(client)
    party_id = _create_party(client, headers)
    invoice_id = _create_invoice(client, headers, party_id)
    payment_id = _create_payment(client, headers, party_id, amount="12000", status="pending")

    allocate = client.post(
        f"/api/v1/finance/payments/{payment_id}/allocate",
        headers=headers,
        json={"allocations": [{"invoice_id": invoice_id, "amount": "12000"}]},
    )
    assert allocate.status_code == 409
    assert "Only completed payments" in allocate.json()["detail"]


def test_allocate_payment_prevents_overallocation_and_duplicate(client):
    headers, _ = _finance_tenant(client)
    party_id = _create_party(client, headers)
    invoice_id = _create_invoice(client, headers, party_id)
    payment_id = _create_payment(client, headers, party_id, amount="12000")

    over_allocate = client.post(
        f"/api/v1/finance/payments/{payment_id}/allocate",
        headers=headers,
        json={"allocations": [{"invoice_id": invoice_id, "amount": "13000"}]},
    )
    assert over_allocate.status_code == 409
    assert "exceeds" in over_allocate.json()["detail"].lower()

    first = client.post(
        f"/api/v1/finance/payments/{payment_id}/allocate",
        headers=headers,
        json={"allocations": [{"invoice_id": invoice_id, "amount": "6000"}]},
    )
    assert first.status_code == 200
    assert first.json()["amount_allocated"] == "6000.00"
    assert first.json()["unallocated_amount"] == "6000.00"

    duplicate = client.post(
        f"/api/v1/finance/payments/{payment_id}/allocate",
        headers=headers,
        json={"allocations": [{"invoice_id": invoice_id, "amount": "1000"}]},
    )
    assert duplicate.status_code == 409
    assert "already allocated" in duplicate.json()["detail"].lower()


def test_invoice_and_receivables_status_after_partial_and_full_payment(client):
    headers, _ = _finance_tenant(client)
    party_id = _create_party(client, headers)
    invoice_id = _create_invoice(client, headers, party_id)
    payment_id = _create_payment(client, headers, party_id, amount="12000")

    partial = client.post(
        f"/api/v1/finance/payments/{payment_id}/allocate",
        headers=headers,
        json={"allocations": [{"invoice_id": invoice_id, "amount": "5000"}]},
    )
    assert partial.status_code == 200

    invoice_after_partial = client.get(f"/api/v1/finance/invoices/{invoice_id}", headers=headers)
    assert invoice_after_partial.status_code == 200
    assert invoice_after_partial.json()["status"] == "partial"
    assert invoice_after_partial.json()["balance_due"] == "7000.00"

    receivables_partial = client.get("/api/v1/finance/receivables", headers=headers)
    assert receivables_partial.status_code == 200
    assert len(receivables_partial.json()) == 1
    assert receivables_partial.json()[0]["balance_due"] == "7000.00"

    remaining_payment_id = _create_payment(client, headers, party_id, amount="7000")
    full = client.post(
        f"/api/v1/finance/payments/{remaining_payment_id}/allocate",
        headers=headers,
        json={"allocations": [{"invoice_id": invoice_id, "amount": "7000"}]},
    )
    assert full.status_code == 200

    invoice_after_full = client.get(f"/api/v1/finance/invoices/{invoice_id}", headers=headers)
    assert invoice_after_full.status_code == 200
    assert invoice_after_full.json()["status"] == "paid"
    assert invoice_after_full.json()["balance_due"] == "0.00"

    receivables_full = client.get("/api/v1/finance/receivables", headers=headers)
    assert receivables_full.status_code == 200
    assert receivables_full.json() == []


def test_payment_direction_default_and_explicit(client):
    headers, _ = _finance_tenant(client)
    party_id = _create_party(client, headers)

    defaulted = client.post(
        "/api/v1/finance/payments",
        headers=headers,
        json={
            "party_id": party_id,
            "amount": "1000",
            "currency": "RUB",
            "payment_date": "2026-01-10",
        },
    )
    assert defaulted.status_code == 201
    assert defaulted.json()["direction"] == "incoming"
    assert defaulted.json()["status"] == "completed"

    outgoing = client.post(
        "/api/v1/finance/payments",
        headers=headers,
        json={
            "party_id": party_id,
            "amount": "500",
            "currency": "RUB",
            "payment_date": "2026-01-11",
            "direction": "outgoing",
        },
    )
    assert outgoing.status_code == 201
    assert outgoing.json()["direction"] == "outgoing"

    fetched = client.get(
        f"/api/v1/finance/payments/{outgoing.json()['id']}",
        headers=headers,
    )
    assert fetched.status_code == 200
    assert fetched.json()["direction"] == "outgoing"


def test_payment_legacy_type_maps_direction(client):
    headers, _ = _finance_tenant(client)
    party_id = _create_party(client, headers)

    income = client.post(
        "/api/v1/finance/payments",
        headers=headers,
        json={
            "party_id": party_id,
            "amount": "2000",
            "currency": "RUB",
            "payment_date": "2026-01-12",
            "legacy_payment_type": "INCOME",
        },
    )
    assert income.status_code == 201
    assert income.json()["direction"] == "incoming"
    assert income.json()["status"] == "completed"

    expense = client.post(
        "/api/v1/finance/payments",
        headers=headers,
        json={
            "party_id": party_id,
            "amount": "300",
            "currency": "RUB",
            "payment_date": "2026-01-13",
            "legacy_payment_type": "EXPENSE",
        },
    )
    assert expense.status_code == 201
    assert expense.json()["direction"] == "outgoing"
    assert expense.json()["status"] == "completed"

    unknown = client.post(
        "/api/v1/finance/payments",
        headers=headers,
        json={
            "party_id": party_id,
            "amount": "50",
            "currency": "RUB",
            "payment_date": "2026-01-14",
            "legacy_payment_type": "WEIRD",
        },
    )
    assert unknown.status_code == 201
    assert unknown.json()["direction"] == "needs_review"
    assert unknown.json()["status"] == "pending"
