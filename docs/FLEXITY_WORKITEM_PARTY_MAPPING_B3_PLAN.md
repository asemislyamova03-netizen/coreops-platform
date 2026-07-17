# FLEXITY WORKITEM PARTY MAPPING B3 PLAN

**Дата:** 2026-07-02
**Проект:** Flexity
**Категория:** `documentation_only` — B3 planning / review
**Статус:** ожидает HQ approval перед implementation
**Предшествующие slices:** B1 ✅, B2a ✅ PASSED

**Основание:**

- [FLEXITY_SALES_TENANT_BOOTSTRAP_PLAN.md](./FLEXITY_SALES_TENANT_BOOTSTRAP_PLAN.md)
- [FLEXITY_SALES_TENANT_B2A_MANUAL_SMOKE_REPORT.md](./FLEXITY_SALES_TENANT_B2A_MANUAL_SMOKE_REPORT.md)

**Ограничения:** plan only — код, migrations, deploy, public inbound, cherry-pick, merge не выполнялись.

---

## 1. Purpose

**B3** нужен после successful B2a manual smoke, чтобы **sales tenant** (`flexity-sales`) был:

- **семантически корректен** — контакт/лид не называется «клиентом» до конвертации;
- **удобен в Platform Console** — manual flow Party → WorkItem → CRM stages;
- **готов к public inbound** (B2b) без переделки UX.

B3 выравнивает **mapping WorkItem ↔ Party** и **sales labels/copy** в Console, используя существующие сущности — без новой CRM и без Lead table.

---

## 2. Context

| Факт | Статус |
|------|--------|
| B1 template `flexity_sales_basic` | ✅ done |
| B2a API smoke | ✅ PASSED |
| Public inbound | ❌ disabled (404) |
| Cherry-pick / merge | ❌ forbidden |
| Entity model | WorkItem = lead, Party = contact candidate |
| B2b public inbound | ⏸ only after B3 + HQ approval |

**Главная проблема из B2a:** Console создаёт Party с `party_role=client`, хотя sales funnel ожидает `lead` / «Контакт» до конвертации.

---

## 3. Current Findings

### 3.1 Party creation in Platform Console

| Aspect | Current behavior | File |
|--------|------------------|------|
| Entry point | Clients page → «Создать клиента» | `ClientsPage.tsx` |
| Modal | `CreateClientModal` | `CreateClientModal.tsx` |
| API call | `POST /api/v1/parties` via `createParty()` | `api/parties.ts` |
| Default `party_role` | **Hardcoded `"client"`** | `CreateClientModal.tsx:9,36` |
| Default `party_type` | `"person"` only | `CreateClientModal.tsx:34` |
| UI copy | «Создать клиента», «Имя клиента» | hardcoded RU strings |
| Hint | Shows `party_role: client` in `<code>` | line 98–100 |

### 3.2 `party_role` — backend support

| Layer | Finding |
|-------|---------|
| **Storage** | `metadata_json.party_role` — **free string**, no DB enum |
| **Schema** | `PartyCreate.party_role: str \| None` | `parties/schemas.py:72–75` |
| **Filter** | `GET /parties?party_role=` filters by metadata | `parties/routes.py`, `repository.py` |
| **Validation** | No whitelist — any string up to 64 chars |
| **Migration** | **Not required** for `lead`, `contact`, `prospect` |

**Conclusion:** backend already supports `lead` / `contact` / `prospect` as metadata tags. No new table or enum.

### 3.3 Known role values in codebase

| Role | Where used | Notes |
|------|------------|-------|
| `client` | Console default, WorkItem participant | Kindergarten + sales today |
| `guardian` | kg template, ClientsPage visibility | Legacy seeded rows |
| `enrollee` | kg custom fields | Child entity |
| `staff` | kg labels | Staff |
| `lead` | `flexity_sales_basic` labels (B1) | B2a API smoke ✅ |
| `contact` | `flexity_sales_basic` labels (B1) | Template only, not Console |
| `prospect` | Not in codebase | Could be alias; not required |
| `supplier`, `partner` | `ruUi.ts` fallbacks only | Display map |

**WorkItem participant roles** (separate from `party_role`):

```python
# backend/app/core/enums.py
class WorkItemParticipantRole:
    CLIENT = "client"
    ASSIGNEE = "assignee"
    OBSERVER = "observer"
    OTHER = "other"
```

No `lead` in participant enum — participant role ≠ party metadata role.

