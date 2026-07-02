# FLEXITY SALES TENANT BOOTSTRAP PLAN

**Дата:** 2026-07-02  
**Проект:** Flexity  
**Категория:** `documentation_only` — B1 setup / implementation plan  
**Статус:** ожидает HQ approval перед любым кодом  
**Backlog slice:** **B1 — Sales Tenant Bootstrap**

**Основание:**

- [FLEXITY_INBOUND_LEADS_TENANT_BLUEPRINT.md](./FLEXITY_INBOUND_LEADS_TENANT_BLUEPRINT.md)
- [FLEXITY_INBOUND_LEADS_TENANT_BACKLOG.md](./FLEXITY_INBOUND_LEADS_TENANT_BACKLOG.md)
- [FLEXITY_PUBLIC_INBOUND_BRANCH_REVIEW.md](./FLEXITY_PUBLIC_INBOUND_BRANCH_REVIEW.md) — B0 closed

**Ограничения этого документа:** plan only — код, migrations, deploy, cherry-pick, merge, production не выполнялись.

---

## 1. Purpose

**B1** нужен для создания и настройки **внутреннего Flexity sales tenant** — рабочего CRM-контура, через который команда Flexity ведёт:

- входящие заявки (сначала **вручную**);
- лиды / opportunities;
- диагностику, КП, договор (последующие slices B4–B5);
- подготовку к конвертации в client tenant (B6–B7).

**Public inbound на B1 не подключается.** Ветка `codex/public-inbound-leads` не мержится и не cherry-pick'ится до завершения B1 и manual smoke (HQ decision B0).

Sales tenant должен быть **готов и проверен** до public API (B2b).

---

## 2. Context

| Факт | Статус |
|------|--------|
| Approved architecture | **Option C — Hybrid** |
| B0 branch review | ✅ завершён — no merge as-is |
| Public inbound | ⏸ отложен до B1 + B2a manual smoke |
| Manual before automation | ✅ backlog rule |
| Lead = WorkItem, Client = Party | ✅ blueprint |
| Provider CRM | ❌ не создаём |
| Migrations on B1 | ❌ не ожидаются (config + tenant records only) |

**Цель B1:** один внутренний tenant `flexity-sales` с pipeline `flexity_sales` и stages для HQ sales funnel — на базе **существующих** tenant / industry_templates / workflows / platform-console.

---

## 3. Existing Tenant / Seed Mechanisms

### 3.1 Сводка механизмов

| Mechanism | What it does | Usable for B1? |
|-----------|--------------|----------------|
| `POST /api/v1/tenants` | Creates tenant + optional plan + apply template | ✅ Primary |
| `IndustryTemplateService.apply_to_tenant` | Pipelines, labels, documents, catalog, AI agents | ✅ Via template |
| `IndustryTemplateService.seed_templates` | Upserts templates from `seed.py` on app startup | ✅ Add `flexity_sales_basic` |
| `ModuleRegistryService.provision_tenant_modules` | Default modules on tenant create | ✅ Automatic |
| `SubscriptionService.assign_plan` | Plan on tenant create | ✅ e.g. `enterprise` |
| Platform Console `TenantCreatePage` | UI for tenant + template + plan | ✅ Manual bootstrap |
| `TenantDetailPage` → Apply Template | Re-apply template to existing tenant | ✅ If tenant exists without pipeline |
| `scripts/mvp_smoke.py` | API smoke: tenant + party + work-item | ✅ Reference for B1 smoke |
| `scripts/seed_booking_demo.py` + `booking/seed.py` | Idempotent tenant-scoped demo seed | ✅ Pattern for optional CLI |
| `tests/test_mvp_scenario.py` | E2E tenant journey | ✅ Regression reference |

### 3.2 File reference table

