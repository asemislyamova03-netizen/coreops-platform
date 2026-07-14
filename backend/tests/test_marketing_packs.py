import uuid
from datetime import date

REGISTER_PAYLOAD = {
    "email": "packs-owner@example.com",
    "password": "securepass123",
    "full_name": "Packs Owner",
    "company_name": "Packs Provider",
    "company_slug": "packs-provider",
}


def _setup_marketing_tenant(client, *, slug_suffix: str = "packs") -> tuple[dict[str, str], str]:
    payload = {
        **REGISTER_PAYLOAD,
        "email": f"packs-{slug_suffix}@example.com",
        "company_name": f"Packs Provider {slug_suffix}",
        "company_slug": f"packs-provider-{slug_suffix}",
    }
    reg = client.post("/api/v1/auth/register", json=payload)
    assert reg.status_code == 201, reg.text
    login = client.post(
        "/api/v1/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )
    assert login.status_code == 200, login.text
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    tenant_id = client.post(
        "/api/v1/tenants",
        json={"name": "Flexity Sales", "slug": f"flexity-sales-packs-{slug_suffix}"},
        headers=headers,
    ).json()["id"]
    tenant_headers = {**headers, "X-Tenant-ID": tenant_id}
    client.post(f"/api/v1/tenants/{tenant_id}/modules/parties/enable", headers=headers)
    client.post(f"/api/v1/tenants/{tenant_id}/modules/marketing/enable", headers=headers)
    return tenant_headers, tenant_id


def _create_topic(client, headers, *, title: str = "Test topic", status: str = "approved") -> str:
    response = client.post(
        "/api/v1/marketing/topics",
        headers=headers,
        json={"title": title, "rubric": "Vision", "status": status},
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_create_pack_without_topic(client):
    headers, _ = _setup_marketing_tenant(client, slug_suffix="no-topic")

    created = client.post(
        "/api/v1/marketing/packs",
        headers=headers,
        json={"title": "Standalone pack", "planned_date": "2026-07-10"},
    )
    assert created.status_code == 201
    body = created.json()
    assert body["title"] == "Standalone pack"
    assert body["topic_id"] is None
    assert body["status"] == "draft"
    assert body["preflight_status"] == "not_run"
    assert body["approval_status"] == "draft"
    assert body["publish_status"] == "not_started"
    assert body["slug"] == "standalone-pack"
    assert len(body["texts"]) == 4


def test_create_pack_with_topic(client):
    headers, _ = _setup_marketing_tenant(client, slug_suffix="with-topic")
    topic_id = _create_topic(client, headers, title="Linked topic")

    created = client.post(
        "/api/v1/marketing/packs",
        headers=headers,
        json={
            "title": "Pack with topic",
            "topic_id": topic_id,
            "slug": "pack-with-topic",
        },
    )
    assert created.status_code == 201
    body = created.json()
    assert body["topic_id"] == topic_id
    assert body["topic"] is not None
    assert body["topic"]["title"] == "Linked topic"


def test_pack_slug_unique_per_tenant(client):
    headers, _ = _setup_marketing_tenant(client, slug_suffix="slug-uniq")

    first = client.post(
        "/api/v1/marketing/packs",
        headers=headers,
        json={"title": "First", "slug": "same-slug"},
    )
    assert first.status_code == 201

    second = client.post(
        "/api/v1/marketing/packs",
        headers=headers,
        json={"title": "Second", "slug": "same-slug"},
    )
    assert second.status_code == 409
    assert second.json()["detail"] == "pack_slug_exists"


def test_create_pack_creates_four_empty_text_rows(client):
    headers, _ = _setup_marketing_tenant(client, slug_suffix="four-texts")

    created = client.post(
        "/api/v1/marketing/packs",
        headers=headers,
        json={"title": "Four channels"},
    )
    assert created.status_code == 201
    texts = created.json()["texts"]
    assert len(texts) == 4
    channels = {t["channel"] for t in texts}
    assert channels == {"telegram", "instagram", "threads", "insights"}
    assert all(t["text"] == "" for t in texts)
    assert all(t["char_count"] == 0 for t in texts)


def test_list_packs_tenant_scoped(client):
    headers, _ = _setup_marketing_tenant(client, slug_suffix="list")

    client.post(
        "/api/v1/marketing/packs",
        headers=headers,
        json={"title": "Pack A", "slug": "pack-a"},
    )
    client.post(
        "/api/v1/marketing/packs",
        headers=headers,
        json={"title": "Pack B", "slug": "pack-b"},
    )

    listed = client.get("/api/v1/marketing/packs", headers=headers)
    assert listed.status_code == 200
    titles = {p["title"] for p in listed.json()}
    assert {"Pack A", "Pack B"}.issubset(titles)


def test_get_pack_detail_includes_texts(client):
    headers, _ = _setup_marketing_tenant(client, slug_suffix="detail-texts")

    pack_id = client.post(
        "/api/v1/marketing/packs",
        headers=headers,
        json={"title": "Detail pack", "slug": "detail-pack"},
    ).json()["id"]

    detail = client.get(f"/api/v1/marketing/packs/{pack_id}", headers=headers)
    assert detail.status_code == 200
    assert len(detail.json()["texts"]) == 4

    texts_only = client.get(f"/api/v1/marketing/packs/{pack_id}/texts", headers=headers)
    assert texts_only.status_code == 200
    assert len(texts_only.json()) == 4


def test_get_pack_detail_includes_topic_summary(client):
    headers, _ = _setup_marketing_tenant(client, slug_suffix="detail-topic")
    topic_id = _create_topic(client, headers, title="Summary topic")

    pack_id = client.post(
        "/api/v1/marketing/packs",
        headers=headers,
        json={"title": "Topic pack", "topic_id": topic_id, "slug": "topic-pack"},
    ).json()["id"]

    detail = client.get(f"/api/v1/marketing/packs/{pack_id}", headers=headers)
    assert detail.status_code == 200
    topic = detail.json()["topic"]
    assert topic["id"] == topic_id
    assert topic["title"] == "Summary topic"
    assert topic["rubric"] == "Vision"


def test_patch_pack_title_and_source(client):
    headers, _ = _setup_marketing_tenant(client, slug_suffix="patch")

    pack_id = client.post(
        "/api/v1/marketing/packs",
        headers=headers,
        json={"title": "Original", "slug": "patch-pack"},
    ).json()["id"]

    patched = client.patch(
        f"/api/v1/marketing/packs/{pack_id}",
        headers=headers,
        json={"title": "Renamed", "source": "api"},
    )
    assert patched.status_code == 200
    body = patched.json()
    assert body["title"] == "Renamed"
    assert body["source"] == "api"


def test_patch_pack_topic_same_tenant(client):
    headers, _ = _setup_marketing_tenant(client, slug_suffix="patch-topic")
    topic_id = _create_topic(client, headers, title="Patch topic")

    pack_id = client.post(
        "/api/v1/marketing/packs",
        headers=headers,
        json={"title": "No topic yet", "slug": "patch-topic-pack"},
    ).json()["id"]

    patched = client.patch(
        f"/api/v1/marketing/packs/{pack_id}",
        headers=headers,
        json={"topic_id": topic_id},
    )
    assert patched.status_code == 200
    assert patched.json()["topic_id"] == topic_id
    assert patched.json()["topic"]["title"] == "Patch topic"


def test_patch_pack_rejects_cross_tenant_topic(client):
    uid = uuid.uuid4().hex[:8]
    register_payload = {
        "email": f"pack-iso-{uid}@example.com",
        "password": "securepass123",
        "full_name": "Iso Owner",
        "company_name": f"Iso Provider {uid}",
        "company_slug": f"iso-provider-{uid}",
    }
    reg = client.post("/api/v1/auth/register", json=register_payload)
    assert reg.status_code == 201
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    tenant_a = client.post(
        "/api/v1/tenants",
        json={"name": "A", "slug": f"pack-tenant-a-{uid}"},
        headers=headers,
    ).json()["id"]
    tenant_b = client.post(
        "/api/v1/tenants",
        json={"name": "B", "slug": f"pack-tenant-b-{uid}"},
        headers=headers,
    ).json()["id"]
    for tid in (tenant_a, tenant_b):
        client.post(f"/api/v1/tenants/{tid}/modules/parties/enable", headers=headers)
        client.post(f"/api/v1/tenants/{tid}/modules/marketing/enable", headers=headers)

    headers_a = {**headers, "X-Tenant-ID": tenant_a}
    headers_b = {**headers, "X-Tenant-ID": tenant_b}

    foreign_topic = _create_topic(client, headers_a, title="Tenant A topic")
    pack_id = client.post(
        "/api/v1/marketing/packs",
        headers=headers_b,
        json={"title": "Tenant B pack", "slug": "tenant-b-pack"},
    ).json()["id"]

    patched = client.patch(
        f"/api/v1/marketing/packs/{pack_id}",
        headers=headers_b,
        json={"topic_id": foreign_topic},
    )
    assert patched.status_code == 404
    assert patched.json()["detail"] == "Topic not found"


def test_cross_tenant_pack_access_returns_404(client):
    uid = uuid.uuid4().hex[:8]
    register_payload = {
        "email": f"pack-x-{uid}@example.com",
        "password": "securepass123",
        "full_name": "Cross Owner",
        "company_name": f"Cross Provider {uid}",
        "company_slug": f"cross-provider-{uid}",
    }
    reg = client.post("/api/v1/auth/register", json=register_payload)
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    tenant_a = client.post(
        "/api/v1/tenants",
        json={"name": "A", "slug": f"cross-a-{uid}"},
        headers=headers,
    ).json()["id"]
    tenant_b = client.post(
        "/api/v1/tenants",
        json={"name": "B", "slug": f"cross-b-{uid}"},
        headers=headers,
    ).json()["id"]
    for tid in (tenant_a, tenant_b):
        client.post(f"/api/v1/tenants/{tid}/modules/parties/enable", headers=headers)
        client.post(f"/api/v1/tenants/{tid}/modules/marketing/enable", headers=headers)

    headers_a = {**headers, "X-Tenant-ID": tenant_a}
    headers_b = {**headers, "X-Tenant-ID": tenant_b}

    pack_id = client.post(
        "/api/v1/marketing/packs",
        headers=headers_a,
        json={"title": "Secret pack", "slug": "secret-pack"},
    ).json()["id"]

    cross_get = client.get(f"/api/v1/marketing/packs/{pack_id}", headers=headers_b)
    assert cross_get.status_code == 404

    cross_list = client.get("/api/v1/marketing/packs", headers=headers_b)
    assert all(p["id"] != pack_id for p in cross_list.json())


def test_take_pack_visible_via_packs_api(client):
    headers, _ = _setup_marketing_tenant(client, slug_suffix="take-visible")
    topic_id = _create_topic(client, headers, title="Taken topic")

    taken = client.post(
        f"/api/v1/marketing/topics/{topic_id}/take",
        headers=headers,
        json={"planned_date": "2026-07-12", "slug": "taken-pack"},
    )
    assert taken.status_code == 201
    pack_id = taken.json()["id"]

    detail = client.get(f"/api/v1/marketing/packs/{pack_id}", headers=headers)
    assert detail.status_code == 200
    body = detail.json()
    assert body["slug"] == "taken-pack"
    assert body["topic_id"] == topic_id
    assert body["topic"]["title"] == "Taken topic"
    assert len(body["texts"]) == 4
    assert body["planned_date"] == "2026-07-12"


def test_packs_module_entitlement_required(client):
    payload = {
        **REGISTER_PAYLOAD,
        "email": "packs-no-mod@example.com",
        "company_slug": "packs-no-mod-provider",
    }
    reg = client.post("/api/v1/auth/register", json=payload)
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    tenant_id = client.post(
        "/api/v1/tenants",
        json={"name": "No mod", "slug": "packs-no-mod-tenant"},
        headers=headers,
    ).json()["id"]
    tenant_headers = {**headers, "X-Tenant-ID": tenant_id}

    blocked = client.get("/api/v1/marketing/packs", headers=tenant_headers)
    assert blocked.status_code == 403

    client.post(f"/api/v1/tenants/{tenant_id}/modules/parties/enable", headers=headers)
    client.post(f"/api/v1/tenants/{tenant_id}/modules/marketing/enable", headers=headers)

    allowed = client.get("/api/v1/marketing/packs", headers=tenant_headers)
    assert allowed.status_code == 200


def test_list_packs_filter_by_status_and_topic(client):
    headers, _ = _setup_marketing_tenant(client, slug_suffix="filters")
    topic_id = _create_topic(client, headers)

    linked = client.post(
        "/api/v1/marketing/packs",
        headers=headers,
        json={"title": "Linked", "topic_id": topic_id, "slug": "linked-pack"},
    )
    assert linked.status_code == 201

    client.post(
        "/api/v1/marketing/packs",
        headers=headers,
        json={"title": "Unlinked", "slug": "unlinked-pack"},
    )

    by_topic = client.get(
        "/api/v1/marketing/packs",
        headers=headers,
        params={"topic_id": topic_id},
    )
    assert by_topic.status_code == 200
    assert len(by_topic.json()) == 1
    assert by_topic.json()[0]["topic_id"] == topic_id

    by_status = client.get(
        "/api/v1/marketing/packs",
        headers=headers,
        params={"status": "draft"},
    )
    assert by_status.status_code == 200
    assert len(by_status.json()) >= 2
