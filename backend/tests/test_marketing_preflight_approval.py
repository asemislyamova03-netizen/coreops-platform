import uuid

REGISTER_PAYLOAD = {
    "email": "preflight-owner@example.com",
    "password": "securepass123",
    "full_name": "Preflight Owner",
    "company_name": "Preflight Provider",
    "company_slug": "preflight-provider",
}


def _setup_marketing_tenant(client, *, slug_suffix: str = "pf") -> tuple[dict[str, str], str]:
    payload = {
        **REGISTER_PAYLOAD,
        "email": f"pf-{slug_suffix}@example.com",
        "company_name": f"PF Provider {slug_suffix}",
        "company_slug": f"pf-provider-{slug_suffix}",
    }
    reg = client.post("/api/v1/auth/register", json=payload)
    assert reg.status_code == 201, reg.text
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    tenant_id = client.post(
        "/api/v1/tenants",
        json={"name": "Flexity Sales", "slug": f"flexity-sales-pf-{slug_suffix}"},
        headers=headers,
    ).json()["id"]
    tenant_headers = {**headers, "X-Tenant-ID": tenant_id}
    client.post(f"/api/v1/tenants/{tenant_id}/modules/parties/enable", headers=headers)
    client.post(f"/api/v1/tenants/{tenant_id}/modules/marketing/enable", headers=headers)
    return tenant_headers, tenant_id


def _create_pack(client, headers, *, slug: str = "pf-pack") -> str:
    response = client.post(
        "/api/v1/marketing/packs",
        headers=headers,
        json={"title": "Preflight pack", "slug": slug},
    )
    assert response.status_code == 201
    return response.json()["id"]


def _put_text(client, headers, pack_id: str, channel: str, text: str) -> None:
    resp = client.put(
        f"/api/v1/marketing/packs/{pack_id}/texts/{channel}",
        headers=headers,
        json={"text": text},
    )
    assert resp.status_code == 200


def _preflight_and_approve(client, headers, pack_id: str) -> None:
    pf = client.post(f"/api/v1/marketing/packs/{pack_id}/preflight", headers=headers)
    assert pf.status_code == 200
    assert pf.json()["status"] in ("passed", "warning")
    approved = client.post(f"/api/v1/marketing/packs/{pack_id}/approve", headers=headers)
    assert approved.status_code == 200
    assert approved.json()["approval_status"] == "approved"
    assert approved.json()["status"] == "approved"


def test_preflight_empty_pack_fails(client):
    headers, _ = _setup_marketing_tenant(client, slug_suffix="empty-pf")
    pack_id = _create_pack(client, headers, slug="empty-pf-pack")

    pf = client.post(f"/api/v1/marketing/packs/{pack_id}/preflight", headers=headers)
    assert pf.status_code == 200
    body = pf.json()
    assert body["status"] == "failed"
    assert body["preflight_status"] == "failed"
    assert body["pack_status"] == "preflight_failed"
    assert any(e["code"] == "no_publishable_text" for e in body["errors"])

    detail = client.get(f"/api/v1/marketing/packs/{pack_id}", headers=headers)
    assert detail.json()["preflight_status"] == "failed"
    assert detail.json()["status"] == "preflight_failed"


def test_preflight_with_telegram_text_passes(client):
    headers, _ = _setup_marketing_tenant(client, slug_suffix="tg-pf")
    pack_id = _create_pack(client, headers, slug="tg-pf-pack")
    _put_text(client, headers, pack_id, "telegram", "Hello Telegram")

    pf = client.post(f"/api/v1/marketing/packs/{pack_id}/preflight", headers=headers)
    assert pf.status_code == 200
    body = pf.json()
    assert body["status"] in ("passed", "warning")
    assert body["preflight_status"] == "passed"
    assert body["pack_status"] == "ready_for_approval"
    assert body["channel_eligibility"]["telegram"] is True


