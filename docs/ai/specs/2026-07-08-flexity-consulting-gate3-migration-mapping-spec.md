# Flexity Consulting Gate 3 Migration Mapping Spec (First Client)

**Дата:** 2026-07-08
**Статус:** documentation-only spec
**Режим:** no code / no migrations / no import / no production actions

---

## Task Classification

| Параметр | Значение |
|---|---|
| Project | Flexity |
| Category | documentation_only |
| Risk level | high (данные клиента + переход legacy -> Core) |
| Intended scope | migration mapping/spec + cleanup backlog |
| Forbidden scope | любые write-операции, import, export, deploy, restart |
| Required plan | этот Gate 3 spec + отдельный approval до любых действий |

---

## 1. Executive summary

- Legacy `/dashboard` остаётся в bridge-режиме на переходный период.
- Flexity Core является целевой платформой для первого подписочного Consulting клиента.
- Gate 3 — это только mapping/spec и backlog очистки, без импорта и без изменений прод-систем.
- В документе используются только имена полей, структурные правила и агрегатные выводы; бизнес-значения и персональные данные не включаются.

---

## 2. Source-to-target entity mapping

| Source table/entity | Source purpose | Target Flexity module/entity | Migration priority | Risk level | Notes |
|---|---|---|---|---|---|
| `legacy_db_scope` | Один клиент в одной SQLite БД | `tenants` (`tenant`) | required | high | Создать 1 tenant для first client |
| `branch (implicit)` | В legacy явной branch-модели нет | `branches` (`default_branch=main`) | required | medium | Применить E3a baseline |
| `users` | Пользователи legacy приложения | `auth/users` + memberships | required | medium | С маппингом ролей |
| `roles`, `user_roles` | Права/связи пользователей | `rbac/roles`, memberships | required | low | Проверка уникальности связок |
| `clients` | Клиенты/контакты | `parties/contacts` | required | high | PII-поля мигрируются только в tenant scope |
| `suppliers` | Контрагенты-поставщики | `parties` (supplier role) | optional | medium | Можно второй волной |
| `orders` | Сделки/кейсы/проекты | `crm/work_items` | required | high | Базовый бизнес-контур |
| `order_stages` | Этапы пайплайна | `crm/pipeline_stages` | required | high | Нужна нормализация `template_id` |
| `order_items` | Линии услуги в заказе | `crm/work_item_lines` + `catalog` link | required | medium | Проверить сервисные ссылки |
| `leads`, `lead_activities` | Лиды и активность | `crm/leads` + activities | optional | medium | Сейчас таблицы пустые |
| `consultation_bookings` | Записи консультаций | `crm/bookings` | archive | low | Сейчас пусто |
| `services` | Справочник услуг | `catalog/services` | required | medium | Импорт до work_items |
| `items`, `item_groups`, `units`, `nomenclature` | Доп. каталог | `catalog/*` | optional | low | Часть таблиц пустая |
| `contracts` | Договоры | `documents/contracts` | required | high | Есть `order_id NULL` и zero amount кейсы |
| `contract_templates` | Шаблоны договоров | `documents/templates` | optional | medium | Низкий объём |
| `acts` | Акты | `documents/acts` | optional | medium | Низкий объём |
| `document_requests` | Запросы документов | `documents/workflow_requests` | archive | low | Пусто |
| `payments` | Платежи (in/out) | `finance/payments` | required | high | Статусы/типы через mapping matrix |
| `payment_allocations` | Распределение платежей | `finance/payment_allocations` | optional | low | Сейчас пусто |
| `payment_methods` | Справочник методов оплаты | `finance/ref/payment_methods` | required | low | Справочник до платежей |
| `payment_operation_types` | Типы операций | `finance/ref/operation_types` | required | low | Справочник до платежей |
| `dds_kinds`, `income_kinds`, `expense_kinds`, `expense_categories` | Финансовые классификаторы | `finance/ref/*` | required | medium | Нужна единая Core taxonomy |
| `cashflow_plans` | План-факт cashflow | `finance/cashflow_plans` | skip | low | Таблица пустая |
| `number_sequences` | Нумераторы документов | `core/numbering` | optional | low | Можно инициализировать заново |
| `activity_logs` | Legacy события | `audit/import_logs` | required | medium | Как migration telemetry, не бизнес-истина |
| `external_*`, `message_*`, `integration_accounts`, `portal_accounts`, `webhook_events` | Интеграционные контуры | `integrations/*` | archive | medium | Late-phase или archive-only |
| `alembic_version` | Техническая мета | skip | skip | Не мигрируется как бизнес-данные |
| `subscription (implicit)` | В legacy нет устойчивой модели тарифа | `subscriptions/tariffs` | required | medium | Тариф задаётся в Core напрямую |

