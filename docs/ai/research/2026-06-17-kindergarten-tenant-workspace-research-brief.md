# Research Brief: kindergarten tenant workspace MVP

## Context

- Проект: Flexity.
- Тип задачи: read-only исследование следующего этапа после стабилизации Platform Console.
- Текущий факт: Platform Console уже работает как provider-owner панель, tenant `ИП АЗМИНА` создан и обслуживается через `/console`.
- Цель исследования: определить минимальный tenant-facing workspace для `kindergarten_basic` (рабочий интерфейс клиента, а не провайдерская админка платформы).

## Current state

### 1) Разница Platform Console vs tenant workspace

- **Platform Console (`/console`)** сейчас реализован как провайдерская панель:
  - роуты: `/tenants`, `/tenants/new`, `/tenants/:tenantId`;
  - доступ через `ProtectedRoute` и проверку `isProviderOwner`;
  - sidebar содержит только раздел `Tenants`.
- **Tenant workspace** в текущем UI отсутствует:
  - нет отдельного tenant shell;
  - нет tenant menu (children/parents/invoices/documents/crm);
  - нет dedicated tenant login-landing/entry flow.

Итог: `/console` = control plane (управление tenant-ами), а tenant workspace должен быть data plane (операционная работа внутри конкретного tenant).

### 2) Текущая модель доступа backend

- `auth/me` уже возвращает:
  - `provider` (provider staff info),
  - `tenants` (tenant memberships).
- Tenant контекст формируется через:
  - `tenant_id` в path **или**
  - `X-Tenant-ID` header.
- Модульные API защищены через `require_module("...")` + tenant context.

Это уже достаточная основа для tenant workspace без архитектурного рефакторинга auth.

## Recommended URL structure

## Option A (рекомендуется для MVP, быстрее и безопаснее)

- Оставить один SPA домен и base:
  - `/console` — provider owner control plane
  - `/workspace/:tenantSlug/*` — tenant workspace

Плюсы:
- без нового deploy topology и nginx/subdomain работы;
- переиспользование текущего auth/token слоя;
- быстрый запуск MVP.

## Option B (позже, не для первого шага)

- Отдельный subdomain для tenant app, например `app.flexity.asia` или `tenant.flexity.asia`.

Минусы на текущем этапе:
- дополнительная инфраструктурная сложность;
- больше рисков и DevOps работ.

## Recommended navigation flow for tenant_owner

1. Пользователь логинится.
2. Backend возвращает memberships (`auth/me.tenants`).
3. Если пользователь provider owner -> может попасть в `/console`.
4. Если пользователь tenant owner/admin/member -> должен попадать в `/workspace/:tenantSlug`.
5. В tenant workspace при каждом API вызове передаётся tenant context (`X-Tenant-ID` или tenant_id в пути).

Примечание: текущий frontend guard жёстко ориентирован на `provider_owner`; для tenant workspace понадобится отдельный guard на `me.tenants.length > 0`.

## Existing backend APIs usable for first tenant UI

## CRM / workflows

- `/pipelines` (list/create/get/update)
- `/work-items` (list/create/get/update/delete)
- `/work-items/{id}/move-stage`
- `/work-items/{id}/activities`
- `/work-items/{id}/tasks`

## Parties (дети/родители)

- `/parties` (list/create/get/update/delete)
- `/parties/custom-field-definitions`
- Поддержка `party_role` в schema/metadata (enrollee/guardian можно моделировать уже сейчас).

## Catalog (услуги/тарифы)

- `/catalog/items`
- `/catalog/price-lists`
- `/catalog/units`

## Documents (договоры/заявления)

- `/document-templates`
- `/documents`
- `/documents/generate`
- `/documents/{id}/send-for-signature`
- `/documents/{id}/upload-signed-file`

## Finance (счета/оплаты)

- `/finance/invoices`
- `/finance/payments`
- `/finance/receivables`
- `/finance/summary`

## Template-related

- `kindergarten_basic` в seed уже содержит:
  - роли tenant (`tenant_owner`, `tenant_admin`, `member`);
  - enrollment pipeline;
  - custom fields для enrollee/guardian;
  - document templates (contract/application);
  - catalog items (subscription/fees).