def test_preflight_with_multiple_channel_texts_passes(client):
    headers, _ = _setup_marketing_tenant(client, slug_suffix="multi-pf")
    pack_id = _create_pack(client, headers, slug="multi-pf-pack")
    _put_text(client, headers, pack_id, "telegram", "TG")
    _put_text(client, headers, pack_id, "instagram", "IG caption")
    _put_text(client, headers, pack_id, "threads", "Threads")

    pf = client.post(f"/api/v1/marketing/packs/{pack_id}/preflight", headers=headers)
    assert pf.status_code == 200
    assert pf.json()["status"] in ("passed", "warning")
    assert pf.json()["channel_eligibility"]["telegram"] is True
    assert pf.json()["channel_eligibility"]["instagram"] is True


def test_preflight_cross_tenant_returns_404(client):
    uid = uuid.uuid4().hex[:8]
    register_payload = {
        "email": f"pf-x-{uid}@example.com",
        "password": "securepass123",
        "full_name": "Cross PF",
        "company_name": f"Cross PF {uid}",
        "company_slug": f"pf-cross-{uid}",
    }
    reg = client.post("/api/v1/auth/register", json=register_payload)
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    tenant_a = client.post(
        "/api/v1/tenants",
        json={"name": "A", "slug": f"pf-a-{uid}"},
        headers=headers,
    ).json()["id"]
    tenant_b = client.post(
        "/api/v1/tenants",
        json={"name": "B", "slug": f"pf-b-{uid}"},
        headers=headers,
    ).json()["id"]
    for tid in (tenant_a, tenant_b):
        client.post(f"/api/v1/tenants/{tid}/modules/parties/enable", headers=headers)
        client.post(f"/api/v1/tenants/{tid}/modules/marketing/enable", headers=headers)

    headers_a = {**headers, "X-Tenant-ID": tenant_a}
    headers_b = {**headers, "X-Tenant-ID": tenant_b}
    pack_id = _create_pack(client, headers_a, slug=f"secret-pf-{uid}")
    _put_text(client, headers_a, pack_id, "telegram", "secret")

    blocked = client.post(f"/api/v1/marketing/packs/{pack_id}/preflight", headers=headers_b)
    assert blocked.status_code == 404


def test_approve_before_preflight_fails(client):
    headers, _ = _setup_marketing_tenant(client, slug_suffix="early-approve")
    pack_id = _create_pack(client, headers, slug="early-approve-pack")
    _put_text(client, headers, pack_id, "telegram", "content")

    approve = client.post(f"/api/v1/marketing/packs/{pack_id}/approve", headers=headers)
    assert approve.status_code == 409
    assert approve.json()["detail"] == "preflight_not_passed"


def test_approve_after_preflight_succeeds(client):
    headers, _ = _setup_marketing_tenant(client, slug_suffix="approve-ok")
    pack_id = _create_pack(client, headers, slug="approve-ok-pack")
    _put_text(client, headers, pack_id, "telegram", "Ready to approve")

    pf = client.post(f"/api/v1/marketing/packs/{pack_id}/preflight", headers=headers)
    assert pf.status_code == 200
    assert pf.json()["preflight_status"] == "passed"

    approve = client.post(f"/api/v1/marketing/packs/{pack_id}/approve", headers=headers)
    assert approve.status_code == 200
    body = approve.json()
    assert body["approval_status"] == "approved"
    assert body["status"] == "approved"
    assert body["approved_at"] is not None
    assert body["approved_by_user_id"] is not None


def test_reject_pack_works(client):
    headers, _ = _setup_marketing_tenant(client, slug_suffix="reject")
    pack_id = _create_pack(client, headers, slug="reject-pack")
    _put_text(client, headers, pack_id, "telegram", "reject me")

    client.post(f"/api/v1/marketing/packs/{pack_id}/preflight", headers=headers)
    reject = client.post(
        f"/api/v1/marketing/packs/{pack_id}/reject",
        headers=headers,
        json={"reason": "needs rewrite"},
    )
    assert reject.status_code == 200
    body = reject.json()
    assert body["approval_status"] == "rejected"
    assert body["status"] == "draft"
    assert body["metadata_json"].get("reject_reason") == "needs rewrite"