---

## 3. Field-by-field mapping tables

### 3.1 Tenant / branch bootstrap (system mapping)

| Source field | Target field | Transform rule | Required cleanup | Nullable allowed | Default if missing | Validation rule | Risk |
|---|---|---|---|---|---|---|---|
| `legacy_db_id` (technical) | `tenants.slug` | derive slug by approved naming policy | проверить уникальность slug | no | n/a | unique slug | medium |
| `legacy_db_scope` | `tenants.name` | assign approved tenant display name | стандартизировать имя | no | n/a | not empty | low |
| `branch (not present)` | `tenants.default_branch_id` | create branch first, then set FK | нет | no | create `main` | FK exists | low |
| `branch (not present)` | `branches.code` | static bootstrap value | нет | no | `main` | unique per tenant | low |
| `branch (not present)` | `branches.name` | static bootstrap label | нет | no | `Main branch` | not empty | low |

### 3.2 Users / roles

| Source field | Target field | Transform rule | Required cleanup | Nullable allowed | Default if missing | Validation rule | Risk |
|---|---|---|---|---|---|---|---|
| `users.id` | `users.external_legacy_id` | preserve as source reference | удалить пробелы/мусор | no | n/a | unique per tenant import batch | low |
| `users.username`/`login` (if present) | `users.login` | lowercase + trim | deduplicate collisions | no | generate placeholder + manual review | unique login | medium |
| `users.email` (if present) | `users.email` | lowercase + trim | format check | yes | null | email format | medium |
| `users.phone` (if present) | `users.phone` | normalize to canonical format | format cleanup | yes | null | phone pattern | medium |
| `users.is_active` (if present) | `users.is_active` | map bool-like values | normalize non-bool | no | `true` | boolean | low |
| `user_roles.role_id` | `user_memberships.role_id` | map legacy role -> Core role dictionary | unmapped role backlog | no | fallback `operator` (manual confirm) | role exists | medium |

### 3.3 Parties / contacts (`clients`, `suppliers`)

| Source field | Target field | Transform rule | Required cleanup | Nullable allowed | Default if missing | Validation rule | Risk |
|---|---|---|---|---|---|---|---|
| `clients.id` | `parties.external_legacy_id` | preserve source key | none | no | n/a | unique per tenant | low |
| `clients.party_type` | `parties.party_kind` | map `PERSON/BUSINESS` -> Core enum | map unknown values | no | `person` | enum membership | medium |
| `clients.status` | `parties.status` | map legacy status -> Core status | inconsistent status mapping | no | `active` (manual check) | enum membership | high |
| `clients.name` / business name | `parties.display_name` | trim, normalize whitespace | empty-name queue | no | `Unnamed party` + manual | length > 0 | high |
| `clients.phone` | `contacts.phone` | normalize format | invalid phone cleanup | yes | null | format rule | high |
| `clients.email` | `contacts.email` | lowercase + trim | invalid email cleanup | yes | null | format rule | high |
| `clients.iin_bin` | `parties.tax_id` | normalize chars only | invalid length review | yes | null | country-specific length/pattern | high |
| `suppliers.*` core identity fields | `parties` (supplier role) | same as clients mapping | deduplicate by safe keys | yes | null | role + identity consistency | medium |

### 3.4 CRM pipeline/work items (`orders`, `order_stages`, `order_items`)

