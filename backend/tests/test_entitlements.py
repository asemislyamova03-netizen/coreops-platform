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


def test_list_plans(client):
    headers = _auth(client)
    response = client.get("/api/v1/plans", headers=headers)
    assert response.status_code == 200
    codes = {p["code"] for p in response.json()}
    assert codes == {"starter", "business", "enterprise"}


def test_assign_plan_enables_modules(client):
    headers = _auth(client)
    tenant = client.post(
        "/api/v1/tenants",
        json={"name": "Starter Client", "slug": "starter-client", "plan_code": "starter"},
        headers=headers,
    )
    assert tenant.status_code == 201
    tenant_id = tenant.json()["id"]

    subscription = client.get(
        f"/api/v1/tenants/{tenant_id}/subscription",
        headers=headers,
    )
    assert subscription.status_code == 200
    assert subscription.json()["plan_code"] == "starter"

    modules = client.get(f"/api/v1/tenants/{tenant_id}/modules", headers=headers).json()
    by_code = {m["module_code"]: m for m in modules}
    assert by_code["crm"]["status"] == "trial"
    assert by_code["parties"]["status"] == "trial"


def test_entitlement_feature_check(client, db_session):
    import uuid

    from app.core.entitlements import EntitlementService

    headers = _auth(client)
    tenant_id = client.post(
        "/api/v1/tenants",
        json={"name": "Biz", "slug": "biz-client", "plan_code": "business"},
        headers=headers,
    ).json()["id"]

    service = EntitlementService(db_session, uuid.UUID(tenant_id))
    service.assert_feature("finance.invoices.create")

    try:
        service.assert_feature("ai.tasks.create")
        raised = False
    except Exception:
        raised = True
    assert raised
