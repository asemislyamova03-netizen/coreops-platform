# Implementation Plan: Platform Console MVP (Track B-lite)

**Дата:** 2026-06-09  
**Research brief:** [2026-06-09-flexity-platform-console-research-brief.md](../research/2026-06-09-flexity-platform-console-research-brief.md)  
**Статус:** waiting for approval — код не писать до явного approve

---

## Goal

Первый визуальный **Platform Console** для Flexity `provider_owner` (superadmin): login, список tenants, создание tenant, карточка tenant с modules/subscription/labels и базовыми actions через существующий FastAPI REST API.

**Track B-lite first** — только новый frontend в `platform-console/`, **без изменений backend**.

**Track A later** (отдельный plan): user invite, memberships list, labels PATCH, Plan CRUD, subscription cancel/suspend.

---

## Classification

| Поле | Значение |
|------|----------|
| Category | `platform_core` / frontend |
| Risk | low–medium (новая папка, npm deps, нет prod deploy в этом плане) |
| Backend changes | **none** в Track B-lite |
| flexity_admin | read-only UX reference, не трогать |

---

## Architecture

```
Flexity/
  backend/              # FastAPI REST API (не менять в этом плане)
  platform-console/     # NEW: Vite + React + TypeScript SPA
  docs/ai/plans/        # этот файл
```

| Слой | Решение |
|------|---------|
| API | FastAPI `/api/v1/*` |
| Auth | JWT Bearer (`access_token` + `refresh_token`) |
| Dev proxy | Vite proxy `/api` → `http://localhost:8000` (обход отсутствия CORS в backend) |
| Runtime Flask | **не использовать** |
| flexity_admin | UX reference для `consulting_basic` позже |

---

## Scope

### Track B-lite — in scope

1. Scaffold `platform-console/` (Vite + React + TypeScript)
2. Login → `POST /api/v1/auth/login`
3. Auth state + token storage (localStorage) + auto-refresh
4. Tenants list → `GET /api/v1/tenants`
5. Create tenant form: `name`, `slug`, `plan_code`, `industry_template_code`
6. Tenant detail: modules, subscription, labels, apply template, enable/disable module
7. Basic navigation / sidebar
8. `platform-console/README.md` с командами запуска

### Track B-lite — out of scope

- shadcn/ui, Tailwind (можно добавить отдельным этапом после MVP)
- OpenAPI codegen
- Audit screens (API есть, UI — Phase 1.1)
- Template editor (CRUD JSON)
- Deploy на nginx / production
- Backend CORS middleware
- Любые изменения `backend/`, `deploy/`, migrations, `.env`

### Track A — later (отдельный approved plan)

| Endpoint / feature | Приоритет |
|--------------------|-----------|
| User invite / list / disable | P0 |
| `GET /tenants/{id}/memberships` | P0 |
| `PATCH /tenants/{id}/labels` | P1 |
| Plan CRUD | P1 |
| Subscription cancel / suspend | P1 |

---

## API mapping (существующий backend, без изменений)

Базовый префикс: `/api/v1`

### Auth

| UI action | Method | Path | Body / headers |
|-----------|--------|------|----------------|
| Login | POST | `/auth/login` | `{ email, password }` |
| Refresh | POST | `/auth/refresh` | `{ refresh_token }` |
| Current user | GET | `/auth/me` | `Authorization: Bearer <access>` |

**Guard UI:** показывать console только если `me.provider.role === "provider_owner"`. Иначе — экран «Access denied».

### Tenants

| UI action | Method | Path |
|-----------|--------|------|
| List | GET | `/tenants` |
| Detail | GET | `/tenants/{tenant_id}` |
| Create | POST | `/tenants` |
| Update status | PATCH | `/tenants/{tenant_id}` |

**Create body** (из `TenantCreate`):

```json
{
  "name": "Детский сад Альфа",
  "slug": "ds-alpha",
  "plan_code": "starter",
  "industry_template_code": "kindergarten_basic"
}
```

`plan_code` и `industry_template_code` — optional, но форма предлагает выбор из справочников.

### Dropdowns для create form