### 3.4 WorkItem ↔ Party linking

| Mechanism | Status |
|-----------|--------|
| `primary_party_id` on WorkItem | ✅ supported API + Console |
| `participants: [{ party_id, role }]` | ✅ CreateWorkItemModal sends `role: "client"` |
| Party picker | Required in `CreateWorkItemModal` — no orphan WorkItem |
| Client detail → deals tab | ✅ `listWorkItems({ primary_party_id })` |
| CRM kanban card | Shows title, status, type — **no Party name** |

**Files:**

- `CreateWorkItemModal.tsx:62–74` — link + participant
- `ClientDetailPage.tsx:49–52` — related WorkItems
- `CrmPipelineBoard.tsx` — kanban display

### 3.5 Labels from template

**Backend:** `GET /api/v1/tenants/{tenant_id}/labels` → `TenantSettings.labels_config` (copied from template on apply).

**`flexity_sales_basic` (B1):**

| Key | Value |
|-----|-------|
| `entities.work_item` | Лид |
| `entities.party` | Контакт |
| `entities.pipeline` | Воронка продаж |
| `party_roles.lead` | Лид |
| `party_roles.client` | Клиент |
| `party_roles.contact` | Контакт |

**Console label loading:**

| Component | Behavior |
|-----------|----------|
| `WorkspaceLabelsProvider` | Fetches labels per tenant | `WorkspaceLabelsContext.tsx` |
| `CrmPage` | Uses `entityLabel("work_item")` → **«Лид»** on sales tenant ✅ |
| `clientsSectionTitle` | Hardcoded `guardian` + `party` → **«Родитель / Контакт»** mismatch ❌ |
| `CreateClientModal` | Ignores labels — always «клиент» ❌ |
| `CreateWorkItemModal` | Hardcoded «Клиент» in select label ❌ |
| `partyRoleLabel()` | Uses template `party_roles` when key matches ✅ |
| `formatPartyRole()` | `ruUi.ts` — no `lead`/`contact` keys → shows raw key |

### 3.6 CRM kanban behavior

| Feature | Status |
|---------|--------|
| Default pipeline | `pickDefaultPipeline()` → `is_default` ✅ |
| Stage columns | From pipeline stages ✅ |
| Create button | «Создать заявку» — uses work_item label in loading text only |
| Stage move | `WorkItemStageSelect` on card ✅ |
| Party on card | ❌ not shown |
| WorkItem detail route | ❌ none (known gap) |

### 3.7 Clients list visibility — **critical B3 blocker**

`ClientsPage.tsx` filters parties:

```typescript
// Only visible: null, "client", "guardian"
function isVisibleClientParty(party: Party): boolean {
  const role = getPartyRole(party);
  return role === null || role === DEFAULT_CLIENT_PARTY_ROLE || role === "guardian";
}
```

**If B3 sets `party_role=lead` without fixing this filter, new contacts will NOT appear in the Clients list.**

### 3.8 Can user create lead without calling it «client»?

| Path | Today |
|------|-------|
| Console UI | ❌ No — always «клиент», role `client` |
| API direct | ✅ Yes — B2a used `party_role=lead` |
| Labels only (Option C) | ⚠️ Partial — CRM shows «Лид» for WorkItem, Party still «клиент» |

### 3.9 Industry template awareness in Console

Console **does not read** `industry_template_code` or `template_code` today.

Template influence is **indirect** — only via `/tenants/{id}/labels`.

No `flexity_sales`-specific branches exist (good — prefer label-driven behavior).

---

## 4. Sales Tenant Desired Behavior

Manual flow after B3:

1. User opens `/console/workspace/flexity-sales/crm`.
2. Sidebar hint: **«Лид / Воронка продаж»** (from labels).
3. User goes to **Contacts** section (nav may still say «Клиенты», hint shows «Лид / Контакт»).
4. User creates **contact/company** with default `party_role=lead` (or selectable lead/contact).
5. User creates **WorkItem** as sales lead — label «Лид», links to Party.
6. WorkItem appears in kanban at `new_lead`.
7. User moves through `flexity_sales` stages.
8. Party role becomes **`client`** only after acceptance/conversion (B6+) — not in B3 scope.

**Data semantics:**

| Stage | Party role | WorkItem |
|-------|------------|----------|
| Early funnel | `lead` or `contact` | open / in_progress |
| Accepted | still `lead` until B6 | in_progress |
| Converted (B6) | → `client` | won + `converted_to_tenant` |

