# Implementation Plan: `0014_core_branches_baseline`

**Дата:** 2026-07-09  
**Статус:** waiting for approval (documentation-only)  
**Ветка:** `main`  
**Режим:** planning only — no code, no migration file, no alembic upgrade, no staging/live DB writes

---

## Task Classification

| Параметр | Значение |
|---|---|
| Project | Flexity |
| Category | platform_core |
| Risk level | high (tenant baseline, FK cycle, blocks Consulting import readiness) |
| Intended scope (this step) | только этот файл: `docs/ai/plans/2026-07-09-flexity-core-0014-branches-baseline-plan.md` |
| Forbidden scope | code, alembic upgrade, deploy, import, live/staging DB writes, `consulting_os.db`, legacy `/dashboard` |
| Required plan type | migration implementation plan (local-first, approval-gated) |

### Inputs used

- `docs/ai/reviews/2026-07-08-flexity-core-branch-schema-blocker-review.md`
- `docs/ai/plans/2026-07-08-flexity-core-e3-regulated-foundation-implementation-plan.md` (E3a)
- `docs/ai/plans/2026-07-08-flexity-consulting-c1c-core-api-readiness-plan.md`
- `docs/ai/plans/2026-07-08-flexity-consulting-c2c-write-import-planning.md`
- `docs/ai/specs/2026-07-08-flexity-consulting-gate3-migration-mapping-spec.md`
- `docs/ai/reports/2026-07-08-flexity-coreops-staging-c1c-app-smoke-report.md`
- `docs/ai/reports/2026-07-08-flexity-coreops-staging-alembic-upgrade-0013-report.md`
- Code read-only: `backend/alembic/versions/*`, `backend/app/modules/branches/*`, `backend/app/modules/tenants/*`, `backend/app/modules/imports_dry_run/*`, relevant tests

---

## 1) Current state

### 1.1 Alembic head (локально)

| Item | Value |
|---|---|
| Local migration head | `0013_c1c_payment_direction` |
| File | `backend/alembic/versions/20260708_0013_c1c_payment_direction.py` |
| `down_revision` | `0012_booking_e1` |
| Chain | `0001_phase1` → … → `0012_booking_e1` → `0013_c1c_payment_direction` |

Проверено read-only через `alembic.script.ScriptDirectory` (2026-07-09).

### 1.2 Что уже есть в Postgres schema (через Alembic до `0013`)

**Таблица `tenants`** (с `0001_phase1`, расширена поздними фазами):

- `id` (UUID PK)
- `provider_company_id` (FK → `provider_companies.id`)
- `name`, `slug`
- `industry_template_id` (nullable FK, добавлен в phase3)
- `status` (`tenant_status` enum-as-string)
- `created_at`, `updated_at`
- **нет** `default_branch_id`

**Таблица `payments`** (после `0013`):

- колонка `direction` (`payment_direction`: `incoming` / `outgoing` / `needs_review`, default `incoming`)
- index `ix_payments_direction`

**Таблица `branches`:**

- **отсутствует** во всех 13 существующих Alembic revisions

### 1.3 Что уже есть в application code (E3a baseline)

| Area | State |
|---|---|
| `backend/app/modules/branches/models.py` | ORM `Branch`: `tenant_id`, `code`, `name`, `is_active`, `is_default`, timestamps; `uq_branch_tenant_code` |
| `backend/app/modules/branches/repository.py` | `create`, `get_default` |
| `backend/app/modules/branches/service.py` | `ensure_default_branch`: code=`main`, name=`Main branch`, `is_default=True`, `is_active=True` |
| `backend/app/modules/tenants/models.py` | `default_branch_id` FK → `branches.id` ON DELETE SET NULL (nullable) |
| `backend/app/modules/tenants/service.py` | `TenantService.create()` вызывает `BranchService.ensure_default_branch(tenant.id)` |
| `backend/app/modules/tenants/schemas.py` | `TenantResponse.default_branch_id` exposed |
| `backend/app/modules/models.py` | `Branch` registered for metadata |
| Tests | `test_create_tenant_provisions_default_branch`, dry-run `missing_default_branch_id`, documents import `branch_id` in `context_json` |

