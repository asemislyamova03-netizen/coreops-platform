# C2 Plan: Flexity Consulting Import Script (Planning Only)

**Дата:** 2026-07-08
**Статус:** documentation-only plan
**Режим:** без code changes, без import, без production действий

---

## 1. Executive summary

- C1 завершён локально: target mapping contracts, import summary contract, status acceptance policy и backup/rollback runbook уже зафиксированы.
- C2 на этом этапе планирует только будущую реализацию import script, без написания кода.
- Legacy `/dashboard` остаётся bridge/reference источником в transition.
- Production import не входит в C2.

---

## 2. Import preconditions

До реализации и запуска будущего import script обязательно:

1. **Source DB backup:** подтверждён backup источника и зафиксирован backup ID.
2. **Target tenant:** целевой tenant для first Consulting клиента создан.
3. **Default branch:** `default_branch` (`main`) существует и привязан к tenant.
4. **Users/roles:** базовые роли и доступы готовы, login policy подтверждён.
5. **Status mapping contract:** утверждён и заморожен (`status acceptance policy`).
6. **Import batch summary:** контракт summary утверждён и обязателен для каждого batch.
7. **Rollback/export backup readiness:** runbook утверждён до dry-run/write-mode.
8. **Approval gates:** отдельные approvals на C2 code, local dry-run, staging import, client review, production cutover.

---

## 3. Source and target overview

- **Source:** legacy `consult_app` SQLite (`consulting_os.db`) как read-only источник.
- **Target:** Flexity Core PostgreSQL tenant-aware модули (`tenants`, `branches`, `auth`, `parties`, `workflows`, `catalog`, `documents`, `finance`, `audit`, `subscriptions`).
- В C2 документации не включать персональные значения, только схемы/правила/агрегаты.

---

## 4. Proposed import script architecture

### 4.1 Read-only source adapter
- Подключение к SQLite в read-only режиме.
- Только SELECT/metadata операции.

### 4.2 Transform/mapping layer
- Использует утверждённые contracts C1/Gate3:
  - status mapping,
  - nullable/default policies,
  - entity linkage rules.

### 4.3 Validation layer
- Проверка required fields.
- Проверка enum/status соответствия.
- Проверка ссылочной консистентности до любой записи.

### 4.4 Dry-run mode
- По умолчанию основной режим.
- Генерирует только counts/validation reports/warnings.

### 4.5 Write mode disabled by default
- Должен быть явно включаемым флагом только после отдельных approvals.

### 4.6 Import batch summary generation
- Генерация `ImportBatchSummary` по контракту C1:
  - totals,
  - per-entity stats,
  - warnings/errors/review counts.

### 4.7 Error report
- Технические ошибки и validation нарушения без PII.
- Разделение на `blocking` и `review`.

### 4.8 Rollback notes
- Ссылка на runbook backup/rollback.
- Обязательная фиксация rollback checkpoint перед любым write-mode.

---

## 5. Staged import order

1. Tenant/default_branch checks.
2. Users.
3. Parties/contacts.
4. Catalog/services.
5. CRM pipeline/work_items/orders/cases.
6. Contracts/documents.
7. Finance/payments/debts.
8. Import/audit summary.

---

## 6. Dry-run requirements

Dry-run в C2+ обязан:

- не выполнять DB writes;
- показывать only counts;
- фиксировать validation errors;
- фиксировать unmapped statuses;
- фиксировать duplicate warnings;
- фиксировать orphan warnings;
- сравнивать finance aggregates (source vs target-prepared expectations);
- формировать import summary preview.

---

## 7. Validation rules

Минимальный набор в будущем import script:

1. **Required fields:** критичные поля обязательны или должны иметь утверждённый default.
2. **Status mapping:** только через утверждённую matrix/policy.
3. **Tenant isolation:** все target записи строго tenant-scoped.
4. **Branch assignment:** branch policy применяется consistently (`default_branch` как baseline).
5. **Duplicate handling:** технические дубли/коллизии помечаются и маршрутизируются по policy.
6. **Orphan handling:** критичные orphan-случаи блокируют batch.
7. **Zero contract amount policy:** `0` допускается только по согласованному правилу + review flag.
8. **`contracts.order_id NULL` policy:** nullable link + review queue согласно C1 contracts.
9. **`order_stages.template_id NULL` policy:** fallback default template + warning/review.

---

## 8. Data protection rules

- Запрет raw PII в логах/отчётах.
- Маскирование чувствительных значений в диагностике.
- Запрет full dumps.
- Локально/стейдж only до отдельного production approval.
- Запрет копирования source DB без отдельного approval.
- Import report должен быть без персональных данных.

---

## 9. Testing plan

1. Unit tests для mapping functions.
2. Dry-run tests на synthetic fixtures.
3. Import summary contract tests.
4. Rollback simulation (tabletop/операционный сценарий).
5. Tenant isolation checks.
6. Finance aggregate checks.
7. Никаких production tests в C2.

---

## 10. Implementation gates

1. C2 plan approval.
2. C2 code approval.
3. Local dry-run approval.
4. Staging import approval.
5. Client review approval.
6. Production cutover approval.

---

## 11. Out of scope

- Production import.
- Production data export.
- Deploy.
- Service restart.
- Legacy app rewrite.
- Dual-write.
- Full accounting.
- Clinic/Booking/Trailers scope.
- Payroll/taxes/inventory expansion.

---

## 12. Decision checkpoint

**Decision:** Core готов для C2 script implementation (после отдельного code approval).

Обоснование:
- C1 закрыл минимальные readiness blockers локально.
- Нужные contracts и runbook уже определены.
- Дополнительный C1b перед началом C2 script implementation не требуется при сохранении текущего scope.

---

## 13. Post-migration operating model / Source of truth decision

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

Approval required before C2 import script implementation.
