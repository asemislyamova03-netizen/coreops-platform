# C1 Implementation Plan: Flexity Consulting Core Target Readiness Fixes

**Дата:** 2026-07-08  
**Статус:** draft / awaiting approval  
**Режим:** documentation-only (без code changes, без migrations, без import script, без production действий)

---

## Task Classification

| Параметр | Значение |
|---|---|
| Project | Flexity |
| Category | platform_core |
| Risk level | high |
| Intended scope | закрыть минимальные Core blockers до планирования import script |
| Forbidden scope | production import, deploy, data export, broad refactoring |
| Required plan | этот C1 plan + отдельный approval до кода |

---

## 1) Executive summary

- Первый пакет: **Consulting / Sales CRM**.
- Legacy `/dashboard` остаётся bridge-слоем на переходный период.
- Core на текущем этапе **частично готов** к первому импорту.
- C1 закрывает только минимальные блокеры, необходимые до старта C2 (import script planning).
- C1 не является full Flexity launch и не включает production import.

---

## 2) Blockers to close (только из readiness review)

| Blocker | Why it blocks import | Minimal fix | File/module area | Risk | Test needed |
|---|---|---|---|---|---|
| Нет финального target contract для `orders -> work_items` и `order_stages -> stage templates` | Нельзя гарантировать корректный импорт CRM-структуры | Зафиксировать final entity/status/template contract для C2 | `backend/app/modules/workflows/*`, `docs/ai/specs/*` | high | contract tests + status/template mapping tests |
| Не утверждены правила для `contracts.order_id NULL` и `contracts.amount=0` | Документы могут потерять связь с кейсами или искажать финансы | Утвердить правило: nullable-link policy + review flags + zero-amount policy | `backend/app/modules/documents/*`, `docs/ai/specs/*` | high | documents validation tests + import dry-run assertions |
| Нет утверждённого rollback/backup process для source/target | Нет безопасного отката при ошибке импорта | Подготовить и утвердить runbook backup + rollback | `docs/ai/runbooks/*` (новый документ) | critical | runbook checklist validation (tabletop) |
| Нет формализованного import log summary контракта | Нет audit evidence по import batch | Определить import batch summary schema (counts/errors/warnings) | `backend/app/modules/audit/*`, `docs/ai/specs/*` | high | audit contract tests + summary serialization tests |
| Не зафиксирована финальная status mapping acceptance policy | Риск потери/искажения бизнес-статусов | Утвердить acceptance thresholds для unknown/unmapped + manual queue policy | `docs/ai/specs/*`, `backend/app/modules/workflows/*`, `backend/app/modules/finance/*`, `backend/app/modules/documents/*` | high | status mapping matrix tests |
| Не подтверждён E2E access readiness импортированных пользователей | Пользователь может не войти или получить неверные права | Зафиксировать login+role acceptance checklist на tenant scope | `backend/app/modules/auth/*`, `backend/app/modules/tenants/*`, `backend/tests/*` | high | auth/role integration tests + tenant isolation regression |

---

## 3) Proposed file-level changes (C1 minimal scope)

> Ниже — минимальный план целевых файлов для будущей реализации C1. Сейчас файлы не меняются.

| Path | Create/Modify | Purpose | Risk | Rollback note | Tests |
|---|---|---|---|---|---|
| `docs/ai/specs/2026-07-08-flexity-consulting-gate3-migration-mapping-spec.md` | modify | зафиксировать final contracts для work_items/stages/documents/finance statuses | medium | вернуть предыдущую версию spec | spec consistency check |
| `docs/ai/specs/2026-07-08-flexity-consulting-import-batch-summary-contract.md` | create | формальный import log summary contract | low | удалить документ | contract lint/checklist |
| `docs/ai/specs/2026-07-08-flexity-consulting-status-acceptance-policy.md` | create | policy unknown/unmapped statuses + thresholds/manual review | low | удалить документ | mapping policy review |
| `docs/ai/runbooks/2026-07-08-flexity-consulting-import-backup-rollback-runbook.md` | create | backup/rollback process до любого import script | medium | удалить/переписать runbook | tabletop validation |
| `backend/app/modules/workflows/schemas.py` | modify (planned) | явно закрепить target status/stage contracts (если не хватает) | high | revert schema changes | unit + mapping tests |
| `backend/app/modules/workflows/service.py` | modify (planned) | добавить status/template acceptance hooks (minimal) | high | revert service changes | service tests |
| `backend/app/modules/documents/schemas.py` | modify (planned) | правила nullable `work_item` link + zero-amount handling flags | high | revert schema changes | documents validation tests |
| `backend/app/modules/finance/schemas.py` | modify (planned) | финализация `payments.type -> direction/status` contract | high | revert schema changes | finance mapping tests |
| `backend/app/modules/audit/schemas.py` | modify (planned) | import batch summary schema | medium | revert schema changes | schema tests |
| `backend/app/modules/audit/service.py` | modify (planned) | сервисный контракт записи import summary | high | revert service changes | audit service tests |
| `backend/tests/test_tenant_isolation.py` | modify/create (planned) | подтверждение tenant-safe access после import readiness fixes | high | revert tests | tenant isolation tests |
| `backend/tests/test_auth_login_roles.py` | create (planned) | проверка login + role assignment для imported users | high | remove test file | auth integration tests |
| `backend/tests/test_status_mapping_contracts.py` | create (planned) | проверка статусов для workflows/documents/finance | medium | remove test file | mapping tests |
| `backend/tests/test_import_summary_contract.py` | create (planned) | проверка структуры import summary (без запуска импорта) | medium | remove test file | audit summary tests |