**Важно:** локальные pytest используют `create_all` и видят E3a schema. Staging Postgres (`coreops_staging_0013`) и live (`coreops` @ `0012`) **не** имеют branch schema, потому что Alembic revision для branches не создан.

### 1.4 Чего не хватает для branch baseline

| Missing artifact | Impact |
|---|---|
| `branches` table | невозможно persist default branch на Postgres через Alembic path |
| `tenants.default_branch_id` column | tenant create / import context не может durable FK на branch |
| Backfill для pre-existing tenants | tenants без branch останутся без `default_branch_id` после schema-only upgrade |
| Alembic revision after `0013` | staging/live schema drift vs ORM |

### 1.5 Почему `0013` недостаточно

`0013_c1c_payment_direction` решает **только C1c finance gap**:

- добавляет `payments.direction` для Consulting payment mapping (`incoming` / `outgoing` / `needs_review`).

`0013` **не затрагивает**:

- tenant/branch baseline (E3a);
- `branches` table;
- `tenants.default_branch_id`;
- import readiness contract `TenantBranchReadiness` (требует реальный `default_branch_id`).

C1c app smoke на staging runner доказал documents import + payment direction + audit hook в **service/sqlite path**, но **не** доказал durable branch persistence на staging Postgres. Blocker review зафиксировал: write-import и real-source dry-run **заблокированы** до `0014`.

### 1.6 Environment snapshot

| Environment | Alembic revision | Branch schema |
|---|---|---|
| Local code + pytest (`create_all`) | N/A (ORM) | present |
| Local Alembic chain | head `0013` | absent |
| Staging `coreops_staging_0013` | `0013` | absent |
| Live `coreops` | `0012` | absent; **must not touch** |

---

## 2) Цель `0014_core_branches_baseline`

Создать новую Alembic revision **`0014_core_branches_baseline`** (после approval и отдельного code step), которая:

1. **Создаёт таблицу `branches`** — aligned с существующим ORM `Branch`.
2. **Добавляет `tenants.default_branch_id`** — nullable UUID FK → `branches.id` ON DELETE SET NULL.
3. **Обеспечивает совместимость с E3a branch code** — без изменения service constants (`main` / `Main branch`).
4. **Готовит Core к Consulting import readiness** — tenant bootstrap stage 1 из Gate 3 mapping spec может durable resolve `default_branch_id`.
5. **Не ломает C1c** — `payments.direction` и documents import path остаются без regression.

### Target revision metadata (planned)

| Field | Planned value |
|---|---|
| `revision` | `0014_core_branches_baseline` |
| `down_revision` | `0013_c1c_payment_direction` |
| File (example) | `backend/alembic/versions/20260709_0014_core_branches_baseline.py` |

---

## 3) Предлагаемая DB schema

Схема **должна совпадать с текущим ORM**, а не вводить новые поля без Change Request.

### 3.1 Таблица `branches`

| Column | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| `id` | UUID | NOT NULL | `gen_random_uuid()` / app-generated | PK; matches `UUIDPrimaryKeyMixin` |
| `tenant_id` | UUID | NOT NULL | — | FK → `tenants.id` ON DELETE **CASCADE**; indexed |
| `code` | VARCHAR(64) | NOT NULL | — | per-tenant business code; bootstrap=`main` |
| `name` | VARCHAR(255) | NOT NULL | — | display name; bootstrap=`Main branch` |
| `is_active` | BOOLEAN | NOT NULL | `true` | **ORM uses `is_active`, not separate `status` enum** |
| `is_default` | BOOLEAN | NOT NULL | `false` | bootstrap branch sets `true` |
| `created_at` | TIMESTAMPTZ | NOT NULL | `now()` | `TimestampMixin` convention |
| `updated_at` | TIMESTAMPTZ | NOT NULL | `now()` | `TimestampMixin` convention |

