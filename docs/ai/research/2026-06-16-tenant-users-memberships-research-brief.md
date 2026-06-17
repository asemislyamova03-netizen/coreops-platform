# Research Brief: Track A tenant users and memberships in Platform Console

## Context

- Задача: убрать ручные SQL-операции по назначению пользователей в tenant и дать управляемый UI в Platform Console.
- Проект: Flexity.
- Статус: read-only анализ, без code changes.
- Входной контекст: console и provider owner уже работают, tenant `ИП АЗМИНА` существует, `tenant_owner` назначался вручную.

## Current state

- Backend уже имеет создание membership через `POST /tenants/{tenant_id}/memberships`, но только по `user_id`.
- Backend не имеет endpoint для просмотра memberships tenant (`GET /tenants/{tenant_id}/memberships` отсутствует).
- Backend не имеет отдельного users API для поиска/создания пользователя из superadmin tenant flow.
- Backend auth содержит только bootstrap register/login/refresh/me; invite/create user и password reset endpoint отсутствуют.
- `auth/me` уже возвращает список доступных tenant memberships пользователя.
- Frontend `TenantDetailPage` имеет табы `Info`, `Modules`, `Subscription`, `Labels`, `Apply Template`; таба `Users` нет.
- Frontend API слой не содержит функций для memberships/users/password reset.

## Relevant files

### Backend inspected

- `backend/app/api/v1/router.py`
- `backend/app/modules/tenants/routes.py`
- `backend/app/modules/tenants/service.py`
- `backend/app/modules/tenants/repository.py`
- `backend/app/modules/tenants/schemas.py`
- `backend/app/modules/tenants/models.py`
- `backend/app/modules/auth/routes.py`
- `backend/app/modules/auth/service.py`
- `backend/app/modules/auth/schemas.py`
- `backend/app/modules/auth/models.py`
- `backend/app/modules/provider/models.py`
- `backend/app/main.py`

### Frontend inspected

- `platform-console/src/pages/TenantDetailPage.tsx`
- `platform-console/src/pages/TenantCreatePage.tsx`
- `platform-console/src/api/tenants.ts`
- `platform-console/src/auth/AuthContext.tsx`
- `platform-console/src/types/auth.ts`
- `platform-console/src/types/tenant.ts`

## Architecture classification

- Project: Flexity
- Primary category: platform_core
- Architecture layer: Flexity Core + universal auth/tenants flows
- Risk level: medium

## Risks

- Риск размывания auth архитектуры, если добавить invite/reset без явного provider scope и audit.
- Риск скрытой эскалации прав, если membership endpoints не проверяют принадлежность user к provider company.
- Риск дублирования users логики между tenants и auth, если сделать endpoints в разных стилях.
- Риск нестабильного UX, если добавить UI tab без server-side search/filter и без четких ошибок конфликтов.
- Риск несовместимости enum-ролей (строковый формат в API vs enum storage в БД) при ручной сериализации.

## Constraints

- Не трогать deploy/nginx.
- Не делать migrations без отдельного approval.
- Не делать широкий рефакторинг auth architecture.
- Не делать tenant customization.
- Не трогать Flask legacy проекты.
- Минимальный Track A, ориентированный на superadmin/provider_owner flow.

## Recommendation

- Реализовать минимальный Track A поэтапно:
  1. `GET /tenants/{tenant_id}/memberships` (read/list + базовые user fields).
  2. `POST /tenants/{tenant_id}/memberships` расширить вариантом `user_email` (или отдельным endpoint add-existing-by-email), чтобы убрать ручной SQL с UUID.
  3. Добавить controlled endpoint для invite/create tenant user (минимум: email, full_name, role, temp password policy/flow).
  4. Добавить безопасный password reset endpoint для provider_owner (server-side checks + audit event, без выдачи секретов).
  5. Добавить tab `Users` в `TenantDetailPage` для list/add/create/reset через новые API.

## Do not touch

- `deploy/`
- nginx/server config
- миграции и alembic scripts
- широкие изменения `auth` bootstrap логики
- tenant customization roadmap scope
- legacy `Trailers` / `Consulting` codebases

## Next safe step

- Подтвердить implementation plan для Track A.
- После approval: делать маленькими шагами сначала backend list/add-existing, затем invite/reset, затем frontend tab `Users`.

## Final checks

- No code changes.
- No migrations.
- No deploy.
- No destructive commands.
