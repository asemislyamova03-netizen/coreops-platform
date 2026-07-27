"""M7.5-D: plan item → create-topic action."""

from __future__ import annotations

from fastapi.testclient import TestClient

PLANS = "/api/v1/marketing/content-plans"
RUBRICS = "/api/v1/marketing/rubrics"
TOPICS = "/api/v1/marketing/topics"
PACKS = "/api/v1/marketing/packs"


def _setup(client: TestClient, *, suffix: str) -> tuple[dict[str, str], str]:
    email = f"m75d-{suffix}@example.com"
    password = "securepass123"
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": f"M75D {suffix}",
            "company_name": f"M75D Co {suffix}",
            "company_slug": f"m75d-co-{suffix}",
        },
    )
    assert reg.status_code == 201, reg.text
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    tenant = client.post(
        "/api/v1/tenants",
        json={"name": f"M75D Tenant {suffix}", "slug": f"m75d-tenant-{suffix}"},
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
    email = f"m75d-iso-{suffix}@example.com"
    password = "securepass123"
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": f"M75D Iso {suffix}",
            "company_name": f"M75D Iso Co {suffix}",
            "company_slug": f"m75d-iso-co-{suffix}",
        },
    )
    assert reg.status_code == 201, reg.text
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    tenant_a = client.post(
        "/api/v1/tenants",
        json={"name": f"Iso A {suffix}", "slug": f"m75d-iso-a-{suffix}"},
        headers=headers,
    )
    assert tenant_a.status_code == 201, tenant_a.text
    tenant_b = client.post(
        "/api/v1/tenants",
        json={"name": f"Iso B {suffix}", "slug": f"m75d-iso-b-{suffix}"},
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


def _rubric(client: TestClient, headers: dict[str, str], code: str = "asem_column"):
    created = client.post(
        RUBRICS,
        headers=headers,
        json={"code": code, "name": code.replace("_", " ").title(), "sort_order": 1},
    )
    assert created.status_code == 201, created.text
    return created.json()


def _approved_plan_with_item(client: TestClient, headers: dict[str, str], rubric_id: str):
    plan = client.post(
        PLANS,
        headers=headers,
        json={
            "title": "August dogfood",
            "period_start": "2026-08-01",
            "period_end": "2026-08-31",
        },
    )
    assert plan.status_code == 201, plan.text
    plan_id = plan.json()["id"]
    item = client.post(
        f"{PLANS}/{plan_id}/items",
        headers=headers,
        json={
            "planned_date": "2026-08-10",
            "rubric_id": rubric_id,
            "working_title": "Dogfood title",
            "channels": ["telegram", "instagram"],
            "angle": "angle-x",
            "audience": "founders",
            "cta": "try flexity",
            "pain": "chaos",
            "insight": "systems win",
            "funnel_stage": "awareness",
            "notes": "from plan",
            "line_key": "d-line-1",
            "sort_order": 0,
        },
    )
    assert item.status_code == 201, item.text
    approved = client.post(f"{PLANS}/{plan_id}/approve", headers=headers)
    assert approved.status_code == 200, approved.text
    return plan.json()["id"], item.json()["id"]


def test_create_topic_happy_path_mapping_and_no_pack(client: TestClient):
    headers, _ = _setup(client, suffix="ok")
    rubric = _rubric(client, headers)
    plan_id, item_id = _approved_plan_with_item(client, headers, rubric["id"])

    before_topics = client.get(TOPICS, headers=headers).json()
    before_packs = client.get(PACKS, headers=headers)
    assert before_packs.status_code == 200
    packs_before = before_packs.json()

    resp = client.post(
        f"{PLANS}/{plan_id}/items/{item_id}/create-topic", headers=headers
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["replayed"] is False
    assert body["item"]["status"] == "topic_created"
    assert body["item"]["topic_id"] == body["topic"]["id"]
    topic = body["topic"]
    assert topic["status"] == "approved"
    assert topic["rubric"] == rubric["code"]
    assert topic["title"] == "Dogfood title"
    assert topic["source"] == "content_plan"
    assert topic["recommended_channels"] == ["telegram", "instagram"]
    assert topic["planned_date"] == "2026-08-10"
    assert topic["audience"] == "founders"
    assert topic["cta"] == "try flexity"
    assert topic["metadata_json"]["plan_item_id"] == item_id
    assert topic["metadata_json"]["plan_id"] == plan_id
    assert topic["metadata_json"]["rubric_id"] == rubric["id"]
    assert topic["metadata_json"]["channels"] == ["telegram", "instagram"]

    after_topics = client.get(TOPICS, headers=headers).json()
    assert len(after_topics) == len(before_topics) + 1
    after_packs = client.get(PACKS, headers=headers).json()
    assert after_packs == packs_before


def test_create_topic_replay_same_topic(client: TestClient):
    headers, _ = _setup(client, suffix="replay")
    rubric = _rubric(client, headers)
    plan_id, item_id = _approved_plan_with_item(client, headers, rubric["id"])
    first = client.post(
        f"{PLANS}/{plan_id}/items/{item_id}/create-topic", headers=headers
    )
    assert first.status_code == 201
    topic_id = first.json()["topic"]["id"]

    second = client.post(
        f"{PLANS}/{plan_id}/items/{item_id}/create-topic", headers=headers
    )
    assert second.status_code == 200, second.text
    assert second.json()["replayed"] is True
    assert second.json()["topic"]["id"] == topic_id

    topics = client.get(TOPICS, headers=headers).json()
    assert len([t for t in topics if t["id"] == topic_id]) == 1


def test_create_topic_requires_approved_plan_and_item(client: TestClient):
    headers, _ = _setup(client, suffix="guards")
    rubric = _rubric(client, headers)
    plan = client.post(
        PLANS,
        headers=headers,
        json={
            "title": "Draft only",
            "period_start": "2026-08-01",
            "period_end": "2026-08-31",
        },
    ).json()
    item = client.post(
        f"{PLANS}/{plan['id']}/items",
        headers=headers,
        json={
            "planned_date": "2026-08-10",
            "rubric_id": rubric["id"],
            "working_title": "T",
            "channels": ["telegram"],
        },
    ).json()

    draft = client.post(
        f"{PLANS}/{plan['id']}/items/{item['id']}/create-topic", headers=headers
    )
    assert draft.status_code == 409
    assert "plan_not_approved" in draft.text

    # Approve then cancel path: cancel only on draft plan — so create second plan
    plan2 = client.post(
        PLANS,
        headers=headers,
        json={
            "title": "With cancel",
            "period_start": "2026-08-01",
            "period_end": "2026-08-31",
        },
    ).json()
    item2 = client.post(
        f"{PLANS}/{plan2['id']}/items",
        headers=headers,
        json={
            "planned_date": "2026-08-11",
            "rubric_id": rubric["id"],
            "working_title": "Keep",
            "channels": ["telegram"],
        },
    ).json()
    item3 = client.post(
        f"{PLANS}/{plan2['id']}/items",
        headers=headers,
        json={
            "planned_date": "2026-08-12",
            "rubric_id": rubric["id"],
            "working_title": "Cancel me",
            "channels": ["telegram"],
        },
    ).json()
    assert (
        client.post(
            f"{PLANS}/{plan2['id']}/items/{item3['id']}/cancel", headers=headers
        ).status_code
        == 200
    )
    assert client.post(f"{PLANS}/{plan2['id']}/approve", headers=headers).status_code == 200

    cancelled = client.post(
        f"{PLANS}/{plan2['id']}/items/{item3['id']}/create-topic", headers=headers
    )
    assert cancelled.status_code == 409
    assert "item_cancelled" in cancelled.text

    # Archive plan blocks new create-topic
    ok_item = item2["id"]
    assert (
        client.post(f"{PLANS}/{plan2['id']}/archive", headers=headers).status_code
        == 200
    )
    archived = client.post(
        f"{PLANS}/{plan2['id']}/items/{ok_item}/create-topic", headers=headers
    )
    assert archived.status_code == 409
    assert "plan_not_approved" in archived.text


def test_create_topic_tenant_isolation(client: TestClient):
    h1, h2 = _setup_two_tenants(client, suffix="iso")
    r1 = _rubric(client, h1, code="a_code")
    plan_id, item_id = _approved_plan_with_item(client, h1, r1["id"])
    cross = client.post(
        f"{PLANS}/{plan_id}/items/{item_id}/create-topic", headers=h2
    )
    assert cross.status_code == 404


def test_regression_manual_topic_and_plans_still_work(client: TestClient):
    headers, _ = _setup(client, suffix="reg")
    rubric = _rubric(client, headers, code="legacy_ok")
    topic = client.post(
        TOPICS,
        headers=headers,
        json={
            "title": "Manual topic",
            "rubric": rubric["code"],
            "recommended_channels": ["telegram"],
            "status": "approved",
        },
    )
    assert topic.status_code == 201, topic.text
    plan = client.post(
        PLANS,
        headers=headers,
        json={
            "title": "Manual plan",
            "period_start": "2026-09-01",
            "period_end": "2026-09-30",
        },
    )
    assert plan.status_code == 201
