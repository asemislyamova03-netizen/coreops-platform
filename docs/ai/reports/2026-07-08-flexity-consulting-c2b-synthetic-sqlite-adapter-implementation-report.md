# Flexity Consulting C2b Synthetic SQLite Adapter Implementation Report

**Дата:** 2026-07-08
**Статус:** C2b-code local implementation completed
**Режим:** synthetic SQLite fixture only + read-only adapter + C2a dry-run pipeline
**План:** `docs/ai/plans/2026-07-08-flexity-consulting-c2b-readonly-sqlite-source-adapter-plan.md`

---

## Task Classification

1. **Project:** Flexity
2. **Category:** platform_core (local import dry-run tooling)
3. **Risk level:** low (synthetic fixture; no production DB)
4. **Intended scope:** `imports_dry_run/*` C2b modules, script, tests, fixture, this report
5. **Forbidden scope:** `consulting_os.db`, production data, export, Core writes/API writes, deploy, migrations, legacy `/dashboard` / `/var/www/consult_app`
6. **Required plan:** approved C2b-code (synthetic fixture only)

---

## 1) Files changed

### Code (new)
- `backend/app/modules/imports_dry_run/sqlite_readonly.py` — RO open + no-write assert + production path blocklist
- `backend/app/modules/imports_dry_run/sqlite_source_adapter.py` — `ReadonlySqliteSourceAdapter`
- `backend/app/modules/imports_dry_run/masking.py` — log/report field masking
- `backend/app/modules/imports_dry_run/schema_fingerprint.py` — expected schema fingerprint + mismatch gate
- `backend/app/modules/imports_dry_run/synthetic_sqlite_fixture.py` — builder for synthetic legacy-shaped SQLite
- `backend/scripts/c2b_readonly_dry_run.py` — local dry-run entry (synthetic DB only)

### Code (updated)
- `backend/app/modules/imports_dry_run/__init__.py` — package docstring
- `backend/app/modules/imports_dry_run/pipeline.py` — source typing accepts any `.load()` adapter (C2a + C2b)
- `backend/app/modules/imports_dry_run/schemas.py` — `ImportDryRunContext` alias
- `backend/.gitignore` — ignore `tests/_c2b_tmp/`

### Tests / fixture
- `backend/tests/test_imports_sqlite_readonly.py` (new)
- `backend/tests/fixtures/consulting_legacy_min.sqlite` (synthetic DB file, generated locally)

### Report
- `docs/ai/reports/2026-07-08-flexity-consulting-c2b-synthetic-sqlite-adapter-implementation-report.md`

---

## 2) Tests run / results

Command:

```text
python -m pytest tests/test_imports_sqlite_readonly.py tests/test_imports_dry_run.py tests/test_status_mapping_contracts.py tests/test_import_summary_contract.py -q
```

Result:

- **21 passed**
- **0 failed**
- warnings only (existing SQLite FK-cycle teardown warning)

Additional:

```text
python scripts/c2b_readonly_dry_run.py
```

Result: successful summary with `source_system=legacy_consult_app`, finance check passed, no-op target endpoint checks recorded.

Covered in `test_imports_sqlite_readonly.py`:

- schema fingerprint match
- read-only insert rejection + writable connection fail closed
- production path block (`consulting_os.db`)
- adapter DTO parity with C2a synthetic fixture
- adapter → C2a pipeline dry-run (no Core writes)
- `max_rows_per_table` batching
- schema mismatch raise / explicit allow
- masking / no raw PII assert

---

## 3) Synthetic SQLite fixture structure

Built by `build_synthetic_sqlite_fixture()` from C2a `build_consulting_synthetic_fixture()` data (fictional `@synthetic.local` only).

| Table | Purpose | Synthetic rows (default) |
|---|---|---:|
| `users` | login / active | 3 (incl. duplicate login) |
| `clients` | parties preview | 2 |
| `services` | catalog | 2 |
| `orders` | work items | 3 (incl. unknown status + orphan client) |
| `order_stages` | stages | 3 (NULL template_id + unknown status) |
| `order_items` | lines | 3 (orphan order/service cases) |
| `contracts` | documents | 2 (NULL order_id + zero amount) |
| `payments` | finance | 3 (unknown type + orphan order) |