| Поле | Method | Path |
|------|--------|------|
| Plans | GET | `/plans` |
| Templates | GET | `/industry-templates` |

Известные seed-значения (если `SEED_ON_STARTUP=true`):

- Plans: `starter`, `business`, `enterprise`
- Templates: `kindergarten_basic`

### Tenant detail tabs

| Tab | Method | Path | Actions |
|-----|--------|------|---------|
| Info | GET | `/tenants/{id}` | PATCH status (select: trial/active/suspended/archived) |
| Modules | GET | `/tenants/{id}/modules` | POST `.../modules/{code}/enable`, POST `.../disable` |
| Subscription | GET | `/tenants/{id}/subscription` | POST `/tenants/{id}/subscription` `{ plan_code }` |
| Labels | GET | `/tenants/{id}/labels` | read-only |
| Apply template | GET | `/industry-templates` | POST `/tenants/{id}/apply-template/{template_id}` |

### Module actions (если API позволяет — да)

| Action | Method | Path |
|--------|--------|------|
| Enable | POST | `/tenants/{tenant_id}/modules/{module_code}/enable` |
| Disable | POST | `/tenants/{tenant_id}/modules/{module_code}/disable` |

Не включать в MVP: PATCH mode (`external`/`hybrid`) — сложнее, Track B.2.

---

## Environment / API base URL

### `platform-console/.env.example`

```env
# Dev: Vite proxy sends /api → localhost:8000 (see vite.config.ts)
VITE_API_BASE_URL=/api/v1

# Production build (later, not in this plan):
# VITE_API_BASE_URL=https://flexity.asia/api/v1
```

### Локальная разработка

| Сервис | URL |
|--------|-----|
| FastAPI API | `http://localhost:8000` |
| Swagger | `http://localhost:8000/docs` |
| Platform Console (Vite) | `http://localhost:5173` |
| Proxied API from Vite | `http://localhost:5173/api/v1/*` → `localhost:8000/api/v1/*` |

**Почему proxy:** в backend **нет CORS middleware** (`grep` по `backend/` — пусто). Прямые запросы с `:5173` на `:8000` упадут. Proxy — без изменения backend.

### Backend prerequisites (ручная подготовка, не часть кода плана)

```bash
cd backend
cp .env.example .env
# SEED_ON_STARTUP=true — чтобы были plans, modules, kindergarten_basic
docker compose up --build
# или: uvicorn без docker
```

Первый пользователь (только если БД пустая):

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"owner@example.com","password":"securepass123","full_name":"Owner","company_name":"Flexity Provider","company_slug":"flexity-provider"}'
```

---

## Files to create (exact)

Все пути относительно `Flexity/platform-console/`.

### Root / config

| File | Purpose |
|------|---------|
| `package.json` | deps, scripts `dev` / `build` / `preview` |
| `package-lock.json` | lockfile (после `npm install`) |
| `vite.config.ts` | React plugin, dev proxy `/api` → `http://localhost:8000` |
| `tsconfig.json` | TypeScript strict |
| `tsconfig.node.json` | Vite node types |
| `index.html` | entry HTML |
| `.env.example` | `VITE_API_BASE_URL` |
| `.gitignore` | `node_modules`, `dist`, `.env` |
| `README.md` | setup, run, browser checklist |

### `src/` — application

| File | Purpose |
|------|---------|
| `src/main.tsx` | React root, QueryClientProvider, BrowserRouter |
| `src/App.tsx` | route tree |
| `src/vite-env.d.ts` | `ImportMetaEnv` for `VITE_API_BASE_URL` |
| `src/index.css` | minimal global styles (no Tailwind in B-lite) |

### `src/api/` — HTTP layer

| File | Purpose |
|------|---------|
| `src/api/client.ts` | `apiFetch()`: base URL, Bearer header, 401 → refresh → retry |
| `src/api/auth.ts` | `login()`, `refresh()`, `getMe()` |
| `src/api/tenants.ts` | `listTenants()`, `getTenant()`, `createTenant()`, `patchTenant()` |
| `src/api/modules.ts` | `listTenantModules()`, `enableModule()`, `disableModule()` |
| `src/api/subscriptions.ts` | `listPlans()`, `getSubscription()`, `assignPlan()` |
| `src/api/industry-templates.ts` | `listTemplates()`, `applyTemplate()` |
| `src/api/labels.ts` | `getTenantLabels()` |

