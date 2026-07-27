"""M7.5-A HTTP API tests: Marketing Guide + Rubrics."""



from __future__ import annotations



from fastapi.testclient import TestClient



GUIDES = "/api/v1/marketing/guides"

RUBRICS = "/api/v1/marketing/rubrics"

TOPICS = "/api/v1/marketing/topics"





def _setup(client: TestClient, *, suffix: str) -> tuple[dict[str, str], str]:

    """One platform bootstrap + one tenant with marketing enabled."""

    email = f"m75a-{suffix}@example.com"

    password = "securepass123"

    reg = client.post(

        "/api/v1/auth/register",

        json={

            "email": email,

            "password": password,

            "full_name": f"M75A {suffix}",

            "company_name": f"M75A Co {suffix}",

            "company_slug": f"m75a-co-{suffix}",

        },

    )

    assert reg.status_code == 201, reg.text

    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})

    assert login.status_code == 200, login.text

    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    tenant = client.post(

        "/api/v1/tenants",

        json={"name": f"M75A Tenant {suffix}", "slug": f"m75a-tenant-{suffix}"},

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

    """Same provider owner, two client tenants (register is bootstrap-once)."""

    email = f"m75a-iso-{suffix}@example.com"

    password = "securepass123"

    reg = client.post(

        "/api/v1/auth/register",

        json={

            "email": email,

            "password": password,

            "full_name": f"M75A Iso {suffix}",

            "company_name": f"M75A Iso Co {suffix}",

            "company_slug": f"m75a-iso-co-{suffix}",

        },

    )

    assert reg.status_code == 201, reg.text

    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}



    tenant_a = client.post(

        "/api/v1/tenants",

        json={"name": f"Iso A {suffix}", "slug": f"m75a-iso-a-{suffix}"},

        headers=headers,

    )

    assert tenant_a.status_code == 201, tenant_a.text

    tenant_b = client.post(

        "/api/v1/tenants",

        json={"name": f"Iso B {suffix}", "slug": f"m75a-iso-b-{suffix}"},

        headers=headers,

    )

    assert tenant_b.status_code == 201, tenant_b.text



    id_a, id_b = tenant_a.json()["id"], tenant_b.json()["id"]

    for tenant_id in (id_a, id_b):

        assert (

            client.post(

                f"/api/v1/tenants/{tenant_id}/modules/parties/enable",

                headers={**headers, "X-Tenant-ID": tenant_id},

            ).status_code

            == 200

        )

        assert (

            client.post(

                f"/api/v1/tenants/{tenant_id}/modules/marketing/enable",

                headers={**headers, "X-Tenant-ID": tenant_id},

            ).status_code

            == 200

        )

    return (

        {**headers, "X-Tenant-ID": id_a},

        {**headers, "X-Tenant-ID": id_b},

    )





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

        "activate": False,

    }

    body.update(overrides)

    return body





def test_guide_active_404_then_activate_and_supersede(client: TestClient):

    headers, _ = _setup(client, suffix="guide-lifecycle")

    missing = client.get(f"{GUIDES}/active", headers=headers)

    assert missing.status_code == 404



    created = client.post(GUIDES, headers=headers, json=_guide_body())

    assert created.status_code == 201, created.text

    assert created.json()["status"] == "draft"

    assert created.json()["version"] == 1



    activated = client.post(

        f"{GUIDES}/{created.json()['id']}/activate", headers=headers

    )

    assert activated.status_code == 200

    assert activated.json()["status"] == "active"



    active = client.get(f"{GUIDES}/active", headers=headers)

    assert active.status_code == 200

    assert active.json()["id"] == created.json()["id"]



    second = client.post(

        GUIDES, headers=headers, json=_guide_body(activate=True, business_name="Flexity v2")

    )

    assert second.status_code == 201, second.text

    assert second.json()["status"] == "active"

    assert second.json()["version"] == 2



    history = client.get(GUIDES, headers=headers)

    assert history.status_code == 200

    rows = history.json()

    assert len(rows) == 2

    statuses = {row["id"]: row["status"] for row in rows}

    assert statuses[created.json()["id"]] == "superseded"

    assert statuses[second.json()["id"]] == "active"



    only_one_active = [row for row in rows if row["status"] == "active"]

    assert len(only_one_active) == 1





def test_guide_tenant_isolation(client: TestClient):

    h1, h2 = _setup_two_tenants(client, suffix="g-iso")

    created = client.post(GUIDES, headers=h1, json=_guide_body(activate=True))

    assert created.status_code == 201

    guide_id = created.json()["id"]



    assert client.get(f"{GUIDES}/active", headers=h2).status_code == 404

    assert client.get(f"{GUIDES}/{guide_id}", headers=h2).status_code == 404

    assert client.get(f"{GUIDES}/{guide_id}", headers=h1).status_code == 200





