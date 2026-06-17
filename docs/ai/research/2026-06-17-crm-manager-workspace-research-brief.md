# Research Brief: CRM manager workspace (W2 reframe)

## Classification

- **Project:** Flexity
- **Category:** universal_module (`workflows`/CRM, `parties`, `documents`, `finance`) + industry_template (`kindergarten_basic` labels/pipeline)
- **Mode:** research only — no code, no deploy, no migrations
- **Risk level:** medium

## Context

После Stage W1 в production развёрнут **tenant workspace shell** (`/console/workspace/:tenantSlug/*`) с placeholder-навигацией: Dashboard, Children, Parents, Services, Invoices, Documents.

**Направление W2 меняется:** не «справочник детей» (Children-first), а **рабочее место менеджера** на универсальном CRM/workflows с отраслевыми подписями из `kindergarten_basic`.

Целевой пользователь: `tenant_owner` / `tenant_admin` / `member` детского сада (и в будущем — consulting_basic с другими labels).

## Product direction (manager workspace)

1. **Dashboard** — входящие лиды/заявки, активные сделки по воронке, задачи и следующие действия, оплаты и долги.
2. **CRM Pipeline** — лиды/заявки, сделка (`work_item`), статусы воронки, ответственный, следующий шаг.
3. **Client card** — контакт/родитель/компания через `parties`; дети/получатели услуги — как `party_role`/relationship, не как главный первый экран.
4. **Documents** — договор, КП/заявка; акт/отчёт — позже.
5. **Finance** — счёт, оплата, долг.
6. **Industry labels** — не отдельная kindergarten CRM, а конфигурация template:
   - `kindergarten_basic`: «Заявка», «Родитель», «Ребёнок», «Договор», «Абонемент»
   - `consulting_basic` (позже): «Лид», «Клиент», «Проект», «КП», «Договор»

## Current state

### W1 workspace shell (deployed)

- Routes: `/console/workspace/:tenantSlug/{section}`
- Guard: membership + provider_owner fallback (`TenantWorkspaceGuard`)
- Context: `TenantWorkspaceContext` из `auth/me` + slug
- Sidebar (placeholder): Dashboard, Children, Parents, Services, Invoices, Documents
- API client: **ещё нет** обязательного `X-Tenant-ID` для workspace-запросов
- Labels API: **не подключён** во frontend workspace

**Файлы shell:** `platform-console/src/components/layout/Workspace*.tsx`, `platform-console/src/auth/TenantWorkspace*.tsx`, `platform-console/src/routes.tsx`.

### Архитектурная позиция Flexity

Универсальные модули уже задекларированы в `docs/ai/PRODUCT_ARCHITECTURE.md`:

- `workflows` / CRM → pipelines, work items, tasks, activities
- `parties` → контрагенты, роли, custom fields
- `documents`, `finance`, `catalog`

Детский сад — **tenant + `kindergarten_basic` template**, не отдельное Flask-приложение и не отдельный kindergarten CRM.

Tenant customization (редактирование labels клиентом) — **CR-2026-06-05-001**, не implementation scope W2.

---

## Backend API map (existing)

Базовый префикс: `/api/v1`. Tenant context: header `X-Tenant-ID` или `tenant_id` в path (см. `backend/app/core/tenancy.py`).

### CRM / workflows (`require_module("crm")`)

| Method | Path | Назначение для manager workspace |
|--------|------|----------------------------------|
| GET | `/pipelines` | Воронки и стадии (kanban columns) |
| GET | `/pipelines/{id}` | Детали воронки |
| GET | `/work-items` | Список заявок/сделок (`pipeline_id`, `stage_id`, `status`, `work_item_type`, `search`) |
| POST | `/work-items` | Создание заявки (W3+) |
| GET | `/work-items/{id}` | Карточка сделки |
| PATCH | `/work-items/{id}` | Обновление |
| POST | `/work-items/{id}/move-stage` | Перемещение по воронке (W3+) |
| POST | `/work-items/{id}/activities` | Запись активности |
| POST | `/work-items/{id}/tasks` | Создание задачи |

**Модель:** единая сущность `WorkItem` — нет отдельных таблиц Lead/Deal. Тип задаётся `work_item_type` + pipeline.

**Файлы:** `backend/app/modules/workflows/routes.py`, `models.py`, `schemas.py`, `service.py`.

### Parties (`require_module("parties")`)

| Method | Path | Назначение |
|--------|------|------------|
| GET | `/parties` | Список (`party_type`, `status`, `search`) |
| POST/PATCH/DELETE | `/parties` | CRUD (W3+) |
| GET | `/parties/{id}` | Карточка клиента |
| GET | `/parties/custom-field-definitions` | Поля по `entity_type` / `party_role` |

`party_role` (enrollee/guardian/staff) хранится в `metadata_json`, не как отдельная колонка.

**Файлы:** `backend/app/modules/parties/*`.