### `src/types/` — manual types (no codegen)

| File | Purpose |
|------|---------|
| `src/types/auth.ts` | `TokenPair`, `MeResponse`, `ProviderStaffInfo` |
| `src/types/tenant.ts` | `Tenant`, `TenantCreate`, `TenantStatus` |
| `src/types/module.ts` | `TenantModule`, `ModuleStatus` |
| `src/types/subscription.ts` | `Plan`, `Subscription` |
| `src/types/template.ts` | `IndustryTemplate` |

### `src/auth/` — session

| File | Purpose |
|------|---------|
| `src/auth/tokenStorage.ts` | `get/set/clear` access + refresh in `localStorage` |
| `src/auth/AuthContext.tsx` | user state, login/logout, bootstrap `getMe()` |
| `src/auth/ProtectedRoute.tsx` | redirect to `/login` if no token; check `provider_owner` |

### `src/components/layout/`

| File | Purpose |
|------|---------|
| `src/components/layout/AppLayout.tsx` | sidebar + outlet |
| `src/components/layout/Sidebar.tsx` | nav: Tenants, (Templates read-only optional) |
| `src/components/layout/Header.tsx` | user email, logout button |

### `src/components/ui/` — minimal primitives (no external UI lib)

| File | Purpose |
|------|---------|
| `src/components/ui/Button.tsx` | button |
| `src/components/ui/Input.tsx` | text input |
| `src/components/ui/Select.tsx` | native select wrapper |
| `src/components/ui/Table.tsx` | simple table |
| `src/components/ui/Alert.tsx` | error/success messages |
| `src/components/ui/Loading.tsx` | spinner / text |

### `src/pages/`

| File | Purpose |
|------|---------|
| `src/pages/LoginPage.tsx` | email + password form |
| `src/pages/TenantsListPage.tsx` | table: name, slug, status, created_at |
| `src/pages/TenantCreatePage.tsx` | form: name, slug, plan_code, industry_template_code |
| `src/pages/TenantDetailPage.tsx` | tabs: Info, Modules, Subscription, Labels, Apply Template |
| `src/pages/AccessDeniedPage.tsx` | not provider_owner |

### `src/routes.tsx`

| Route | Page |
|-------|------|
| `/login` | `LoginPage` |
| `/` | redirect → `/tenants` |
| `/tenants` | `TenantsListPage` |
| `/tenants/new` | `TenantCreatePage` |
| `/tenants/:tenantId` | `TenantDetailPage` |

---

## Files not to touch

| Path | Reason |
|------|--------|
| `flexity_admin/**` | legacy reference only |
| `backend/**` | Track B-lite = no backend changes |
| `backend/alembic/**` | no migrations |
| `deploy/**` | no deploy in this plan |
| `backend/.env` | no env changes |
| `Flexity.code-workspace` | optional later |
| Root `README.md` | optional one-line link later (out of scope) |

---

## Implementation steps

### Step 0 — Approval gate (before any command)

Получить явный **approve** на этот plan и на команды ниже (Step 1).

### Step 1 — Scaffold (approval-required: `npm install`)

```bash
cd Flexity
npm create vite@latest platform-console -- --template react-ts
cd platform-console
npm install react-router-dom @tanstack/react-query
npm install
```

**Approval-required:** `npm create vite`, `npm install` — скачивают пакеты из npm registry.

Добавить/настроить вручную после scaffold:

- `vite.config.ts` — proxy
- `.env` из `.env.example`
- структура `src/` по таблице выше

**Не запускать** в Step 1: `npm install -g`, shadcn CLI, Tailwind.

### Step 2 — API client + types

1. `src/api/client.ts` — единая точка fetch
2. Manual types в `src/types/*` по OpenAPI/Swagger (`http://localhost:8000/openapi.json`) или `backend/app/modules/*/schemas.py`
3. Обработка ошибок API: показывать `detail` из FastAPI JSON

### Step 3 — Auth