**Mapping note (user field `status`):** в E3a модели нет отдельного `status` enum для branch. Семантика «активен/неактивен» выражена через `is_active`. Отдельный `branch_status` enum **не добавлять** в `0014` без Change Request — это расходится с текущим `Branch` ORM.

### 3.2 Изменение `tenants`

| Column | Type | Nullable | FK | Notes |
|---|---|---|---|---|
| `default_branch_id` | UUID | **NULL** (transition) | → `branches.id` ON DELETE SET NULL | indexed; matches current ORM |

Nullable на переходном этапе — осознанное решение E3a: позволяет chicken-and-egg create order и совместимо с service bootstrap. Making NOT NULL — отдельный future gate после backfill policy.

### 3.3 FK / index / constraint strategy

**Upgrade order (recommended):**

```text
1. CREATE TABLE branches
   - FK branches.tenant_id → tenants.id (CASCADE)
   - UNIQUE (tenant_id, code) AS uq_branch_tenant_code
   - INDEX ix_branches_tenant_id

2. ALTER TABLE tenants ADD COLUMN default_branch_id UUID NULL
   - INDEX ix_tenants_default_branch_id

3. ADD FK tenants.default_branch_id → branches.id ON DELETE SET NULL
   - use deferred / use_alter pattern if dialect requires breaking cycles
```

**Circular FK (`tenants` ↔ `branches`):**

- ORM уже моделирует cycle: `Branch.tenant_id` → `tenants`, `Tenant.default_branch_id` → `branches`.
- SQLite tests показывают benign `drop_all` warning на этом cycle — ожидаемо.
- Postgres upgrade: создать `branches` first (FK only to `tenants`), затем column + FK on `tenants`.
- При необходимости: `op.create_foreign_key(..., use_alter=True)` для `tenants.default_branch_id`.

**Unique strategy:**

- `UNIQUE (tenant_id, code)` — `uq_branch_tenant_code` (как в ORM `__table_args__`).
- Pattern аналогичен `booking_territories` (`uq_booking_territory_tenant_code` в `0012`).

**Default branch constraint (application-level today):**

- ORM/service: `BranchRepository.get_default()` ищет `is_default=True` per tenant.
- DB-level partial unique index `(tenant_id) WHERE is_default = true` — **optional future hardening**, не обязателен для `0014` если совпадаем с текущим E3a scope.
- Migration backfill must ensure **at most one** `is_default=true` per tenant.

**Связь `tenants.default_branch_id` ↔ `branches`:**

- `default_branch_id` — pointer tenant → canonical default branch row.
- `branches.is_default` — marker на branch row.
- Service `ensure_default_branch` синхронизирует оба при tenant create.
- Backfill migration должна установить **оба** поля согласованно.

---

## 4) Backfill strategy

### 4.1 Recommended approach: **Hybrid**

| Scenario | Mechanism |
|---|---|
| Existing tenants at upgrade time | Alembic `upgrade()` data step (idempotent) |
| New tenants after upgrade | `BranchService.ensure_default_branch` (unchanged) |

Это соответствует blocker review §5 recommendation.

### 4.2 Backfill algorithm (per tenant row)

Для каждого `tenants` row где `default_branch_id IS NULL`:

1. Проверить, есть ли branch с `tenant_id = tenants.id AND is_default = true`.
2. Если есть — set `tenants.default_branch_id = branch.id` (heal FK only).
3. Если нет — INSERT into `branches`:
   - `id` = new UUID
   - `tenant_id` = tenant.id
   - `code` = `'main'`
   - `name` = `'Main branch'`
   - `is_active` = `true`
   - `is_default` = `true`
   - timestamps = `now()`
4. UPDATE `tenants SET default_branch_id = <new branch id>`.

### 4.3 Safe bootstrap values

| Field | Value | Source |
|---|---|---|
| `code` | `main` | `BranchService.ensure_default_branch` |
| `name` | `Main branch` | same |
| `is_active` | `true` | same |
| `is_default` | `true` | same |

