# Implementation Plan: Stage W1 tenant workspace shell (kindergarten_basic)

## Goal

Подготовить и реализовать минимальный tenant-facing shell (без бизнес-экранов) для `kindergarten_basic`, чтобы пользователь с tenant membership попадал в рабочее пространство tenant, а не только в provider-owner Platform Console.

## Classification

- Project: Flexity
- Category: platform_core + industry_template
- Plan mode: planning only (no code in this stage)
- Risk level: medium

## Scope

### In scope (W1)

1. Роутинг и URL для tenant workspace.
2. Отдельный tenant layout shell.
3. Membership-based guard (tenant user access).
4. Tenant selector/context bootstrap из `auth/me.tenants`.
5. Навигация-заглушка под kindergarten MVP разделы.
6. Read-only placeholder screens (без полноценной бизнес-логики экранов).

### Out of scope (explicitly not included)

- Реальные kindergarten бизнес-экраны CRUD (children/parents/invoices/documents) в production-ready виде.
- Tenant customization layer implementation.
- Invite/reset password изменения.
- Deploy/nginx/migrations/prod DB changes.
- Любые изменения legacy Flask (Trailers/Consulting).

## URL / Routing proposal

## Recommendation

- Оставить provider-owner control plane на:
  - `/console/*`
- Добавить tenant workspace на:
  - `/workspace/:tenantSlug/*`

## Why separate from `/console`

- `/console` уже выполняет роль control plane (управление tenant-ами провайдером).
- `/workspace/:tenantSlug` нужен как operating plane для работы внутри конкретного tenant.
- Разделение снижает риск смешения ролей и правил доступа.
- Не требует нового subdomain/nginx этапа на W1.

## Frontend scope (W1)

1. Добавить tenant workspace route tree:
   - `/workspace/:tenantSlug`
   - разделы-навигация (placeholder): dashboard, enrollees, guardians, services, finance, documents.
2. Добавить `TenantWorkspaceLayout`:
   - верхняя панель: текущий tenant, пользователь;
   - левое меню: MVP секции.
3. Добавить `TenantWorkspaceGuard`:
   - доступ при `me.tenants.length > 0` (membership-based);
   - редирект для provider_owner без tenant selection не ломать.
4. Добавить tenant selector/context:
   - выбор tenant по `tenantSlug` из URL;
   - fallback, если slug не найден в memberships.
5. Placeholder screens:
   - read-only страницы “Coming in W2/W3” с минимальной диагностикой tenant context.

## Backend scope (W1)

## Current APIs sufficiency

- Для W1 текущие API **достаточны**:
  - `GET /auth/me` уже возвращает memberships (`tenants`).
  - tenant context в backend уже поддержан через `tenant_id` path или `X-Tenant-ID`.

## Need for new endpoint

- Новый endpoint на W1 **не обязателен**.
- Опционально в будущем (W2+) можно рассмотреть `GET /workspace/me` (aggregated context), но не включать в W1 по принципу минимального шага.

## Migrations

- Не требуются.

## Exact files likely to change (post-approval implementation)

### Frontend (primary)

- `platform-console/src/routes.tsx`
- `platform-console/src/auth/AuthContext.tsx` (только если нужен helper для active tenant)
- `platform-console/src/auth/ProtectedRoute.tsx` (разделение provider/tenant guards)
- `platform-console/src/components/layout/AppLayout.tsx` (если переиспользуется)
- `platform-console/src/components/layout/Sidebar.tsx` (или новый workspace sidebar)
- `platform-console/src/types/auth.ts`
- `platform-console/src/api/client.ts` (только если добавится tenant header adapter)
- `platform-console/src/pages/*`:
  - новый workspace layout page
  - placeholder pages для dashboard/enrollees/guardians/services/finance/documents

### Backend (likely no changes for W1)

- Нет обязательных изменений.
- Если появится необходимость минимального helper endpoint, это будет отдельный mini-plan approval.

## Tests / checks

### Required for W1

- `cd platform-console && npm run build`
- Route/guard smoke (manual):
  - provider_owner продолжает входить в `/console`;
  - tenant membership user может открыть `/workspace/:tenantSlug`;
  - invalid slug -> controlled fallback/error page;
  - без токена -> редирект на `/login`.

### Backend tests

- Только если в W1 будут backend изменения (по текущему плану не нужны).

## Rollback

1. Удалить/отключить workspace routes и guards.
2. Вернуть единственный поток `/console` как до W1.
3. Не требуется rollback БД/миграций (их нет в W1).

## Risks

1. Смешение provider/tenant guard логики и случайный редирект не в тот workspace.
2. Неправильная обработка `tenantSlug`, leading to access confusion.
3. Преждевременное усложнение W1 бизнес-экранными задачами.
4. Попытка внедрить tenant customization до отдельного approved scope.

## Forbidden scope reminder

- No code yet in этой задаче (план только).
- No deploy, no nginx, no migrations, no prod DB changes.
- No auth/password reset/invite work.
- No legacy Flask changes.

## Approval

Status: waiting for approval

## Next safe step

- После approval выполнить W1 только фронтенд-этапом (routes + layout + guard + placeholders), без backend API расширений и без инфраструктурных изменений.