### Documents (`require_module("documents")`)

| Method | Path | Назначение |
|--------|------|------------|
| GET | `/document-templates` | Шаблоны (договор, заявление) |
| GET | `/documents` | Список (`status` only) |
| POST | `/documents/generate` | Генерация (W3+) |
| GET | `/documents/{id}` | Детали |

Связи: `party_id`, `work_item_id` на `DocumentInstance`.

**Файлы:** `backend/app/modules/documents/*`.

### Finance (`require_module("finance")`)

| Method | Path | Назначение |
|--------|------|------------|
| GET | `/finance/summary` | KPI dashboard |
| GET | `/finance/receivables` | Долги |
| GET | `/finance/invoices` | Счета (`party_id` filter **есть**) |
| GET | `/finance/payments` | Оплаты (`party_id` filter **есть**) |

**Файлы:** `backend/app/modules/finance/*`.

### Catalog (`require_module("catalog")`)

| Method | Path | Назначение |
|--------|------|------------|
| GET | `/catalog/items` | Услуги/абонементы (вторично для W2 CRM) |

Не главный экран менеджера на W2; используется в карточке сделки/счёта позже.

### Industry labels

| Method | Path | Назначение |
|--------|------|------------|
| GET | `/tenants/{tenant_id}/labels` | `labels_config` tenant (из template apply) |

**Файл:** `backend/app/modules/industry_templates/routes.py`  
**Seed:** `backend/app/modules/industry_templates/seed.py` → `kindergarten_basic.labels_config`

Пример labels для kindergarten:

```json
{
  "entities": {
    "work_item": "Заявка",
    "party": "Контрагент",
    "invoice": "Счёт",
    "payment": "Оплата",
    "pipeline": "Воронка поступления"
  },
  "party_roles": {
    "enrollee": "Ребёнок",
    "guardian": "Родитель",
    "staff": "Сотрудник"
  },
  "catalog_item_types": {
    "subscription_service": "Абонемент",
    "fee": "Сбор"
  }
}
```

---

## What exists vs what is missing (for CRM manager W2)

### Достаточно для read-only W2 (с оговорками)

| Capability | API | Оговорка |
|------------|-----|----------|
| Список заявок по воронке | `GET /pipelines` + `GET /work-items?pipeline_id=` | Kanban собирается на frontend |
| Dashboard KPI (финансы) | `GET /finance/summary`, `/finance/receivables` | Нет CRM KPI aggregate |
| Список клиентов | `GET /parties` | Фильтр `party_role` только client-side |
| Счета/оплаты клиента | `GET /finance/invoices?party_id=` | OK |
| Отраслевые подписи | `GET /tenants/{id}/labels` | Read-only; PATCH labels — не в scope |

### Пробелы (мешают полноценному manager UX)

| Gap | Impact | W2 mitigation |
|-----|--------|---------------|
| `WorkItemResponse` не включает `activities`, `tasks` | Нет таймлайна/задач на карточке сделки | **Mini backend:** расширить detail response или list endpoints |
| Нет `GET .../activities`, `GET .../tasks` | Dashboard «следующие действия» слабый | То же |
| Нет `primary_party_id` в `GET /work-items` | Client card: сделки клиента — N+1 или client filter | **Mini backend:** query filter |
| Нет `party_id` в `GET /documents` | Документы клиента — client filter all docs | **Mini backend:** query filter |
| Нет `party_role` в `GET /parties` | Смешение ролей в списке | Client-side filter по `metadata_json.party_role` |
| Нет child↔guardian relation API | Связь только через metadata/custom fields | W2: показать роли отдельными строками; relation graph — W3+ |
| Нет `GET /workspace/dashboard` aggregate | Много параллельных запросов | W2: frontend compose; aggregate endpoint — опционально W2.1 |
| Нет assignee на work item | «Ответственный менеджер» | `created_by_user_id` / participant `assignee`; membership users list — нет tenant user API |
| Note/Reminder models без API | Напоминания | Out of W2 |

### Рекомендация по backend для W2

- **Минимальный обязательный шаг (если approval):** точечные read-only расширения без миграций:
  1. `GET /work-items?primary_party_id=`
  2. `GET /parties?party_role=`
  3. `GET /documents?party_id=`
  4. `WorkItemDetailResponse` = `WorkItemResponse` + `activities[]` + `tasks[]` + embedded `stage` name (или отдельные GET list)
- **Не делать:** новый kindergarten CRM модуль, новые таблицы Lead/Deal, tenant customization PATCH.

---

## kindergarten_basic → CRM manager flow

### Pipeline (уже в seed)

Воронка `enrollment` («Воронка поступления»):

`new_lead` → `first_contact` → `tour` → `awaiting_documents` → `contract_draft` → `contract_signed` → `payment_received` → `enrolled` | `lost`

В UI менеджера:

