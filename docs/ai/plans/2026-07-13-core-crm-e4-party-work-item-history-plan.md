# Implementation Plan: Core CRM E4 — Previous interactions / Party work item history

**Дата:** 2026-07-13  
**Проект:** Flexity / `coreops-platform`  
**Тип:** documentation-only implementation plan  
**Статус:** ⏸ **waiting for approval** (код / migrations / deploy / server — не трогать)  
**Prerequisites:**
- E1–E1.4 disposition + board/list UX deployed
- E2 Match API deployed (`POST /parties/match`)
- E3 CreateWorkItemModal match UI deployed + browser smoke by Асем
- Deploy report: `docs/ai/reports/2026-07-13-core-crm-e2-e3-match-deploy-smoke-report.md`

**CRM URL:** https://flexity.asia/console/workspace/flexity-sales/crm  
**Tenant:** `flexity-sales` (`90553fe9-22d1-458d-ab84-c7353f2d80e2`)

---

## Goal

В `LeadDetailModal` показать блок **«История обращений контакта»**: другие WorkItems того же linked Party, чтобы оператор видел прошлые обращения, источник, стадию, статус и disposition.

E4 **не** мержит контакты, **не** auto-link, **не** трогает public inbound.

---

## Classification

| Field | Value |
|-------|-------|
| **Project** | Flexity |
| **Category** | `universal_module` (CRM / workflows UI) — plan is `documentation_only` |
| **Risk** | low–medium (UI state when switching WorkItem; incomplete history if wrong data source) |
| **Intended scope (after approval)** | primarily frontend `LeadDetailModal` (+ tiny CrmPage callback/`key` if open-previous) |
| **Forbidden now** | code, migrations, backend changes, deploy, server, inbound, merge |

### Task Classification (coordinator)

1. **Project:** Flexity  
2. **Category:** documentation_only (implementation later: universal_module CRM UI)  
3. **Risk level:** low  
4. **Intended scope:** this plan file only  
5. **Forbidden scope:** production code, server, migrations, public inbound  
6. **Required plan:** documentation-only change → this document  

---

## Product context

| Step | Role |
|------|------|
| **E2** | найти существующий Party по контактам |
| **E3** | дать выбрать «использовать этот контакт» |
| **E4** | показать историю WorkItems этого Party в карточке лида |
| **E5 / inbound** (later) | использовать тот же контекст при public intake |

Модель: много WorkItems → один Party. Каждое новое обращение = новый WorkItem.

---

## 1. Data availability audit (facts)

### Backend already has party filter

`GET /api/v1/work-items` already accepts:

| Query param | Present |
|-------------|---------|
| `primary_party_id` | ✅ |
| `pipeline_id` | ✅ |
| `stage_id` | ✅ |
| `status` | ✅ |
| `search` | ✅ |
| `skip` / `limit` | ✅ default 50, **max 200** |

Source: `backend/app/modules/workflows/routes.py` → `list_work_items`.

Repository:

- filters `WorkItem.tenant_id == tenant_id` (tenant isolation);
- filters `WorkItem.primary_party_id == primary_party_id` when set;
- **orders by `updated_at DESC`**;
- does **not** include participant-only WorkItems (only `primary_party_id`).

### WorkItem list / response fields (enough for E4)

`WorkItemResponse` includes:

| Field | Needed for history UI |
|-------|------------------------|
| `id` | open / exclude current |
| `title` | ✅ |
| `source` | ✅ |
| `stage_id` | ✅ (label via pipeline.stages) |
| `status` | ✅ |
| `custom_fields` | ✅ includes `disposition` / `disposition_note` when set (via CustomFieldService in `_to_response`) |
| `created_at` / `updated_at` | ✅ |
| `primary_party_id` | ✅ |
| `pipeline_id` | useful if multi-pipeline later |

### Frontend API already wired

`platform-console/src/api/workflows.ts`:

```ts
listWorkItems({ primary_party_id, limit, ... })
```

### Existing consumer (pattern to reuse)

`ClientDetailPage` already loads:

```ts
queryKey: ["workspace-party-work-items", partyId]
queryFn: () => listWorkItems({ primary_party_id: partyId, limit: 200 })
```

`LeadDetailModal` already **invalidates** `["workspace-party-work-items"]` on save/close/reopen, but **does not yet display** history.

### CrmPage board list is not enough alone

CrmPage loads:

```ts
listWorkItems({ pipeline_id: pipeline.id, limit: 200 })
```

Filtering that in-modal (Option A) would miss:

- WorkItems outside current pipeline;
- items beyond board limit;
- closed items if board view filters client-side.

---

