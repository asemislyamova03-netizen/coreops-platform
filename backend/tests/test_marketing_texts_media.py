import uuid

REGISTER_PAYLOAD = {
    "email": "texts-media-owner@example.com",
    "password": "securepass123",
    "full_name": "Texts Media Owner",
    "company_name": "Texts Media Provider",
    "company_slug": "texts-media-provider",
}


def _setup_marketing_tenant(client, *, slug_suffix: str = "tm") -> tuple[dict[str, str], str]:
    payload = {
        **REGISTER_PAYLOAD,
        "email": f"tm-{slug_suffix}@example.com",
        "company_name": f"TM Provider {slug_suffix}",
        "company_slug": f"tm-provider-{slug_suffix}",
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
        json={"name": "Flexity Sales", "slug": f"flexity-sales-tm-{slug_suffix}"},
        headers=headers,
    ).json()["id"]
    tenant_headers = {**headers, "X-Tenant-ID": tenant_id}
    client.post(f"/api/v1/tenants/{tenant_id}/modules/parties/enable", headers=headers)
    client.post(f"/api/v1/tenants/{tenant_id}/modules/marketing/enable", headers=headers)
    return tenant_headers, tenant_id


def _create_pack(client, headers, *, slug: str = "text-pack") -> str:
    response = client.post(
        "/api/v1/marketing/packs",
        headers=headers,
        json={"title": "Text pack", "slug": slug},
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_update_text_telegram_and_instagram(client):
    headers, _ = _setup_marketing_tenant(client, slug_suffix="channels")
    pack_id = _create_pack(client, headers, slug="channels-pack")

    tg = client.put(
        f"/api/v1/marketing/packs/{pack_id}/texts/telegram",
        headers=headers,
        json={"text": "Telegram post body"},
    )
    assert tg.status_code == 200
    assert tg.json()["channel"] == "telegram"
    assert tg.json()["text"] == "Telegram post body"
    assert tg.json()["char_count"] == len("Telegram post body")
    assert tg.json()["version"] == 2

    ig = client.put(
        f"/api/v1/marketing/packs/{pack_id}/texts/instagram",
        headers=headers,
        json={"text": "Instagram caption"},
    )
    assert ig.status_code == 200
    assert ig.json()["channel"] == "instagram"


def test_update_text_threads_and_insights(client):
    headers, _ = _setup_marketing_tenant(client, slug_suffix="all-ch")
    pack_id = _create_pack(client, headers, slug="all-ch-pack")

    for channel, body in (
        ("threads", "Threads copy"),
        ("insights", "Long article body"),
    ):
        resp = client.put(
            f"/api/v1/marketing/packs/{pack_id}/texts/{channel}",
            headers=headers,
            json={"text": body},
        )
        assert resp.status_code == 200
        assert resp.json()["text"] == body


def test_unsupported_channel_rejected(client):
    headers, _ = _setup_marketing_tenant(client, slug_suffix="bad-ch")
    pack_id = _create_pack(client, headers, slug="bad-ch-pack")

    resp = client.put(
        f"/api/v1/marketing/packs/{pack_id}/texts/tiktok",
        headers=headers,
        json={"text": "nope"},
    )
    assert resp.status_code == 422


def test_text_update_visible_in_pack_detail(client):
    headers, _ = _setup_marketing_tenant(client, slug_suffix="detail-text")
    pack_id = _create_pack(client, headers, slug="detail-text-pack")

    client.put(
        f"/api/v1/marketing/packs/{pack_id}/texts/telegram",
        headers=headers,
        json={"text": "Visible in detail"},
    )

    detail = client.get(f"/api/v1/marketing/packs/{pack_id}", headers=headers)
    assert detail.status_code == 200
    tg_row = next(t for t in detail.json()["texts"] if t["channel"] == "telegram")
    assert tg_row["text"] == "Visible in detail"


def test_text_update_increments_version(client):
    headers, _ = _setup_marketing_tenant(client, slug_suffix="version")
    pack_id = _create_pack(client, headers, slug="version-pack")

    first = client.put(
        f"/api/v1/marketing/packs/{pack_id}/texts/telegram",
        headers=headers,
        json={"text": "v1"},
    )
    second = client.put(
        f"/api/v1/marketing/packs/{pack_id}/texts/telegram",
        headers=headers,
        json={"text": "v2"},
    )
    assert first.json()["version"] == 2
    assert second.json()["version"] == 3


def test_empty_text_allowed(client):
    headers, _ = _setup_marketing_tenant(client, slug_suffix="empty")
    pack_id = _create_pack(client, headers, slug="empty-pack")

    resp = client.put(
        f"/api/v1/marketing/packs/{pack_id}/texts/telegram",
        headers=headers,
        json={"text": ""},
    )
    assert resp.status_code == 200
    assert resp.json()["text"] == ""
    assert resp.json()["char_count"] == 0


def test_cross_tenant_pack_text_update_returns_404(client):
    uid = uuid.uuid4().hex[:8]
    register_payload = {
        "email": f"txt-x-{uid}@example.com",
        "password": "securepass123",
        "full_name": "Cross Owner",
        "company_name": f"Cross Provider {uid}",
        "company_slug": f"cross-txt-{uid}",
    }
    reg = client.post("/api/v1/auth/register", json=register_payload)
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    tenant_a = client.post(
        "/api/v1/tenants",
        json={"name": "A", "slug": f"txt-a-{uid}"},
        headers=headers,
    ).json()["id"]
    tenant_b = client.post(
        "/api/v1/tenants",
        json={"name": "B", "slug": f"txt-b-{uid}"},
        headers=headers,
    ).json()["id"]
    for tid in (tenant_a, tenant_b):
        client.post(f"/api/v1/tenants/{tid}/modules/parties/enable", headers=headers)
        client.post(f"/api/v1/tenants/{tid}/modules/marketing/enable", headers=headers)

    headers_a = {**headers, "X-Tenant-ID": tenant_a}
    headers_b = {**headers, "X-Tenant-ID": tenant_b}
    pack_id = _create_pack(client, headers_a, slug=f"secret-{uid}")

    blocked = client.put(
        f"/api/v1/marketing/packs/{pack_id}/texts/telegram",
        headers=headers_b,
        json={"text": "hack"},
    )
    assert blocked.status_code == 404


def test_attach_media_metadata_to_pack(client):
    headers, _ = _setup_marketing_tenant(client, slug_suffix="attach")
    pack_id = _create_pack(client, headers, slug="attach-pack")

    created = client.post(
        f"/api/v1/marketing/packs/{pack_id}/media",
        headers=headers,
        json={
            "file_name": "instagram-feed.png",
            "mime_type": "image/png",
            "storage_key": "landing/www/assets/social/test/instagram-feed.png",
            "public_url": "https://www.flexity.asia/assets/social/test/instagram-feed.png",
            "width": 1080,
            "height": 1080,
            "role": "instagram_feed",
        },
    )
    assert created.status_code == 201
    body = created.json()
    assert body["file_name"] == "instagram-feed.png"
    assert body["mime_type"] == "image/png"
    assert body["status"] == "stored"
    assert body["width"] == 1080


def test_media_list_returns_attached_media(client):
    headers, _ = _setup_marketing_tenant(client, slug_suffix="list-media")
    pack_id = _create_pack(client, headers, slug="list-media-pack")

    client.post(
        f"/api/v1/marketing/packs/{pack_id}/media",
        headers=headers,
        json={
            "file_name": "feed.png",
            "mime_type": "image/jpeg",
            "storage_key": "path/feed.png",
        },
    )

    listed = client.get(f"/api/v1/marketing/packs/{pack_id}/media", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert listed.json()[0]["file_name"] == "feed.png"


def test_media_appears_in_pack_detail(client):
    headers, _ = _setup_marketing_tenant(client, slug_suffix="detail-media")
    pack_id = _create_pack(client, headers, slug="detail-media-pack")

    client.post(
        f"/api/v1/marketing/packs/{pack_id}/media",
        headers=headers,
        json={
            "file_name": "detail-feed.png",
            "mime_type": "image/webp",
            "storage_key": "path/detail-feed.webp",
        },
    )

    detail = client.get(f"/api/v1/marketing/packs/{pack_id}", headers=headers)
    assert detail.status_code == 200
    assert len(detail.json()["media_assets"]) == 1
    assert detail.json()["media_assets"][0]["file_name"] == "detail-feed.png"


def test_media_patch_updates_metadata(client):
    headers, _ = _setup_marketing_tenant(client, slug_suffix="patch-media")
    pack_id = _create_pack(client, headers, slug="patch-media-pack")

    asset_id = client.post(
        f"/api/v1/marketing/packs/{pack_id}/media",
        headers=headers,
        json={
            "file_name": "old.png",
            "mime_type": "image/png",
            "storage_key": "path/old.png",
        },
    ).json()["id"]

    patched = client.patch(
        f"/api/v1/marketing/media/{asset_id}",
        headers=headers,
        json={
            "file_name": "new.png",
            "preview_url": "https://cdn.example/preview.png",
            "width": 1080,
            "height": 1080,
        },
    )
    assert patched.status_code == 200
    assert patched.json()["file_name"] == "new.png"
    assert patched.json()["preview_url"] == "https://cdn.example/preview.png"


def test_media_delete_archives_asset(client):
    headers, _ = _setup_marketing_tenant(client, slug_suffix="del-media")
    pack_id = _create_pack(client, headers, slug="del-media-pack")

    asset_id = client.post(
        f"/api/v1/marketing/packs/{pack_id}/media",
        headers=headers,
        json={
            "file_name": "remove.png",
            "mime_type": "image/png",
            "storage_key": "path/remove.png",
        },
    ).json()["id"]

    deleted = client.delete(f"/api/v1/marketing/media/{asset_id}", headers=headers)
    assert deleted.status_code == 200
    assert deleted.json()["status"] == "archived"

    listed = client.get(f"/api/v1/marketing/packs/{pack_id}/media", headers=headers)
    assert listed.json() == []


def test_invalid_mime_type_rejected(client):
    headers, _ = _setup_marketing_tenant(client, slug_suffix="bad-mime")
    pack_id = _create_pack(client, headers, slug="bad-mime-pack")

    resp = client.post(
        f"/api/v1/marketing/packs/{pack_id}/media",
        headers=headers,
        json={
            "file_name": "video.mp4",
            "mime_type": "video/mp4",
            "storage_key": "path/video.mp4",
        },
    )
    assert resp.status_code == 409
    assert "invalid_mime_type" in resp.json()["detail"]


def test_cross_tenant_media_access_denied(client):
    uid = uuid.uuid4().hex[:8]
    register_payload = {
        "email": f"med-x-{uid}@example.com",
        "password": "securepass123",
        "full_name": "Media Cross",
        "company_name": f"Media Cross {uid}",
        "company_slug": f"med-cross-{uid}",
    }
    reg = client.post("/api/v1/auth/register", json=register_payload)
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    tenant_a = client.post(
        "/api/v1/tenants",
        json={"name": "A", "slug": f"med-a-{uid}"},
        headers=headers,
    ).json()["id"]
    tenant_b = client.post(
        "/api/v1/tenants",
        json={"name": "B", "slug": f"med-b-{uid}"},
        headers=headers,
    ).json()["id"]
    for tid in (tenant_a, tenant_b):
        client.post(f"/api/v1/tenants/{tid}/modules/parties/enable", headers=headers)
        client.post(f"/api/v1/tenants/{tid}/modules/marketing/enable", headers=headers)

    headers_a = {**headers, "X-Tenant-ID": tenant_a}
    headers_b = {**headers, "X-Tenant-ID": tenant_b}
    pack_id = _create_pack(client, headers_a, slug=f"med-secret-{uid}")

    asset_id = client.post(
        f"/api/v1/marketing/packs/{pack_id}/media",
        headers=headers_a,
        json={
            "file_name": "secret.png",
            "mime_type": "image/png",
            "storage_key": "path/secret.png",
        },
    ).json()["id"]

    cross_get = client.get(f"/api/v1/marketing/packs/{pack_id}/media", headers=headers_b)
    assert cross_get.status_code == 404

    cross_patch = client.patch(
        f"/api/v1/marketing/media/{asset_id}",
        headers=headers_b,
        json={"file_name": "stolen.png"},
    )
    assert cross_patch.status_code == 404

    cross_delete = client.delete(f"/api/v1/marketing/media/{asset_id}", headers=headers_b)
    assert cross_delete.status_code == 404


def test_texts_module_entitlement_required(client):
    payload = {
        **REGISTER_PAYLOAD,
        "email": "tm-no-mod@example.com",
        "company_slug": "tm-no-mod-provider",
    }
    reg = client.post("/api/v1/auth/register", json=payload)
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    tenant_id = client.post(
        "/api/v1/tenants",
        json={"name": "No mod", "slug": "tm-no-mod-tenant"},
        headers=headers,
    ).json()["id"]
    tenant_headers = {**headers, "X-Tenant-ID": tenant_id}

    blocked = client.get("/api/v1/marketing/packs", headers=tenant_headers)
    assert blocked.status_code == 403