---

## 5. Party Role Options

| Option | Description | Pros | Cons | Code? | Migration? | Recommendation |
| ------ | ----------- | ---- | ---- | ----- | ---------- | -------------- |
| **A — keep `client`** | No role change; only UI copy | Zero data change; kg safe | Lead = client semantically wrong; blocks clean B6 conversion | Console copy only | No | ❌ Not recommended |
| **B — use `lead`** | Default `party_role=lead` for sales tenant | Matches B1 labels + B2a API; no migration | Must fix ClientsPage filter + modals | Console only | **No** | ✅ **Recommended** |
| **B2 — use `contact`** | Default `party_role=contact` | Softer semantics | Less aligned with funnel «лид»; same filter fix needed | Console only | No | ⚠️ Acceptable alternate |
| **C — labels/copy only** | Keep `client`, change displayed text | Minimal diff | Data still wrong; filter unchanged | Console labels | No | ❌ Insufficient |
| **D — add `prospect`** | New role string | Clear funnel language | Redundant with `lead`; more label work | Console + labels | No | ⚠️ Only if HQ prefers term |
| **E — new DB enum** | Formal party_role column/enum | Strict validation | **Requires migration** — out of B3 scope | Backend + migration | **Yes** | ❌ Stop — HQ approval |

**Recommended:** **Option B — `party_role=lead`**, driven by template `party_roles` in labels (not hardcoded tenant slug).

**Fallback for non-sales tenants:** keep `client` (kindergarten, etc.).

---

## 6. WorkItem Mapping

### 6.1 Required fields (sales lead)

| Field | B3 value | Notes |
|-------|----------|-------|
| `pipeline_id` | `flexity_sales` | Auto from default pipeline |
| `stage_id` | first stage (`new_lead`) | Existing logic |
| `work_item_type` | `inquiry` | OK for manual; `demo_request` later for inbound |
| `title` | user input | required |
| `primary_party_id` | selected Party | required in Console today |
| `source` | optional; `manual` default in UI placeholder | future inbound sets own source |
| `status` | `open` on create | auto |
| `participants[].role` | `client` or `other` | see §6.3 |

### 6.2 Party link

- **Primary link:** `primary_party_id` — keep as-is.
- **Participant:** `{ party_id, role }` — separate from `party_role` metadata.

### 6.3 Participant role vs party_role

| Field | Purpose | B3 recommendation |
|-------|---------|-------------------|
| `Party.metadata_json.party_role` | CRM taxonomy (lead/client) | `lead` for sales |
| `WorkItemParticipant.role` | WorkItem relation enum | Keep `client` **or** switch to `other` for sales |

Using participant `client` on a `lead` Party is slightly inconsistent but **works today** and needs no backend change. Optional B3.1: use `other` when default party role is `lead`.

### 6.4 Source / metadata

| Field | Storage | B3 |
|-------|---------|-----|
| `source` | WorkItem column | Optional text; suggest placeholder «manual» |
| UTM / form data | `custom_fields_json` | B2b inbound later |
| No new fields | — | ✅ |

### 6.5 Cross-tenant safety

- Changes must be **label-driven**, not `if slug == flexity-sales`.
- Kindergarten continues `guardian` / `client` via `kindergarten_basic` labels.
- No change to `kindergarten_basic` seed in B3.

---

## 7. UI / Console Adjustments

### 7.1 Proposed changes (minimal slice)

| File | Change | Risk |
|------|--------|------|
| `workspace/labelHelpers.ts` | Add `pickDefaultPartyRole(labels)` → prefers `lead` if in `party_roles`, else `client` | Low |
| `WorkspaceLabelsContext.tsx` | Fix `clientsSectionTitle` — use default party role label + `party` entity label (not hardcoded `guardian`) | Low |
| `CreateClientModal.tsx` | Accept default role from context; dynamic title «Создать {partyLabel}»; set `party_role` from template | Low |
| `ClientsPage.tsx` | Expand `isVisibleClientParty` — include roles from `labels.party_roles` keys + `client` + `guardian` + null | Medium — test kg |
| `CreateWorkItemModal.tsx` | Replace «Клиент» with `entityLabel("party")`; button «Создать {workItemLabel}» | Low |
| `i18n/ruUi.ts` | Add `lead`, `contact`, `prospect` to `partyRoleRu` | Low |
| `CrmPipelineBoard.tsx` | Optional: show `primary_party_id` or name if enriched | Low priority |
| `WorkspaceSidebar.tsx` | Optional: nav hint only (main label stays `ui.clients`) | Low |