| Path | What it does | Use for B1? | Risk |
|------|--------------|-------------|------|
| `backend/app/modules/tenants/service.py` | `TenantService.create` — tenant, membership, modules, plan, template apply | ✅ Core | Low — only provider_owner creates |
| `backend/app/modules/tenants/schemas.py` | `TenantCreate`: name, slug, plan_code, industry_template_code | ✅ | Low |
| `backend/app/modules/tenants/routes.py` | CRUD tenants, users, memberships | ✅ | Low |
| `backend/app/modules/tenants/models.py` | `Tenant`, `TenantSettings`, `UserTenantMembership` | ✅ Read | None |
| `backend/app/modules/industry_templates/seed.py` | `KINDERGARTEN_BASIC`, `INDUSTRY_TEMPLATES` list | ✅ **Extend** with sales template | Medium — only edit this file per kindergarten guardrail extension for new template |
| `backend/app/modules/industry_templates/service.py` | `seed_templates`, `apply_to_tenant`, `_apply_pipelines` (skips existing pipeline code) | ✅ | Low — idempotent pipeline create |
| `backend/app/modules/industry_templates/repository.py` | `get_pipeline(tenant_id, code)`, create pipeline/stages | ✅ | Low |
| `backend/app/modules/industry_templates/routes.py` | `POST /tenants/{id}/apply-template/{template_id}` | ✅ Re-apply | Low |
| `backend/app/modules/workflows/models.py` | `Pipeline`, `PipelineStage`, `WorkItem`, `Activity` | ✅ Read | None |
| `backend/app/modules/workflows/routes.py` | Pipelines + work-items API | ✅ Smoke | Low |
| `backend/app/modules/parties/routes.py` | Party CRUD | ✅ Manual lead | Low |
| `backend/app/modules/module_registry/seed.py` | Module definitions (`crm`, `parties`, …) | ✅ Read | None |
| `backend/app/modules/subscriptions/service.py` | `assign_plan`, `seed_catalog` | ✅ | Low |
| `backend/app/main.py` | Startup: `seed_templates()` if `SEED_ON_STARTUP` | ✅ | Low |
| `backend/scripts/mvp_smoke.py` | Manual API smoke script | ✅ Template for sales smoke | None |
| `backend/scripts/seed_booking_demo.py` | CLI idempotent booking demo | ✅ Pattern only | Don't mix Booking into B1 |
| `platform-console/src/pages/TenantCreatePage.tsx` | Create tenant form | ✅ Manual path | Low |
| `platform-console/src/pages/TenantDetailPage.tsx` | Users, modules, apply template | ✅ Post-create setup | Low |
| `platform-console/src/pages/workspace/CrmPage.tsx` | Kanban — uses `pickDefaultPipeline` | ✅ Verify | Low |
| `platform-console/src/components/workspace/CreateWorkItemModal.tsx` | Manual WorkItem create | ✅ B2a manual | Low |
| `platform-console/src/components/workspace/CreateClientModal.tsx` | Manual Party create | ✅ B2a manual | Low |
| `platform-console/src/auth/TenantWorkspaceGuard.tsx` | Resolve tenant by slug; provider_owner fallback | ✅ Open `flexity-sales` | Low |
| `platform-console/src/workspace/formatters.ts` | `pickDefaultPipeline` → `is_default` pipeline | ✅ Must set `is_default: true` on `flexity_sales` | Medium if wrong default |
| `backend/tests/test_industry_templates.py` | Template seed/apply tests | ✅ Extend in impl | Low |
| `backend/tests/test_mvp_scenario.py` | Full kg journey | ⚠️ Do not break | Regression |

### 3.3 Что уже есть: `kindergarten_basic`

- Единственный template в `INDUSTRY_TEMPLATES` (`seed.py` line 232).
- Pipeline `enrollment` with stages including `new_lead` … `enrolled` / `lost`.
- Labels: «Заявка», «Родитель», «Ребёнок» — **не подходят** для Flexity sales tenant.
- **Нельзя** использовать `kindergarten_basic` для sales tenant без путаницы в UI и labels.

### 3.4 Как создаются WorkItem / Party (без нового кода)

| Entity | API | Tenant context |
|--------|-----|----------------|
| Party | `POST /api/v1/parties` | Header `X-Tenant-ID` |
| WorkItem | `POST /api/v1/work-items` | `pipeline_id`, `stage_id`, `primary_party_id` |
| Pipeline | Created by `apply_to_tenant` from template | Per-tenant rows in `pipelines` / `pipeline_stages` |

### 3.5 Как platform-console открывает workspace

1. User logs in → `auth/me` returns tenant memberships.
2. URL `/console/workspace/{tenantSlug}/...` → `TenantWorkspaceGuard`.
3. Membership match **or** `provider_owner` + `listTenants()` by slug.
4. `WorkspaceLayout` + `X-Tenant-ID` on API calls.
5. `CrmPage` loads pipelines → `pickDefaultPipeline` → lists work-items.

