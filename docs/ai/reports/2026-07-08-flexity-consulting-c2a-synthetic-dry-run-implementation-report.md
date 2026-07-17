# Flexity Consulting C2a Synthetic Dry-Run Implementation Report

**Дата:** 2026-07-08  
**Статус:** C2a local implementation completed  
**Режим:** synthetic/local-only dry-run  
**Архитектурное правило:** Flexity Core = REST/API target. Import generates/validates Core API-shaped payloads. Target adapter = dry-run/no-op only (no direct PostgreSQL inserts, no Core DB writes, no production API calls).

---

## Task Classification

1. **Project:** Flexity  
2. **Category:** platform_core (local import dry-run tooling)  
3. **Risk level:** low (synthetic + no-op only)  
4. **Intended scope:** `backend/app/modules/imports_dry_run/*`, `backend/scripts/c2a_synthetic_dry_run.py`, `backend/tests/test_imports_dry_run.py`, this report  
5. **Forbidden scope:** production data, real SQLite adapter, Core DB writes, production API calls, deploy, migrations, legacy `/dashboard` or `/var/www/consult_app`, dual-write  
6. **Required plan:** implementation (approved for C2a synthetic dry-run only)

---

## 1) Files changed

### Code
- `backend/app/modules/imports_dry_run/__init__.py`
- `backend/app/modules/imports_dry_run/schemas.py` (includes `TenantBranchReadiness`)
- `backend/app/modules/imports_dry_run/synthetic_fixtures.py`
- `backend/app/modules/imports_dry_run/pipeline.py`
  - Synthetic source adapter
  - Legacy-to-Core mapping/transform
  - Validation layer
  - Dry-run/no-op target adapter (REST DTO validation only)
  - Import batch summary + warning/error report
  - Tenant / `default_branch` readiness check
- `backend/scripts/c2a_synthetic_dry_run.py`

### Tests
- `backend/tests/test_imports_dry_run.py`

### Report
- `docs/ai/reports/2026-07-08-flexity-consulting-c2a-synthetic-dry-run-implementation-report.md`

---

## 2) Tests run / results

Command:

```text
python -m pytest tests/test_imports_dry_run.py tests/test_status_mapping_contracts.py tests/test_import_summary_contract.py -q
```

Result:

- **11 passed**
- **0 failed**
- warnings only (existing SQLite FK-cycle warning in test teardown)

Additional local execution:

```text
python scripts/c2a_synthetic_dry_run.py
```

Result: successful synthetic summary/report JSON output (no PII, no DB/API writes).

---

## 3) Pipeline structure (implemented)

1. **Synthetic source adapter** — `SyntheticSourceAdapter` + `build_consulting_synthetic_fixture()`  
2. **Legacy-to-Core mapping/transform** — C1 helpers (`map_legacy_order_status`, stage status, contract assessment, payment type)  
3. **Validation layer** — statuses, required fields, duplicates/orphans, policy checks, finance aggregates, tenant/branch readiness  
4. **Dry-run/no-op target adapter** — validates payloads against Core REST DTO schemas; never calls HTTP; never writes DB  
5. **Import batch summary + warning/error report** — `ImportBatchSummary` + `DryRunValidationReport`

---

## 4) Synthetic scenarios covered

C2a fixture intentionally includes synthetic non-PII cases:

- duplicate user login warning;
- unknown order status warning;
- unknown stage status warning;
- missing `order_stages.template_id` fallback warning;
- orphan references:
  - order → missing client,
  - stage → missing order,
  - order item → missing order/service,
  - payment → missing order;
- `contracts.order_id NULL` policy warning;
- zero contract amount policy warning;
- unknown payment type warning;
- finance aggregate consistency check (`source_total == mapped_total`);
- tenant + `default_branch` assignment readiness (pass with IDs; fail without `default_branch_id`).

---

## 5) Validation rules covered

- status mapping (orders / stages / contracts / payments);
- required fields (e.g. user login, client display name);
- unknown statuses/types → review warnings;
- duplicates / orphans;
- zero contract amount policy;
- `contracts.order_id NULL` policy;
- `order_stages.template_id NULL` policy;
- finance aggregate checks;
- tenant / `default_branch` assignment readiness;
- generated payload compatibility with existing Core REST API schemas (DTO `model_validate`).

