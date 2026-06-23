# Flexity Platform Console

Внутренний SPA для `provider_owner`: управление tenants, модулями, подписками и industry templates через Flexity FastAPI REST API.

Tenant users (`tenant_owner`, `tenant_admin`, `member`) входят через тот же login и попадают в manager workspace (`/console/workspace/{slug}/...`).

## Prerequisites

1. **Node.js** 18+ (рекомендуется 20+)
2. **Flexity backend** на `http://127.0.0.1:8000`

```bash
cd ../backend
cp .env.example .env
# SEED_ON_STARTUP=true — plans, modules, kindergarten_basic
docker compose up --build
```

Первый provider owner (только если БД пустая):

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"owner@example.com","password":"securepass123","full_name":"Owner","company_name":"Flexity Provider","company_slug":"flexity-provider"}'
```

## Setup

```bash
cd platform-console
cp .env.example .env
npm install
```

## Dev

```bash
npm run dev
```

Откройте http://localhost:5173/console/

Корень `http://localhost:5173/` не откроет приложение — SPA живёт под префиксом `/console/` (`base` в Vite + `basename` в React Router).

Vite проксирует `/api` → `http://127.0.0.1:8000` (обход отсутствия CORS в backend; на Windows `localhost` может резолвиться в `::1`).

## Build

```bash
npm run build
npm run preview   # http://localhost:4173/console/
```

## Environment

| Variable | Dev | Production (later) |
|----------|-----|------------------|
| `VITE_API_BASE_URL` | `/api/v1` | `https://flexity.asia/api/v1` |

## Demo onboarding smoke flow

Полный путь для demo-ready owner journey:

| # | Step | Expected |
|---|------|----------|
| 1 | Register provider via `curl` (см. выше) | `201`, tokens returned |
| 2 | Open http://localhost:5173/console/login, login as provider | Redirect to `/console/tenants` |
| 3 | **Создать организацию**: name, slug, plan (`starter`), template (`kindergarten_basic`) | Redirect to tenant detail |
| 4 | Tab **Users** → **Создать пользователя**: tenant owner email, имя, temp password, роль **Владелец организации** | User created, credentials shown once |
| 5 | Tab **Users** → **Создать пользователя**: manager email, имя, temp password, роль **Участник** | Second user created |
| 6 | Tab **Modules** → enable `parties` if disabled | Status → enabled |
| 7 | Logout → login as **tenant owner** | Redirect to `/console/workspace/{slug}/dashboard` |
| 8 | Logout → login as **manager** | Redirect to workspace |
| 9 | **Клиенты** → **Создать клиента** | Client appears in list |
| 10 | Provider: **Открыть рабочее место** from tenant card | Workspace opens for same tenant |

### Optional: owner_email at tenant creation

Поле **Email владельца организации** на форме создания организации назначает `tenant_owner` только если пользователь с этим email **уже существует** в системе. Для нового владельца используйте шаг 4 (создание пользователя на вкладке Users).

## Browser smoke checklist (provider console)

| # | Step | Expected |
|---|------|----------|
| 1 | Open http://localhost:5173/console/ | Redirect to `/console/login` |
| 2 | Login as provider_owner | Redirect to `/console/tenants` |
| 3 | Tenants list | Table renders |
| 4 | «Создать tenant» | Form with plan/template/owner email |
| 5 | Create: name + slug + `starter` + `kindergarten_basic` | Redirect to tenant detail |
| 6 | Tab Modules | Modules list with statuses |
| 7 | Enable `parties` if disabled | Status → enabled |
| 8 | Tab Subscription | Shows starter plan |
| 9 | Tab Users → create tenant owner | Role `tenant_owner` available |
| 10 | Tab Apply Template | Apply shows success + result JSON |
| 11 | Logout | Back to login, `/tenants` blocked |
| 12 | Login as tenant user (not provider) | Workspace dashboard, not `/tenants` |

## Rollback

```bash
rm -rf platform-console/node_modules platform-console/dist
# or remove entire folder:
# rm -rf platform-console/
```

## Out of scope (later tracks)

- Password reset / first-login change password
- Labels PATCH
- Plan CRUD
- Subscription cancel/suspend
- Audit UI
- Tailwind / shadcn
- Production deploy