| Source field | Target field | Transform rule | Required cleanup | Nullable allowed | Default if missing | Validation rule | Risk |
|---|---|---|---|---|---|---|---|
| `orders.id` | `work_items.external_legacy_id` | preserve key | none | no | n/a | unique per tenant | low |
| `orders.number` | `work_items.code` | trim, keep legacy number | dedupe check (currently 0 dup groups) | no | auto sequence | unique code per tenant | medium |
| `orders.client_id` | `work_items.party_id` | FK map via `clients.id -> parties.id` | missing party references | no | n/a | FK exists | high |
| `orders.status` | `work_items.status` | map via status matrix | unknown statuses queue | no | `open` | enum membership | high |
| `orders.executor_user_id` | `work_items.owner_user_id` | FK map users | null executor policy | yes | tenant default owner | FK exists if not null | medium |
| `order_stages.order_id` | `work_item_stages.work_item_id` | FK map orders | none (orphans not found) | no | n/a | FK exists | medium |
| `order_stages.status` | `work_item_stages.status` | map via stage matrix | unknown statuses queue | no | `not_started` | enum membership | medium |
| `order_stages.template_id` | `work_item_stages.template_id` | map if available; else fallback default template | **37 NULL cleanup** | yes (temporary) | default template per service | template exists or fallback noted | high |
| `order_items.order_id` | `work_item_lines.work_item_id` | FK map orders | none | no | n/a | FK exists | medium |
| `order_items.service_id` | `work_item_lines.service_id` | FK map services | missing service mapping | no | fallback `legacy_service_unknown` | FK exists | high |
| `order_items.amount/price` (if present) | `work_item_lines.amount` | numeric cast | negative/zero policy | yes | `0` | numeric >= 0 by policy | medium |

### 3.5 Catalog/services (`services` + refs)

| Source field | Target field | Transform rule | Required cleanup | Nullable allowed | Default if missing | Validation rule | Risk |
|---|---|---|---|---|---|---|---|
| `services.id` | `catalog_services.external_legacy_id` | preserve key | none | no | n/a | unique per tenant | low |
| `services.name` | `catalog_services.name` | trim + normalize spaces | empty names queue | no | `Legacy service` + manual | length > 0 | medium |
| `services.status` (if present) | `catalog_services.status` | map to Core enum | unknown statuses | yes | `active` | enum membership | medium |
| `item_groups.id/parent_id` | `catalog_groups.*` | map hierarchy | broken parent links | yes | null parent | no self-loop | low |
| `units.id/name` | `catalog_units.*` | dictionary transfer | dedupe by code/name | yes | system default unit | unique code | low |

### 3.6 Contracts/documents (`contracts`, `acts`)

| Source field | Target field | Transform rule | Required cleanup | Nullable allowed | Default if missing | Validation rule | Risk |
|---|---|---|---|---|---|---|---|
| `contracts.id` | `documents.external_legacy_id` | preserve key | none | no | n/a | unique per tenant | low |
| `contracts.number` | `documents.number` | trim | dedupe check (currently no dup groups) | no | auto generated number | unique by doc type | medium |
| `contracts.client_id` | `documents.party_id` | FK map via parties | missing party references | no | n/a | FK exists | high |
| `contracts.order_id` | `documents.work_item_id` | FK map where available | **10 NULL -> manual/auto rule** | yes (temporary) | null + review tag | if null then review required | high |
| `contracts.service_id` | `documents.service_id` | FK map services | missing service mapping | yes | null | FK exists if not null | medium |
| `contracts.status` | `documents.status` | map by matrix | unknown status handling | no | `draft` | enum membership | high |
| `contracts.amount` | `documents.total_amount` | numeric cast | **3 zero amounts policy** | no | `0` + review flag | numeric >= 0 | high |
| `acts.id` | `documents.external_legacy_id` (type=act) | preserve key | none | no | n/a | unique per tenant/type | low |
| `acts.order_id` | `documents.work_item_id` | FK map orders | missing links | yes | null | FK exists if not null | medium |

### 3.7 Finance/payments/debts (`payments` + refs)

| Source field | Target field | Transform rule | Required cleanup | Nullable allowed | Default if missing | Validation rule | Risk |
|---|---|---|---|---|---|---|---|
| `payments.id` | `finance_payments.external_legacy_id` | preserve key | none | no | n/a | unique per tenant | low |
| `payments.type` | `finance_payments.direction` | map `INCOME/EXPENSE` -> Core enum | unknown type queue | no | reject row + manual | enum membership | high |
| `payments.amount` | `finance_payments.amount` | decimal cast | enforce non-negative | no | n/a | amount >= 0 | high |
| `payments.payment_date` | `finance_payments.payment_date` | parse date | invalid date queue | no | import date (flagged) | valid date | medium |
| `payments.order_id` | `finance_payments.work_item_id` | FK map orders | allow multi-payments per order | yes | null | FK exists if not null | medium |
| `payments.client_id` | `finance_payments.party_id` | FK map parties | missing party references | yes | null | FK exists if not null | medium |
| `payments.method_id` | `finance_payments.method_id` | map via payment_methods dictionary | unmapped methods | yes | `unknown_method` | dictionary exists | medium |
| `payments.operation_type_id` | `finance_payments.operation_type_id` | map via operation types dictionary | unmapped ops | yes | `other` | dictionary exists | medium |
| `payments.dds_kind_id` | `finance_payments.kind_id` | map via finance taxonomy | dictionary alignment | yes | null | dictionary exists | medium |
| `payment_allocations.*` | `finance_allocations.*` | direct FK mapping if table used | currently empty | yes | skip import | FK integrity | low |

