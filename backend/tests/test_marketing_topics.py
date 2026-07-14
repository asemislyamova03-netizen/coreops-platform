import uuid
from datetime import date

REGISTER_PAYLOAD = {
    "email": "marketing-owner@example.com",
    "password": "securepass123",
    "full_name": "Marketing Owner",
    "company_name": "Marketing Provider",
    "company_slug": "marketing-provider",
}


def _auth_headers(client) -> dict[str, str]:
    client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    token = client.post(
        "/api/v1/auth/login",
        json={"email": REGISTER_PAYLOAD["email"], "password": REGISTER_PAYLOAD["password"]},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _setup_marketing_tenant(
    client,
    *,
    slug_suffix: str = "main",
    email: str | None = None,
) -> tuple[dict[str, str], str]:
    payload = {
        **REGISTER_PAYLOAD,
        "email": email or f"marketing-{slug_suffix}@example.com",
        "company_name": f"Marketing Provider {slug_suffix}",
        "company_slug": f"marketing-provider-{slug_suffix}",
    }
    reg = client.post("/api/v1/auth/register", json=payload)
    assert reg.status_code == 201, reg.text
    login = client.post(
        "/api/v1/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    tenant_id = client.post(
        "/api/v1/tenants",
        json={"name": "Flexity Sales", "slug": f"flexity-sales-{slug_suffix}"},
        headers=headers,
    ).json()["id"]
    tenant_headers = {**headers, "X-Tenant-ID": tenant_id}

    parties_enable = client.post(
        f"/api/v1/tenants/{tenant_id}/modules/parties/enable",
        headers=headers,
    )
    assert parties_enable.status_code == 200

    marketing_enable = client.post(
        f"/api/v1/tenants/{tenant_id}/modules/marketing/enable",
        headers=headers,
    )
    assert marketing_enable.status_code == 200

    return tenant_headers, tenant_id


def test_marketing_module_required(client):
    headers = _auth_headers(client)
    tenant_id = client.post(
        "/api/v1/tenants",
        json={"name": "No Marketing", "slug": "no-marketing-tenant"},
        headers=headers,
    ).json()["id"]
    tenant_headers = {**headers, "X-Tenant-ID": tenant_id}

    blocked = client.get("/api/v1/marketing/topics", headers=tenant_headers)
    assert blocked.status_code == 403

    client.post(f"/api/v1/tenants/{tenant_id}/modules/parties/enable", headers=headers)
    client.post(f"/api/v1/tenants/{tenant_id}/modules/marketing/enable", headers=headers)

    allowed = client.get("/api/v1/marketing/topics", headers=tenant_headers)
    assert allowed.status_code == 200


def test_marketing_health(client):
    tenant_headers, _ = _setup_marketing_tenant(client, slug_suffix="health")
    response = client.get("/api/v1/marketing/health", headers=tenant_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["module"] == "marketing"


def test_create_and_list_topics(client):
    tenant_headers, _ = _setup_marketing_tenant(client, slug_suffix="create")

    created = client.post(
        "/api/v1/marketing/topics",
        headers=tenant_headers,
        json={
            "title": "AI в госсекторе",
            "rubric": "Продуктовое видение Flexity",
            "angle": "Кейс внедрения",
            "status": "approved",
            "priority": 5,
            "recommended_channels": ["telegram", "instagram"],
        },
    )
    assert created.status_code == 201
    body = created.json()
    assert body["title"] == "AI в госсекторе"
    assert body["status"] == "approved"
    assert body["used_count"] == 0
    topic_id = body["id"]

    listed = client.get("/api/v1/marketing/topics", headers=tenant_headers)
    assert listed.status_code == 200
    ids = {item["id"] for item in listed.json()}
    assert topic_id in ids


def test_get_and_update_topic(client):
    tenant_headers, _ = _setup_marketing_tenant(client, slug_suffix="update")

    created = client.post(
        "/api/v1/marketing/topics",
        headers=tenant_headers,
        json={
            "title": "Original title",
            "rubric": "News",
            "status": "draft",
        },
    ).json()
    topic_id = created["id"]

    fetched = client.get(f"/api/v1/marketing/topics/{topic_id}", headers=tenant_headers)
    assert fetched.status_code == 200
    assert fetched.json()["title"] == "Original title"

    updated = client.patch(
        f"/api/v1/marketing/topics/{topic_id}",
        headers=tenant_headers,
        json={"title": "Updated title", "status": "approved"},
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Updated title"
    assert updated.json()["status"] == "approved"


def test_archive_topic_hides_from_default_list(client):
    tenant_headers, _ = _setup_marketing_tenant(client, slug_suffix="archive")

    created = client.post(
        "/api/v1/marketing/topics",
        headers=tenant_headers,
        json={"title": "To archive", "rubric": "Test", "status": "approved"},
    ).json()
    topic_id = created["id"]

    archived = client.post(
        f"/api/v1/marketing/topics/{topic_id}/archive",
        headers=tenant_headers,
    )
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"

    listed = client.get("/api/v1/marketing/topics", headers=tenant_headers)
    assert all(item["id"] != topic_id for item in listed.json())

    with_archived = client.get(
        "/api/v1/marketing/topics",
        headers=tenant_headers,
        params={"include_archived": True},
    )
    assert any(item["id"] == topic_id for item in with_archived.json())


def test_mark_used_increments_counter(client):
    tenant_headers, _ = _setup_marketing_tenant(client, slug_suffix="mark-used")

    created = client.post(
        "/api/v1/marketing/topics",
        headers=tenant_headers,
        json={
            "title": "Usage topic",
            "rubric": "Test",
            "status": "approved",
            "reusable": True,
        },
    ).json()
    topic_id = created["id"]

    marked = client.post(
        f"/api/v1/marketing/topics/{topic_id}/mark-used",
        headers=tenant_headers,
    )
    assert marked.status_code == 200
    body = marked.json()
    assert body["used_count"] == 1
    assert body["last_used_at"] is not None
    assert body["status"] == "approved"


def test_mark_used_non_reusable_sets_used_status(client):
    tenant_headers, _ = _setup_marketing_tenant(client, slug_suffix="mark-used-nr")

    created = client.post(
        "/api/v1/marketing/topics",
        headers=tenant_headers,
        json={
            "title": "One-shot topic",
            "rubric": "Test",
            "status": "approved",
            "reusable": False,
        },
    ).json()
    topic_id = created["id"]

    marked = client.post(
        f"/api/v1/marketing/topics/{topic_id}/mark-used",
        headers=tenant_headers,
    )
    assert marked.status_code == 200
    assert marked.json()["status"] == "used"


def test_take_topic_creates_draft_pack(client):
    tenant_headers, _ = _setup_marketing_tenant(client, slug_suffix="take")

    created = client.post(
        "/api/v1/marketing/topics",
        headers=tenant_headers,
        json={
            "title": "Take me",
            "rubric": "Vision",
            "status": "approved",
            "slug_hint": "take-me-topic",
        },
    ).json()
    topic_id = created["id"]

    taken = client.post(
        f"/api/v1/marketing/topics/{topic_id}/take",
        headers=tenant_headers,
        json={"planned_date": "2026-07-10", "source": "console"},
    )
    assert taken.status_code == 201
    pack = taken.json()
    assert pack["topic_id"] == topic_id
    assert pack["slug"] == "take-me-topic"
    assert pack["planned_date"] == "2026-07-10"
    assert pack["status"] == "draft"
    assert len(pack["texts"]) == 4
    channels = {t["channel"] for t in pack["texts"]}
    assert channels == {"telegram", "instagram", "threads", "insights"}


def test_take_topic_requires_approved_status(client):
    tenant_headers, _ = _setup_marketing_tenant(client, slug_suffix="take-draft")

    created = client.post(
        "/api/v1/marketing/topics",
        headers=tenant_headers,
        json={"title": "Draft only", "rubric": "Test", "status": "draft"},
    ).json()

    taken = client.post(
        f"/api/v1/marketing/topics/{created['id']}/take",
        headers=tenant_headers,
        json={"planned_date": "2026-07-10"},
    )
    assert taken.status_code == 409
    assert taken.json()["detail"] == "topic_not_approved"


def test_take_topic_duplicate_blocked_same_date(client):
    tenant_headers, _ = _setup_marketing_tenant(client, slug_suffix="take-dup")

    created = client.post(
        "/api/v1/marketing/topics",
        headers=tenant_headers,
        json={"title": "Dup topic", "rubric": "Test", "status": "approved", "reusable": True},
    ).json()
    topic_id = created["id"]
    planned = "2026-07-11"

    first = client.post(
        f"/api/v1/marketing/topics/{topic_id}/take",
        headers=tenant_headers,
        json={"planned_date": planned, "slug": "dup-pack-a"},
    )
    assert first.status_code == 201

    second = client.post(
        f"/api/v1/marketing/topics/{topic_id}/take",
        headers=tenant_headers,
        json={"planned_date": planned, "slug": "dup-pack-b"},
    )
    assert second.status_code == 409
    assert "topic_duplicate_blocked" in second.json()["detail"]


def test_topic_tenant_isolation(client):
    uid = uuid.uuid4().hex[:8]
    register_payload = {
        "email": f"mkt-iso-{uid}@example.com",
        "password": "securepass123",
        "full_name": "Isolation Owner",
        "company_name": f"Isolation Provider {uid}",
        "company_slug": f"isolation-provider-{uid}",
    }
    reg = client.post("/api/v1/auth/register", json=register_payload)
    assert reg.status_code == 201
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    tenant_a = client.post(
        "/api/v1/tenants",
        json={"name": "Tenant A", "slug": f"mkt-tenant-a-{uid}"},
        headers=headers,
    ).json()["id"]
    tenant_b = client.post(
        "/api/v1/tenants",
        json={"name": "Tenant B", "slug": f"mkt-tenant-b-{uid}"},
        headers=headers,
    ).json()["id"]

    for tenant_id in (tenant_a, tenant_b):
        client.post(f"/api/v1/tenants/{tenant_id}/modules/parties/enable", headers=headers)
        client.post(f"/api/v1/tenants/{tenant_id}/modules/marketing/enable", headers=headers)

    headers_a = {**headers, "X-Tenant-ID": tenant_a}
    headers_b = {**headers, "X-Tenant-ID": tenant_b}

    created = client.post(
        "/api/v1/marketing/topics",
        headers=headers_a,
        json={"title": "Tenant A topic", "rubric": "A", "status": "approved"},
    )
    assert created.status_code == 201
    topic_id = created.json()["id"]

    cross_get = client.get(f"/api/v1/marketing/topics/{topic_id}", headers=headers_b)
    assert cross_get.status_code == 404

    list_b = client.get("/api/v1/marketing/topics", headers=headers_b)
    assert all(item["id"] != topic_id for item in list_b.json())

    cross_patch = client.patch(
        f"/api/v1/marketing/topics/{topic_id}",
        headers=headers_b,
        json={"title": "Hijack"},
    )
    assert cross_patch.status_code == 404


def test_marketing_in_module_registry(client):
    headers = _auth_headers(client)
    response = client.get("/api/v1/modules/registry", headers=headers)
    assert response.status_code == 200
    codes = {item["code"] for item in response.json()}
    assert "marketing" in codes


def test_topic_create_persists_rich_metadata(client):
    tenant_headers, _ = _setup_marketing_tenant(client, slug_suffix="meta-create")

    created = client.post(
        "/api/v1/marketing/topics",
        headers=tenant_headers,
        json={
            "title": "Rich metadata topic",
            "rubric": "business_diagnosis",
            "angle": "Диагностика без хаоса",
            "priority": 10,
            "audience": "Собственники SMB",
            "pain": "Фрагментированный учёт",
            "insight": "Сначала процессы, потом ИИ",
            "source_ref": "Разбор заявки flexity-sales",
            "cta": "Запросить диагностику",
            "funnel_stage": "diagnosis",
            "notes": "M7-A smoke shape",
            "planned_date": "2026-07-20",
            "status": "draft",
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["audience"] == "Собственники SMB"
    assert body["pain"] == "Фрагментированный учёт"
    assert body["insight"] == "Сначала процессы, потом ИИ"
    assert body["source_ref"] == "Разбор заявки flexity-sales"
    assert body["cta"] == "Запросить диагностику"
    assert body["funnel_stage"] == "diagnosis"
    assert body["planned_date"] == "2026-07-20"
    assert body["metadata_json"]["insight"] == "Сначала процессы, потом ИИ"
    assert body["source"] == "manual"


def test_topic_patch_updates_rich_metadata(client):
    tenant_headers, _ = _setup_marketing_tenant(client, slug_suffix="meta-patch")

    created = client.post(
        "/api/v1/marketing/topics",
        headers=tenant_headers,
        json={
            "title": "Patch me",
            "rubric": "asem_column",
            "insight": "old insight",
            "cta": "old cta",
            "status": "draft",
        },
    ).json()
    topic_id = created["id"]

    updated = client.patch(
        f"/api/v1/marketing/topics/{topic_id}",
        headers=tenant_headers,
        json={
            "insight": "new insight",
            "cta": "",
            "funnel_stage": "trust",
            "source_ref": "https://example.com/ref",
        },
    )
    assert updated.status_code == 200, updated.text
    body = updated.json()
    assert body["insight"] == "new insight"
    assert body["cta"] is None
    assert "cta" not in body["metadata_json"]
    assert body["funnel_stage"] == "trust"
    assert body["source_ref"] == "https://example.com/ref"


def test_topic_create_legacy_without_editorial_still_works(client):
    tenant_headers, _ = _setup_marketing_tenant(client, slug_suffix="meta-legacy")

    created = client.post(
        "/api/v1/marketing/topics",
        headers=tenant_headers,
        json={
            "title": "Legacy M6 create",
            "rubric": "News",
            "status": "approved",
            "priority": 5,
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["metadata_json"] == {}
    assert body["audience"] is None
    assert body["insight"] is None


def test_topic_rich_metadata_tenant_isolation(client):
    uid = uuid.uuid4().hex[:8]
    register_payload = {
        "email": f"mkt-meta-iso-{uid}@example.com",
        "password": "securepass123",
        "full_name": "Meta Isolation Owner",
        "company_name": f"Meta Isolation Provider {uid}",
        "company_slug": f"meta-isolation-provider-{uid}",
    }
    reg = client.post("/api/v1/auth/register", json=register_payload)
    assert reg.status_code == 201
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    tenant_a = client.post(
        "/api/v1/tenants",
        json={"name": "Meta A", "slug": f"meta-a-{uid}"},
        headers=headers,
    ).json()["id"]
    tenant_b = client.post(
        "/api/v1/tenants",
        json={"name": "Meta B", "slug": f"meta-b-{uid}"},
        headers=headers,
    ).json()["id"]
    for tenant_id in (tenant_a, tenant_b):
        client.post(f"/api/v1/tenants/{tenant_id}/modules/parties/enable", headers=headers)
        client.post(f"/api/v1/tenants/{tenant_id}/modules/marketing/enable", headers=headers)

    headers_a = {**headers, "X-Tenant-ID": tenant_a}
    headers_b = {**headers, "X-Tenant-ID": tenant_b}

    created = client.post(
        "/api/v1/marketing/topics",
        headers=headers_a,
        json={
            "title": "Secret insight topic",
            "rubric": "founder_notes",
            "insight": "tenant-a-only",
            "status": "draft",
        },
    )
    assert created.status_code == 201
    topic_id = created.json()["id"]

    cross = client.get(f"/api/v1/marketing/topics/{topic_id}", headers=headers_b)
    assert cross.status_code == 404

    cross_patch = client.patch(
        f"/api/v1/marketing/topics/{topic_id}",
        headers=headers_b,
        json={"insight": "hijack"},
    )
    assert cross_patch.status_code == 404