**Sales tenant доступен без provider CRM UI** — достаточно slug `flexity-sales` и membership (или provider_owner).

---

## 4. Target Sales Tenant

| Field | Value |
| ----- | ----- |
| **Name** | Flexity Sales |
| **Slug** | `flexity-sales` |
| **Purpose** | Internal Flexity sales workspace (dogfooding HQ funnel) |
| **Pipeline** | `flexity_sales` (`is_default: true`) |
| **Industry template code** | `flexity_sales_basic` (proposed — new seed entry) |
| **Plan (recommended)** | `enterprise` — all modules for documents/finance later |
| **Owner/Admin** | HQ decision — provider sales manager as `tenant_owner` |
| **Visibility** | Internal only — not a client-facing tenant |
| **Public inbound** | **Disabled** — no `PUBLIC_LEADS_*` until B2b after B1 smoke |
| **Environment** | Dev/staging first; production tenant creation = separate approval |

### Distinction from client tenants

| | Sales tenant | Client tenant (B6+) |
|---|--------------|-------------------|
| Slug | `flexity-sales` | e.g. `client-kg-astana` |
| Template | `flexity_sales_basic` | `kindergarten_basic`, etc. |
| Purpose | Sell Flexity | Operate client business |
| Created | B1 | B6 conversion |

---

## 5. Sales Pipeline

### Pipeline definition

| Property | Value |
|----------|-------|
| `code` | `flexity_sales` |
| `name` | Воронка продаж Flexity (RU label in template) |
| `entity_type` | `work_item` |
| `is_default` | `true` |

### Stages

| Stage | Meaning | Entry condition | Exit condition |
| ----- | ------- | --------------- | -------------- |
| `new_lead` | New incoming/manual lead | WorkItem created (manual or future inbound) | Manager moves to `contacted` or `rejected` |
| `contacted` | First contact made | Communication started | `diagnosis` or `rejected` |
| `diagnosis` | Discovery / diagnosis | Needs analysis | `proposal_prepared` or `rejected` |
| `proposal_prepared` | CP draft prepared | Diagnosis sufficient | `proposal_sent` |
| `proposal_sent` | CP sent to client | Approved CP sent | `negotiation`, `accepted`, or `rejected` |
| `negotiation` | Terms discussion | Client responded | `accepted` or `rejected` |
| `accepted` | Client accepted offer | Agreement reached | `converted_to_tenant` (B6) |
| `rejected` | Lead lost | No deal | Terminal — `WorkItem.status=lost` |
| `converted_to_tenant` | Real tenant created | B6 conversion done | Terminal — `WorkItem.status=won` |

**Terminal flags:** `rejected`, `converted_to_tenant` → `is_terminal: true` in seed (mirror kindergarten pattern).

**MVP cut (optional):** можно начать с 5 stages (`new_lead` → `contacted` → `proposal_sent` → `accepted` | `rejected`) и расширить позже — HQ confirm in §10.

### Sort order (proposed)

| Code | sort_order |
|------|------------|
| new_lead | 10 |
| contacted | 20 |
| diagnosis | 30 |
| proposal_prepared | 40 |
| proposal_sent | 50 |
| negotiation | 60 |
| accepted | 70 |
| rejected | 80 |
| converted_to_tenant | 90 |

---

## 6. Entity Usage

### 6.1 WorkItem as Lead / Opportunity

| Aspect | B1 specification |
|--------|----------------|
| **Required fields** | `pipeline_id`, `stage_id`, `work_item_type`, `title` |
| **Recommended types** | `inquiry` (manual), `demo_request` (future public inbound) |
| **Status** | `open` on create; `won`/`lost` on terminal stages |
| **Source metadata** | `source` string (`manual`, `public_demo_form` later); `custom_fields_json` for UTM |
| **Party link** | `primary_party_id` + participant role `client` |
| **Notes/activity** | `Activity`, `Note` — existing API; UI: `WorkItemActivityComposer` |
| **B1 scope** | Manual create only; no public API |

### 6.2 Party as Client Candidate