Не генерировать per-tenant custom names в migration без product policy change.

### 4.4 Idempotency rules

Migration data step must be safe to re-run logic-wise:

- Skip tenant if `default_branch_id IS NOT NULL` **and** referenced branch exists.
- If `default_branch_id` points to missing branch → flag/heal (staging: recreate; document for review).
- If multiple `is_default=true` for same tenant → pick deterministic winner (lowest `created_at` or `id`), demote others to `is_default=false`, log/note in migration comment.
- Use `op.get_bind()` + raw SQL or SQLAlchemy Core; avoid importing app services inside migration (keeps alembic self-contained).

### 4.5 Staging empty DB path

Current `coreops_staging_0013` expected near-empty:

- Schema + optional empty backfill loop (0 rows) is sufficient.
- First tenant create via API will call `ensure_default_branch`.

### 4.6 Live / populated future path

When live eventually reaches `0014` (separate gate, not this plan):

- Mandatory backup before upgrade.
- Backfill required for all existing tenants.
- Post-upgrade verify: `COUNT(*) FROM tenants WHERE default_branch_id IS NULL` = 0 (or documented exceptions).

---

## 5) Downgrade strategy

### 5.1 Planned `downgrade()` steps (reverse order)

```text
1. SET tenants.default_branch_id = NULL   (all rows)
2. DROP FK tenants.default_branch_id → branches.id
3. DROP INDEX ix_tenants_default_branch_id
4. DROP COLUMN tenants.default_branch_id
5. DROP TABLE branches (CASCADE drops tenant-scoped branch rows)
```

### 5.2 Risks with backfilled data

| Risk | Severity | Mitigation |
|---|---|---|
| Loss of all branch rows | high on populated env | backup before upgrade; downgrade only on staging with approval |
| `default_branch_id` cleared | medium | documents `context_json.branch_id` is metadata only — no FK, but reconciliation harder |
| Re-upgrade duplicates | low if idempotent backfill | backfill checks existing `main` branch |
| Live downgrade | **forbidden** without separate DR plan | never part of this gate |

### 5.3 Staging downgrade policy

- Allowed only on isolated `coreops_staging_0013` clone with explicit approval.
- Acceptable because staging has no production import data.
- Prefer fresh DB recreate over downgrade if faster/safer.

---

## 6) Local implementation plan

**Только после explicit approval этого документа и отдельного approval на code.**

### 6.1 Files to create/modify (future code step)

| File | Action |
|---|---|
| `backend/alembic/versions/20260709_0014_core_branches_baseline.py` | **create** migration |
| `backend/tests/test_migration_0014_branches.py` (or extend existing) | **create** upgrade/downgrade + backfill tests |
| `backend/app/modules/branches/models.py` | **no change** (align migration to model) |
| `backend/app/modules/tenants/models.py` | **no change** |
| `backend/app/modules/tenants/service.py` | **no change** expected |

### 6.2 Files not to touch

- `backend/alembic/versions/20260708_0013_c1c_payment_direction.py` (immutable history)
- live/staging deploy scripts, nginx, systemd
- `consulting_os` / legacy SQLite
- `backend/app/modules/documents/*` (C1c already done)
- `backend/app/modules/finance/*` (except regression tests)
- legacy `/dashboard`

### 6.3 Implementation steps (post-approval)

1. Create migration file with `revision = "0014_core_branches_baseline"`, `down_revision = "0013_c1c_payment_direction"`.
2. Implement `upgrade()`:
   - create `branches` table per §3;
   - add `tenants.default_branch_id` + indexes/FKs per §3.3;
   - run idempotent backfill per §4.
3. Implement `downgrade()` per §5.
4. Cross-check against ORM:
   - column types, lengths, FK ondelete, unique constraint name `uq_branch_tenant_code`.
5. Local DB: fresh Postgres or local dev DB only.
6. Run `alembic upgrade head` locally.
7. Run pytest suite (§7).
8. Run `alembic downgrade -1` locally, then `upgrade` again — verify reversibility.
9. **Do not** apply to staging/live in same step.