Canonical local file:

- `backend/tests/fixtures/consulting_legacy_min.sqlite`

No real personal data. No copy of production DB.

---

## 4) Read-only / no-write guarantees

1. Open via SQLite URI `file:…?mode=ro`.
2. `assert_connection_is_readonly()` probes `CREATE TABLE` and fails closed if writable.
3. Tests assert `INSERT` raises `OperationalError` on RO connection.
4. Path blocklist refuses `consulting_os.db` and `/var/www/consult_app`.
5. Target remains `DryRunNoOpTargetAdapter` — DTO validate only; **no HTTP**, **no Core DB**.
6. Adapter performs only `SELECT` (+ schema pragma reads).

---

## 5) Masking / logging behavior

`masking.py`:

- Sensitive keys (`display_name`, `email`, `phone`, `iin*`, `notes`, document text, etc.) → masked.
- Emails keep domain, hide local part (`c***@synthetic.local` style).
- `assert_no_raw_pii()` fails if forbidden raw fragments appear in serialized log payload.
- Pipeline summaries stay aggregate / issue-code based (no customer row dumps).

---

## 6) Schema mismatch behavior

- Expected fingerprint computed from C2b expected table/column/type baseline.
- On load, adapter compares live fingerprint; mismatch → `SchemaMismatchError` (fail closed).
- Override only via explicit `allow_schema_mismatch=True` (for controlled review experiment; not default).

---

## 7) How adapter connects to C2a pipeline

```text
ReadonlySqliteSourceAdapter.load()
        ↓  same dict[str, list[dict]] as SyntheticSourceAdapter
SyntheticDryRunPipeline.run(context)
        ↓  C1 mapping + validation (unchanged)
DryRunNoOpTargetAdapter (REST DTO validate, no-op)
        ↓
ImportBatchSummary + DryRunValidationReport
```

- Mapper/validator **not bypassed**.
- Source IDs remain in row `id` fields / later metadata external refs; Core PKs not invented as truth.
- Context `source_system` for C2b runs: `legacy_consult_app`.

---

## 8) Compliance confirmation

Confirmed for this C2b-code step:

- no real `consulting_os.db` access;
- no production data;
- no data export of real client DB;
- no import into Core;
- no Core API writes;
- no Core DB writes;
- no deploy / migrations / service restarts;
- no legacy `/dashboard` or `/var/www/consult_app` changes;
- no dual-write.

---

## 9) What remains before real-source dry-run (C2b-dry-run)

1. Separate **approval** for real-source dry-run (≠ this C2b-code approval).
2. Confirmed **source DB backup ID** per import runbook.
3. Path allowlist / runtime config for production path (currently blocked by design in C2b-code).
4. Off-peak / short RO read procedure to limit SQLite lock risk.
5. Re-run dry-run locally/on server with aggregate-only report (no PII).
6. Keep no-op target until C2c staging REST adapter is approved.

---

## 10) Are C1c Core API readiness fixes still needed?

**For C2b synthetic / future real-source dry-run (no-op target):** no — documents/payments partial APIs do not block read-only source validation.

**For C2c / real write import:** **yes, still needed** (parallel recommended):

1. Documents/contracts: direct create/upsert vs generate-only.
2. Payments: explicit direction / legacy INCOME–EXPENSE contract on finance API.

These remain blockers for faithful **write** import, not for C2b read-only adapter work.

---

## 11) Risks / rollback

**Risks:** path blocklist bypass if misconfigured later; schema drift on live DB; mistaken real dry-run without backup; PII if masking skipped on custom logs.

**Rollback:** remove C2b modules/script/tests/fixture; keep C2a path intact. No DB migration to undo.

---

C2b synthetic SQLite adapter complete locally. Approval required before real-source dry-run or any real SQLite access.