| Aspect | B1 specification |
|--------|----------------|
| **Types** | `person` or `organization` (B2B) |
| **Role** | `party_role=lead` in `metadata_json` (manual: `client` in `CreateClientModal` today — **align taxonomy in B3**) |
| **Contacts** | `contact_methods`: email, phone |
| **WorkItem link** | `primary_party_id` on WorkItem |
| **Future** | `party_role=client` after acceptance (B6) |

**Note:** `CreateClientModal` currently sets `party_role=client`. For sales funnel, B1 smoke may use `lead` via API until UI aligned in B3.

### 6.3 DocumentInstance for Proposal / Contract

| Aspect | B1 |
|--------|-----|
| Attached to WorkItem/Party | Prepared in template seed, **not required in B1** |
| Templates (future B5) | `commercial_proposal`, `diagnosis_checklist`, `implementation_contract` stubs in `flexity_sales_basic` |
| B1 action | Optional: seed empty/minimal templates only |

### 6.4 Tenant / Subscription / Project

| Entity | B1 |
|--------|-----|
| Real client `Tenant` | ❌ Not created — B6 |
| `Subscription` on sales tenant | Optional `enterprise` for module access; not client billing |
| Project `implementation` WorkItem | ❌ B7 — in client tenant after conversion |

---

## 7. Manual Lead Flow After B1

Пошаговый **manual path** (без public API):

1. **Provider owner** opens Platform Console → `/console/tenants` or directly `/console/workspace/flexity-sales/dashboard`.
2. **CRM** → `/console/workspace/flexity-sales/crm` — kanban shows `flexity_sales` stages.
3. **Create Party** (Clients → «Создать клиента») — contact name, phone/email.
4. **Create WorkItem** (CRM → «Создать заявку») — select party, title, optional source text.
5. WorkItem lands in stage **`new_lead`** (first stage of default pipeline).
6. Manager **moves stages** via `WorkItemStageSelect` (on client detail → deals tab or kanban).
7. **Activities** — add call/note via `WorkItemActivityComposer`.
8. **Diagnosis / proposal docs** — later slices B4–B5; not blocking B1 done.
9. **No public endpoint** called.

### API equivalent (smoke / script)

```http
POST /api/v1/tenants          # once — create sales tenant (provider_owner)
POST /api/v1/parties          # X-Tenant-ID: <sales-tenant-uuid>
POST /api/v1/work-items       # pipeline flexity_sales, stage new_lead
POST /api/v1/work-items/{id}/move-stage
```

Reference: `backend/scripts/mvp_smoke.py` lines 44–80.

---

## 8. Platform Console Verification

### B1 verification checklist (post-implementation)

| # | Check | Expected |
|---|-------|----------|
| 1 | Login as provider_owner or sales `tenant_owner` | Success |
| 2 | Navigate `/console/workspace/flexity-sales/dashboard` | Dashboard loads |
| 3 | CRM `/crm` | Pipeline `flexity_sales` columns visible |
| 4 | Stages | All 9 stages (or MVP subset) shown |
| 5 | Create client/party | Party in list |
| 6 | Create work item | Card appears in `new_lead` |
| 7 | Move stage | Card moves column |
| 8 | Client detail → deals tab | Linked WorkItem visible |
| 9 | Add activity | Activity saved |
| 10 | No provider-only sales UI | Only standard workspace |

### Known UI gaps (document, not block B1)

- No dedicated WorkItem detail route.
- `CreateWorkItemModal` requires existing party first.
- Labels depend on `flexity_sales_basic` `labels_config` — not kindergarten labels.

---

## 9. Implementation Options

### Option 1 — Industry template seed + manual console create

**What:** Add `FLEXITY_SALES_BASIC` to `industry_templates/seed.py`; operator creates tenant via Console with `industry_template_code=flexity_sales_basic`, `plan_code=enterprise`, slug `flexity-sales`.

| Pros | Cons |
|------|------|
| Matches existing architecture | Requires one small code change (seed.py) |
| No migrations | Manual steps for users/memberships |
| Idempotent template seed on startup | Tenant row not auto-created |
| Same pattern as kindergarten | Slug not enforced by code |

**Risks:** Low — single file, config-only.

---

### Option 2 — Industry template seed + idempotent CLI script