### 6.4 Rollback (local)

- `alembic downgrade 0013_c1c_payment_direction`
- or drop/recreate local dev database

---

## 7) Test plan

Минимальный набор проверок после local migration implementation.

### 7.1 Migration tests

| Test | Expected |
|---|---|
| Empty DB `0013 → 0014` upgrade | `branches` exists; `tenants.default_branch_id` exists |
| Downgrade `0014 → 0013` | column dropped; table dropped; no orphan FK errors |
| Re-upgrade | clean second pass |

### 7.2 Tenant / branch behavior

| Test | File / approach | Expected |
|---|---|---|
| Existing tenant gets default branch on backfill | new migration test with pre-seeded tenant @ `0013` | `default_branch_id` set; `branches.code=main` |
| New tenant creation | `test_tenants.py::test_create_tenant_provisions_default_branch` | still PASS |
| Tenant list/detail exposes `default_branch_id` | `test_create_and_list_tenants` | still PASS |

### 7.3 Tenant isolation

| Test | File | Expected |
|---|---|---|
| Cross-tenant party access denied | `test_tenant_isolation.py` | still PASS |
| Branch IDs not shared across tenants | extend or reuse tenant create test | distinct `default_branch_id` per tenant |

### 7.4 Consulting import readiness

| Test | File | Expected |
|---|---|---|
| Dry-run fails without `default_branch_id` | `test_imports_dry_run.py::test_dry_run_fails_without_default_branch_id` | still PASS |
| Dry-run passes with context | `test_imports_dry_run.py` (happy path) | `tenant_branch_readiness.passed=True` |
| Documents import stores `branch_id` in `context_json` | `test_documents.py` | still PASS |

### 7.5 C1c regressions

| Test | File | Expected |
|---|---|---|
| `Payment.direction` default/explicit/legacy map | `test_finance.py`, `test_status_mapping_contracts.py` | still PASS |
| Documents import endpoint | `test_documents.py` | still PASS |
| Import batch summary contract | `test_import_summary_contract.py` | still PASS |

### 7.6 Auth / tenant regression

| Test | File | Expected |
|---|---|---|
| Register/login roles | `test_auth_login_roles.py` | still PASS |
| Tenant create requires provider owner | `test_tenants.py` | still PASS |
| Membership access control | `test_tenants.py`, `test_tenant_isolation.py` | still PASS |

### 7.7 Suggested commands (local only, post-approval)

```bash
cd backend
alembic upgrade head
python -m pytest tests/test_tenants.py tests/test_tenant_isolation.py tests/test_imports_dry_run.py tests/test_documents.py tests/test_finance.py tests/test_auth_login_roles.py -q
alembic downgrade -1
alembic upgrade head
```

---

## 8) Staging plan

**Только после local GREEN + отдельного explicit approval.**

### 8.1 Target

| Item | Value |
|---|---|
| Database | isolated `coreops_staging_0013` |
| Runner | `/opt/flexity/coreops_staging_0013/runner/backend/` |
| Action | `alembic upgrade 0014_core_branches_baseline` |
| Live | **untouched** |

### 8.2 Preflight (read-only)

- Confirm `alembic current` = `0013_c1c_payment_direction`
- Confirm no live DB connection / no `coreops` writes
- Backup or clone confirmation per coreops runbook

### 8.3 Post-upgrade smoke checklist

| Check | Method | Pass criteria |
|---|---|---|
| `branches` table exists | `\d branches` / information_schema | table present with §3 columns |
| `tenants.default_branch_id` exists | `\d tenants` | column + FK + index |
| Alembic head | `alembic current` | `0014_core_branches_baseline` |
| Existing tenant default branch | SQL or API tenant create | `default_branch_id` not null after create |
| C1c documents import | staging runner smoke (Gate-style) | import path still works |
| C1c payment direction | staging runner / SQL | `payments.direction` still present |
| Tenant isolation | smoke or pytest against staging DSN (if approved) | no cross-tenant leak |
| Live DB | read-only verify | still @ `0012`, unchanged |

