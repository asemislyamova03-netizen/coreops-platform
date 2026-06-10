"""End-to-end MVP journey from TZ Definition of Done (single integration test)."""

import uuid


def test_mvp_core_journey(client):
  uid = uuid.uuid4().hex[:8]
  register = {
      "email": f"mvp-{uid}@example.com",
      "password": "securepass123",
      "full_name": "MVP Owner",
      "company_name": "MVP Provider",
      "company_slug": f"mvp-provider-{uid}",
  }

  assert client.post("/api/v1/auth/register", json=register).status_code == 201
  token = client.post(
      "/api/v1/auth/login",
      json={"email": register["email"], "password": register["password"]},
  ).json()["access_token"]
  headers = {"Authorization": f"Bearer {token}"}

  tenant = client.post(
      "/api/v1/tenants",
      json={
          "name": "MVP Kindergarten",
          "slug": f"mvp-tenant-{uid}",
          "industry_template_code": "kindergarten_basic",
          "plan_code": "enterprise",
      },
      headers=headers,
  )
  assert tenant.status_code == 201
  tenant_id = tenant.json()["id"]
  th = {**headers, "X-Tenant-ID": tenant_id}

  modules = {m["module_code"]: m for m in client.get(f"/api/v1/tenants/{tenant_id}/modules", headers=headers).json()}
  assert modules["parties"]["status"] in ("enabled", "trial")
  assert modules["crm"]["status"] in ("enabled", "trial")
  assert modules["ai"]["status"] in ("enabled", "trial")

  templates = client.get("/api/v1/document-templates", headers=th)
  assert templates.status_code == 200
  assert any(t["code"] == "parent_contract" for t in templates.json())

  agents = client.get("/api/v1/ai/agents", headers=th)
  assert agents.status_code == 200
  assert len(agents.json()) >= 1

  guardian = client.post(
      "/api/v1/parties",
      headers=th,
      json={
          "party_type": "person",
          "display_name": "Родитель MVP",
          "party_role": "guardian",
      },
  )
  assert guardian.status_code == 201
  party_id = guardian.json()["id"]

  pipeline = next(
      p for p in client.get("/api/v1/pipelines", headers=th).json() if p["code"] == "enrollment"
  )
  stage_id = min(pipeline["stages"], key=lambda s: s["sort_order"])["id"]

  work_item = client.post(
      "/api/v1/work-items",
      headers=th,
      json={
          "pipeline_id": pipeline["id"],
          "stage_id": stage_id,
          "work_item_type": "inquiry",
          "title": "MVP заявка",
          "primary_party_id": party_id,
      },
  )
  assert work_item.status_code == 201
  work_item_id = work_item.json()["id"]

  service = client.post(
      "/api/v1/catalog/items",
      headers=th,
      json={
          "item_type": "subscription_service",
          "name": "Обучение MVP",
          "sku": f"mvp-edu-{uid}",
          "base_price": "12000",
          "currency": "RUB",
      },
  )
  assert service.status_code == 201

  contract = next(t for t in templates.json() if t["code"] == "parent_contract")
  document = client.post(
      "/api/v1/documents/generate",
      headers=th,
      json={
          "template_id": contract["id"],
          "context": {
              "contract_number": "MVP-1",
              "contract_date": "2025-09-01",
              "kindergarten_name": "MVP Kindergarten",
              "guardian_name": "Родитель MVP",
              "guardian_relationship": "мать",
              "child_name": "Ребёнок MVP",
              "start_date": "2025-09-01",
              "monthly_fee": "12000",
          },
          "party_id": party_id,
          "work_item_id": work_item_id,
      },
  )
  assert document.status_code == 201

  legal = client.post(
      "/api/v1/accounting/legal-entities",
      headers=th,
      json={"name": "ООО MVP Сад", "country": "RU", "tax_number": "7700000001"},
  )
  assert legal.status_code == 201

  invoice = client.post(
      "/api/v1/finance/invoices",
      headers=th,
      json={
          "party_id": party_id,
          "legal_entity_id": legal.json()["id"],
          "lines": [{"description": "Обучение", "quantity": "1", "unit_price": "12000"}],
          "issue": True,
      },
  )
  assert invoice.status_code == 201
  invoice_id = invoice.json()["id"]

  payment = client.post(
      "/api/v1/finance/payments",
      headers=th,
      json={
          "party_id": party_id,
          "amount": "12000",
          "currency": "RUB",
          "payment_date": "2025-09-15",
      },
  )
  assert payment.status_code == 201

  allocated = client.post(
      f"/api/v1/finance/payments/{payment.json()['id']}/allocate",
      headers=th,
      json={"allocations": [{"invoice_id": invoice_id, "amount": "12000"}]},
  )
  assert allocated.status_code == 200
  assert allocated.json()["status"] == "completed"
  paid_invoice = client.get(f"/api/v1/finance/invoices/{invoice_id}", headers=th)
  assert paid_invoice.status_code == 200
  assert paid_invoice.json()["status"] == "paid"

  connection = client.post(
      "/api/v1/integrations/connections",
      headers=th,
      json={
          "provider_code": "bitrix24",
          "module_code": "crm",
          "name": "Bitrix MVP",
          "credentials_json": {"portal_url": "https://demo.bitrix24.ru"},
      },
  )
  assert connection.status_code == 201
  conn_id = connection.json()["id"]
  assert client.post(f"/api/v1/integrations/connections/{conn_id}/test", headers=th).json()["success"]

  client.patch(
      f"/api/v1/tenants/{tenant_id}/modules/crm/mode",
      headers=headers,
      json={"mode": "external", "external_provider_code": "bitrix24"},
  )

  agent_id = agents.json()[0]["id"]
  task = client.post(
      "/api/v1/ai/tasks",
      headers=th,
      json={"agent_id": agent_id, "title": "MVP AI task", "run_mock": True},
  )
  assert task.status_code == 201
  proposal_id = task.json()["output_json"]["proposal_id"]

  assert client.post(f"/api/v1/ai/action-proposals/{proposal_id}/approve", headers=th).status_code == 200
  assert (
      client.post(f"/api/v1/ai/action-proposals/{proposal_id}/execute", headers=th).json()["status"]
      == "executed"
  )

  security = client.get("/api/v1/audit/security-events", headers=headers)
  assert security.status_code == 200
  assert any(e["event_type"] == "login_success" for e in security.json())

  audit_logs = client.get(f"/api/v1/audit/logs?tenant_id={tenant_id}", headers=headers)
  assert audit_logs.status_code == 200
  assert any(log["action"] == "approve" for log in audit_logs.json())

  receivables = client.get("/api/v1/finance/receivables", headers=th)
  assert receivables.status_code == 200
  assert len(receivables.json()) == 0