**What:** Option 1 plus `backend/scripts/seed_sales_tenant.py` (pattern from `seed_booking_demo.py`): if no tenant with slug `flexity-sales`, create via internal service calls; if exists, ensure template applied / pipeline present.

| Pros | Cons |
|------|------|
| Repeatable dev/staging bootstrap | New script file + tests |
| Documents UUIDs for future `PUBLIC_LEADS_*` | Must not hardcode production secrets |
| Idempotent | Slightly more code than Option 1 |

**Risks:** Low–medium — scope control script to sales tenant only.

---

### Option 3 — Manual/admin setup only (no seed code change)

**What:** Create empty tenant via Console; manually create pipeline/stages via API or DB — **no template**.

| Pros | Cons |
|------|------|
| Zero code changes now | Error-prone, not repeatable |
| Fastest doc-only | No labels, no document templates |
| | Deviates from industry template pattern |
| | Hard to reproduce across environments |

**Risks:** Medium — drift, wrong stages, breaks blueprint.

---

### Recommendation

**Primary: Option 1** — add `flexity_sales_basic` to `industry_templates/seed.py` (configuration-only, same pattern as `kindergarten_basic`; **no migrations**).

**Secondary (same B1 slice or B1.1): Option 2** — optional idempotent `seed_sales_tenant.py` + ops runbook documenting tenant UUID, pipeline UUID, stage UUID for future inbound env.

**Not recommended: Option 3** except as emergency local hack.

**No new provider CRM. No new Lead table. No public inbound in B1.**

---

## 10. Required Decisions Before Code

| # | Decision | Default recommendation |
|---|----------|------------------------|
| 1 | Sales tenant name/slug | **Flexity Sales** / `flexity-sales` |
| 2 | Pipeline stages | Full 9 stages (§5) or MVP 5-stage cut |
| 3 | Owner/admin users | Provider owner + named `tenant_owner` email(s) |
| 4 | Seed script allowed? | **Yes** — `flexity_sales_basic` in `seed.py` only |
| 5 | Migrations expected? | **No** |
| 6 | B1 includes smoke tests? | **Yes** — extend `test_industry_templates.py` + manual/console checklist |
| 7 | Public inbound remains disabled? | **Yes** until B2b |
| 8 | Optional CLI `seed_sales_tenant.py`? | HQ choose — recommended for dev repeatability |
| 9 | Plan code for sales tenant | `enterprise` |
| 10 | Document templates in B1 seed | Minimal stubs only (`diagnosis_checklist`, `commercial_proposal`) — optional |

---

## 11. Risks

| Risk | Mitigation |
|------|------------|
| Hardcoded internal tenant UUID in code | Use env + runbook; script resolves by slug |
| Conflict with `kindergarten_basic` seed | Only **add** template; don't modify kg stages |
| Wrong workflow scope | Dedicated `flexity_sales` pipeline, not `enrollment` |
| Console shows wrong pipeline | `is_default: true` on `flexity_sales` |
| Incomplete WorkItem/Party links | Smoke: create party → work item with `primary_party_id` |
| Impact on demo/client tenants | B1 only adds template + creates separate tenant |
| Future inbound routing | Document slug + UUIDs in runbook after bootstrap |
| `party_role` mismatch (`client` vs `lead`) | Document in B3; B1 smoke via API acceptable |
| Accidental production tenant create | Separate approval for prod; dev/staging only in B1 impl |
| Scope creep into B2/B0 | B1 plan forbids public_leads cherry-pick |

---

## 12. Acceptance Criteria for Future B1 Implementation

B1 считается **done**, когда:

- [ ] Industry template `flexity_sales_basic` exists in seed (or equivalent documented manual equivalent — seed preferred).
- [ ] Tenant **Flexity Sales** exists with slug **`flexity-sales`** (dev/staging).
- [ ] Pipeline **`flexity_sales`** with all approved stages exists on that tenant.
- [ ] Pipeline is **default** (`is_default: true`).
- [ ] Modules **`parties`** + **`crm`** enabled (via plan/template).
- [ ] Manual **WorkItem** lead can be created in sales tenant.
- [ ] Manual **Party** can be created and linked.
- [ ] Workspace opens: `/console/workspace/flexity-sales/crm`.
- [ ] Stage move works on at least one WorkItem.
- [ ] **No** production deploy in B1 slice.
- [ ] **No** public inbound enabled (`PUBLIC_LEADS_ENABLED` unset or false).
- [ ] **No** cherry-pick / merge of `codex/public-inbound-leads`.
- [ ] Smoke documented: pytest + console checklist (§8).
- [ ] Ops runbook with tenant/pipeline/stage UUIDs for future B2b (optional but recommended).

