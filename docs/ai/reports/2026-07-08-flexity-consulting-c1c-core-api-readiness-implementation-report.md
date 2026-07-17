# Flexity Consulting C1c Core API Readiness Implementation Report

**Дата:** 2026-07-08
**Статус:** C1c local implementation completed
**Режим:** local-only (без production/import/export/deploy/legacy действий)
**План:** `docs/ai/plans/2026-07-08-flexity-consulting-c1c-core-api-readiness-plan.md` (approved for local code)

---

## Task Classification

1. **Project:** Flexity
2. **Category:** platform_core (minimal Core REST write-readiness)
3. **Risk level:** medium (local schema + API surface; migration for payment direction not applied to production)
4. **Intended scope:** documents import endpoint, payment direction field, minimal audit summary hook, tests, this report
5. **Forbidden scope:** production, deploy, import, legacy Flask, real SQLite, data export, service restarts, full accounting, debt API, subscription API redesign
6. **Required plan:** C1c plan (approved)

---

## 1) Files changed

### Code
- `backend/app/core/enums.py` — `PaymentDirection` enum
- `backend/app/modules/documents/schemas.py` — `DocumentImportCreate`
- `backend/app/modules/documents/service.py` — `import_document()` (no generate/files)
- `backend/app/modules/documents/routes.py` — `POST /documents/import`
- `backend/app/modules/finance/models.py` — `Payment.direction` column
- `backend/app/modules/finance/schemas.py` — direction on create/response; `legacy_payment_type` helper; align `map_legacy_payment_type` with `PaymentDirection`
- `backend/app/modules/finance/service.py` — persist/return direction; map from legacy type when provided
- `backend/app/modules/audit/service.py` — `record_import_batch_summary_event()` (audit log hook only)
- `backend/app/modules/imports_dry_run/pipeline.py` — validate against import + direction-ready DTOs

### Migration (local file only; not applied to production)
- `backend/alembic/versions/20260708_0013_c1c_payment_direction.py`

### Tests
- `backend/tests/test_documents.py` — import contract tests
- `backend/tests/test_finance.py` — direction + legacy type mapping API tests
- `backend/tests/test_status_mapping_contracts.py` — EXPENSE path + PaymentDirection
- `backend/tests/test_import_summary_contract.py` — audit summary event hook
- `backend/tests/test_imports_dry_run.py` — endpoints now `/documents/import` + payments ready

### Report
- `docs/ai/reports/2026-07-08-flexity-consulting-c1c-core-api-readiness-implementation-report.md`

---

## 2) Migrations created

| Revision | Purpose | Applied to production? |
|---|---|---|
| `0013_c1c_payment_direction` | Add `payments.direction` (`incoming` / `outgoing` / `needs_review`), default `incoming` | **No** — file created for local/schema readiness only; separate approval required before any alembic upgrade |

Documents import deliberately stores `amount`, `external_ref`, review flags and optional `branch_id` in `context_json` — **no documents migration**.

Local pytest uses `Base.metadata.create_all` (includes model column); production DB still needs approved migration before live finance writes expecting direction.

---

## 3) Tests run / results

Commands (local):

```text
python -m pytest tests/test_documents.py tests/test_finance.py tests/test_status_mapping_contracts.py tests/test_import_summary_contract.py tests/test_imports_dry_run.py tests/test_audit.py -q

python -m pytest tests/test_tenant_isolation.py tests/test_tenants.py tests/test_imports_sqlite_readonly.py -q
```

Results:

- **27 passed** (first suite)
- **28 passed** (tenant/sqlite suite)
- **0 failed**
- Existing SQLite FK-cycle teardown warnings only

---

## 4) Which P0 gaps were closed

| Gap | Decision | Outcome |
|---|---|---|
| **A — Documents/contracts import** | A1 | `POST /api/v1/documents/import` creates historical instance without template generate; preserves status policy, null `work_item_id`, zero amount review flags, `external_ref` / source metadata / optional `branch_id` in `context_json` |
| **B — Payment direction** | B1 (local model + migration file) | First-class `direction` on create/response/model; default `incoming` keeps existing `PaymentCreate` callers working; optional `legacy_payment_type` maps INCOME/EXPENSE/unknown |

---

## 5) What remains partial

| Area | Status |
|---|---|
| Dedicated `POST/GET /audit/import-batches` API | **Not built** (by plan: staging may use audit event; production prefers later) |
| Debt / receivables import API | **Deferred (D1)** — no separate debt API |
| Subscription / package API changes | **Not changed** — existing assign endpoint unchanged |
| Payment direction filter on list | Nice-to-have; not required for v1 |
| Idempotent upsert by `external_ref` | Metadata stored; no uniqueness/upsert enforcement yet |
| Alembic upgrade on any real DB | **Not run** |
| C2c staging REST write client | Not started — needs separate approval |
| Binary signed file / template content migration | Out of C1c |

---

## 6) Rollback notes

If C1c local rollback is required:

1. Revert/remove documents import route/service/schema additions.
2. Revert finance direction field from model/schemas/service; remove migration file `0013_c1c_payment_direction` or run downgrade **only** on environments where upgrade was applied (none in production).
3. Remove `record_import_batch_summary_event` from audit service.
4. Revert imports_dry_run pipeline payload/endpoint expectations.
5. Revert C1c test additions.
6. Re-run documents/finance/status/import-summary/dry-run suites.

No production data rollback steps: no prod writes, no deploy, no live alembic upgrade.

---

## 7) Risks

1. Production/staging Postgres without migration `0013` will reject Payment ORM inserts that expect `direction` once that code is deployed — **gate alembic separately**.
2. Amount on imported documents lives only in `context_json` — analytics that expect a column will not see it until a later schema.
3. `legacy_payment_type` overrides create status/direction when set — callers must understand the helper.
4. Import summary durability is audit-log-only; production cutover still wants a dedicated list API (plan C2).
5. Dry-run now marks documents/payments as **ready**; do not confuse DTO readiness with approved C2c write execution.

---

## 8) Compliance confirmation

Confirmed for this C1c local step:

- no production actions
- no deploy
- no import execution against Core/production
- no data export
- no legacy Flask / `/dashboard` / `/var/www/consult_app` changes
- no real SQLite / `consulting_os.db` access
- no service restarts
- no full accounting expansion
- no separate debt API
- no subscription API changes
- no dual-write

---

C1c complete locally. Approval required before C2c write-import planning.