## Missing APIs / gaps for smooth tenant MVP

1. Нет tenant-workspace specific frontend routes/guards (UI gap, не backend).
2. Нет готового “tenant dashboard aggregate” endpoint (можно стартовать с compose на frontend из `/finance/summary`, `/work-items`, `/receivables`).
3. Нет явного backend endpoint для “child-guardian relation graph” (связь можно временно держать через metadata/custom fields, но для production UX позже нужен явный relation model/API).
4. Нет tenant-oriented access profile endpoint (например `GET /workspace/me` с выбранным tenant контекстом и разрешениями по модулю).
5. Нет специализированных kindergarten read-model endpoints (например “enrollees list with guardian+balance+contract status” в одном ответе) — для MVP можно начать с нескольких базовых вызовов.

## MVP screens for kindergarten tenant workspace

1. **Dashboard**
   - KPI: open enrollment items, overdue invoices, this month payments, contracts pending signature.
   - Источники: `/work-items`, `/finance/summary`, `/finance/receivables`, `/documents`.

2. **Children / Enrollees**
   - Таблица детей (роль enrollee), быстрый просмотр custom fields (birth_date, group, start_date).
   - CRUD через `/parties`.

3. **Parents / Guardians**
   - Таблица родителей (роль guardian), контакты, relationship.
   - CRUD через `/parties`.

4. **Services / Catalog**
   - Список услуг и сборов (`subscription_service`, `fee`).
   - CRUD через `/catalog/items`, опционально price-lists.

5. **Invoices / Payments**
   - Счета, оплаты, аллокация, просрочки.
   - `/finance/invoices`, `/finance/payments`, `/finance/receivables`.

6. **Documents / Contracts**
   - Список шаблонов и документов, генерация договора/заявления, статусы подписи.
   - `/document-templates`, `/documents`, `/documents/generate`.

## Recommended implementation stages (после этого research)

### Stage W1: Tenant app shell and routing
- Добавить tenant workspace routes и отдельный layout.
- Добавить tenant-aware guard (membership-based).
- Добавить tenant selector logic на основе `auth/me.tenants`.

### Stage W2: Read-only MVP data screens
- Dashboard (read-only aggregates).
- Lists: enrollees, guardians, invoices, documents.
- Без сложных транзакционных действий на первом шаге.

### Stage W3: Core operations
- Create/update parties (children/guardians).
- Generate contract/application.
- Create invoice/payment + allocate payment.

### Stage W4: Kindergarten UX hardening
- Унифицированные карточки ребёнок+родитель+договор+баланс.
- Ролевые ограничения внутри tenant (`tenant_owner/admin/member`).
- Улучшенные read-model endpoints при необходимости.

## Risks

1. Смешение control plane (`/console`) и tenant workspace без чётких guard-правил.
2. Утечки tenant контекста при отсутствии обязательного `tenant_id`/`X-Tenant-ID` в frontend API-слое workspace.
3. Переусложнение MVP (попытка сразу делать full ERP вместо операционного детсад-сценария).
4. Преждевременная реализация tenant customization layer (сейчас это CR, не implementation scope).
5. Слишком ранний переход к отдельному subdomain без необходимости.

## What not to build yet

- Отдельный новый Flask/legacy проект для детского сада.
- Новый параллельный auth механизм.
- Tenant customization layer implementation (до отдельного approved plan).
- Глубокий рефакторинг backend модулей под kindergarten package.
- Deploy/infrastructure изменения в рамках исследовательного этапа.

## Recommendation

- Для следующего шага подготовить отдельный **implementation plan** на Stage W1 (tenant workspace shell + routing + guard + базовый tenant context adapter), без изменений в production deploy process и без миграций.
- Держать `/console` как provider-owner control plane и вводить `/workspace/:tenantSlug` как tenant operating plane.

## Final checks

- No code changes in backend/frontend modules.
- No migrations.
- No deploy.
- No nginx/system changes.
- No production DB/auth mutations.