def test_text_edit_after_approve_resets_approval(client):
    headers, _ = _setup_marketing_tenant(client, slug_suffix="reset-text")
    pack_id = _create_pack(client, headers, slug="reset-text-pack")
    _put_text(client, headers, pack_id, "telegram", "original")
    _preflight_and_approve(client, headers, pack_id)

    client.put(
        f"/api/v1/marketing/packs/{pack_id}/texts/telegram",
        headers=headers,
        json={"text": "edited after approve"},
    )

    detail = client.get(f"/api/v1/marketing/packs/{pack_id}", headers=headers)
    assert detail.status_code == 200
    body = detail.json()
    assert body["approval_status"] == "draft"
    assert body["preflight_status"] == "not_run"
    assert body["status"] == "draft"
    assert body["approved_at"] is None


def test_media_edit_after_approve_resets_approval(client):
    headers, _ = _setup_marketing_tenant(client, slug_suffix="reset-media")
    pack_id = _create_pack(client, headers, slug="reset-media-pack")
    _put_text(client, headers, pack_id, "telegram", "with media")
    _preflight_and_approve(client, headers, pack_id)

    asset_id = client.post(
        f"/api/v1/marketing/packs/{pack_id}/media",
        headers=headers,
        json={
            "file_name": "feed.png",
            "mime_type": "image/png",
            "storage_key": "path/feed.png",
        },
    ).json()["id"]

    detail_after_attach = client.get(f"/api/v1/marketing/packs/{pack_id}", headers=headers)
    assert detail_after_attach.json()["approval_status"] == "draft"
    assert detail_after_attach.json()["preflight_status"] == "not_run"

    # Re-approve then patch media
    _put_text(client, headers, pack_id, "telegram", "with media")
    _preflight_and_approve(client, headers, pack_id)

    client.patch(
        f"/api/v1/marketing/media/{asset_id}",
        headers=headers,
        json={"width": 1080, "height": 1080},
    )

    detail = client.get(f"/api/v1/marketing/packs/{pack_id}", headers=headers)
    assert detail.json()["approval_status"] == "draft"
    assert detail.json()["preflight_status"] == "not_run"
    assert detail.json()["status"] == "draft"


def test_pack_detail_reflects_preflight_and_approval_statuses(client):
    headers, _ = _setup_marketing_tenant(client, slug_suffix="detail-status")
    pack_id = _create_pack(client, headers, slug="detail-status-pack")
    _put_text(client, headers, pack_id, "telegram", "status flow")

    client.post(f"/api/v1/marketing/packs/{pack_id}/preflight", headers=headers)
    mid = client.get(f"/api/v1/marketing/packs/{pack_id}", headers=headers)
    assert mid.json()["status"] == "ready_for_approval"
    assert mid.json()["preflight_status"] == "passed"

    client.post(f"/api/v1/marketing/packs/{pack_id}/approve", headers=headers)
    final = client.get(f"/api/v1/marketing/packs/{pack_id}", headers=headers)
    assert final.json()["status"] == "approved"
    assert final.json()["approval_status"] == "approved"


def test_preflight_module_entitlement_required(client):
    payload = {
        **REGISTER_PAYLOAD,
        "email": "pf-no-mod@example.com",
        "company_slug": "pf-no-mod-provider",
    }
    reg = client.post("/api/v1/auth/register", json=payload)
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    tenant_id = client.post(
        "/api/v1/tenants",
        json={"name": "No mod", "slug": "pf-no-mod-tenant"},
        headers=headers,
    ).json()["id"]
    tenant_headers = {**headers, "X-Tenant-ID": tenant_id}

    blocked = client.post(
        "/api/v1/marketing/packs/00000000-0000-0000-0000-000000000001/preflight",
        headers=tenant_headers,
    )
    assert blocked.status_code == 403