## 2. Backend options

| Option | Description | Verdict |
|--------|-------------|---------|
| **A — frontend-only from CrmPage cache** | Filter loaded board list by `primary_party_id` | ❌ incomplete history |
| **B — existing API filter** | `GET /work-items?primary_party_id=…&limit=…` | ✅ **recommended** |
| **C — new endpoint** | `GET /parties/{id}/work-items` | ❌ not needed for E4 |

### Recommendation

**Option B — no backend code for E4 v1.**

Use existing authenticated, tenant-scoped list endpoint. Same path as ClientDetailPage.

Optional later (not E4):

- dedicated `GET /parties/{party_id}/work-items` only if need summary DTO / smaller payload;
- include participant roles beyond `primary_party_id` — out of scope unless product asks.

---

## 3. UI behavior (LeadDetailModal)

### When to show

| Condition | Behavior |
|-----------|----------|
| `primary_party_id` present | Show block **«История обращений контакта»** |
| Party loading | Small loading line inside block |
| Party history empty (after exclude current) | «Других обращений пока нет» |
| No `primary_party_id` | Do **not** show history block (contact section already says «Контакт не привязан») |

### List content (top 5)

For each history row (sorted `updated_at` desc from API):

- title
- date (`updated_at` or `created_at` — prefer **updated_at**, label as дата)
- source label (reuse leadSources / existing source helpers)
- stage label (from `pipeline.stages` by `stage_id`; if other pipeline → fallback stage code/id muted)
- status (RU label)
- disposition label if `custom_fields.disposition` present (reuse `getDispositionLabel`)
- action: **«Открыть»**

### Placement

Below contact (Party) section, before disposition/close controls — so operator sees context while reviewing the lead.

### Visual

Reuse existing muted list / form-section patterns; no new design system. Soft border list, not heavy cards.

---

## 4. Current WorkItem handling

**Recommended:** **exclude current WorkItem** from the history list.

Rationale:

- block title is «история» / previous interactions;
- avoids clutter and double-open of the same item;
- empty state becomes meaningful: «Других обращений пока нет».

Alternative (not preferred): show current with badge «текущее» — only if HQ wants full Party timeline in one list.

---

## 5. Open previous WorkItem

### Preference (HQ)

If safe → open other WorkItem in the **same** modal.

### Feasibility

`CrmPage` holds `selectedWorkItemId` and renders:

```tsx
<LeadDetailModal workItemId={selectedWorkItemId} ... />
```

**No `key={selectedWorkItemId}` today.**  
`LeadDetailModal` uses one-shot `hydrated` flag — switching `workItemId` without remount would leave stale form state.

### Recommended E4 behavior

1. History row click / «Открыть» calls parent callback `onOpenWorkItem(id)`.
2. CrmPage: `setSelectedWorkItemId(id)`.
3. Add **`key={selectedWorkItemId}`** on `LeadDetailModal` so React remounts and rehydrates cleanly.
4. Optional: if unsaved edits exist, `window.confirm` before switch (minimal safety).

If confirm-on-dirty feels heavy for v1: remount without confirm (same as closing and opening another card from board).

### Fallback (only if remount proves risky)

v1 read-only summary without navigation + link to ClientDetailPage (already exists: «Открыть карточку контрагента»). Prefer remount path first.

---

## 6. Filtering / security

| Rule | How |
|------|-----|
| Tenant isolation | API already scopes by `ctx.tenant` / `WorkItem.tenant_id` |
| Same Party only | `primary_party_id` query |
| Sort | API `updated_at DESC` |
| Cap | request `limit: 20` (display top **5** after exclude current) |
| Cross-tenant | impossible via normal workspace client (tenant header + require_module crm) |
| Participants without primary | **out of E4** — CRM create path sets `primary_party_id` |

Do **not** pass board `pipeline_id` into history query — history should include closed/rejected from other stages and any pipeline of this Party in tenant.

---

## 7. Relation to match / dedup

```
E2 Match API  → find Party
E3 UI choice  → reuse Party on new WorkItem
E4 History    → show that Party’s prior WorkItems
E5 inbound    → later: match-before-create + optional history context
```

E4 does not change match logic. It only consumes Party linkage.

---

## 8. Migration decision

| Question | Answer |
|----------|--------|
| Migration needed? | **No** |
| New tables? | **No** |
| New columns? | **No** |
| Template seed? | **No** |

Data already in `work_items` + EAV custom fields.

---

## 9. Implementation steps (after HQ code approval)

### Slice E4 (frontend-only)