1. `tokenStorage.ts` — keys: `flexity_access_token`, `flexity_refresh_token`
2. `AuthContext` — on mount: если есть access → `GET /auth/me`
3. `LoginPage` — submit → save tokens → navigate `/tenants`
4. Logout — clear storage, navigate `/login` (client-side only; backend logout endpoint нет)
5. `ProtectedRoute` — require token + `provider?.role === "provider_owner"`

### Step 4 — Layout + navigation

1. `AppLayout` + `Sidebar`: Tenants (active), placeholder для будущих разделов
2. Header: `me.user.full_name`, Logout
3. Простые стили в `index.css` (sidebar слева, content справа)

### Step 5 — Tenants list

1. `useQuery(['tenants'], listTenants)`
2. Table columns: name, slug, status, created_at (locale `ru-RU`)
3. Link row → `/tenants/:id`
4. Button «Создать tenant» → `/tenants/new`

### Step 6 — Create tenant form

1. Parallel fetch: `GET /plans`, `GET /industry-templates` для select options
2. Fields:
   - `name` (required)
   - `slug` (required, pattern `^[a-z0-9]+(?:-[a-z0-9]+)*$`, auto-suggest from name optional)
   - `plan_code` (select, empty option «без плана»)
   - `industry_template_code` (select by `code`, empty option «без шаблона»)
3. Submit → `POST /tenants` → redirect to detail
4. Show API validation errors (409 slug exists, etc.)

### Step 7 — Tenant detail

**Tab: Info**

- Display: id, name, slug, status, industry_template_id, dates
- Status dropdown → `PATCH /tenants/{id}` `{ status }`

**Tab: Modules**

- `GET /tenants/{id}/modules`
- Table: module_code, status, mode
- Buttons: Enable / Disable (hide Disable if already disabled, etc.)
- Invalidate query after action

**Tab: Subscription**

- `GET /plans` + `GET /tenants/{id}/subscription`
- Show current plan or «нет подписки»
- Select plan + «Назначить» → `POST /tenants/{id}/subscription`

**Tab: Labels**

- `GET /tenants/{id}/labels`
- JSON pretty-print or key-value list (read-only)
- Note in UI: «Редактирование — в Track A»

**Tab: Apply Template**

- `GET /industry-templates` — list active templates
- Button «Применить» + confirm dialog → `POST /tenants/{id}/apply-template/{template_id}`
- Show `ApplyTemplateResponse` summary (counts applied)

### Step 8 — README + smoke

1. `platform-console/README.md` — prerequisites, commands, browser checklist
2. Manual browser smoke (see Tests/checks)

---

## Commands reference

### Terminal 1 — Backend

```bash
cd backend
docker compose up --build
# Health:
curl -s http://localhost:8000/api/v1/health
```

### Terminal 2 — Platform Console

```bash
cd platform-console
cp .env.example .env
npm install          # approval-required
npm run dev
# → http://localhost:5173
```

### Build check (optional, after MVP works)

```bash
cd platform-console
npm run build
npm run preview
# → http://localhost:4173
```

---

## Tests / checks

### Automated (Track B-lite — minimal)

| Check | Command |
|-------|---------|
| TypeScript compile | `cd platform-console && npm run build` |
| No backend regression | `cd backend && pytest` (unchanged) |

Unit tests для React — **out of scope** Track B-lite (добавить в Track B.2 при необходимости).

### Browser manual smoke checklist

**Prerequisites:** backend up, provider_owner exists, `SEED_ON_STARTUP=true` (plans + templates).

| # | Step | Expected |
|---|------|----------|
| 1 | Open `http://localhost:5173` | Redirect to `/login` |
| 2 | Login with provider_owner credentials | Redirect to `/tenants` |
| 3 | Tenants list loads | Table renders (may be empty) |
| 4 | Click «Создать tenant» | Form with plan/template dropdowns |
| 5 | Create tenant: name + slug + `starter` + `kindergarten_basic` | 201, redirect to detail |
| 6 | Tab Modules | List modules, statuses shown |
| 7 | Enable `parties` (if disabled) | Status → enabled |
| 8 | Tab Subscription | Shows starter plan |
| 9 | Tab Labels | JSON labels from kindergarten template |
| 10 | Tab Apply Template | List templates; apply shows success message |
| 11 | Logout | Back to login, `/tenants` blocked |
| 12 | Login as non-provider user (if exists) | Access denied screen |

