"""M7.5-C: prompt export + JSON preview/import + fingerprint."""

from __future__ import annotations

import copy
import uuid

from fastapi.testclient import TestClient

from app.modules.marketing.content_plan_schema import (
    SCHEMA_VERSION,
    PlanDocument,
    compute_import_fingerprint,
    parse_plan_document,
)

PLANS = "/api/v1/marketing/content-plans"
PROMPT = f"{PLANS}/prompt-export"
PREVIEW = f"{PLANS}/import/preview"
COMMIT = f"{PLANS}/import/commit"
GUIDES = "/api/v1/marketing/guides"
RUBRICS = "/api/v1/marketing/rubrics"
TOPICS = "/api/v1/marketing/topics"
PACKS = "/api/v1/marketing/packs"


def _setup(client: TestClient, *, suffix: str) -> tuple[dict[str, str], str]:
    email = f"m75c-{suffix}@example.com"
    password = "securepass123"
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": f"M75C {suffix}",
            "company_name": f"M75C Co {suffix}",
            "company_slug": f"m75c-co-{suffix}",
        },
    )
    assert reg.status_code == 201, reg.text
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    tenant = client.post(
        "/api/v1/tenants",
        json={"name": f"M75C Tenant {suffix}", "slug": f"m75c-tenant-{suffix}"},
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
    email = f"m75c-iso-{suffix}@example.com"
    password = "securepass123"
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": f"M75C Iso {suffix}",
            "company_name": f"M75C Iso Co {suffix}",
            "company_slug": f"m75c-iso-co-{suffix}",
        },
    )
    assert reg.status_code == 201, reg.text
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    tenant_a = client.post(
        "/api/v1/tenants",
        json={"name": f"Iso A {suffix}", "slug": f"m75c-iso-a-{suffix}"},
        headers=headers,
    )
    assert tenant_a.status_code == 201, tenant_a.text
    tenant_b = client.post(
        "/api/v1/tenants",
        json={"name": f"Iso B {suffix}", "slug": f"m75c-iso-b-{suffix}"},
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


def _guide_body(**overrides):
    body = {
        "business_name": "Flexity",
        "business_summary": "Multi-tenant ERP platform",
        "products_services": "Core + Marketing Cabinet",
        "audiences": "Founders of service businesses",
        "goals": "Dogfood content ops",
        "channels": ["telegram", "instagram"],
        "default_frequency": "daily",
        "tone_rules": "calm",
        "constraints": "no hype",
        "sources_notes": "internal notes",
        "extra_json": {"locale": "ru"},
        "activate": True,
    }
    body.update(overrides)
    return body


def _ensure_guide_and_rubric(
    client: TestClient,
    headers: dict[str, str],
    *,
    code: str = "asem_column",
) -> dict:
    guide = client.post(GUIDES, headers=headers, json=_guide_body())
    assert guide.status_code == 201, guide.text
    rubric = client.post(
        RUBRICS,
        headers=headers,
        json={"code": code, "name": code.replace("_", " ").title(), "sort_order": 1},
    )
    assert rubric.status_code == 201, rubric.text
    return rubric.json()


def _plan_doc(
    *,
    rubric_code: str = "asem_column",
    line_key: str = "line-1",
    item_date: str = "2026-08-10",
    title: str = "August plan",
    extra_items: list[dict] | None = None,
) -> dict:
    items = [
        {
            "line_key": line_key,
            "date": item_date,
            "rubric_code": rubric_code,
            "working_title": "First post",
            "channels": ["telegram"],
            "angle": "value",
            "goal": "awareness",
        }
    ]
    if extra_items:
        items.extend(extra_items)
    return {
        "schema_version": SCHEMA_VERSION,
        "period_start": "2026-08-01",
        "period_end": "2026-08-31",
        "title": title,
        "items": items,
    }


def test_prompt_built_from_guide_and_active_rubrics(client: TestClient):
    headers, _ = _setup(client, suffix="prompt")
    rubric = _ensure_guide_and_rubric(client, headers)
    resp = client.post(
        PROMPT,
        headers=headers,
        json={
            "period_start": "2026-08-01",
            "period_end": "2026-08-31",
            "channels": ["telegram", "instagram"],
            "target_item_count": 8,
            "language": "ru",
            "additional_instructions": "Prefer morning slots",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["schema_version"] == SCHEMA_VERSION
    assert body["guide_version"] >= 1
    assert rubric["code"] in body["rubric_codes"]
    assert str(rubric["id"]) in [str(x) for x in body["rubric_ids"]]
    assert SCHEMA_VERSION in body["prompt_text"]
    assert "Prefer morning slots" in body["prompt_text"]
    assert "asem_column" in body["prompt_text"]
    assert "json_schema" in body
    assert "access_token" not in resp.text


def test_prompt_fail_closed_no_guide_or_rubrics(client: TestClient):
    headers, _ = _setup(client, suffix="prompt-fail")
    no_guide = client.post(
        PROMPT,
        headers=headers,
        json={
            "period_start": "2026-08-01",
            "period_end": "2026-08-31",
            "channels": ["telegram"],
            "target_item_count": 3,
        },
    )
    assert no_guide.status_code == 404
    assert "marketing_guide_not_found" in no_guide.text

    client.post(GUIDES, headers=headers, json=_guide_body())
    no_rubrics = client.post(
        PROMPT,
        headers=headers,
        json={
            "period_start": "2026-08-01",
            "period_end": "2026-08-31",
            "channels": ["telegram"],
            "frequency": "daily",
        },
    )
    assert no_rubrics.status_code == 409
    assert "no_active_rubrics" in no_rubrics.text


def test_prompt_tenant_isolation(client: TestClient):
    h1, h2 = _setup_two_tenants(client, suffix="prompt-iso")
    _ensure_guide_and_rubric(client, h1, code="tenant_a_rubric")
    missing = client.post(
        PROMPT,
        headers=h2,
        json={
            "period_start": "2026-08-01",
            "period_end": "2026-08-31",
            "channels": ["telegram"],
            "target_item_count": 2,
        },
    )
    assert missing.status_code == 404


def test_preview_valid_no_writes(client: TestClient):
    headers, _ = _setup(client, suffix="preview-ok")
    _ensure_guide_and_rubric(client, headers)
    before = client.get(PLANS, headers=headers)
    assert before.status_code == 200
    assert before.json() == []

    plan = _plan_doc()
    preview = client.post(PREVIEW, headers=headers, json={"plan": plan})
    assert preview.status_code == 200, preview.text
    body = preview.json()
    assert body["valid"] is True
    assert body["errors"] == []
    assert body["import_fingerprint"]
    assert body["fingerprint_already_imported"] is False
    assert body["resolved_items"][0]["resolved"] is True

    after = client.get(PLANS, headers=headers)
    assert after.json() == []


def test_preview_invalid_schema_malformed_duplicate_dates(client: TestClient):
    headers, _ = _setup(client, suffix="preview-bad")
    _ensure_guide_and_rubric(client, headers)

    bad_version = _plan_doc()
    bad_version["schema_version"] = "m7.5.plan.v0"
    r1 = client.post(PREVIEW, headers=headers, json={"plan": bad_version})
    assert r1.status_code == 200
    assert r1.json()["valid"] is False
    assert any("schema" in e["code"] or "schema" in e["message"] for e in r1.json()["errors"])

    r2 = client.post(PREVIEW, headers=headers, json={"plan": "{not-json"})
    assert r2.status_code == 200
    assert r2.json()["valid"] is False
    assert any(e["code"] == "malformed_json" for e in r2.json()["errors"])

    dup = _plan_doc(
        extra_items=[
            {
                "line_key": "line-1",
                "date": "2026-08-11",
                "rubric_code": "asem_column",
                "working_title": "Dup key",
                "channels": ["telegram"],
            }
        ]
    )
    r3 = client.post(PREVIEW, headers=headers, json={"plan": dup})
    assert r3.status_code == 200
    assert r3.json()["valid"] is False
    assert any("duplicate_line_key" in (e["code"] + e["message"]) for e in r3.json()["errors"])

    out = _plan_doc(item_date="2026-09-01")
    r4 = client.post(PREVIEW, headers=headers, json={"plan": out})
    assert r4.status_code == 200
    assert r4.json()["valid"] is False
    assert any(
        "planned_date_out_of_period" in (e["code"] + e["message"])
        for e in r4.json()["errors"]
    )


def test_preview_unknown_and_inactive_rubric(client: TestClient):
    headers, _ = _setup(client, suffix="preview-rubric")
    rubric = _ensure_guide_and_rubric(client, headers, code="live_code")

    unknown = client.post(
        PREVIEW, headers=headers, json={"plan": _plan_doc(rubric_code="ghost_code")}
    )
    assert unknown.status_code == 200
    body = unknown.json()
    assert body["valid"] is False
    assert "ghost_code" in body["unknown_rubric_codes"]
    assert body["resolved_items"][0]["resolved"] is False

    archived = client.post(f"{RUBRICS}/{rubric['id']}/archive", headers=headers)
    assert archived.status_code == 200, archived.text
    inactive = client.post(
        PREVIEW, headers=headers, json={"plan": _plan_doc(rubric_code="live_code")}
    )
    assert inactive.status_code == 200
    ib = inactive.json()
    assert ib["valid"] is False
    assert any(e["code"] == "rubric_not_active" for e in ib["errors"])


def test_preview_explicit_mapping_and_cross_tenant(client: TestClient):
    h1, h2 = _setup_two_tenants(client, suffix="map")
    r1 = _ensure_guide_and_rubric(client, h1, code="local_a")
    r2 = _ensure_guide_and_rubric(client, h2, code="local_b")

    ok = client.post(
        PREVIEW,
        headers=h1,
        json={
            "plan": _plan_doc(rubric_code="alias_code"),
            "rubric_code_map": {"alias_code": r1["id"]},
        },
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["valid"] is True
    assert ok.json()["resolved_items"][0]["rubric_id"] == r1["id"]

    cross = client.post(
        PREVIEW,
        headers=h1,
        json={
            "plan": _plan_doc(rubric_code="alias_code"),
            "rubric_code_map": {"alias_code": r2["id"]},
        },
    )
    assert cross.status_code == 404
    assert "marketing_rubric_not_found" in cross.text


def test_fingerprint_canonicalization_and_tenant_scope():
    doc_a = parse_plan_document(_plan_doc())
    shuffled = {
        "title": "August plan",
        "period_end": "2026-08-31",
        "schema_version": SCHEMA_VERSION,
        "period_start": "2026-08-01",
        "items": [
            {
                "channels": ["telegram"],
                "working_title": "First post",
                "rubric_code": "asem_column",
                "date": "2026-08-10",
                "line_key": "line-1",
                "goal": "awareness",
                "angle": "value",
            }
        ],
    }
    doc_b = parse_plan_document(shuffled)
    tenant = uuid.UUID("11111111-1111-1111-1111-111111111111")
    other = uuid.UUID("22222222-2222-2222-2222-222222222222")
    assert compute_import_fingerprint(tenant, doc_a) == compute_import_fingerprint(
        tenant, doc_b
    )
    assert compute_import_fingerprint(tenant, doc_a) != compute_import_fingerprint(
        other, doc_a
    )


def test_commit_create_replay_and_statuses(client: TestClient):
    headers, _ = _setup(client, suffix="commit")
    _ensure_guide_and_rubric(client, headers)
    plan = _plan_doc()

    first = client.post(COMMIT, headers=headers, json={"plan": plan})
    assert first.status_code == 201, first.text
    body = first.json()
    assert body["replayed"] is False
    assert body["item_count"] == 1
    assert body["plan"]["source"] == "json_import"
    assert body["plan"]["status"] == "draft"
    assert body["plan"]["import_fingerprint"] == body["import_fingerprint"]
    plan_id = body["plan"]["id"]

    items = client.get(f"{PLANS}/{plan_id}/items", headers=headers)
    assert items.status_code == 200
    assert len(items.json()) == 1
    assert items.json()[0]["status"] == "draft"
    assert items.json()[0]["line_key"] == "line-1"
    assert items.json()[0]["topic_id"] is None

    topics = client.get(TOPICS, headers=headers)
    assert topics.status_code == 200
    topic_payload = topics.json()
    if isinstance(topic_payload, list):
        assert topic_payload == []
    elif isinstance(topic_payload, dict) and "items" in topic_payload:
        assert topic_payload["items"] == []

    packs = client.get(PACKS, headers=headers)
    assert packs.status_code in (200, 404, 405, 422)
    if packs.status_code == 200:
        payload = packs.json()
        if isinstance(payload, list):
            assert payload == []
        elif isinstance(payload, dict) and "items" in payload:
            assert payload["items"] == []

    preview = client.post(PREVIEW, headers=headers, json={"plan": plan})
    assert preview.json()["fingerprint_already_imported"] is True
    assert preview.json()["existing_plan_id"] == plan_id

    shuffled = copy.deepcopy(plan)
    shuffled["items"][0] = {
        "goal": "awareness",
        "angle": "value",
        "channels": ["telegram"],
        "working_title": "First post",
        "rubric_code": "asem_column",
        "date": "2026-08-10",
        "line_key": "line-1",
    }
    replay = client.post(COMMIT, headers=headers, json={"plan": shuffled})
    assert replay.status_code == 200, replay.text
    assert replay.json()["replayed"] is True
    assert replay.json()["plan"]["id"] == plan_id

    listed = client.get(PLANS, headers=headers)
    assert len(listed.json()) == 1


def test_commit_validation_failure_zero_writes(client: TestClient):
    headers, _ = _setup(client, suffix="commit-fail")
    _ensure_guide_and_rubric(client, headers)
    bad = _plan_doc(rubric_code="missing_code")
    resp = client.post(COMMIT, headers=headers, json={"plan": bad})
    assert resp.status_code == 409
    assert client.get(PLANS, headers=headers).json() == []


def test_commit_item_failure_full_rollback(
    client: TestClient, db_session, monkeypatch
):
    import pytest

    headers, _ = _setup(client, suffix="commit-rb")
    _ensure_guide_and_rubric(client, headers)
    plan = _plan_doc(
        extra_items=[
            {
                "line_key": "line-2",
                "date": "2026-08-11",
                "rubric_code": "asem_column",
                "working_title": "Second",
                "channels": ["instagram"],
            }
        ]
    )

    from app.modules.marketing import repository as repo_mod

    original = repo_mod.MarketingRepository.create_content_plan_item
    calls = {"n": 0}

    def flaky(self, **kwargs):
        calls["n"] += 1
        if calls["n"] >= 2:
            raise RuntimeError("forced_item_failure")
        return original(self, **kwargs)

    monkeypatch.setattr(
        repo_mod.MarketingRepository, "create_content_plan_item", flaky
    )
    with pytest.raises(RuntimeError, match="forced_item_failure"):
        client.post(COMMIT, headers=headers, json={"plan": plan})
    # Shared test session keeps flushed rows until rollback (prod Session.close rolls back).
    db_session.rollback()
    assert client.get(PLANS, headers=headers).json() == []


def test_import_tenant_isolation(client: TestClient):
    h1, h2 = _setup_two_tenants(client, suffix="imp-iso")
    _ensure_guide_and_rubric(client, h1, code="shared_code")
    _ensure_guide_and_rubric(client, h2, code="shared_code")
    plan = _plan_doc(rubric_code="shared_code")
    created = client.post(COMMIT, headers=h1, json={"plan": plan})
    assert created.status_code == 201, created.text
    plan_id = created.json()["plan"]["id"]

    assert client.get(f"{PLANS}/{plan_id}", headers=h2).status_code == 404
    assert client.get(PLANS, headers=h2).json() == []


def test_regression_manual_plan_and_topics_still_work(client: TestClient):
    """M7.5-A/B + Topics regression smoke."""
    headers, _ = _setup(client, suffix="regress")
    rubric = _ensure_guide_and_rubric(client, headers)

    plan = client.post(
        PLANS,
        headers=headers,
        json={
            "title": "Manual",
            "period_start": "2026-08-01",
            "period_end": "2026-08-31",
        },
    )
    assert plan.status_code == 201
    item = client.post(
        f"{PLANS}/{plan.json()['id']}/items",
        headers=headers,
        json={
            "planned_date": "2026-08-05",
            "rubric_id": rubric["id"],
            "working_title": "Manual item",
            "channels": ["telegram"],
            "line_key": "manual-1",
        },
    )
    assert item.status_code == 201, item.text

    topic = client.post(
        TOPICS,
        headers=headers,
        json={
            "title": "Topic smoke",
            "rubric": rubric["code"],
            "recommended_channels": ["telegram"],
        },
    )
    assert topic.status_code == 201, topic.text


def test_shared_schema_parse_roundtrip():
    raw = _plan_doc()
    doc = parse_plan_document(raw)
    assert isinstance(doc, PlanDocument)
    assert doc.schema_version == SCHEMA_VERSION
    again = parse_plan_document(doc.model_dump(mode="json"))
    assert again.items[0].line_key == "line-1"
