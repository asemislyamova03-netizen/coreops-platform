# Implementation Plan: Stage W2 CRM manager workspace

## Goal

Реализовать **read-only рабочее место менеджера** в tenant workspace на универсальных модулях Flexity (CRM/workflows, parties, documents, finance), с отраслевыми подписями из `kindergarten_basic`.

**Явно не цель W2:** справочник детей/родителей (Children-first). Дети и родители — роли внутри client/deal card.

## Classification

- **Project:** Flexity
- **Category:** universal_module + industry_template
- **Risk level:** medium
- **Depends on:** W1 tenant workspace shell (deployed)

## Scope

### In scope (W2)

1. **Tenant API adapter** — `X-Tenant-ID` на всех workspace module calls.
2. **Labels context** — загрузка `GET /tenants/{tenant_id}/labels`, подписи в nav и заголовках.
3. **Navigation reframe** — заменить W1 placeholders на CRM manager sections.
4. **Dashboard (read-only)** — compose: work items, finance summary, receivables, open documents.
5. **Pipeline view (read-only)** — воронка `enrollment` + список/board заявок по стадиям.
6. **Clients list (read-only)** — parties с акцентом на `guardian` как клиент; не отдельные Children/Parents menus.
7. **Client card (read-only)** — party detail + связанные work items, invoices, documents (через compose/filter).
8. **Documents list (read-only)** — tenant documents.
9. **Finance view (read-only)** — invoices list + receivables/summary widgets.

### Out of scope (W2)

- CRUD work items, move-stage, create party, generate document, create invoice/payment (→ W3).
- Children/Parents как top-level navigation.
- Catalog/services admin screen.
- Tenant customization (PATCH labels, branding).
- Отдельный kindergarten CRM backend.
- child↔guardian relation graph API.
- Kanban drag-and-drop.
- Deploy/nginx/migrations/prod DB changes в рамках code task (deploy — отдельный approval).
- Legacy Flask (Consulting/Trailers) code changes.

---

## Product mapping (kindergarten_basic)

| Manager concept | Flexity entity | kindergarten label |
|-----------------|----------------|--------------------|
| Lead / заявка | `WorkItem` (early stages) | «Заявка» |
| Deal / сделка | `WorkItem` (active pipeline) | «Заявка» (same entity) |
| Client | `Party` (`party_role=guardian`) | «Родитель» / «Контрагент» |
| Child on card | `Party` (`party_role=enrollee`) | «Ребёнок» |
| Contract | `DocumentInstance` | «Договор» (template `parent_contract`) |
| Application | `DocumentInstance` | заявление (`enrollment_application`) |
| Invoice / debt | `Invoice`, receivables | «Счёт» |

`consulting_basic` later reuses same screens with different `labels_config`.

---

## Backend scope

### Default assumption: minimal backend (preferred first)

W2 может стартовать **frontend-only** с client-side filter:

- `party_role` из `party.metadata_json`
- `primary_party_id` / `party_id` — filter work items/invoices client-side (малый объём MVP)

### Recommended mini-backend (optional slice — separate approval if split)

Без миграций, только routes/schemas/service:

| Change | Files | Why |
|--------|-------|-----|
| `GET /work-items?primary_party_id=` | `workflows/routes.py`, `repository.py` | Client card deals |
| `GET /parties?party_role=` | `parties/routes.py`, `repository.py` | Clients list |
| `GET /documents?party_id=` | `documents/routes.py`, `repository.py` | Client documents |
| `WorkItemDetailResponse` + activities + tasks | `workflows/schemas.py`, `service.py` | Deal card timeline/tasks |

**Not required for W2 MVP if performance acceptable:** `GET /workspace/dashboard` aggregate.

### Backend forbidden

- New tables Lead/Deal/KindergartenChild
- Alembic migrations
- Auth/tenant membership changes
- Tenant labels PATCH (customization CR)

---

## Frontend scope (W2)

### Navigation (replace W1)

| Old W1 segment | W2 segment | Action |
|----------------|------------|--------|
| `dashboard` | `dashboard` | Implement real compose |
| `children` | — | Remove top-level |
| `parents` | — | Remove top-level |
| `services` | — | Remove (defer catalog) |
| `invoices` | `finance` | Merge into finance view |
| `documents` | `documents` | Implement list |
| — | `pipeline` | New |
| — | `clients` | New |
| — | `clients/:partyId` | New detail route |

### Screens

1. **DashboardPage** — widgets: new leads count, active deals, receivables total, docs pending.
2. **PipelinePage** — columns from default pipeline stages; cards = work items.
3. **ClientsListPage** — table parties (default filter `guardian`).
4. **ClientDetailPage** — header party; tabs: Overview, Deals, Documents, Finance; enrollee block if linked via participants/metadata.
5. **DocumentsPage** — table documents + status.
6. **FinancePage** — invoices table + summary strip.

### Shared infrastructure

- `WorkspaceLabelsProvider` / hook `useWorkspaceLabels()`
- `setWorkspaceTenantId()` in API client interceptors
- Reuse `Table`, `Loading`, `Alert`, `panel` CSS from console

---

## Exact files likely to change (post-approval)

### Frontend (primary)