### 7.2 What NOT to build in B3

- Provider CRM UI
- New Lead table / page
- WorkItem detail route (separate backlog)
- Public inbound form
- Role selector UI (unless HQ wants — can be B3.1)

### 7.3 Template-aware copy matrix (target)

| UI element | Kindergarten tenant | Sales tenant |
|------------|---------------------|--------------|
| CRM subtitle | Заявка / Воронка поступления | Лид / Воронка продаж |
| Clients subtitle | Родитель / Контрагент → should be guardian-based | Лид / Контакт |
| Create party modal | «Создать клиента» (guardian flow) | «Создать контакт» |
| Create work item | «Создать заявку» | «Создать лид» (or keep «заявку» if label = Лид) |
| Party default role | `client` (or `guardian` if extended) | `lead` |

---

## 8. Backend/API Adjustments

### 8.1 Required for B3

**None** — if Option B (metadata `party_role=lead`).

Backend already:

- accepts any `party_role` string;
- filters by `party_role`;
- applies template labels on tenant create;
- links WorkItem ↔ Party.

### 8.2 Optional (not in minimal B3)

| Change | When | Migration? |
|--------|------|------------|
| Expose `template_code` on `TenantResponse` | If Console needs explicit template detection | No |
| Enrich `WorkItemResponse` with `primary_party_display_name` | If kanban should show contact name | No |
| Add `lead` to `WorkItemParticipantRole` enum | Only if participant semantics matter | **Maybe** — prefer `other` first |
| Validate `party_role` whitelist | Stricter data | **Avoid** in B3 |

### 8.3 API defaults

No API default changes recommended — role should be set explicitly by Console based on tenant labels.

---

## 9. Compatibility / Regression Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| `kindergarten_basic` Clients list | High if filter too broad | Keep `guardian` + `client`; test kg tenant |
| Existing `client` parties in sales tenant | Low | Still visible after filter fix |
| Finance/documents on Party | Low | No role assumption in finance API |
| `CreateWorkItemModal` party list | Medium if `lead` filtered out | Fix ClientsPage filter first |
| Hardcoded `guardian` in labels context | Medium for sales UX | B3 fixes context |
| API tests | Low | No backend change in minimal slice |
| Platform-console tests | None exist today | Manual + optional vitest later |

**Regression tests to run after B3 implementation:**

- `pytest tests/test_industry_templates.py`
- `pytest tests/test_parties.py`
- `pytest tests/test_workflows.py`
- `pytest tests/test_mvp_scenario.py` (kindergarten journey)
- Manual console smoke on `flexity-sales` + one kg tenant

---

## 10. Recommended B3 Implementation Slice

### Approach: **Label-driven sales UX (Option B)**

**Principle:** derive default `party_role` and copy from `labels_config.party_roles` — works for `flexity_sales_basic` without hardcoding slug.

### Minimal slice (HQ approve → implement)

| # | Task | Files |
|---|------|-------|
| 1 | `pickDefaultPartyRole(labels)` — if `lead` in party_roles → `lead`, elif `client` → `client`, else first key | `labelHelpers.ts` |
| 2 | Fix `clientsSectionTitle` to use default role + party entity labels | `WorkspaceLabelsContext.tsx` |
| 3 | `CreateClientModal` — use labels for title/labels; pass dynamic `party_role` | `CreateClientModal.tsx` |
| 4 | `ClientsPage` — visible roles = keys from `labels.party_roles` + `client` + `guardian` + null | `ClientsPage.tsx` |
| 5 | `CreateWorkItemModal` — `entityLabel("party")` instead of «Клиент» | `CreateWorkItemModal.tsx` |
| 6 | Add `lead`, `contact` to `partyRoleRu` | `ruUi.ts` |

**Estimated files:** 5–6 platform-console files only.
**No backend changes. No migrations. No seed changes.**

### Out of scope for minimal B3

- Party role migration on existing sales tenant rows (manual fix or re-create)
- WorkItem kanban party name
- Role selector in modal
- `party_role` update on stage `accepted` (B6)
- Public inbound

### If HQ wants even smaller slice

**B3-min:** only items 3 + 4 + 5 (modal + filter + work item label) — still required together because `lead` without filter breaks list.