- **Pipeline screen** = board/list по стадиям; сущность в labels = «Заявка» (`work_item`).
- **Lead** = `WorkItem` в ранних стадиях (`new_lead`, `first_contact`, …).
- **Deal/opportunity** = тот же `WorkItem` в активных/поздних стадиях до `enrolled`/`lost`.

### Parties roles (не отдельные экраны первого уровня)

| Роль | Label | Роль в CRM flow |
|------|-------|-----------------|
| `guardian` | Родитель | **Primary client** на заявке (`primary_party_id`, participant `client`) |
| `enrollee` | Ребёнок | Получатель услуги, блок в client/deal card |
| `staff` | Сотрудник | Позже |

### Documents & finance в сценарии поступления

1. Заявка (`work_item`) создана на родителя.
2. Документы: `enrollment_application`, `parent_contract` из seed templates.
3. Счёт/оплата: `finance/invoices` + `payments` после стадии `payment_received`.

### Catalog

`edu-monthly`, `registration-fee`, `enrollment-fee` — подписи «Абонемент»/«Сбор»; не отдельный пункт меню W2.

---

## Consulting Flask — только reference

**Проект:** `flexity_admin` (Consulting OS), не целевая платформа.

Использовать **только для извлечения процесса**, не для копирования кода:

| Consulting (reference) | Flexity (target) |
|------------------------|------------------|
| Lead + manager | `WorkItem` + participant `assignee` / `created_by_user_id` |
| Order / project stage | `WorkItem` + `pipeline` stages |
| Client card | `Party` + связанные work items, invoices, documents |
| Tasks on lead/order | `Task` on `WorkItem` |
| Manager visibility rules | Tenant RBAC (позже); W2 — без сложного row-level security |

Из `docs/planning/TZ_CONSULTING_OS.md`: привязка договора к заказу, задачи к lead/stage, комиссии менеджера — **универсальные паттерны**, реализация во Flexity modules.

**Запрещено в W2:** переносить Flask routes/models, дублировать CRM вне `workflows`.

---

## Recommended first screen & navigation (W2)

### Первый экран после login в workspace

**Dashboard (manager cockpit)** — не Children.

Блоки (read-only W2):

1. Новые заявки (`work-items` в стадиях `new_lead`, `first_contact`)
2. Активные сделки (не terminal stages)
3. Просроченные/открытые receivables
4. Документы на подпись (filter `status` client-side)
5. Ближайшие задачи (если backend отдаёт tasks)

### Навигация workspace (замена W1 placeholders)

| Route segment | UI label (EN dev / RU via labels) | Содержание |
|---------------|-----------------------------------|------------|
| `dashboard` | Dashboard | Manager cockpit |
| `pipeline` | Pipeline / «Воронка» | Board/list work items |
| `clients` | Clients / «Контрагенты» | Parties list (guardian-first sort/filter) |
| `documents` | Documents | Tenant documents list |
| `finance` | Finance | Invoices + receivables summary |

**Убрать с верхнего уровня W2:**

- `children`, `parents` → внутрь **client card** / deal card как role sections
- `services` → catalog admin позже (не manager W2)
- `invoices` как отдельный пункт → объединить в `finance`

Labels в sidebar: `GET /tenants/{tenant_id}/labels` + fallback English keys.

---

## Risks

1. **Children-first regression** — если оставить старую навигацию, продукт уйдёт в ERP-справочник вместо CRM.
2. **Отсутствие `X-Tenant-ID`** — риск wrong-tenant или 403 при вызовах module API из workspace.
3. **Frontend-only фильтрация** — performance/UX при росте данных; точечные backend filters предпочтительны.
4. **Смешение AI tasks (`/ai/tasks`) и CRM tasks** — не использовать AI tasks в manager dashboard.
5. **Tenant customization** — не реализовывать редактирование labels в W2 (только read from template).
6. **Преждевременный kanban DnD** — W2 read-only; move-stage в W3.

---

## What not to build in W2

- Отдельный kindergarten CRM пакет или Flask app
- Children/Parents как главные list-экраны
- CRUD заявок, генерация документов, оплаты (это W3)
- Tenant customization layer (CR)
- Миграции, новые сущности Lead/Deal
- Deploy/nginx changes в research scope
- Relation graph API (child↔guardian) — отложить

---

## Recommendation

1. Утвердить W2 как **CRM manager workspace (read-only)** на универсальных модулях.
2. Подготовить implementation plan (`docs/ai/plans/2026-06-17-crm-manager-workspace-w2-plan.md`).
3. Первый implementation slice после approval:
   - `X-Tenant-ID` + labels hook
   - перестройка sidebar/routes
   - Dashboard compose
   - Pipeline list (read-only)
4. Опциональный mini-backend slice — только query filters + work item detail with tasks/activities (без миграций).

---

## Final checks

- No code changes in this task.
- No migrations, deploy, nginx, prod DB.
- No legacy Flask edits.
- No tenant customization implementation.
