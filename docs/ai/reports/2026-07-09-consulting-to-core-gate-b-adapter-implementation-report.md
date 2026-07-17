# Report: Consulting → Core Gate B Real-Source Adapter Implementation

**Дата:** 2026-07-09
**Статус:** implementation complete — **READY_FOR_GATE_B_DRY_RUN_APPROVAL**
**Режим:** adapter code only — no real-source dry-run executed

---

## 1) Task classification

| Параметр | Значение |
|---|---|
| Project | Flexity Core / Consulting → Core migration |
| Category | universal_module (`imports_dry_run` extension) |
| Risk level | medium — code enables future real-source read; not executed in this step |
| Scope | Gate B adapter minimal implementation only |
| Migrations | **no** |
| Live touched | **no** |
| Real-source dry-run executed | **no** |

**Basis:**

- Plan: `docs/ai/plans/2026-07-09-consulting-to-core-gate-b-real-source-adapter-plan.md`
- Gate A: `docs/ai/reports/2026-07-09-consulting-to-core-real-source-preflight-report.md`

---

## 2) Files changed

| File | Change |
|---|---|
| `backend/app/modules/imports_dry_run/real_source_allowlist.py` | **new** — allowlist, backup ID, output path guards |
| `backend/app/modules/imports_dry_run/production_schema_fingerprint.py` | **new** — wave-1 required columns check |
| `backend/app/modules/imports_dry_run/production_sqlite_fixture.py` | **new** — production-shaped synthetic test fixture |
| `backend/app/modules/imports_dry_run/masked_report.py` | **new** — aggregate-only report + PII scan |
| `backend/app/modules/imports_dry_run/gate_b_runner.py` | **new** — CLI validation + dry-run runner |
| `backend/app/modules/imports_dry_run/sqlite_readonly.py` | **updated** — synthetic vs real-source path guards |
| `backend/app/modules/imports_dry_run/sqlite_source_adapter.py` | **updated** — `schema_profile` synthetic / `production_gate_b` |
| `backend/scripts/c2b_real_source_dry_run.py` | **new** — thin CLI entry |
| `backend/tests/test_gate_b_real_source_adapter.py` | **new** — 24 tests |

---

## 3) Files intentionally not touched

| Area | Status |
|---|---|
| `backend/scripts/c2b_readonly_dry_run.py` | unchanged (synthetic entry) |
| `backend/app/modules/imports_dry_run/pipeline.py` | unchanged |
| Migrations / Alembic | unchanged |
| Auth / tenants service / live backend | unchanged |
| Consulting Flask `/dashboard` | unchanged |
| `consulting_os.db` (production) | not read |
| Staging/live Core DB | no writes |

---

## 4) CLI implemented

Entry: `backend/scripts/c2b_real_source_dry_run.py`
Core logic: `backend/app/modules/imports_dry_run/gate_b_runner.py`

### Required flags

| Flag | Enforcement |
|---|---|
| `--mode real-source-readonly` | fail if missing or different |
| `--source-db` | must match allowlist + exist |
| `--backup-id` | required; format `consulting-gate-b-YYYYMMDD-HHMM-operator` |
| `--tenant-id` | required UUID |
| `--default-branch-id` | required UUID |
| `--output` | required absolute path outside git repo |

### Optional flags

| Flag | Purpose |
|---|---|
| `--created-by-user-id` | audit context (default dry-run system UUID) |
| `--scenario-name` | default `gate_b_real_source_readonly` |
| `--overwrite` | allow replacing existing output file |

### Command template — DO NOT RUN WITHOUT SEPARATE GATE B APPROVAL

```bash
# DO NOT RUN WITHOUT SEPARATE GATE B APPROVAL
cd /opt/flexity/coreops_staging_0013/runner/backend

/opt/flexity/envs/coreops/bin/python scripts/c2b_real_source_dry_run.py \
  --mode real-source-readonly \
  --source-db /var/www/consult_app/instance/consulting_os.db \
  --backup-id consulting-gate-b-YYYYMMDD-HHMM-operator \
  --tenant-id <staging-dry-run-tenant-uuid> \
  --default-branch-id <tenant-default-branch-uuid> \
  --output /opt/flexity/import_work/reports/real_source_dry_run_YYYYMMDD_HHMM.json
```

