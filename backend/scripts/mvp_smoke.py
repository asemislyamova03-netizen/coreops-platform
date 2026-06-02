#!/usr/bin/env python3
"""Manual MVP smoke — same flow as tests/test_mvp_scenario.py (requires running API)."""

from __future__ import annotations

import sys
import uuid

import httpx

BASE = "http://localhost:8000/api/v1"
SLUG = f"mvp-smoke-{uuid.uuid4().hex[:8]}"


def main() -> int:
    client = httpx.Client(base_url=BASE, timeout=30.0)
    register = {
        "email": f"owner-{SLUG}@example.com",
        "password": "securepass123",
        "full_name": "Smoke Owner",
        "company_name": "Smoke Provider",
        "company_slug": f"smoke-{SLUG}",
    }

    steps: list[tuple[str, bool]] = []

    def check(name: str, response: httpx.Response, expected: int = 200) -> None:
        ok = response.status_code == expected
        steps.append((name, ok))
        mark = "OK" if ok else "FAIL"
        print(f"  [{mark}] {name} -> {response.status_code}")
        if not ok:
            print(f"       {response.text[:300]}")

    print("MVP smoke against", BASE)

    r = client.post("/auth/register", json=register)
    check("register", r, 201)
    r = client.post("/auth/login", json={"email": register["email"], "password": register["password"]})
    check("login", r)
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    r = client.post(
        "/tenants",
        headers=headers,
        json={
            "name": "Smoke Kindergarten",
            "slug": SLUG,
            "industry_template_code": "kindergarten_basic",
            "plan_code": "enterprise",
        },
    )
    check("create tenant", r, 201)
    tenant_id = r.json()["id"]
    th = {**headers, "X-Tenant-ID": tenant_id}

    r = client.get("/ai/agents", headers=th)
    check("ai agents seeded", r)
    r = client.get("/document-templates", headers=th)
    check("document templates", r)

    r = client.post(
        "/parties",
        headers=th,
        json={"party_type": "person", "display_name": "Guardian", "party_role": "guardian"},
    )
    check("create party", r, 201)
    party_id = r.json()["id"]

    pipelines = client.get("/pipelines", headers=th).json()
    pipeline_id = pipelines[0]["id"]
    stage_id = pipelines[0]["stages"][0]["id"]
    r = client.post(
        "/work-items",
        headers=th,
        json={
            "title": "Smoke lead",
            "pipeline_id": pipeline_id,
            "stage_id": stage_id,
            "work_item_type": "inquiry",
            "primary_party_id": party_id,
        },
    )
    check("create work item", r, 201)

    r = client.post(
        "/finance/invoices",
        headers=th,
        json={
            "party_id": party_id,
            "lines": [{"description": "Fee", "quantity": "1", "unit_price": "1000"}],
            "issue": True,
        },
    )
    check("create invoice", r, 201)

    r = client.get("/audit/security-events", headers=headers)
    check("audit security events", r)

    client.close()
    failed = [name for name, ok in steps if not ok]
    print()
    if failed:
        print("FAILED:", ", ".join(failed))
        return 1
    print("All smoke steps passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
