import uuid

REGISTER_PAYLOAD = {
    "email": "preflight-owner@example.com",
    "password": "securepass123",
    "full_name": "Preflight Owner",
    "company_name": "Preflight Provider",
    "company_slug": "preflight-provider",
}

# >40 chars so M7-C1 short-text warning does not fire on happy paths
_LONG_TEXT = (
    "Готовый текст для preflight: системы и процессы важнее хаотичного ИИ-внедрения."
)
assert len(_LONG_TEXT) >= 40


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


def _create_topic(client, headers, *, title: str = "PF topic", status: str = "approved", **extra) -> str:
    payload = {
        "title": title,
        "rubric": "business_diagnosis",
        "status": status,
        "audience": "Owners SMB",
        "pain": "Fragmented ops",
        "insight": "Process before AI tools",
        "source_ref": "internal notes",
        "cta": "Book a call",
        "funnel_stage": "awareness",
        "notes": "preflight fixture",
        "planned_date": "2026-07-20",
        **extra,
    }
    response = client.post("/api/v1/marketing/topics", headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _create_pack(client, headers, *, slug: str = "pf-pack", topic_id: str | None = None) -> str:
    body: dict = {"title": "Preflight pack", "slug": slug}
    if topic_id is not None:
        body["topic_id"] = topic_id
    response = client.post(
        "/api/v1/marketing/packs",
        headers=headers,
        json=body,
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _create_ready_pack(client, headers, *, slug: str) -> str:
    """Pack with approved rich topic — required for M7-C1 pass path."""
    topic_id = _create_topic(client, headers, title=f"Topic {slug}")
    return _create_pack(client, headers, slug=slug, topic_id=topic_id)


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
    assert pf.json()["preflight_status"] == "passed"
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
    assert body["version"] == "m7-c1"
    assert body["passed"] is False
    assert any(e["code"] == "no_publishable_text" for e in body["errors"])
    assert any(e["code"] == "topic_missing" for e in body["blockers"])

    detail = client.get(f"/api/v1/marketing/packs/{pack_id}", headers=headers)
    assert detail.json()["preflight_status"] == "failed"
    assert detail.json()["status"] == "preflight_failed"


def test_preflight_with_telegram_text_passes(client):
    headers, _ = _setup_marketing_tenant(client, slug_suffix="tg-pf")
    pack_id = _create_ready_pack(client, headers, slug="tg-pf-pack")
    _put_text(client, headers, pack_id, "telegram", _LONG_TEXT)

    pf = client.post(f"/api/v1/marketing/packs/{pack_id}/preflight", headers=headers)
    assert pf.status_code == 200
    body = pf.json()
    assert body["status"] in ("passed", "warning")
    assert body["preflight_status"] == "passed"
    assert body["pack_status"] == "ready_for_approval"
    assert body["passed"] is True
    assert body["version"] == "m7-c1"
    assert body["channel_eligibility"]["telegram"] is True
    assert body["topic_context_summary"]["has_audience"] is True


def test_preflight_with_multiple_channel_texts_passes(client):
    headers, _ = _setup_marketing_tenant(client, slug_suffix="multi-pf")
    pack_id = _create_ready_pack(client, headers, slug="multi-pf-pack")
    _put_text(client, headers, pack_id, "telegram", _LONG_TEXT)
    _put_text(client, headers, pack_id, "instagram", _LONG_TEXT + " IG")
    _put_text(client, headers, pack_id, "threads", _LONG_TEXT + " TH")

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
    pack_id = _create_ready_pack(client, headers, slug="early-approve-pack")
    _put_text(client, headers, pack_id, "telegram", _LONG_TEXT)

    approve = client.post(f"/api/v1/marketing/packs/{pack_id}/approve", headers=headers)
    assert approve.status_code == 409
    assert approve.json()["detail"] == "preflight_not_passed"


def test_approve_after_preflight_succeeds(client):
    headers, _ = _setup_marketing_tenant(client, slug_suffix="approve-ok")
    pack_id = _create_ready_pack(client, headers, slug="approve-ok-pack")
    _put_text(client, headers, pack_id, "telegram", _LONG_TEXT)

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
    pack_id = _create_ready_pack(client, headers, slug="reject-pack")
    _put_text(client, headers, pack_id, "telegram", _LONG_TEXT)

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
    pack_id = _create_ready_pack(client, headers, slug="reset-text-pack")
    _put_text(client, headers, pack_id, "telegram", _LONG_TEXT)
    _preflight_and_approve(client, headers, pack_id)

    client.put(
        f"/api/v1/marketing/packs/{pack_id}/texts/telegram",
        headers=headers,
        json={"text": "edited after approve " + _LONG_TEXT},
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
    pack_id = _create_ready_pack(client, headers, slug="reset-media-pack")
    _put_text(client, headers, pack_id, "telegram", _LONG_TEXT)
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
    _put_text(client, headers, pack_id, "telegram", _LONG_TEXT)
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
    pack_id = _create_ready_pack(client, headers, slug="detail-status-pack")
    _put_text(client, headers, pack_id, "telegram", _LONG_TEXT)

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


# --- M7-C1 Preflight v2 -------------------------------------------------


def test_m7c1_no_topic_blocks(client):
    headers, _ = _setup_marketing_tenant(client, slug_suffix="m7c1-no-topic")
    pack_id = _create_pack(client, headers, slug="m7c1-no-topic-pack")
    _put_text(client, headers, pack_id, "telegram", _LONG_TEXT)

    pf = client.post(f"/api/v1/marketing/packs/{pack_id}/preflight", headers=headers)
    body = pf.json()
    assert body["status"] == "failed"
    assert body["passed"] is False
    assert any(e["code"] == "topic_missing" for e in body["blockers"])


def test_m7c1_topic_not_approved_blocks(client):
    headers, _ = _setup_marketing_tenant(client, slug_suffix="m7c1-draft-topic")
    topic_id = _create_topic(client, headers, title="Draft topic", status="draft")
    pack_id = _create_pack(client, headers, slug="m7c1-draft-topic-pack", topic_id=topic_id)
    _put_text(client, headers, pack_id, "telegram", _LONG_TEXT)

    pf = client.post(f"/api/v1/marketing/packs/{pack_id}/preflight", headers=headers)
    body = pf.json()
    assert body["status"] == "failed"
    assert any(e["code"] == "topic_not_approved" for e in body["errors"])


def test_m7c1_context_triple_missing_blocks(client):
    headers, _ = _setup_marketing_tenant(client, slug_suffix="m7c1-triple")
    topic_id = _create_topic(
        client,
        headers,
        title="Empty context",
        audience="",
        pain="",
        cta="",
        insight="has insight",
        source_ref="src",
        notes="n",
        planned_date="2026-07-21",
        funnel_stage="awareness",
    )
    # Explicitly clear editorial via patch in case empty strings ignored on create
    client.patch(
        f"/api/v1/marketing/topics/{topic_id}",
        headers=headers,
        json={"audience": None, "pain": None, "cta": None},
    )
    pack_id = _create_pack(client, headers, slug="m7c1-triple-pack", topic_id=topic_id)
    _put_text(client, headers, pack_id, "telegram", _LONG_TEXT)

    pf = client.post(f"/api/v1/marketing/packs/{pack_id}/preflight", headers=headers)
    body = pf.json()
    assert body["status"] == "failed"
    assert any(e["code"] == "context_triple_missing" for e in body["blockers"])


def test_m7c1_missing_insight_source_warns_but_passes(client):
    headers, _ = _setup_marketing_tenant(client, slug_suffix="m7c1-warn-ins")
    topic_id = _create_topic(
        client,
        headers,
        title="Warn insight",
        insight="",
        source_ref="",
        notes="",
        planned_date="",
    )
    client.patch(
        f"/api/v1/marketing/topics/{topic_id}",
        headers=headers,
        json={
            "insight": None,
            "source_ref": None,
            "notes": None,
            "planned_date": None,
        },
    )
    pack_id = _create_pack(client, headers, slug="m7c1-warn-ins-pack", topic_id=topic_id)
    _put_text(client, headers, pack_id, "telegram", _LONG_TEXT)

    pf = client.post(f"/api/v1/marketing/packs/{pack_id}/preflight", headers=headers)
    body = pf.json()
    assert body["passed"] is True
    assert body["preflight_status"] == "passed"
    assert body["status"] == "warning"
    codes = {w["code"] for w in body["warnings"]}
    assert "insight_missing" in codes
    assert "source_ref_missing" in codes
    assert "notes_missing" in codes
    assert "topic_planned_date_missing" in codes
    assert "media_missing" in codes

    approve = client.post(f"/api/v1/marketing/packs/{pack_id}/approve", headers=headers)
    assert approve.status_code == 200


def test_m7c1_cta_missing_for_funnel_warns(client):
    headers, _ = _setup_marketing_tenant(client, slug_suffix="m7c1-cta-funnel")
    topic_id = _create_topic(
        client,
        headers,
        title="Diagnosis topic",
        funnel_stage="diagnosis",
        cta="",
        audience="Owners",
        pain="Chaos",
    )
    client.patch(
        f"/api/v1/marketing/topics/{topic_id}",
        headers=headers,
        json={"cta": None, "funnel_stage": "diagnosis"},
    )
    pack_id = _create_pack(client, headers, slug="m7c1-cta-funnel-pack", topic_id=topic_id)
    _put_text(client, headers, pack_id, "telegram", _LONG_TEXT)

    pf = client.post(f"/api/v1/marketing/packs/{pack_id}/preflight", headers=headers)
    body = pf.json()
    assert body["passed"] is True
    assert any(w["code"] == "cta_missing_for_funnel" for w in body["warnings"])


def test_m7c1_all_social_texts_too_short_blocks(client):
    headers, _ = _setup_marketing_tenant(client, slug_suffix="m7c1-short-all")
    pack_id = _create_ready_pack(client, headers, slug="m7c1-short-all-pack")
    _put_text(client, headers, pack_id, "telegram", "short")
    _put_text(client, headers, pack_id, "instagram", "tiny")
    _put_text(client, headers, pack_id, "threads", "mini")

    pf = client.post(f"/api/v1/marketing/packs/{pack_id}/preflight", headers=headers)
    body = pf.json()
    assert body["status"] == "failed"
    assert any(e["code"] == "all_texts_too_short" for e in body["blockers"])


def test_m7c1_channel_text_short_warns(client):
    headers, _ = _setup_marketing_tenant(client, slug_suffix="m7c1-short-warn")
    pack_id = _create_ready_pack(client, headers, slug="m7c1-short-warn-pack")
    # 25 chars: above blocker threshold (20), below warn threshold (40)
    medium = "x" * 25
    _put_text(client, headers, pack_id, "telegram", medium)

    pf = client.post(f"/api/v1/marketing/packs/{pack_id}/preflight", headers=headers)
    body = pf.json()
    assert body["passed"] is True
    assert body["status"] == "warning"
    assert any(
        w["code"] == "channel_text_short" and w.get("channel") == "telegram"
        for w in body["warnings"]
    )


def test_m7c1_report_v2_shape_persisted(client):
    headers, _ = _setup_marketing_tenant(client, slug_suffix="m7c1-shape")
    pack_id = _create_ready_pack(client, headers, slug="m7c1-shape-pack")
    _put_text(client, headers, pack_id, "telegram", _LONG_TEXT)

    pf = client.post(f"/api/v1/marketing/packs/{pack_id}/preflight", headers=headers)
    body = pf.json()
    assert body["version"] == "m7-c1"
    assert "blockers" in body and "checklist" in body
    assert "topic_context_summary" in body
    assert isinstance(body["channel_checks"], list)
    assert isinstance(body["media_checks"], dict)

    detail = client.get(f"/api/v1/marketing/packs/{pack_id}", headers=headers)
    report = detail.json()["preflight_report_json"]
    assert report["version"] == "m7-c1"
    assert report["passed"] is True
    assert "blockers" in report
    assert "checklist" in report
