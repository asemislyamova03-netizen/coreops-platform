# FLEXITY SALES TENANT B1 IMPLEMENTATION REPORT

**Дата:** 2026-07-02  
**Slice:** B1 — Sales Tenant Bootstrap Template  
**Статус:** ✅ implementation complete (dev/local)

---

## 1. Task Classification

| Field     | Value                                                              |
| --------- | ------------------------------------------------------------------ |
| Project   | Flexity                                                            |
| Category  | `industry_template`                                                |
| Risk      | low                                                                |
| Scope     | sales tenant template only (`flexity_sales_basic`)                 |
| Forbidden | production, deploy, migrations, public inbound, merge, cherry-pick |

---

## 2. Summary

B1 добавляет industry template **`flexity_sales_basic`** в существующий механизм `industry_templates/seed.py`.

Template описывает внутренний sales workspace Flexity:

- pipeline **`flexity_sales`** (default);
- **9 stages** для HQ sales funnel;
- labels для WorkItem/Party без kindergarten-специфики.

Tenant **`flexity-sales`** создаётся оператором через Platform Console (или API) с `industry_template_code=flexity_sales_basic` — **не hardcoded** в коде.

Public inbound, merge, cherry-pick, deploy и production **не затрагивались**.

---

## 3. Files Changed

| File | Change |
|------|--------|
| `backend/app/modules/industry_templates/seed.py` | Added `FLEXITY_SALES_BASIC`; appended to `INDUSTRY_TEMPLATES` |
| `backend/tests/test_industry_templates.py` | Added 3 tests for flexity sales template |
| `docs/FLEXITY_SALES_TENANT_B1_RUNBOOK.md` | Short ops runbook for tenant bootstrap |
| `docs/FLEXITY_SALES_TENANT_B1_IMPLEMENTATION_REPORT.md` | This report |

---

## 4. What Was Added

### Template `flexity_sales_basic`

| Property | Value |
|----------|-------|
| `code` | `flexity_sales_basic` |
| `name` | Flexity Sales (внутренний) |
| `default_modules` | `parties`, `crm`, `documents`, `finance` |
| `default_custom_fields` | `[]` (minimal) |
| `default_document_templates` | `[]` (B5 later) |
| `default_catalog_items` | `[]` |
| `default_ai_agents` | `[]` |

### Pipeline `flexity_sales`

| # | Stage code | Label (RU) | Terminal |
|---|------------|------------|----------|
| 1 | `new_lead` | Новый лид | |
| 2 | `contacted` | Первичный контакт | |
| 3 | `diagnosis` | Диагностика | |
| 4 | `proposal_prepared` | КП подготовлено | |
| 5 | `proposal_sent` | КП отправлено | |
| 6 | `negotiation` | Переговоры | |
| 7 | `accepted` | Согласовано | |
| 8 | `rejected` | Отказ | ✅ |
| 9 | `converted_to_tenant` | Клиент создан | ✅ |

`is_default: true` на pipeline.

### Labels

- WorkItem → «Лид»
- Party → «Контакт»
- party_roles: `lead`, `client`, `contact`

### Tests

| Test | Purpose |
|------|---------|
| `test_list_industry_templates_includes_flexity_sales` | Template visible via API |
| `test_flexity_sales_basic_seed_structure` | 9 stages, no duplicates, terminals |
| `test_pipelines_after_flexity_sales_template_apply` | Tenant create + pipeline apply |

### Docs

- Runbook: `docs/FLEXITY_SALES_TENANT_B1_RUNBOOK.md`

---

## 5. What Was Not Changed

| Area | Status |
|------|--------|
| Public inbound (`/api/v1/public/leads`) | ❌ not touched |
| Branch `codex/public-inbound-leads` | ❌ no cherry-pick / merge |
| Migrations | ❌ none added |
| Deploy / production | ❌ not touched |
| `kindergarten_basic` template content | ❌ unchanged |
| New CRM module | ❌ none |
| Lead / Diagnosis / Project tables | ❌ none |
| Platform Console UI | ❌ unchanged |
| Landing / demo forms | ❌ unchanged |

---

## 6. Tests / Checks

| Command | Result |
|---------|--------|
| `python -m compileall app/modules/industry_templates/seed.py` | ✅ OK |
| `python -m pytest tests/test_industry_templates.py -v` | ✅ **7 passed** |

All existing kindergarten template tests still pass (no regression).

---

## 7. Risks / Notes

| Risk | Note |
|------|------|
| Tenant not auto-created | B1 only adds template; operator must create `flexity-sales` tenant |
| `party_role=lead` vs Console UI | `CreateClientModal` may still use `client` — align in B3 |
| Document templates empty | B5 will add CP/diagnosis templates |
| Future inbound env | After tenant bootstrap, capture UUIDs in runbook for B2b |
| Hardcoded slug | Slug `flexity-sales` is ops convention, not enforced in code |

---

## 8. Next Recommended Step

**B2a — Manual smoke / verification:**

1. Start backend locally (`SEED_ON_STARTUP` loads templates).
2. Platform Console → create tenant:
   - Name: `Flexity Sales`
   - Slug: `flexity-sales`
   - Template: `flexity_sales_basic`
   - Plan: `enterprise` (recommended)
3. Open `/console/workspace/flexity-sales/crm`.
4. Create Party + WorkItem manually; move through stages.
5. Document tenant/pipeline UUIDs in runbook for future B2b inbound.

**Not next:** public inbound, cherry-pick, merge, deploy.

---

## 9. HQ Summary

### 1. What is done

- `flexity_sales_basic` template in seed
- Pipeline `flexity_sales` with all 9 stages
- Tests green (7/7)
- Runbook + this report

### 2. What is ready

- Template can be applied to new tenant via Console or API
- CRM kanban will show sales pipeline after tenant bootstrap
- Manual lead flow possible (WorkItem + Party)

### 3. What remains

- Create actual `flexity-sales` tenant in dev/staging (ops step)
- B2a manual smoke in platform-console
- B3 label/party_role alignment
- B5 document templates
- B2b public inbound (after smoke + HQ approval)

### 4. Recommended next step

**B2a manual smoke** — bootstrap tenant `flexity-sales` and verify CRM workflow end-to-end.

---

*Report v1.0 — B1 implementation slice complete.*