---

## 4) Data model readiness (only required for C1)

- **Orders/cases/work_items target:** закрепить минимальный контракт `orders -> work_items`, `order_items -> work_item_lines`, `order_stages -> work_item_stages`.
- **Status mapping target:** зафиксировать утверждённые target enums + fallback `needs_review`.
- **Parties/contact required fields:** `external_legacy_id`, `display_name`, `party_kind`, контактные поля с nullable policy и валидацией формата.
- **Catalog/service target:** `services` должны существовать до импорта work_items.
- **Documents/contracts target:** поддержка nullable `work_item_id` с review flag; zero amount policy.
- **Finance/payment/debt target:** mapping `payments.type` в direction/status + агрегатная reconciliation policy.
- **Subscription/package placeholder:** tenant package attach contract для first package (без автоматического биллинга).
- **Import log target:** отдельная batch summary сущность/контракт (counts/errors/warnings/manual-review counters).

---

## 5) API/service readiness (must exist before import)

- Tenant/default_branch: уже доступны; нужен pre-import readiness check.
- Parties: create/list/update должны быть доступны в tenant scope.
- CRM work_items/orders/cases equivalent: create/list контракт должен быть подтверждён для импорта.
- Catalog services: create/list и стабильная dictionary semantics.
- Finance payments/debts: минимальный create/list и корректный direction/status mapping.
- Import log creation: обязательный сервисный контракт формирования batch summary.
- Новые публичные API в C1 не требуются, если существующие внутренние/текущие endpoints покрывают readiness.

---

## 6) Test plan (C1)

### Unit tests
- workflows status/stage contract checks.
- documents nullable-link + amount policy checks.
- finance direction/status mapping checks.
- audit import summary schema/service checks.

### Local integration tests
- auth/login + role assignment для tenant users.
- parties + work_items + documents + finance basic flow (без импорта legacy данных).

### Tenant isolation tests
- запрет cross-tenant доступа для users/parties/work_items/documents/payments.

### Default_branch regression
- проверка, что tenant bootstrap сохраняет `default_branch` поведение без регресса.

### Status mapping tests
- покрытие matrix для orders/stages/contracts/payments, включая unknown/unmapped ветки.

### Finance aggregate preservation tests
- если finance включён в C1 scope: сверка агрегатов на тестовых данных по accepted mapping rules.

### No production tests
- только локальные/стейдж-подобные проверки, без production execution.

---

## 7) What remains manual for first launch

- Billing/subscription invoice back-office операции.
- Часть cleanup review для спорных записей.
- Часть client onboarding шагов по runbook.
- Contract templates migration (если не блокирует first import scope).
- Advanced reports (если не критичны для first import acceptance).

---

## 8) Explicit out of scope

- Import script разработка.
- Actual import execution.
- Production DB writes.
- Любые изменения legacy `/dashboard`.
- Data export из production.
- Deploy/restart/service reconfiguration.
- Full accounting контур.
- Payroll.
- Inventory расширение.
- Clinic/Booking/Trailers задачи.
- EDS/government integrations.
- Certification/compliance claims.

---

## 9) Implementation gates

1. **C1 plan approval** — утверждение этого плана.
2. **C1 code approval** — отдельное явное разрешение на код.
3. **Migration approval if needed** — отдельный gate на миграции (если появятся).
4. **Local test approval** — разрешение на запуск полного локального тест-пакета.
5. **Import script planning approval** — отдельный gate для C2.
6. **Production action approval** — отдельный gate на любые prod-действия.

---

Approval required before C1 code implementation.