### API verification (parallel, curl)

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"owner@example.com","password":"securepass123"}' | jq -r .access_token)

curl -s http://localhost:8000/api/v1/tenants -H "Authorization: Bearer $TOKEN" | jq
```

### UX reference (read-only, не копировать код)

| flexity_admin pattern | Platform Console equivalent |
|-----------------------|----------------------------|
| `base.html` sidebar | `Sidebar.tsx` |
| `auth/login.html` | `LoginPage.tsx` |
| `index.html` director KPI | Future dashboard (Track B.2) |
| role guard | `ProtectedRoute` + provider_owner check |

---

## Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| No CORS in backend | Dev broken without proxy | Vite proxy in `vite.config.ts`; document clearly |
| Token in localStorage | XSS risk | Acceptable for internal MVP; httpOnly cookies — Track A + backend |
| No user invite API | Create tenant without owner membership | Document workaround; Track A |
| Apply template idempotent? | Re-apply may duplicate data | Confirm dialog + warning text |
| `provider_owner` only | Other provider roles blocked | By design; show AccessDenied |
| npm supply chain | Dependency risk | Minimal deps; lockfile committed |

---

## Rollback

### Full rollback (remove frontend scaffold)

```bash
cd Flexity
rm -rf platform-console/
```

If already committed:

```bash
git revert <commit-hash>
# or
git rm -r platform-console/
```

### Partial rollback

| Situation | Action |
|-----------|--------|
| Broken UI, keep scaffold | `git checkout -- platform-console/src` |
| Bad npm state | `rm -rf platform-console/node_modules && npm install` |
| Backend untouched | Nothing to rollback in backend |

### No rollback needed for

- backend database (no migrations)
- deploy/nginx (not touched)
- flexity_admin (not touched)

---

## Dependencies (approval-required)

| Package | Version policy | Purpose |
|---------|----------------|---------|
| `react`, `react-dom` | from vite template | UI |
| `typescript` | from vite template | types |
| `vite`, `@vitejs/plugin-react` | from vite template | bundler |
| `react-router-dom` | ^7.x | routing |
| `@tanstack/react-query` | ^5.x | server state |

**Explicitly not in Track B-lite** (need separate approval):

- `tailwindcss`, `@shadcn/ui`
- `openapi-typescript`
- `axios` (use native `fetch`)

---

## Future tracks (not this plan)

### Track B.2 (frontend only, optional)

- Audit pages (`/audit/security-events`, `/audit/logs`)
- shadcn/ui + Tailwind polish
- Dashboard KPI (client-side aggregate from `/tenants`)

### Track A (backend + frontend, separate plan)

- `POST /auth/invite` or users CRUD
- `GET /tenants/{id}/memberships`
- `PATCH /tenants/{id}/labels`
- Plan admin CRUD
- Subscription cancel/suspend
- CORS middleware OR same-origin deploy via nginx

### Deploy (separate plan)

- `npm run build` → `platform-console/dist/`
- nginx: `location /console/` → static files
- `VITE_API_BASE_URL=https://flexity.asia/api/v1`

---

## Approval

| Item | Status |
|------|--------|
| Research brief | ✅ accepted |
| This implementation plan | ⏳ **waiting for approval** |
| `npm create vite` + `npm install` | ⏳ waiting (explicit sub-approval) |
| Code changes in `platform-console/` | ⏳ waiting |
| Backend changes | ❌ not in this plan |
| Deploy / migrations | ❌ not in this plan |

**Чтобы начать код:** напиши `approve platform-console plan` (и при необходимости `approve npm install`).

---

## Final checks

- [x] Track B-lite first, Track A later
- [x] Exact files listed
- [x] Commands documented
- [x] env / API base URL documented
- [x] Browser smoke checklist included
- [x] Rollback documented
- [x] flexity_admin / backend / migrations / deploy — not touched
- [x] npm install marked approval-required
- [x] No code written