1. In `LeadDetailModal`:
   - when `partyId` set, `useQuery`  
     `["workspace-party-work-items", partyId]` → `listWorkItems({ primary_party_id: partyId, limit: 20 })`;
   - filter out `workItemId`;
   - take first 5;
   - render history block.
2. Reuse `getDispositionLabel`, lead source labels, stage names from `pipeline`.
3. Add optional prop `onOpenWorkItem?: (id: string) => void`.
4. In `CrmPage`: pass `onOpenWorkItem={setSelectedWorkItemId}` and `key={selectedWorkItemId}`.
5. Minimal CSS in `index.css` if needed (section list).
6. Optional tiny helper `partyWorkItemHistoryHelpers.ts` + unit tests for exclude/limit/sort display.

### Files likely to change (code phase)

| File | Change |
|------|--------|
| `platform-console/src/components/workspace/LeadDetailModal.tsx` | history query + UI + open callback |
| `platform-console/src/pages/workspace/CrmPage.tsx` | `key` + `onOpenWorkItem` |
| `platform-console/src/index.css` | small history styles (optional) |
| `platform-console/src/workspace/partyWorkItemHistoryHelpers.ts` | optional pure helpers |
| `…Helpers.test.ts` | optional |

### Files not to touch

- backend / parties / workflows routes (unless HQ later asks Option C)
- migrations / alembic
- public inbound
- CreateWorkItemModal (E3 already done)
- Marketing / Telegram / Margosya / Booking / Clinic / Trailers
- production server without separate deploy approval

---

## 10. Tests / checks plan

### Automated (if helpers added)

- exclude current id from list;
- take top 5 after exclude;
- empty → empty state;
- disposition label present when `custom_fields.disposition` set.

### Manual / API-equivalent smoke (after code + deploy approval)

1. Party with **only current** WorkItem → «Других обращений пока нет».
2. Party with **multiple** WorkItems → list shows others, sorted recent first.
3. Rejected with disposition → reason visible.
4. «Открыть» → modal switches to that WorkItem; form fields match.
5. Board / List still open modal as today.
6. Kindergarten CRM opens 200; no test data required.
7. No cross-tenant leakage (API already tenant-scoped; optional dual-tenant check).

### Build

- `npm run build`
- existing helper tests

---

## 11. Risks

| Risk | Mitigation |
|------|------------|
| Stale form if switch WorkItem without remount | `key={workItemId}` on modal |
| History limited to `primary_party_id` | Document; OK for current CRM create path |
| Stage from another pipeline unknown | Fallback muted label / «другая воронка» |
| Operator loses unsaved edits on «Открыть» | optional confirm; or accept remount like board click |
| Limit 20 hides very old spam storms | Acceptable for MVP; raise later if needed |

---

## 12. Rollback (code/deploy phase)

Console-only rollback of dist backup; no DB rollback. Backend unchanged → no backend rollback for E4.

---

## 13. Recommended next implementation slice

**E4 frontend-only** after this plan approval:

1. History block in `LeadDetailModal` via `listWorkItems({ primary_party_id })`.
2. Exclude current; show top 5.
3. Open previous via parent `setSelectedWorkItemId` + modal `key`.
4. Local build/tests → separate **deploy approval**.

**Not in E4:** new backend endpoint, merge, inbound, participant-based history.

---

## Approval

**Status:** ⏸ waiting for approval  

Approve to allow **frontend implementation only** (no backend / migrations / deploy until separate HQ approval).

---

## HQ summary (plan)

| # | Item | Answer |
|---|------|--------|
| 1 | **Current API/data availability** | ✅ `GET /work-items?primary_party_id=` exists; fields include title/source/stage/status/custom_fields/dates; ClientDetailPage already uses it |
| 2 | **Recommended approach** | **Option B** — existing API filter; frontend fetch in LeadDetailModal |
| 3 | **Backend needed** | **No** (for E4 v1) |
| 4 | **Frontend changes** | LeadDetailModal history block; CrmPage `key` + open callback; optional helper/CSS |
| 5 | **UI block behavior** | Show if Party linked; top 5; empty copy if none; hide if no Party |
| 6 | **Current WorkItem handling** | **Exclude** from list |
| 7 | **Open previous WorkItem** | Same modal via parent id + remount `key` (preferred) |
| 8 | **Tenant/security** | Existing tenant-scoped list; no cross-tenant |
| 9 | **Migration needed** | **No** |
| 10 | **Tests needed** | Helpers + manual smoke (multi/no history, disposition, open, board/list) |
| 11 | **Risks** | hydrated/state on switch (mitigate with `key`); primary_party-only history |
| 12 | **Next implementation slice** | Frontend-only E4 after approval; then deploy approval |