def test_rubric_uniqueness_per_tenant_and_cross_tenant_ok(client: TestClient):

    h1, h2 = _setup_two_tenants(client, suffix="r-uni")

    body = {

        "code": "asem_column",

        "name": "Авторская колонка",

        "description": "d",

        "sort_order": 1,

    }

    r1 = client.post(RUBRICS, headers=h1, json=body)

    assert r1.status_code == 201, r1.text

    dup = client.post(RUBRICS, headers=h1, json=body)

    assert dup.status_code == 409



    r2 = client.post(RUBRICS, headers=h2, json=body)

    assert r2.status_code == 201, r2.text

    assert r2.json()["code"] == "asem_column"

    assert r1.json()["tenant_id"] != r2.json()["tenant_id"]





def test_rubric_lifecycle_and_not_selectable_for_new_topic(client: TestClient):

    headers, _ = _setup(client, suffix="r-life")

    created = client.post(

        RUBRICS,

        headers=headers,

        json={"code": "business_diagnosis", "name": "Диагностика", "sort_order": 5},

    )

    assert created.status_code == 201

    rubric_id = created.json()["id"]



    inactive = client.post(f"{RUBRICS}/{rubric_id}/deactivate", headers=headers)

    assert inactive.status_code == 200

    assert inactive.json()["status"] == "inactive"



    blocked = client.post(

        TOPICS,

        headers=headers,

        json={"title": "Blocked topic", "rubric": "business_diagnosis"},

    )

    assert blocked.status_code == 409

    assert "marketing_rubric_not_selectable" in blocked.text



    active = client.post(f"{RUBRICS}/{rubric_id}/activate", headers=headers)

    assert active.status_code == 200

    ok = client.post(

        TOPICS,

        headers=headers,

        json={"title": "Ok topic", "rubric": "business_diagnosis", "status": "draft"},

    )

    assert ok.status_code == 201, ok.text



    archived = client.post(f"{RUBRICS}/{rubric_id}/archive", headers=headers)

    assert archived.status_code == 200

    blocked2 = client.post(

        TOPICS,

        headers=headers,

        json={"title": "Blocked again", "rubric": "business_diagnosis"},

    )

    assert blocked2.status_code == 409



    # Legacy free-text rubric still allowed when no matching directory row.

    legacy = client.post(

        TOPICS,

        headers=headers,

        json={"title": "Legacy", "rubric": "Продуктовое видение Flexity"},

    )

    assert legacy.status_code == 201, legacy.text





def test_rubric_code_immutable(client: TestClient):

    headers, _ = _setup(client, suffix="r-imm")

    created = client.post(

        RUBRICS,

        headers=headers,

        json={"code": "founder_notes", "name": "Notes"},

    )

    assert created.status_code == 201

    patched = client.patch(

        f"{RUBRICS}/{created.json()['id']}",

        headers=headers,

        json={"code": "other_code", "name": "Notes 2"},

    )

    assert patched.status_code == 409





def test_seed_defaults_idempotent(client: TestClient):

    headers, _ = _setup(client, suffix="r-seed")

    first = client.post(f"{RUBRICS}/seed-defaults", headers=headers, json={})

    assert first.status_code == 200, first.text

    assert first.json()["created"] == 10

    assert first.json()["skipped"] == 0



    second = client.post(f"{RUBRICS}/seed-defaults", headers=headers, json={})

    assert second.status_code == 200

    assert second.json()["created"] == 0

    assert second.json()["skipped"] == 10

    assert second.json()["updated"] == 0



    listed = client.get(f"{RUBRICS}?status=active", headers=headers)

    assert listed.status_code == 200

    assert len(listed.json()) == 10





def test_rubric_tenant_isolation(client: TestClient):

    h1, h2 = _setup_two_tenants(client, suffix="r-iso")

    created = client.post(

        RUBRICS, headers=h1, json={"code": "client_journey", "name": "Journey"}

    )

    assert created.status_code == 201

    rid = created.json()["id"]

    assert client.get(f"{RUBRICS}/{rid}", headers=h2).status_code == 404

    assert client.get(RUBRICS, headers=h2).json() == []





def test_topic_take_pack_regression_with_seeded_rubric(client: TestClient):

    headers, _ = _setup(client, suffix="topic-reg")

    assert client.post(f"{RUBRICS}/seed-defaults", headers=headers, json={}).status_code == 200

    topic = client.post(

        TOPICS,

        headers=headers,

        json={

            "title": "Regression topic",

            "rubric": "asem_column",

            "status": "approved",

            "angle": "angle",

        },

    )

    assert topic.status_code == 201, topic.text

    taken = client.post(

        f"{TOPICS}/{topic.json()['id']}/take",

        headers=headers,

        json={},

    )

    assert taken.status_code == 201, taken.text

    assert taken.json()["topic_id"] == topic.json()["id"]

    pack_id = taken.json()["id"]

    pack = client.get(f"/api/v1/marketing/packs/{pack_id}", headers=headers)

    assert pack.status_code == 200

    assert pack.json()["topic_id"] == topic.json()["id"]