### 8.4 Staging non-actions

- no real-source dry-run until staging branch verification passes
- no write-import
- no nginx public exposure shortcut

---

## 9) Explicit non-goals

В рамках `0014` planning и последующей local implementation **не делать**:

| Non-goal | Reason |
|---|---|
| Production deploy | separate production gate chain |
| Live Alembic upgrade (`coreops`) | live @ `0012`; blocked |
| Real-source dry-run | blocked until durable branch schema verified on staging |
| Write-import / cutover / dual-write | C2c blocked |
| Read `consulting_os.db` / real SQLite | forbidden |
| Changes to legacy `/dashboard` / `consult_app` | bridge only |
| Branch CRUD API / UI | E3a is bootstrap-only |
| `branch_status` enum / new branch fields | not in current ORM |
| Making `default_branch_id` NOT NULL | future policy gate |
| DB partial unique on `is_default` | optional hardening, out of scope |
| PII reading or client data export | compliance |
| Tenant customization layer | Change Request only |
| Booking module changes | unrelated |
| Modifying `0013` revision | immutable |

---

## 10) Risks

| Risk | Level | Mitigation |
|---|---|---|
| FK cycle tenants↔branches | medium | ordered upgrade; `use_alter` if needed; documented in migration |
| ORM vs migration drift | high | migration written to match existing models exactly |
| Backfill on populated live (future) | high | hybrid backfill; backup; separate live gate |
| False readiness claim after `0013` only | high | this plan + staging verification before import gates |
| SQLite test false confidence | medium | require Postgres migration test locally/staging |
| Multiple `is_default` rows | low | idempotent demotion rule in backfill |

---

## 11) Related artifacts

- Blocker review: `docs/ai/reviews/2026-07-08-flexity-core-branch-schema-blocker-review.md`
- E3 foundation: `docs/ai/plans/2026-07-08-flexity-core-e3-regulated-foundation-implementation-plan.md`
- Gate 3 mapping: `docs/ai/specs/2026-07-08-flexity-consulting-gate3-migration-mapping-spec.md`
- C1c plan/report: `docs/ai/plans/2026-07-08-flexity-consulting-c1c-core-api-readiness-plan.md`, `docs/ai/reports/2026-07-08-flexity-consulting-c1c-core-api-readiness-implementation-report.md`
- C2c planning: `docs/ai/plans/2026-07-08-flexity-consulting-c2c-write-import-planning.md`
- Staging 0013 report: `docs/ai/reports/2026-07-08-flexity-coreops-staging-alembic-upgrade-0013-report.md`
- Staging C1c smoke: `docs/ai/reports/2026-07-08-flexity-coreops-staging-c1c-app-smoke-report.md`

---

## Approval gate

**Status: waiting for approval**

Перед любым code/migration/staging action требуется явное подтверждение по пунктам:

- [ ] **Approve schema fields** — `branches` columns aligned with E3a ORM (`is_active`/`is_default`, not separate `status` enum)
- [ ] **Approve FK/index/constraint strategy** — upgrade order, `uq_branch_tenant_code`, nullable `default_branch_id`, ON DELETE rules
- [ ] **Approve backfill strategy** — hybrid: idempotent Alembic backfill for existing tenants + `ensure_default_branch` for new
- [ ] **Approve downgrade strategy** — NULL `default_branch_id` → drop FK/column → drop `branches`; staging-only downgrade policy
- [ ] **Approve local implementation only** — create migration file + local tests; **no staging/live apply** in same step

### Gate chain after this plan

1. This plan approved →  
2. Local migration file + tests (separate approval) →  
3. Local GREEN →  
4. Staging `0014` upgrade on `coreops_staging_0013` only (separate approval) →  
5. Staging verification smoke →  
6. Only then: real-source dry-run consideration →  
7. Much later: write-import, live migration, production deploy

---

**No code, no migration file, no alembic upgrade, no staging/live DB writes until explicit approval.**
