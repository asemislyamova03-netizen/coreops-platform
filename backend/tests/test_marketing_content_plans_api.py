"""M7.5-B HTTP API tests: Content Plans + items."""

from __future__ import annotations

from fastapi.testclient import TestClient

PLANS = "/api/v1/marketing/content-plans"
RUBRICS = "/api/v1/marketing/rubrics"
GUIDES = "/api/v1/marketing/guides"


def _setup(client: TestClient, *, suffix: str) -> tuple[dict[str, str], str]:
    email = f"m75b-{suffix}@example.com"
    password = "securepass123"
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": f"M75B {suffix}",
            "company_name": f"M75B Co {suffix}",
            "company_slug": f"m75b-co-{suffix}",
        },
    )
    assert reg.status_code == 201, reg.text
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    tenant = client.post(
        "/api/v1/tenants",
        json={"name": f"M75B Tenant {suffix}", "slug": f"m75b-tenant-{suffix}"},
        headers=headers,
    )
    assert tenant.status_code == 201, tenant.text
    tenant_id = tenant.json()["id"]
    headers = {**headers, "X-Tenant-ID": tenant_id}
    assert (
        client.post(
            f"/api/v1/tenants/{tenant_id}/modules/parties/enable", headers=headers
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/v1/tenants/{tenant_id}/modules/marketing/enable", headers=headers
        ).status_code
        == 200
    )
    return headers, tenant_id


def _setup_two_tenants(
    client: TestClient, *, suffix: str
) -> tuple[dict[str, str], dict[str, str]]:
    email = f"m75b-iso-{suffix}@example.com"
    password = "securepass123"
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": f"M75B Iso {suffix}",
            "company_name": f"M75B Iso Co {suffix}",
            "company_slug": f"m75b-iso-co-{suffix}",
        },
    )
    assert reg.status_code == 201, reg.text
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    tenant_a = client.post(
        "/api/v1/tenants",
        json={"name": f"Iso A {suffix}", "slug": f"m75b-iso-a-{suffix}"},
        headers=headers,
    )
    assert tenant_a.status_code == 201, tenant_a.text
    tenant_b = client.post(
        "/api/v1/tenants",
        json={"name": f"Iso B {suffix}", "slug": f"m75b-iso-b-{suffix}"},
        headers=headers,
    )
    assert tenant_b.status_code == 201, tenant_b.text
    id_a, id_b = tenant_a.json()["id"], tenant_b.json()["id"]
    for tenant_id in (id_a, id_b):
        h = {**headers, "X-Tenant-ID": tenant_id}
        assert (
            client.post(
                f"/api/v1/tenants/{tenant_id}/modules/parties/enable", headers=h
            ).status_code
            == 200
        )
        assert (
            client.post(
                f"/api/v1/tenants/{tenant_id}/modules/marketing/enable", headers=h
            ).status_code
            == 200
        )
    return ({**headers, "X-Tenant-ID": id_a}, {**headers, "X-Tenant-ID": id_b})


def _active_rubric(client: TestClient, headers: dict[str, str], code: str = "asem_column"):
    created = client.post(
        RUBRICS,
        headers=headers,
        json={"code": code, "name": code.replace("_", " ").title(), "sort_order": 1},
    )
    assert created.status_code == 201, created.text
    return created.json()


def _create_plan(client: TestClient, headers: dict[str, str], **overrides):
    body = {
        "title": "2026-08 Flexity",
        "period_start": "2026-08-01",
        "period_end": "2026-08-31",
    }
    body.update(overrides)
    created = client.post(PLANS, headers=headers, json=body)
    assert created.status_code == 201, created.text
    return created.json()


def test_plan_header_only_and_invalid_period(client: TestClient):
    headers, _ = _setup(client, suffix="period")
    bad = client.post(
        PLANS,
        headers=headers,
        json={
            "title": "Bad",
            "period_start": "2026-08-31",
            "period_end": "2026-08-01",
        },
    )
    assert bad.status_code == 409
    assert "invalid_period" in bad.text

    plan = _create_plan(client, headers)
    assert plan["status"] == "draft"
    assert plan["source"] == "manual"
    assert plan["import_fingerprint"] is None
    # Nested items not accepted on create schema — ignored if present, no items created.
    listed = client.get(f"{PLANS}/{plan['id']}/items", headers=headers)
    assert listed.status_code == 200
    assert listed.json() == []