---

## 11. Tests / Smoke Needed

| Check | Type | Expected |
|-------|------|----------|
| `pytest tests/test_industry_templates.py` | automated | 7 passed, no regression |
| `pytest tests/test_mvp_scenario.py` | automated | kindergarten journey OK |
| API: create Party `lead` + WorkItem | smoke | B2a repeat |
| Console: create contact on sales tenant | manual | `party_role=lead`, visible in list |
| Console: create WorkItem | manual | links to party, in kanban |
| Labels: CRM shows «Лид» | manual | from template |
| Labels: clients hint shows «Лид / Контакт» | manual | after context fix |
| Kindergarten tenant | manual | guardian/client flow unchanged |
| `POST /public/leads` | smoke | still 404 |

**Platform-console unit tests:** none in repo today — optional vitest for `pickDefaultPartyRole` in B3 or B3.1.

---

## 12. Stop Conditions

Cursor must **stop and request HQ approval** if implementation requires:

| Condition | B3 minimal slice |
|-----------|------------------|
| Database migration | ❌ not expected |
| New `party_role` enum column | ❌ not expected |
| New Lead / Diagnosis / Project table | ❌ forbidden |
| Public inbound endpoint | ❌ forbidden |
| Tenant isolation changes | ❌ not needed |
| Changing `client` semantics globally for all tenants | ⚠️ stop — must stay label-driven |
| Production deploy | ❌ forbidden |
| Changes to `kindergarten_basic` seed | ❌ forbidden |
| Hardcoding `flexity-sales` slug in code | ❌ avoid — use labels |

---

## 13. Recommended Next Step

1. **HQ approves B3 minimal slice** (§10).
2. **Implement B3** — platform-console only, 5–6 files.
3. **Console UI smoke** on running dev stack (`flexity-sales` + kg tenant).
4. **Then** HQ decision on **B2b public inbound** cherry-pick.

**Order:** B3 implementation → console smoke → B2b decision.
**Not parallel:** do not cherry-pick inbound while B3 is open.

---

## 14. HQ Summary

### 1. Current issue

Console treats every Party as **«клиент»** (`party_role=client`), while sales tenant template defines **«Лид» / «Контакт»**.
If we switch to `lead` without fixing `ClientsPage` filter, **contacts disappear from the list**.

### 2. Recommended party_role approach

**Option B — `party_role=lead`**, selected automatically from template `labels_config.party_roles` (label-driven, no slug hardcode).
No migration — metadata string only.

### 3. Recommended implementation slice

**5–6 platform-console files:**

- `labelHelpers.ts` — default role picker
- `WorkspaceLabelsContext.tsx` — fix clients section title
- `CreateClientModal.tsx` — dynamic role + copy
- `ClientsPage.tsx` — include `lead` in visible roles
- `CreateWorkItemModal.tsx` — party label from template
- `ruUi.ts` — `lead`/`contact` fallbacks

**No backend. No migrations. No public inbound.**

### 4. Risks

- ClientsPage filter regression for kindergarten
- Participant role `client` on `lead` Party (cosmetic; optional `other`)
- No console automated tests yet
- UI workspace still not smoke-tested in B2a (N/A)

### 5. Next action

**HQ approves B3 plan** → Cursor implements minimal console slice → console UI smoke → B2b decision.

---

## Appendix A — File reference

| Path | Role in B3 |
|------|------------|
| `platform-console/src/components/workspace/CreateClientModal.tsx` | Party create — **primary fix** |
| `platform-console/src/pages/workspace/ClientsPage.tsx` | List filter — **blocker if ignored** |
| `platform-console/src/components/workspace/CreateWorkItemModal.tsx` | WorkItem create + link |
| `platform-console/src/workspace/WorkspaceLabelsContext.tsx` | Section titles |
| `platform-console/src/workspace/labelHelpers.ts` | Label normalization + new helper |
| `platform-console/src/components/workspace/CrmPipelineBoard.tsx` | Kanban (optional enrichment) |
| `platform-console/src/i18n/ruUi.ts` | Role display fallbacks |
| `backend/app/modules/parties/schemas.py` | `party_role` free string — no change |
| `backend/app/modules/industry_templates/seed.py` | `flexity_sales_basic` labels — B1 done |
| `backend/app/modules/workflows/schemas.py` | WorkItem + participant — no change |

---

*Plan v1.0 — documentation only. Implementation requires explicit HQ approval.*
