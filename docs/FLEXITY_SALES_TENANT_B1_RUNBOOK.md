# FLEXITY SALES TENANT — B1 RUNBOOK

**Purpose:** bootstrap internal sales tenant after B1 template implementation.  
**Scope:** dev/staging only. No production deploy in this runbook.

---

## Prerequisites

- Backend running locally with `SEED_ON_STARTUP=true` (default)
- Platform Console connected to same API
- Provider owner account (platform admin)

---

## Step 1 — Verify template loaded

```bash
# After login, list templates
GET /api/v1/industry-templates
```

Expected: `flexity_sales_basic` in list.

Or run tests:

```bash
cd backend
python -m pytest tests/test_industry_templates.py -v
```

---

## Step 2 — Create sales tenant (Platform Console)

1. Open `/console/tenants/new`
2. Fill:
   - **Name:** `Flexity Sales`
   - **Slug:** `flexity-sales`
   - **Industry template:** `flexity_sales_basic`
   - **Plan:** `enterprise` (recommended)
3. Submit

Template auto-applies on create when `industry_template_code` is set.

---

## Step 3 — Add sales team users (optional)

1. Open tenant detail `/console/tenants/{id}`
2. Add users with role `tenant_owner` or `tenant_admin`
3. No hardcoded emails in code — assign per HQ decision

---

## Step 4 — Open workspace

Navigate to:

```
/console/workspace/flexity-sales/crm
```

Expected:

- Pipeline **Воронка продаж Flexity** (`flexity_sales`)
- 9 kanban columns
- Label «Лид» for work items

---

## Step 5 — Manual lead smoke

1. **Clients** → create contact (Party)
2. **CRM** → «Создать заявку» → link Party, set title
3. Card appears in **Новый лид** (`new_lead`)
4. Move through stages (e.g. → Первичный контакт)
5. Add activity/note on work item

---

## Step 6 — Capture UUIDs (for future B2b)

After tenant create, record in secure ops notes (not in git):

| Resource | Where to find |
|----------|---------------|
| Tenant UUID | Tenant detail page or `GET /api/v1/tenants` |
| Pipeline UUID | `GET /api/v1/pipelines` with `X-Tenant-ID` |
| Stage UUIDs | Same pipelines response → `stages[]` |

Future public inbound may need `PUBLIC_LEADS_TENANT_ID` — **not enabled in B1**.

---

## API alternative (smoke script pattern)

Reference: `backend/scripts/mvp_smoke.py`

```http
POST /api/v1/tenants
{
  "name": "Flexity Sales",
  "slug": "flexity-sales",
  "industry_template_code": "flexity_sales_basic",
  "plan_code": "enterprise"
}
```

Then `POST /api/v1/parties` and `POST /api/v1/work-items` with `X-Tenant-ID`.

---

## Troubleshooting

| Issue | Check |
|-------|-------|
| Template not in list | Restart backend; confirm `INDUSTRY_TEMPLATES` includes `flexity_sales_basic` |
| Empty CRM | Pipeline `is_default` must be true (seed has it) |
| Wrong labels | Confirm template `flexity_sales_basic`, not `kindergarten_basic` |
| 403 on tenant | User must be provider_owner or tenant member |

---

## Forbidden in this runbook

- Production deploy
- Enable `PUBLIC_LEADS_*`
- Cherry-pick `codex/public-inbound-leads`
- Merge inbound branch

---

*Runbook v1.0 — companion to B1 implementation report.*