---

## 5) Allowlist behavior

| Path | Allowed |
|---|---|
| `/var/www/consult_app/instance/consulting_os.db` | yes (Gate A canonical) |
| `/opt/flexity/import_work/consulting_os_readonly_YYYYMMDD.db` | yes (immutable copy pattern) |
| Local dev / repo / tests paths | **no** |

Synthetic mode (`open_readonly_sqlite`) still blocks `consulting_os.db` and `/var/www/consult_app` fragments.

Real-source mode uses separate guard (`open_readonly_sqlite_real_source`) — production path allowed only via allowlist.

---

## 6) Fail-closed cases implemented

| Case | Result |
|---|---|
| Wrong `--mode` | exit 2 |
| Missing/invalid `--backup-id` | exit 2 |
| Missing/invalid `--tenant-id` | exit 2 |
| Missing/invalid `--default-branch-id` | exit 2 |
| `--source-db` not allowlisted | exit 2 |
| Source file missing | exit 2 |
| `--output` inside git repo | exit 2 |
| `--output` under `backend/tests/` | exit 2 |
| `--output` exists without `--overwrite` | exit 2 |
| SQLite not read-only (write probe) | error |
| Production schema missing required columns | error |
| Target not `DryRunNoOpTargetAdapter` | error |
| Masked report PII scan failure | error (no file written) |

---

## 7) Masking behavior

- Report contains **aggregates only**: counts, issue codes, finance totals, endpoint check metadata.
- No raw row samples in Gate B report.
- Sensitive dict keys rejected if present with values (`email`, `phone`, `name`, `address`, etc.).
- Pattern scan on serialized JSON: email, phone, IIN-like 12-digit, long digit sequences.
- Known safe tokens scrubbed before scan: UUIDs, backup ID, ISO timestamps.
- Endpoint check field renamed to `detail` (avoids `note` false positive).

---

## 8) Production schema profile

- Profile: `schema_profile="production_gate_b"`
- Validates wave-1 tables + required columns (extra production columns allowed).
- Explicit `SELECT` column lists (no `SELECT *` in production mode).
- Column projection to C2a pipeline domain shape:
  - `users`: `email`/`name` → `login`
  - `clients`: `name` → `display_name`
  - INTEGER ids → `str`
- Synthetic profile unchanged and backward compatible.

---

## 9) Tests run / results

```text
pytest tests/test_gate_b_real_source_adapter.py tests/test_imports_sqlite_readonly.py -q
→ 34 passed

pytest tests/test_imports_dry_run.py -q
→ 4 passed

python -m compileall app/modules/imports_dry_run scripts/c2b_real_source_dry_run.py -q
→ OK
```

**Not run (by design):**

- real-source dry-run against `/var/www/consult_app/instance/consulting_os.db`
- write-import
- staging/live DB operations

---

## 10) Explicit safety statement

| Item | Status |
|---|---|
| Real-source dry-run executed | **no** |
| `consulting_os.db` read for rows | **no** |
| Raw PII printed | **no** |
| SQLite writes | **no** |
| Core writes | **no** |
| Live DB/backend touched | **no** |
| `/dashboard` changed | **no** |
| Write-import | **no** |
| Migrations | **no** |
| Production deploy | **no** |

---

## 11) Next gate

**Approve Gate B command dry-run only after:**

1. Operator records backup ID per runbook.
2. Staging dry-run tenant + `default_branch_id` UUIDs provisioned.
3. Separate Gate B **execution** approval (distinct from this adapter implementation approval).
4. Post-run masked report review (Gate C).

---

## 12) Final verdict

### **READY_FOR_GATE_B_DRY_RUN_APPROVAL**

Adapter implementation complete and tested locally. Gate B execution remains blocked until separate operator approval and preconditions above.

---

**Stop. Do not run real-source dry-run without explicit Gate B execution approval.**