---

## 4. Status mapping matrix

### 4.1 Orders (`orders.status` -> `work_items.status`)

| Legacy value | Proposed Core status | Unknown/unmapped handling | Manual review needed |
|---|---|---|---|
| `COMPLETED` | `done` | n/a | no |
| `IN_PROGRESS` | `in_progress` | n/a | no |
| `CONTRACT_PENDING` | `waiting_contract` | n/a | no |
| `CANCELLED` | `cancelled` | n/a | no |
| any other / `NULL` | `needs_review` | map to `needs_review` queue | yes |

### 4.2 Order stages (`order_stages.status` -> `work_item_stages.status`)

| Legacy value | Proposed Core status | Unknown/unmapped handling | Manual review needed |
|---|---|---|---|
| `NOT_STARTED` | `not_started` | n/a | no |
| `DONE` | `done` | n/a | no |
| any other / `NULL` | `needs_review` | map to `needs_review` queue | yes |

### 4.3 Contracts (`contracts.status` -> `documents.status`)

| Legacy value | Proposed Core status | Unknown/unmapped handling | Manual review needed |
|---|---|---|---|
| `SIGNED` | `signed` | n/a | no |
| `COMPLETED` | `closed` | n/a | no |
| `ON_REVIEW` | `on_review` | n/a | no |
| `CANCELLED` | `cancelled` | n/a | no |
| any other / `NULL` | `draft` + review tag | map temporary and queue | yes |

### 4.4 Payments/debts (`payments.type` + payment state logic)

| Legacy value | Proposed Core status/direction | Unknown/unmapped handling | Manual review needed |
|---|---|---|---|
| `INCOME` | `direction=incoming`, `status=posted` | n/a | no |
| `EXPENSE` | `direction=outgoing`, `status=posted` | n/a | no |
| any other / `NULL` | `status=needs_review` | quarantine row from posting | yes |

---

## 5. Cleanup backlog

| Issue | Affected table/entity | Severity | Proposed cleanup rule | Automatic or manual | Blocks import |
|---|---|---|---|---|---|
| `contracts.order_id` NULL (10 rows) | `contracts` | high | разрешить временно null + проставить `link_review_required`; после маппинга связать вручную/по номеру | mixed | yes (для полного contract->work_item linkage) |
| `order_stages.template_id` NULL (37 rows) | `order_stages` | high | назначить default stage template per service/pipeline | automatic + spot manual | yes (для stage template consistency) |
| Zero contract amounts (3 rows) | `contracts` | medium | rule: если допустимо бизнесом -> keep; иначе mark invalid_amount | manual policy required | no (если есть review flag) |
| Duplicate groups signal on `payments.order_id` | `payments` | low | трактовать как many payments per order, не dedupe по умолчанию | automatic accept | no |
| Orphan records | core FK-linked tables | low | по Gate 2 orphan=0, повторная проверка pre-import | automatic check | no |
| Empty required fields (other future findings) | active entities | high | field-level default + review queue + reject rule для критичных полей | mixed | yes (critical fields only) |
| Inconsistent/unknown statuses | `orders`, `order_stages`, `contracts`, `payments` | high | status matrix + `needs_review` bucket | automatic route + manual finalize | yes (если unmapped > threshold) |

---

## 6. Import strategy (staged order)

1. `tenant` + `default_branch` bootstrap.
2. `users` + `roles` + memberships.
3. `parties/contacts` (`clients` then `suppliers`).
4. `catalog/services` + needed dictionaries.
5. `CRM pipeline/stages` templates and stage dictionaries.
6. `work_items/orders/cases` + lines.
7. `contracts/documents` (+ acts/templates as second wave).
8. `finance/payments/debts` (+ allocations if used).
9. `audit/import logs` and reconciliation summary.

