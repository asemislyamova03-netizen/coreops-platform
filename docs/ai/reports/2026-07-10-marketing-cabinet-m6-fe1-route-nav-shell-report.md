# M6-FE1 — Marketing Console route/nav shell (local only)

**Date:** 2026-07-10  
**Slice:** M6-FE1  
**Branch context:** Marketing Cabinet / ContentOps Cabinet  
**Scope:** platform-console frontend only  

## Summary

Добавлен frontend shell раздела «Маркетинг» в workspace platform-console: навигация, маршруты, placeholder-экраны и skeleton API client для `/api/v1/marketing/*`. Полноценный pack editor, publish и git export **не реализованы**.

## HQ approval scope

| Allowed | Done |
|---------|------|
| Workspace nav «Маркетинг» | ✅ |
| Routes shell | ✅ |
| Placeholder screens | ✅ |
| API client skeleton + safe GET | ✅ |
| Build/typecheck | ✅ |
| Backend changes | ❌ not touched |
| Publish / git export | ❌ not implemented |
| Margosya | ❌ not touched |

## Routes added

Basename приложения: `/console` (`src/main.tsx`).

| URL (browser) | Component |
|---------------|-----------|
| `/console/workspace/:tenantSlug/marketing` | `MarketingDashboardPage` |
| `/console/workspace/:tenantSlug/marketing/topics` | `MarketingTopicsPage` |
| `/console/workspace/:tenantSlug/marketing/packs` | `MarketingPacksPage` |
| `/console/workspace/:tenantSlug/marketing/packs/:packId` | `MarketingPackDetailPage` |

## Navigation

- Пункт **«Маркетинг»** добавлен в `WorkspaceSidebar` между «Финансы» и «Отчёты».
- Proactive module gating во frontend отсутствует (как у documents/finance) — пункт виден всегда; при отключённом модуле показывается info через `moduleDisabledMessage("marketing")` после 403 от API.

## Placeholder screens

### 1. Marketing Dashboard
- Title: «Маркетинг»
- KPI-карточки: Topics, Packs, Pending approval, Latest publications
- Быстрые ссылки на Topics / Packs
- Placeholder для Leads из контента

### 2. Topics
- Title: «Темы»
- GET `/marketing/topics` — read-only таблица при доступном модуле

### 3. Packs
- Title: «Публикации / Packs»
- GET `/marketing/packs` — read-only таблица со ссылками на detail

### 4. Pack detail
- Заголовок из pack.title
- Мета: status, preflight, approval, publish, planned_date
- Tabs (M3): Texts, Media, Preflight, Approval, **Publish (disabled)**, Logs
- Publish tab: текст «Будет подключено позже» + disabled button

## API client

`platform-console/src/api/marketing.ts`:

- `getMarketingHealth()` → `GET /marketing/health`
- `listMarketingTopics()` → `GET /marketing/topics`
- `listMarketingPacks()` → `GET /marketing/packs`
- `getMarketingPack(packId)` → `GET /marketing/packs/{id}`

Types: `platform-console/src/types/marketing.ts`  
Tenant header: через существующий `workspaceApiFetch` (`X-Tenant-ID`).

## Publish actions

| Element | State |
|---------|-------|
| Publish tab button | **disabled** |
| Publish tab content | «Будет подключено позже» |
| Approve / Reject / Preflight run | not wired |
| Git export | not present |

## Files changed

### Created
- `platform-console/src/types/marketing.ts`
- `platform-console/src/api/marketing.ts`
- `platform-console/src/pages/workspace/marketing/MarketingPageHeader.tsx`
- `platform-console/src/pages/workspace/marketing/MarketingDashboardPage.tsx`
- `platform-console/src/pages/workspace/marketing/MarketingTopicsPage.tsx`
- `platform-console/src/pages/workspace/marketing/MarketingPacksPage.tsx`
- `platform-console/src/pages/workspace/marketing/MarketingPackDetailPage.tsx`

### Modified
- `platform-console/src/routes.tsx`
- `platform-console/src/components/layout/WorkspaceSidebar.tsx`
- `platform-console/src/i18n/ruUi.ts`
- `platform-console/src/workspace/moduleErrors.ts`
- `platform-console/src/index.css` (`.workspace-kpi-link`)

## Files intentionally not touched

- `backend/**` (marketing module, migrations, tests)
- Margosya / content-bank repos
- GitHub Actions / deploy configs
- CRM lead detail, booking, clinic, trailers
- Platform admin (`/tenants/*`) routes

## Build / tests

```bash
cd platform-console && npm run build
```

- **Result:** ✅ pass (`tsc && vite build`)
- Separate `npm run typecheck` script: not defined (covered by `tsc` in build)
- Frontend test script in `package.json`: not configured; existing `labelHelpers.test.ts` not run in this slice

## Manual local smoke (recommended)

1. Start backend + platform-console dev server locally.
2. Open workspace tenant with marketing module enabled (or verify 403 placeholder).
3. Confirm sidebar item «Маркетинг».
4. Open dashboard, topics, packs, pack detail routes.

## Backend touched

**No.**

## Deploy needed

**No** — local-only slice per HQ approval.

## Risks

1. Nav item visible even when marketing module disabled — UX relies on API 403 + info alert (consistent with finance/documents pattern).
2. Pack detail tabs are local state only — no deep-linking per tab yet.
3. Lists capped at `limit=200` — sufficient for FE1 shell, not for production scale.
4. Without local backend + enabled marketing module, pages show module-disabled or error states.

## Next recommended step

**M6-FE2** (or next approved FE slice):

1. Pack detail — Texts tab: read/edit via `PUT /packs/{id}/texts/{channel}`
2. Media tab: list + metadata forms
3. Preflight / Approval actions (POST endpoints from BE5)
4. Optional: sub-nav under Marketing (Topics / Packs) in sidebar

Parallel backend option: **M6-BE6** publish logs + git export (when approved).

---

## HQ summary

1. **Status:** ✅ Complete (M6-FE1 local only)
2. **Files changed:** 12 files (7 created, 5 modified) — see above
3. **Routes added:** 4 marketing workspace routes under `/console/workspace/:slug/marketing/*`
4. **Nav item added:** «Маркетинг» in `WorkspaceSidebar`
5. **Placeholder screens:** Dashboard, Topics, Packs, Pack detail (6 tabs)
6. **API client added:** `src/api/marketing.ts` + `src/types/marketing.ts`
7. **Publish actions present/enabled:** Present as disabled placeholder only — **not enabled**
8. **Build/tests:** `npm run build` ✅; no npm test script
9. **Backend touched:** No
10. **Deploy needed:** No
11. **What was not touched:** backend, Margosya, publish/git export, deploy, GHA
12. **Risks:** module 403 UX, no tab deep-links, list limit 200
13. **Next recommended step:** M6-FE2 pack editor tabs + approval actions, or M6-BE6 if backend-first