**Modify:**
- `platform-console/src/routes.tsx`
- `platform-console/src/api/client.ts` — tenant header adapter
- `platform-console/src/components/layout/WorkspaceSidebar.tsx` — CRM nav + labels
- `platform-console/src/auth/TenantWorkspaceContext.tsx` — expose `tenantId` for API/labels
- `platform-console/src/index.css` — dashboard/pipeline/client card layout (minimal)

**Add:**
- `platform-console/src/api/workflows.ts`
- `platform-console/src/api/parties.ts`
- `platform-console/src/api/documents.ts`
- `platform-console/src/api/finance.ts`
- `platform-console/src/api/labels.ts`
- `platform-console/src/types/workflows.ts`
- `platform-console/src/types/party.ts`
- `platform-console/src/types/document.ts`
- `platform-console/src/types/finance.ts`
- `platform-console/src/types/labels.ts`
- `platform-console/src/workspace/WorkspaceLabelsContext.tsx`
- `platform-console/src/pages/workspace/DashboardPage.tsx`
- `platform-console/src/pages/workspace/PipelinePage.tsx`
- `platform-console/src/pages/workspace/ClientsListPage.tsx`
- `platform-console/src/pages/workspace/ClientDetailPage.tsx`
- `platform-console/src/pages/workspace/DocumentsPage.tsx`
- `platform-console/src/pages/workspace/FinancePage.tsx`
- `platform-console/src/components/workspace/*` (widgets, pipeline column, party role badge)

**Remove or deprecate:**
- `platform-console/src/pages/workspace/WorkspacePlaceholderPage.tsx` (replace usages)

### Backend (optional mini-slice)

- `backend/app/modules/workflows/routes.py`
- `backend/app/modules/workflows/repository.py`
- `backend/app/modules/workflows/schemas.py`
- `backend/app/modules/workflows/service.py`
- `backend/app/modules/parties/routes.py`
- `backend/app/modules/parties/repository.py`
- `backend/app/modules/documents/routes.py`
- `backend/app/modules/documents/repository.py`
- `backend/tests/test_workflows.py` (if exists — extend filter tests)

### Forbidden files

- `backend/alembic/**`
- `deploy/**`, nginx configs
- `backend/app/modules/industry_templates/seed.py` (no seed change required for W2 UI)
- Legacy Flask repos
- `.env`, production secrets

---

## Implementation slices (recommended order)

### Slice W2.1 — API adapter + labels + nav (frontend only)

- Tenant header, labels fetch, sidebar/routes reframe.
- Empty states on new pages.
- **Verify:** build + manual route smoke.

### Slice W2.2 — Dashboard + Pipeline read-only (frontend)

- Compose existing APIs.
- **Verify:** data loads for `test-kindergarten` tenant with applied template.

### Slice W2.3 — Clients + Client card read-only

- Clients list; detail with tabs.
- Client-side filters unless W2.4 approved.

### Slice W2.4 — Optional backend filters + work item detail enrichment

- Query params + detail tasks/activities.
- **Verify:** `pytest` workflows/parties/documents tests.

### Slice W2.5 — Documents + Finance pages

- Read-only lists and summary.

---

## Tests / checks

### Required

```bash
cd platform-console && npm run build
```

### Manual smoke (tenant `test-kindergarten`)

| # | Check |
|---|-------|
| 1 | Login tenant user → `/console/workspace/{slug}/dashboard` shows widgets |
| 2 | Pipeline shows enrollment stages + work items (or empty state) |
| 3 | Clients list uses label «Родитель»/«Контрагент» |
| 4 | Client card opens; no top-level Children/Parents nav |
| 5 | Documents + Finance pages load |
| 6 | API calls include `X-Tenant-ID` |
| 7 | Provider console `/console/tenants` unchanged |

### Backend (only if mini-slice)

```bash
cd backend && python -m pytest tests/ -k "workflows or parties or documents" -q
```

---

## Rollback

1. Revert W2 frontend commits; restore W1 placeholder routes in `routes.tsx` + `WorkspaceSidebar.tsx`.
2. Remove new API modules/types.
3. If backend mini-slice deployed: revert filter/detail commits (no DB rollback).
4. Redeploy `platform-console` build from previous `main` commit.

---

## Risks

1. Children-first nav остаётся — продуктовый drift; обязательно удалить W1 segments.
2. Missing `X-Tenant-ID` — silent failures on module APIs.
3. Client-side filtering не масштабируется — plan W2.4 backend filters.
4. `WorkItem` без assignee UX — показывать `created_by` until participant model matures.
5. Смешение `/ai/tasks` и CRM tasks — использовать только `/work-items/.../tasks`.

---

## Deploy impact (after W2 code merge)

| Component | Action |
|-----------|--------|
| `platform-console` rebuild | **yes** |
| `coreops` restart | **no** (unless backend mini-slice) |
| nginx | **no** |
| migrations | **no** |

---

## Approval

**Status: waiting for approval**

Do not write code until explicit approval of:

1. W2 scope as CRM manager (not Children-first).
2. Frontend-only vs including backend mini-slice (W2.4).

---

## Next safe step

После approval начать **Slice W2.1** (tenant API adapter + labels + navigation reframe) без backend changes.