Принцип: каждый этап завершается валидацией агрегатов и чеком ссылочной целостности до перехода к следующему.

---

## 7. Data protection rules

- Не включать в spec и отчёты raw персональные значения.
- Использовать только имена полей, схемные правила и агрегированные findings.
- Персональные данные при будущем импорте допускаются только в рамках целевого tenant.
- Каждый import batch обязан формировать audit/import summary.
- До любого будущего импорта должен существовать подтверждённый backup source DB.
- Полный запрет cross-tenant data exposure на всех этапах.

---

## 8. Core readiness blockers (must-have before import)

- Tenant создан и доступен для first client.
- `default_branch` создан и привязан к tenant.
- Базовые `users/roles` и memberships готовы.
- Готовы модель/endpoint для `parties/contacts`.
- Готовы `CRM pipeline/work_items`.
- Готов `catalog/services`.
- Готов базовый `finance` контур.
- Готов `documents/contracts` контур.
- Есть механизм `import_log`/audit trail.
- Подготовлен rollback/export backup plan (операционный runbook).

---

## 9. Bridge-mode plan (`/dashboard` legacy during transition)

- Legacy `/dashboard` продолжает работать; shutdown не выполняется.
- Write freeze не вводится, пока дата миграции не утверждена отдельно.
- Dual-write не допускается, если не спроектирован и не утверждён явно.
- Cutover дата и сценарий определяются отдельным Gate (после readiness + dry-run).
- Source-of-truth на переходе:
  - legacy остаётся operational source;
  - Core становится target for staged onboarding and verification;
  - окончательная смена source-of-truth только после подписанного cutover checklist.

---

## 10. Acceptance criteria for future import

- Контрольные количества записей совпадают с ожидаемыми агрегатами по этапам.
- Все статусные поля проходят через утверждённую mapping matrix.
- Нет orphan critical records в целевых сущностях.
- Required fields заполнены или корректно defaulted по правилам.
- Пользователи клиента могут войти в Core с корректными правами.
- Ключевые записи отображаются в Core CRM (work_items/pipeline).
- Финансовые суммы сверяются по агрегатам (без персональных детализаций).
- Существует и проверен rollback plan.

---

## 11. Explicit out of scope

- Actual import execution.
- Data export from production.
- Production DB writes.
- Code changes.
- Service restarts.
- Legacy app rewrite.
- Full accounting implementation.
- Clinic/Booking/Trailers modules implementation.

---

## C1 finalization addendum

- Import batch summary contract is formalized in `docs/ai/specs/2026-07-08-flexity-consulting-import-batch-summary-contract.md`.
- Status acceptance policy is formalized in `docs/ai/specs/2026-07-08-flexity-consulting-status-acceptance-policy.md`.
- Backup/rollback operational baseline is formalized in `docs/ai/runbooks/2026-07-08-flexity-consulting-import-backup-rollback-runbook.md`.

---

## Post-migration operating model / Source of truth decision

1. After approved migration and cutover, Flexity Core becomes the only operational source of truth for the consulting client.
2. New leads, clients, cases/orders, statuses, documents, payments/debts, and notes must be created and managed in Flexity Core.
3. Legacy `consult_app` `/dashboard` remains only as temporary bridge/reference/archive during transition.
4. No dual-write model unless separately designed and approved.
5. Incoming lead capture for the consulting client must be routed into Flexity Core, not legacy `consult_app`.
6. Legacy `consult_app` must not be expanded with new features after migration.
7. Constructive legacy knowledge to reuse:
   - proven pipeline/status logic,
   - useful fields,
   - consulting workflow rules,
   - historical data,
   - reporting needs.
8. What not to copy:
   - single-tenant assumptions,
   - SQLite-as-production target,
   - weak source-of-truth boundaries,
   - direct DB coupling,
   - any legacy design that conflicts with Core tenant/API architecture.

### Explicit cutover rule

- Before cutover: legacy `/dashboard` remains working bridge.
- After cutover: Flexity Core is operational system; legacy is archive/reference only.

### Lead intake implication

- First post-migration integration priority is inbound lead capture into Core Consulting package.

---

Approval required before any import script, code change, data export, migration, or production action.
