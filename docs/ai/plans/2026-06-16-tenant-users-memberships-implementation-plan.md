# Implementation Plan: Track A tenant users and memberships in Platform Console

## Goal

Дать минимально достаточный superadmin/provider_owner flow для управления пользователями tenant без ручных SQL-операций:

1. List memberships tenant.
2. Add existing user to tenant.
3. Invite/create user for tenant owner flow.
4. Safe password reset flow.
5. UI tab `Users` в `TenantDetailPage`.

## Classification

- Project: Flexity
- Category: platform_core
- Risk: medium
- Plan type: implementation plan (pre-code)

## Scope

### Files to modify (backend)

- `backend/app/modules/tenants/routes.py`
- `backend/app/modules/tenants/service.py`
- `backend/app/modules/tenants/schemas.py`
- `backend/app/modules/tenants/repository.py`
- `backend/app/modules/auth/service.py` (только если invite/create/reset логичнее разместить здесь)
- `backend/app/modules/auth/schemas.py` (если используются auth DTO для invite/reset)
- `backend/app/api/v1/router.py` (только если появится новый router)

### Files to modify (frontend)

- `platform-console/src/pages/TenantDetailPage.tsx`
- `platform-console/src/api/tenants.ts`
- `platform-console/src/types/tenant.ts`
- `platform-console/src/types/auth.ts` (если нужны новые DTO)
- `platform-console/src/components/ui/*` (только при необходимости формы/модалки)

### Files not to touch

- `deploy/**`
- nginx/system configs
- migrations/alembic файлы
- `backend/app/main.py` (seed/deploy lifecycle)
- tenant customization roadmap files
- legacy repos (`Trailers`, `flexity_admin`, `Consulting Flask`)

## Steps

1. **Backend memberships list**
   - Добавить `GET /tenants/{tenant_id}/memberships`.
   - Вернуть: membership id, role, is_active, created_at + user summary (email, full_name, is_active).
   - Доступ: только provider staff своего provider или authorized tenant owner по текущим правилам.

2. **Backend add existing user**
   - Расширить add-member flow: поддержать добавление existing user по email (в дополнение к `user_id`), чтобы UI мог работать без ручного UUID.
   - Сохранить idempotent поведение: без дубликатов membership, понятная ошибка на conflict.

3. **Backend invite/create tenant user**
   - Добавить минимальный endpoint для создания user и сразу membership в tenant (owner/admin/member role).
   - Проверить, что email уникален, user активен после создания.
   - Без изменения широкой auth архитектуры и без новых зависимостей.

4. **Backend safe password reset**
   - Добавить provider-owner protected endpoint reset password для конкретного user в tenant scope.
   - Правила: min length, hash через `hash_password`, audit event, без возврата hash/token/secrets.

5. **Frontend Users tab**
   - Добавить tab `Users` в `TenantDetailPage`.
   - Реализовать:
     - список memberships;
     - add existing user (email + role);
     - invite/create user (email/full_name/role);
     - reset password action (controlled form, без отображения секретов).
   - Переиспользовать текущие `Alert`, `Table`, `Input`, `Select`, `Button`.

6. **Validation and hardening**
   - Проверить права доступа и ошибки `403/404/409`.
   - Проверить, что существующие tabs (`Modules`, `Subscription`, `Apply Template`) не ломаются.

## Migrations

- Не требуются для Track A (используем текущие таблицы `users`, `user_tenant_memberships`, `provider_staff`).

## Tests/checks

### Backend

- Unit/integration tests для:
  - list memberships;
  - add existing user by email;
  - invite/create user + membership;
  - reset password permission and validation.
- Negative cases:
  - user not found;
  - tenant not found;
  - cross-provider access denied;
  - duplicate membership conflict;
  - short password.

### Frontend

- Smoke checks:
  - `TenantDetailPage` -> tab `Users` loads list.
  - Add existing user updates table.
  - Invite/create user shows success and row appears.
  - Reset password action returns success message without leaks.

### Manual QA (production-safe, no deploy actions in plan stage)

- Проверить, что `auth/me` после login показывает tenant membership.
- Проверить, что user может видеть `test-kindergarten` после назначения.

## Risks

- Неправильный permission scope может дать доступ к чужим tenant.
- Ошибка в reset flow может повлиять на login пользователей.
- UI complexity в одном tab может привести к confusing states без четкой индикации ошибок.

## Rollback

- Backend rollback: откатить новые endpoints/DTO до предыдущего состояния.
- Frontend rollback: убрать tab `Users` и связанные API вызовы.
- Data rollback: для ошибочно созданных memberships/users только отдельной approved admin процедурой (без destructive mass ops).

## Approval

Status: waiting for approval

## Task classification block

1. Project: Flexity
2. Category: platform_core
3. Risk level: medium
4. Intended scope: `backend/app/modules/tenants/*`, `backend/app/modules/auth/*` (точечно), `platform-console/src/pages/TenantDetailPage.tsx`, `platform-console/src/api/tenants.ts`, связанные типы
5. Forbidden scope: deploy/nginx/migrations, tenant customization, legacy Flask repos
6. Required plan: implementation plan