def test_fingerprint_not_accepted_on_create_or_patch(client: TestClient):
    headers, _ = _setup(client, suffix="fp")
    created = client.post(
        PLANS,
        headers=headers,
        json={
            "title": "FP",
            "period_start": "2026-08-01",
            "period_end": "2026-08-07",
            "import_fingerprint": "should-be-ignored",
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["import_fingerprint"] is None

    patched = client.patch(
        f"{PLANS}/{created.json()['id']}",
        headers=headers,
        json={"import_fingerprint": "still-ignored", "title": "FP2"},
    )
    assert patched.status_code == 200
    assert patched.json()["import_fingerprint"] is None
    assert patched.json()["title"] == "FP2"


def test_item_ordering_and_date_validation(client: TestClient):
    headers, _ = _setup(client, suffix="order")
    rubric = _active_rubric(client, headers)
    plan = _create_plan(client, headers)
    out = client.post(
        f"{PLANS}/{plan['id']}/items",
        headers=headers,
        json={
            "planned_date": "2026-09-01",
            "rubric_id": rubric["id"],
            "working_title": "Out",
        },
    )
    assert out.status_code == 409
    assert "planned_date_out_of_period" in out.text

    first = client.post(
        f"{PLANS}/{plan['id']}/items",
        headers=headers,
        json={
            "planned_date": "2026-08-02",
            "rubric_id": rubric["id"],
            "working_title": "B",
            "sort_order": 2,
            "line_key": "k2",
        },
    )
    assert first.status_code == 201, first.text
    second = client.post(
        f"{PLANS}/{plan['id']}/items",
        headers=headers,
        json={
            "planned_date": "2026-08-01",
            "rubric_id": rubric["id"],
            "working_title": "A",
            "sort_order": 5,
            "line_key": "k1",
        },
    )
    assert second.status_code == 201
    third = client.post(
        f"{PLANS}/{plan['id']}/items",
        headers=headers,
        json={
            "planned_date": "2026-08-01",
            "rubric_id": rubric["id"],
            "working_title": "A0",
            "sort_order": 0,
            "line_key": "k0",
        },
    )
    assert third.status_code == 201
    items = client.get(f"{PLANS}/{plan['id']}/items", headers=headers).json()
    titles = [row["working_title"] for row in items]
    assert titles == ["A0", "A", "B"]
    assert all(row["topic_id"] is None for row in items)
    assert all(row["status"] == "draft" for row in items)


def test_line_key_unique_per_plan_and_cross_ok(client: TestClient):
    h1, h2 = _setup_two_tenants(client, suffix="lk")
    r1 = _active_rubric(client, h1, "asem_column")
    r2 = _active_rubric(client, h2, "asem_column")
    p1 = _create_plan(client, h1)
    p1b = _create_plan(client, h1, title="Other plan")
    p2 = _create_plan(client, h2)

    body = {
        "planned_date": "2026-08-05",
        "rubric_id": r1["id"],
        "working_title": "Same key",
        "line_key": "shared",
    }
    assert client.post(f"{PLANS}/{p1['id']}/items", headers=h1, json=body).status_code == 201
    dup = client.post(f"{PLANS}/{p1['id']}/items", headers=h1, json=body)
    assert dup.status_code == 409
    assert "line_key_duplicate" in dup.text

    # Same key in another plan of same tenant OK.
    body_other_plan = {**body, "rubric_id": r1["id"]}
    assert (
        client.post(f"{PLANS}/{p1b['id']}/items", headers=h1, json=body_other_plan).status_code
        == 201
    )
    # Same key other tenant OK.
    body_t2 = {**body, "rubric_id": r2["id"]}
    assert client.post(f"{PLANS}/{p2['id']}/items", headers=h2, json=body_t2).status_code == 201

    # Cancelled line_key cannot be reused in same plan.
    item = client.post(
        f"{PLANS}/{p1['id']}/items",
        headers=h1,
        json={
            "planned_date": "2026-08-06",
            "rubric_id": r1["id"],
            "working_title": "Cancel me",
            "line_key": "cancel-key",
        },
    ).json()
    assert (
        client.post(
            f"{PLANS}/{p1['id']}/items/{item['id']}/cancel", headers=h1
        ).status_code
        == 200
    )
    reuse = client.post(
        f"{PLANS}/{p1['id']}/items",
        headers=h1,
        json={
            "planned_date": "2026-08-07",
            "rubric_id": r1["id"],
            "working_title": "Reuse",
            "line_key": "cancel-key",
        },
    )
    assert reuse.status_code == 409


def test_rubric_tenant_and_inactive(client: TestClient):
    h1, h2 = _setup_two_tenants(client, suffix="rub")
    r1 = _active_rubric(client, h1, "founder_notes")
    r2 = _active_rubric(client, h2, "founder_notes")
    p1 = _create_plan(client, h1)

    cross = client.post(
        f"{PLANS}/{p1['id']}/items",
        headers=h1,
        json={
            "planned_date": "2026-08-03",
            "rubric_id": r2["id"],
            "working_title": "Cross",
        },
    )
    assert cross.status_code == 404

    inactive = client.post(f"{RUBRICS}/{r1['id']}/deactivate", headers=h1)
    assert inactive.status_code == 200
    blocked = client.post(
        f"{PLANS}/{p1['id']}/items",
        headers=h1,
        json={
            "planned_date": "2026-08-03",
            "rubric_id": r1["id"],
            "working_title": "Inactive",
        },
    )
    assert blocked.status_code == 409
    assert "marketing_rubric_not_selectable" in blocked.text

    assert client.post(f"{RUBRICS}/{r1['id']}/activate", headers=h1).status_code == 200
    ok = client.post(
        f"{PLANS}/{p1['id']}/items",
        headers=h1,
        json={
            "planned_date": "2026-08-03",
            "rubric_id": r1["id"],
            "working_title": "Active ok",
            "line_key": "hist",
        },
    )
    assert ok.status_code == 201
    # Historical item keeps rubric_id after archive; list still works.
    assert client.post(f"{RUBRICS}/{r1['id']}/archive", headers=h1).status_code == 200
    items = client.get(f"{PLANS}/{p1['id']}/items", headers=h1)
    assert items.status_code == 200
    assert items.json()[0]["rubric_id"] == r1["id"]


def test_lifecycle_approve_archive_immutability(client: TestClient):
    headers, _ = _setup(client, suffix="life")
    rubric = _active_rubric(client, headers, "client_journey")
    plan = _create_plan(client, headers)

    empty = client.post(f"{PLANS}/{plan['id']}/approve", headers=headers)
    assert empty.status_code == 409
    assert "approve_requires_items" in empty.text

    item = client.post(
        f"{PLANS}/{plan['id']}/items",
        headers=headers,
        json={
            "planned_date": "2026-08-10",
            "rubric_id": rubric["id"],
            "working_title": "Keep",
            "line_key": "keep",
        },
    ).json()
    cancelled = client.post(
        f"{PLANS}/{plan['id']}/items",
        headers=headers,
        json={
            "planned_date": "2026-08-11",
            "rubric_id": rubric["id"],
            "working_title": "Drop",
            "line_key": "drop",
        },
    ).json()
    assert (
        client.post(
            f"{PLANS}/{plan['id']}/items/{cancelled['id']}/cancel", headers=headers
        ).json()["status"]
        == "cancelled"
    )

    approved = client.post(f"{PLANS}/{plan['id']}/approve", headers=headers)
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "approved"
    items = client.get(f"{PLANS}/{plan['id']}/items", headers=headers).json()
    by_id = {row["id"]: row for row in items}
    assert by_id[item["id"]]["status"] == "approved"
    assert by_id[cancelled["id"]]["status"] == "cancelled"

    # Immutable after approve.
    assert (
        client.patch(
            f"{PLANS}/{plan['id']}", headers=headers, json={"title": "Nope"}
        ).status_code
        == 409
    )
    assert (
        client.post(
            f"{PLANS}/{plan['id']}/items",
            headers=headers,
            json={
                "planned_date": "2026-08-12",
                "rubric_id": rubric["id"],
                "working_title": "Nope",
            },
        ).status_code
        == 409
    )
    assert (
        client.patch(
            f"{PLANS}/{plan['id']}/items/{item['id']}",
            headers=headers,
            json={"working_title": "Nope"},
        ).status_code
        == 409
    )
    # status via PATCH ignored / not allowed — attempt with status field ignored by schema
    patched = client.patch(
        f"{PLANS}/{plan['id']}/items/{item['id']}",
        headers=headers,
        json={"status": "topic_created", "working_title": "Still nope"},
    )
    assert patched.status_code == 409

    archived = client.post(f"{PLANS}/{plan['id']}/archive", headers=headers)
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"
    # archived terminal — approve forbidden
    assert client.post(f"{PLANS}/{plan['id']}/approve", headers=headers).status_code == 409


def test_plan_and_item_tenant_isolation(client: TestClient):
    h1, h2 = _setup_two_tenants(client, suffix="iso")
    r1 = _active_rubric(client, h1)
    plan = _create_plan(client, h1)
    item = client.post(
        f"{PLANS}/{plan['id']}/items",
        headers=h1,
        json={
            "planned_date": "2026-08-01",
            "rubric_id": r1["id"],
            "working_title": "Private",
        },
    ).json()

    assert client.get(f"{PLANS}/{plan['id']}", headers=h2).status_code == 404
    assert client.get(f"{PLANS}/{plan['id']}/items", headers=h2).status_code == 404
    assert (
        client.patch(
            f"{PLANS}/{plan['id']}/items/{item['id']}",
            headers=h2,
            json={"working_title": "Hijack"},
        ).status_code
        == 404
    )
    assert client.get(PLANS, headers=h2).json() == []


def test_draft_to_archived_without_approve(client: TestClient):
    headers, _ = _setup(client, suffix="arch-draft")
    plan = _create_plan(client, headers)
    archived = client.post(f"{PLANS}/{plan['id']}/archive", headers=headers)
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"


def test_m75a_guide_rubric_regression_smoke(client: TestClient):
    headers, _ = _setup(client, suffix="m75a-reg")
    guide = client.post(
        GUIDES,
        headers=headers,
        json={
            "business_name": "Flexity",
            "business_summary": "ERP",
            "products_services": "Cabinet",
            "audiences": "Founders",
            "goals": "Dogfood",
            "channels": ["telegram"],
            "default_frequency": "daily",
            "activate": True,
        },
    )
    assert guide.status_code == 201
    assert client.get(f"{GUIDES}/active", headers=headers).status_code == 200
    seed = client.post(f"{RUBRICS}/seed-defaults", headers=headers, json={})
    assert seed.status_code == 200
    assert seed.json()["created"] == 10