---

## 13. Recommended Next Step

### For HQ

1. **Approve this plan** (or request edits to stages/slug/seed approach).
2. **Confirm** Option 1 (+ optional Option 2 CLI).
3. **Confirm** owner emails for sales tenant memberships.

### If proceed

**Next Cursor task:** small **B1 implementation slice only**:

| Allowed files (anticipated) | Change |
|----------------------------|--------|
| `backend/app/modules/industry_templates/seed.py` | Add `FLEXITY_SALES_BASIC`, append to `INDUSTRY_TEMPLATES` |
| `backend/tests/test_industry_templates.py` | Assert new template codes/pipeline |
| `docs/ai/plans/YYYY-MM-DD-b1-sales-tenant-bootstrap-implementation-plan.md` | Formal plan (or use this doc as approved plan) |
| `docs/ai/plans/YYYY-MM-DD-flexity-sales-tenant-runbook.md` | Ops steps + UUID capture |
| `backend/scripts/seed_sales_tenant.py` | Optional — if HQ approves Option 2 |

| Forbidden in B1 implementation |
|-------------------------------|
| `public_leads` / cherry-pick |
| Migrations |
| Provider CRM module |
| Production deploy |
| `platform-console` changes (unless smoke reveals blocker — separate approval) |
| kindergarten_basic behavior changes |

### If postpone

Continue **manual** tenant with wrong template — not recommended; blocks clean B2a/B2b.

---

## 14. HQ Summary

### 1. Recommended B1 approach

**Option 1 + optional Option 2:** добавить industry template **`flexity_sales_basic`** в `seed.py` (config-only, без миграций), создать tenant **`flexity-sales`** через Platform Console (или idempotent CLI), проверить manual CRM flow в workspace.

### 2. Existing code/seeds to reuse

- `TenantService.create` + `industry_template_code` auto-apply
- `IndustryTemplateService.apply_to_tenant` / `_apply_pipelines` (idempotent)
- `kindergarten_basic` seed structure as copy pattern
- `mvp_smoke.py` / `test_mvp_scenario.py` as smoke patterns
- `seed_booking_demo.py` as CLI idempotency pattern
- Platform Console tenant + workspace UI (W2/W3)

### 3. Required HQ decisions

- Confirm slug `flexity-sales` and template name `flexity_sales_basic`
- Confirm 9 vs 5 pipeline stages
- Confirm sales tenant owner(s)
- Approve seed.py change (single-file scope)
- Confirm public inbound stays off
- Optional: approve CLI bootstrap script

### 4. Risks

- Wrong template/labels if reusing kindergarten
- Missing `is_default` on pipeline → empty CRM
- Hardcoded UUIDs for future inbound
- Scope creep into B0/B2 in same PR

### 5. Next action

**HQ approves this plan** → Cursor creates **`docs/ai/plans/YYYY-MM-DD-b1-sales-tenant-bootstrap-implementation-plan.md`** (if needed as formal artifact) → **implement B1 seed + bootstrap smoke only** — no public inbound.

---

## Appendix A. Proposed `flexity_sales_basic` seed outline (for future implementation)

Not code — structure reference for implementer:

```python
FLEXITY_SALES_BASIC = {
    "code": "flexity_sales_basic",
    "name": "Flexity Sales (внутренний)",
    "default_modules": ["parties", "crm", "documents", "finance"],
    "default_pipelines": [{
        "code": "flexity_sales",
        "name": "Воронка продаж Flexity",
        "is_default": True,
        "stages": [ /* §5 stage list */ ],
    }],
    "labels_config": {
        "entities": {"work_item": "Лид", "party": "Контакт", "pipeline": "Воронка продаж"},
        "party_roles": {"lead": "Лид", "client": "Клиент"},
    },
    "default_document_templates": [ /* optional stubs for B5 */ ],
    # minimal catalog / no kg-specific fields
}
```

---

*Plan v1.0 — documentation only. Implementation requires explicit HQ approval.*