---

## 6) Import summary example (no PII)

Example from local script run (`scenario_name=c2a_default`):

| Field | Value |
|---|---|
| `total_source_rows` | 16 |
| `total_imported_rows` | 16 |
| `total_skipped_rows` | 0 |
| `total_error_rows` | 0 |
| `total_review_rows` | 9 |
| `status_mapping_warnings` | 3 |
| `source_system` | `consult_app_synthetic` |
| finance check | `source=9500`, `mapped=9500`, `difference=0`, `passed=true` |
| tenant/branch readiness | `passed=true` (synthetic tenant + default_branch IDs) |

No personal data values were used; only synthetic placeholders and technical IDs.

---

## 7) Generated payloads vs existing Core REST API schemas

C2a uses `source → map → validate → no-op target` (REST-shaped payloads only).

| Endpoint | Schema | Match | Notes |
|---|---|---|---|
| `/api/v1/tenants` | `TenantCreate` + `TenantResponse` | **ready** | Create/response validated; `default_branch` expected from Core tenant create |
| `/api/v1/parties` | `PartyCreate` | **ready** | Match yes |
| `/api/v1/catalog/items` | `CatalogItemCreate` | **ready** | Match yes |
| `/api/v1/work-items` | `WorkItemCreate` | **ready** | Match yes |
| `/api/v1/documents/generate` | `DocumentGenerateRequest` | **partial** | Generate exists; no direct contract import/upsert endpoint |
| `/api/v1/finance/payments` | `PaymentCreate` | **partial** | Amount/status OK; legacy INCOME/EXPENSE direction only via transform/notes |

### Missing / partial target API endpoints

1. **Documents import (partial):** direct contract instance create/upsert missing; only generate flow exists.  
2. **Finance direction (partial):** no explicit direction field on `PaymentCreate`; legacy semantics are indirect.

---

## 8) Are C1b / C1c Core API readiness fixes needed before real import?

For **C2a**: **not required** — synthetic dry-run completed locally.

Before **real import / staging REST target (C2c and later)**, **yes — minimal C1b/C1c-style API readiness items**:

1. Document import contract: direct contract create/upsert vs generate-only.  
2. Explicit finance direction (or approved mapping contract) for legacy payment INCOME/EXPENSE.  
3. Confirm tenant create always provisions `default_branch` and import context requires both IDs (already validated in C2a dry-run).

These are blockers for **real write import**, not for C2a or read-only C2b source planning.

---

## 9) What remains for C2b

- Plan + implement **read-only SQLite source adapter** (only after separate approval).  
- Keep dry-run / no-op target by default.  
- Wire real source rows into existing mapping/validation pipeline.  
- Re-run synthetic + real-adapter dry-run tests on local/staging-safe fixtures.  
- Still **no** production SQLite by default, **no** Core writes, **no** dual-write.  
- Staging REST write client = **C2c**, separately approved.

---

## 10) Risks

1. Partial documents/finance API fit can block or ambiguity real import until C1b/C1c decisions.  
2. Review-warning volume will grow on real legacy data.  
3. Moving from C2a → C2b must keep no-write / no-production-data guarantees unless explicitly approved.  
4. Treating import as direct SQL inserts would violate Core REST target architecture — forbidden by design.

---

## 11) Rollback notes

If C2a rollback is needed:

1. Remove `backend/app/modules/imports_dry_run/`.  
2. Remove `backend/scripts/c2a_synthetic_dry_run.py`.  
3. Remove `backend/tests/test_imports_dry_run.py`.  
4. Re-run related contract/dry-run tests to confirm baseline.

No DB rollback needed: C2a performs no migrations and no DB writes.

---

## 12) Compliance confirmation

Confirmed in C2a:

- no production data used;  
- no real SQLite source adapter;  
- no access to `consulting_os.db`;  
- no import execution against Core/production;  
- no data export of real client data;  
- no deploy;  
- no migrations;  
- no Core API write calls;  
- no Core DB writes;  
- no direct PostgreSQL insert design;  
- no dual-write;  
- no legacy `/dashboard` changes;  
- no `/var/www/consult_app` changes.

---

C2a synthetic dry-run complete locally. Approval required before C2b real source adapter planning.
