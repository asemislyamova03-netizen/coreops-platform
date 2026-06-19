# Session Handoff: W2 CRM manager workspace status

## Branch

`main` (synced with `origin/main` after W2.1 merge)

## Goal

Finish W2 read-only CRM manager workspace in `platform-console` tenant workspace.

## Status

### Already implemented (W1 + W2.1 + W2.2 partial)

- Tenant workspace shell (`/workspace/:tenantSlug/*`)
- `TenantWorkspaceGuard`, `WorkspaceLabelsContext`, `X-Tenant-ID` via `workspaceApiFetch`
- CRM manager navigation: Dashboard, CRM, Clients, Documents, Finance, Reports
- **CRM pipeline board** (`CrmPage` + `CrmPipelineBoard`) — read-only kanban by stages
- Labels from `GET /tenants/{id}/labels` with kindergarten fallbacks

### Completed in this session (W2.2–W2.5 frontend)

- **Dashboard** (`DashboardPage` + `useDashboardData`) — KPIs from pipelines, work-items, finance summary, receivables, documents
- **Clients list** (`ClientsPage`) — `GET /parties`, client-side filter `party_role === "guardian"`, labels from context
- **Client detail** (`ClientDetailPage` + route `clients/:partyId`) — overview, deals, documents, finance tabs
- **Documents** (`DocumentsPage`) — list with status, signature hint, party/work item links
- **Finance** (`FinancePage`) — summary strip, invoices, payments, receivables
- Shared API/types: `parties`, `documents`, `finance`, `query`, `formatters`, `documentHelpers`

### Remaining

| Slice | Scope |
|-------|--------|
| W2.4 | Backend filters — **not started** (optional, separate approval) |
| W3 | CRUD work items, move-stage, document generate |

### Placeholders still

- `ReportsPage` — placeholder (out of W2 scope)

## Exact next slices

1. QA on tenant `test-kindergarten` in browser
2. Commit + PR for W2.2–W2.5 bundle
3. Optional W2.4 backend mini-slice if client-side filtering is insufficient at scale
4. W3: CRUD work items, move-stage, document generate

## Forbidden files

- `backend/alembic/**`
- `deploy/**`, nginx, systemd
- legacy Flask (Trailers, Consulting)
- tenant customization PATCH
- kindergarten-specific CRM backend module

## Do not do next

- Deploy without explicit approval
- Migrations
- W2.4 backend without separate approval
- Children/Parents top-level screens
