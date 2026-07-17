# Implementation Plan: Gate B Real-Source Read-Only Dry-Run Adapter (Preparation Only)

**Дата:** 2026-07-09
**Статус:** waiting for approval — **GATE B PREPARATION ONLY**
**Режим:** planning only — no dry-run execution, no real-source reads, no SQLite/Core writes, no import

---

## 1) Task classification

| Параметр | Значение |
|---|---|
| Project | Flexity Core / Consulting → Core migration |
| Category | documentation_only (this step); next step = minimal `universal_module` adapter code |
| Risk level | medium/high — next approved step touches real client SQLite read-only |
| Intended scope | Gate B adapter plan + minimal implementation proposal (no code in this step) |
| Forbidden scope | dry-run execution, raw PII reads/prints, SQLite writes, Core writes, import, write-import, live upgrade/deploy, `/dashboard` changes |
| Required plan type | implementation plan (code changes blocked until §16 approval checklist) |
| Prior gate | Gate A preflight **PASS** → `READY_FOR_GATE_B_DRY_RUN` |

**Related artifacts:**

- Gate A report: `docs/ai/reports/2026-07-09-consulting-to-core-real-source-preflight-report.md`
- Dry-run gates plan: `docs/ai/plans/2026-07-09-consulting-to-core-real-source-dry-run-plan.md`
- C2b synthetic adapter plan: `docs/ai/plans/2026-07-08-flexity-consulting-c2b-readonly-sqlite-source-adapter-plan.md`
- Gate 3 mapping: `docs/ai/specs/2026-07-08-flexity-consulting-gate3-migration-mapping-spec.md`
- Backup runbook: `docs/ai/runbooks/2026-07-08-flexity-consulting-import-backup-rollback-runbook.md`

---

## 2) Goal (this document only)

Подготовить **минимальный и безопасный** план изменений, чтобы Gate B (real-source read-only dry-run) можно было запустить **после отдельного approval**, не нарушая:

- fail-closed guards;
- read-only SQLite;
- no-write Core target;
- masked-only reporting;
- backup ID + tenant context requirements.

**Этот документ не разрешает запуск Gate B.**

---

## 3) Current state (as-is)

### 3.1 Pipeline architecture (reusable)

```
ReadonlySqliteSourceAdapter.load()
  → SyntheticDryRunPipeline.run(context)
    → map/transform/validate
    → DryRunNoOpTargetAdapter (DTO validate only, no REST/DB writes)
    → ImportBatchSummary + DryRunValidationReport
```

| Component | Path | Role |
|---|---|---|
| C2b entry (synthetic only) | `backend/scripts/c2b_readonly_dry_run.py` | Builds `consulting_legacy_min.sqlite`, hardcoded UUIDs, prints JSON to stdout |
| SQLite RO helpers | `backend/app/modules/imports_dry_run/sqlite_readonly.py` | `open_readonly_sqlite()`, write probe, **production path blocklist** |
| Source adapter | `backend/app/modules/imports_dry_run/sqlite_source_adapter.py` | `SELECT *` from 8 domain tables, synthetic schema fingerprint |
| Schema fingerprint | `backend/app/modules/imports_dry_run/schema_fingerprint.py` | `EXPECTED_TABLES` / `EXPECTED_SCHEMA_FINGERPRINT` aligned to **synthetic fixture** |
| Synthetic fixture | `backend/app/modules/imports_dry_run/synthetic_sqlite_fixture.py` | Simplified legacy-shaped DDL (TEXT ids, `users.login`, subset columns) |
| Masking | `backend/app/modules/imports_dry_run/masking.py` | `mask_row_for_log`, `assert_no_raw_pii` |
| Pipeline | `backend/app/modules/imports_dry_run/pipeline.py` | `SyntheticDryRunPipeline`, `DryRunNoOpTargetAdapter` |
| Context schema | `backend/app/modules/imports_dry_run/schemas.py` | `SyntheticDryRunContext` (`tenant_id`, `default_branch_id`, `created_by_user_id`, …) |
| Tests | `backend/tests/test_imports_sqlite_readonly.py`, `backend/tests/test_imports_dry_run.py` | Synthetic-only coverage |

### 3.2 Synthetic-only limitation (critical)

| Limitation | Detail |
|---|---|
| Entry script | `c2b_readonly_dry_run.py` always regenerates synthetic fixture; no CLI, no `--source-db` |
| Path guard | `assert_path_allowed_for_c2b()` **rejects** any path containing `consulting_os.db` or `/var/www/consult_app` |
| Schema profile | `EXPECTED_SCHEMA_FINGERPRINT` matches **synthetic** DDL, not production `consulting_os.db` |
| Column shape | Synthetic: TEXT ids, `users.login`; Production (Gate A): INTEGER ids, `users.email`/`name`, richer `clients`/`payments` columns |
| Tenant context | Hardcoded test UUIDs in script; no validation against staging tenant |
| Output | stdout JSON only; no masked report file; no backup ID gate |
| Real-source entry | `c2b_real_source_dry_run.py` **does not exist** |

**Implication:** even if path block were removed today, adapter would fail `SchemaMismatchError` on production DB without a **production schema profile** and column normalization layer.

### 3.3 Gate A blockers carried into Gate B prep

| # | Blocker | Status after this plan |
|---|---|---|
| 1 | Separate Gate B dry-run approval | Still required (unchanged) |
| 2 | Backup ID per runbook | Addressed in plan §7; enforcement in code proposal §11 |
| 3 | Script is synthetic-only | Addressed — new real-source entry + mode split §6, §11 |
| 4 | `sqlite_readonly.py` blocks production path | Addressed — allowlist mode §8 |
| 5 | Tenant UUID + `default_branch_id` | Addressed — required CLI flags §6, §9 |
| 6 | Masked PII review after Gate B | Process gate §10; not part of adapter code |

---

## 4) Proposed minimal architecture (to implement after approval)

### 4.1 Mode split (fail-closed default)

| Mode | Path policy | Schema profile | Entry |
|---|---|---|---|
| `synthetic` (default) | Block production fragments (current behavior) | `synthetic` fingerprint | existing `c2b_readonly_dry_run.py` unchanged behavior |
| `real-source-readonly` | **Allowlist only** (§8) | `production_gate_b` fingerprint + SQL projection | new `c2b_real_source_dry_run.py` |

Default for any new helper: **synthetic-safe**. Real-source opens only when **all** gates pass (§12).

### 4.2 New / changed modules (minimal surface)

| File | Change type | Purpose |
|---|---|---|
| `backend/app/modules/imports_dry_run/sqlite_readonly.py` | extend | Split `assert_path_allowed_for_c2b_synthetic()` vs `assert_path_allowlisted_for_real_source()`; shared `open_readonly_sqlite_uri()` |
| `backend/app/modules/imports_dry_run/real_source_allowlist.py` | **new** | Canonical allowlisted paths + backup ID format validation |
| `backend/app/modules/imports_dry_run/production_schema_fingerprint.py` | **new** | Production table/column expectations from Gate A inventory (aggregates only, no row samples) |
| `backend/app/modules/imports_dry_run/sqlite_source_adapter.py` | extend | `schema_profile: Literal["synthetic", "production_gate_b"]`; production SQL with column projection to pipeline domain dicts |
| `backend/app/modules/imports_dry_run/masked_report.py` | **new** | Build Gate B report JSON: aggregates, issue codes, masked samples only |
| `backend/scripts/c2b_real_source_dry_run.py` | **new** | CLI entry with required flags; fail-closed preflight |
| `backend/tests/test_real_source_allowlist.py` | **new** | Allowlist + fail-closed cases (no real DB) |
| `backend/tests/test_production_schema_fingerprint.py` | **new** | Fingerprint unit tests from inline DDL fixtures (synthetic production-shaped DDL in test, not real DB) |

**Non-touch (this phase):** `pipeline.py` mapping logic (reuse as-is), `DryRunNoOpTargetAdapter`, migrations, auth, tenants service, live/staging deploy scripts.

---

## 5) Proposed CLI flags

New script: `backend/scripts/c2b_real_source_dry_run.py`

| Flag | Required | Description |
|---|---|---|
| `--mode` | yes | Must be exactly `real-source-readonly` (explicit opt-in) |
| `--source-db` | yes | Absolute path; must match allowlist (§8) |
| `--backup-id` | yes | Operator-recorded backup ID per runbook; non-empty, format validated |
| `--tenant-id` | yes | UUID of **existing** staging dry-run tenant (not auto-created) |
| `--default-branch-id` | yes | UUID of tenant's default branch (must match `tenants.default_branch_id` when verified read-only) |
| `--output` | yes | Masked report path **outside git** (e.g. `/opt/flexity/import_work/reports/...`) |
| `--created-by-user-id` | optional | UUID for audit context; default = well-known dry-run system user constant |
| `--scenario-name` | optional | Default `gate_b_real_source_readonly` |
| `--max-rows-per-table` | optional | Emergency cap for debugging only; **disallowed in production Gate B** unless explicit debug approval |
| `--allow-schema-drift` | optional | Default **false**; if true, log drift fingerprint but still fail on missing required columns |

**Forbidden flags (must not exist):**

- `--write-import`
- `--target-db-url` with write mode
- `--dump-raw-rows`
- `--copy-db`
- `--skip-backup-id`
- `--skip-allowlist`

**Synthetic script** (`c2b_readonly_dry_run.py`): keep as-is; no `--mode real-source-readonly` on that entry point (separate binaries = clearer ops boundary).

---

## 6) Allowlist strategy

### 6.1 Canonical allowlisted paths (initial)

Paths normalized to resolved absolute POSIX form before compare:

| ID | Path | Notes |
|---|---|---|
| `prod_ro_primary` | `/var/www/consult_app/instance/consulting_os.db` | Gate A confirmed source; URI `mode=ro` only |
| `import_work_copy` | `/opt/flexity/import_work/consulting_os_readonly_*.db` | Optional immutable copy pattern (glob on filename date suffix) |

**Not allowlisted:** any path under repo `tests/`, developer home dirs, Windows paths, symlinks escaping allowlist root.

### 6.2 Enforcement rules

1. `--source-db` resolved with `Path.resolve()`; reject symlinks pointing outside allowlist target directory.
2. Filename for copy pattern must match `consulting_os_readonly_YYYYMMDD.db`.
3. If path matches **both** allowlist and old block fragments → allowlist wins **only** in `real-source-readonly` mode.
4. In `synthetic` mode, block fragments remain enforced (no regression).
5. Env var override (e.g. `FLEXITY_DRY_RUN_SOURCE_SQLITE`) **not accepted** without matching CLI `--source-db` (prevents accidental implicit runs).

### 6.3 Fail-closed on allowlist

| Condition | Result |
|---|---|
| Path not in allowlist | `exit 2` + `BlockedSqlitePathError` message (no path contents read) |
| Path does not exist | `exit 2` + `FileNotFoundError` |
| Path is directory | `exit 2` |
| Block fragment match in synthetic mode | `exit 2` (unchanged) |

---

## 7) Backup ID requirement

Per `docs/ai/runbooks/2026-07-08-flexity-consulting-import-backup-rollback-runbook.md`:

| Rule | Enforcement |
|---|---|
| `--backup-id` required | Script refuses start if missing/blank |
| Format | `consulting-gate-b-YYYYMMDD-HHMM-<operator>` (documented constant; validated by regex) |
| Recorded externally | Backup ID echoed in report metadata only; script does **not** perform backup |
| No backup verification API yet | Operator attestation only; future hook optional |

Policy note: if operational backup artifact was originally tagged with another ID scheme,
record both values in docs:
- `original_generated_backup_id` (artifact-local historical ID)
- `validated_backup_attestation_id` (must satisfy CLI regex)

Report metadata block (masked output):

```json
{
  "gate": "B",
  "mode": "real-source-readonly",
  "backup_id": "<operator-supplied>",
  "source_db_basename": "consulting_os.db",
  "source_db_size_bytes": 1241088,
  "source_db_mtime_utc": "2026-06-29T16:25:48Z"
}
```

No full absolute path in committed docs; basename + size + mtime only.

---

## 8) Read-only SQLite enforcement

| Layer | Mechanism |
|---|---|
| Open | `sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)` |
| Write probe | `assert_connection_is_readonly()` — `CREATE TABLE` must raise `OperationalError` |
| Adapter | No `INSERT`/`UPDATE`/`DELETE`/`VACUUM`/`ATTACH` writable |
| Script | No copy/export side effects |
| Tests | Reuse `test_readonly_connection_rejects_writes` pattern for production-shaped test fixture |

**Explicit ban:** script must not create writable copies of source DB.

---

## 9) Tenant / default_branch dry-run context

Gate A confirmed staging has `branches` + `tenants.default_branch_id` at `0014`, but **no tenant was created** for import.

| Requirement | Detail |
|---|---|
| `--tenant-id` | UUID of pre-provisioned **staging-only** dry-run tenant (operator creates in separate approved step) |
| `--default-branch-id` | Must equal that tenant's `default_branch_id` |
| Validation (read-only) | Optional preflight query against staging Postgres **read-only** connection: verify tenant exists + branch FK — **separate approval**; not required for adapter code MVP |
| Pipeline context | `SyntheticDryRunContext(tenant_id=..., default_branch_id=..., source_system="legacy_consult_app", scenario_name="gate_b_real_source_readonly")` |
| `tenant_branch_readiness` | Pipeline already emits `TenantBranchReadiness`; Gate B report includes `passed` flag based on supplied UUIDs (existence check = phase 2) |

**MVP for adapter implementation:** require UUIDs + validate format; **do not** auto-create tenant/branch.

---

## 10) No-write Core enforcement

| Layer | Guarantee |
|---|---|
| Target adapter | Only `DryRunNoOpTargetAdapter` allowed in `real-source-readonly` mode |
| Guard | Script asserts `isinstance(target, DryRunNoOpTargetAdapter)` before `pipeline.run()` |
| No HTTP client | No `httpx`/`requests` calls in dry-run module path |
| No SQLAlchemy session writes | Script does not import Core DB session factory |
| No `POST`/`PUT`/`PATCH`/`DELETE` | Endpoint checks are schema validation counters only |

If future code adds `WriteImportTargetAdapter`, it must be **unimportable** from `c2b_real_source_dry_run.py` (separate module + explicit Gate D entry).

---

## 11) PII masking guarantees

### 11.1 In-memory processing

- Adapter may read raw rows in process memory (unavoidable for mapping) — **must not log them**.
- All stdout/stderr: aggregates and issue codes only.
- Optional debug sample rows: **disabled** in `real-source-readonly` mode.

### 11.2 Report output (`--output`)

Allowed fields:

- `summary` (ImportBatchSummary aggregates)
- `report.issue_codes`, warning/error counts
- `report.finance_check` (decimals only)
- `report.tenant_branch_readiness`
- `source.schema_fingerprint`, `source.row_counts` per table
- `source.system`, `scenario_name`, `backup_id`
- `target_endpoint_checks` (endpoint, schema_name, status, note)
- `quality_signals` (pre-known aggregates from Gate A: orphan counts, status histograms)

Forbidden in `--output`:

- Raw `display_name`, `email`, `phone`, `iin_bin`, `address`, `note`, `purpose`, `comment`, `body`, `password_hash`
- Full row dumps, CSV exports, base64 blobs
- `SELECT` snippets with literal values

### 11.3 Masking implementation

Before writing `--output`:

1. Run `assert_no_raw_pii()` against report dict with forbidden list built from **known synthetic test strings only** in unit tests; in production run, use structural guard (no keys in `SENSITIVE_KEYS` with unmasked values).
2. Any sample row inclusion must pass `mask_row_for_log()`.
3. Extend `SENSITIVE_KEYS` for Gate B: `counterparty_name`, `purpose`, `password_hash`, `name`, `first_name`, `last_name`, `contact_person`, `request_text`.

### 11.4 Post-Gate B human review (Gate C)

- Operator reviews masked JSON offline.
- No copy into `docs/ai/reports/` without redaction pass.
- Gate C approval separate from Gate B execution approval.

---

## 12) Fail-closed cases (complete list)

Script must `exit 2` (or raise caught fatal error) when:

| # | Condition |
|---|---|
| 1 | `--mode` missing or not `real-source-readonly` |
| 2 | `--source-db` missing |
| 3 | `--backup-id` missing or fails format validation |
| 4 | `--tenant-id` missing or not valid UUID |
| 5 | `--default-branch-id` missing or not valid UUID |
| 6 | `--output` missing or path inside git repo / under `backend/tests/` |
| 7 | `--source-db` not on allowlist |
| 8 | Source file not found |
| 9 | SQLite open not read-only (write probe fails open) |
| 10 | Production schema fingerprint missing required columns |
| 11 | Target adapter is not `DryRunNoOpTargetAdapter` |
| 12 | Report contains sensitive keys without masking |
| 13 | `assert_no_raw_pii` fails |
| 14 | `--max-rows-per-table` set without `FLEXITY_GATE_B_DEBUG=1` env (debug gate) |

---

## 13) Expected dry-run output path

| Artifact | Location | In git? |
|---|---|---|
| Primary masked report | `/opt/flexity/import_work/reports/real_source_dry_run_YYYYMMDD_HHMM.json` | **no** |
| Operator log | `/opt/flexity/import_work/reports/real_source_dry_run_YYYYMMDD_HHMM.log` (aggregates only) | **no** |
| Gate C summary (future) | `docs/ai/reports/2026-07-XX-consulting-to-core-gate-b-dry-run-report.md` | yes, after redaction |
| Source DB | `/var/www/consult_app/instance/consulting_os.db` | never |

---

## 14) Production schema profile (adapter design note)

Gate A confirms production differs from synthetic fixture. Minimal production profile for Gate B **wave-1 tables only**:

| Table | Production specifics | Projection to pipeline domain |
|---|---|---|
| `users` | INTEGER `id`, `email`, `name` | `id=str(id)`, `login=email or name`, `is_active` from column or default true |
| `clients` | `name` not `display_name` | `display_name=name`, map `status`, `party_type`, `email` |
| `orders` | INTEGER ids, extra columns ignored | core fields: `id`, `number`, `client_id`, `status` |
| `order_stages` | `template_id` often NULL | pass through; pipeline emits orphan warnings |
| `order_items` | `amount` numeric/text | `Decimal` coercion (existing) |
| `contracts` | richer schema | core fields + amount/status |
| `payments` | `type`, `dds_kind_id`, etc. | core fields for C1c direction mapping |

Fingerprint: hash of **column names + types** for wave-1 tables only (52-table full inventory not required for Gate B).

`allow_schema_mismatch=True` **not** default for real-source; extra columns OK, missing required columns = hard fail.

---

## 15) Test plan (for implementation phase)

| Test | Type | Notes |
|---|---|---|
| Allowlist accepts canonical prod path | unit | mock filesystem / temp file at allowed path |
| Allowlist rejects `tests/fixtures`, relative paths, random `/tmp` | unit | |
| Blocklist still blocks prod path in synthetic mode | unit | regression |
| `--backup-id` required | unit | argparse / preflight |
| Missing tenant UUID fails | unit | |
| Output path inside repo rejected | unit | |
| Production-shaped DDL fixture loads via `schema_profile=production_gate_b` | unit | **no real DB** |
| INTEGER id normalization | unit | |
| Masked report has no sensitive keys | unit | `assert_no_raw_pii` |
| Pipeline integration with production-shaped fixture + `DryRunNoOpTargetAdapter` | unit | copy of `test_adapter_feeds_c2a_pipeline_without_core_writes` |
| End-to-end script dry-run | **not in CI** | requires Gate B approval + real path |

**Explicitly not run in this planning step:** any test touching `/var/www/consult_app/...`.

---

## 16) Command template — DO NOT RUN WITHOUT SEPARATE GATE B APPROVAL

```bash
# =============================================================================
# DO NOT RUN WITHOUT SEPARATE GATE B APPROVAL
# Preconditions:
#   1. Gate B dry-run approval (operator sign-off)
#   2. Backup ID recorded per runbook
#   3. Minimal adapter implementation merged (§18)
#   4. Staging dry-run tenant + default_branch UUIDs provisioned
#   5. Adapter code review complete
# =============================================================================

BACKUP_ID="consulting-gate-b-YYYYMMDD-HHMM-operator"   # replace after real backup recorded
TENANT_ID="00000000-0000-0000-0000-000000000000"       # replace: staging dry-run tenant
BRANCH_ID="00000000-0000-0000-0000-000000000000"       # replace: tenant.default_branch_id
SOURCE_DB="/var/www/consult_app/instance/consulting_os.db"
REPORT_DIR="/opt/flexity/import_work/reports"
STAMP="$(date -u +%Y%m%d_%H%M)"
OUTPUT="${REPORT_DIR}/real_source_dry_run_${STAMP}.json"

mkdir -p "${REPORT_DIR}"

cd /opt/flexity/coreops_staging_0013/runner/backend

/opt/flexity/envs/coreops/bin/python scripts/c2b_real_source_dry_run.py \
  --mode real-source-readonly \
  --source-db "${SOURCE_DB}" \
  --backup-id "${BACKUP_ID}" \
  --tenant-id "${TENANT_ID}" \
  --default-branch-id "${BRANCH_ID}" \
  --output "${OUTPUT}"

# Post-run (Gate C): review masked JSON offline; do not paste raw content into chat/docs
```

**Local dev:** same CLI; allowlist will reject Windows local paths — use synthetic script for local dev.

---

## 17) Implementation steps (ordered, after §19 approval)

| Step | Action | Verification |
|---|---|---|
| 1 | Add `real_source_allowlist.py` + tests | pytest allowlist |
| 2 | Refactor `sqlite_readonly.py` (synthetic vs real-source guards) | regression `test_imports_sqlite_readonly.py` |
| 3 | Add `production_schema_fingerprint.py` + production-shaped test DDL | pytest fingerprint |
| 4 | Extend `sqlite_source_adapter.py` with `schema_profile` + production SQL projection | adapter unit tests |
| 5 | Add `masked_report.py` builder | masking tests |
| 6 | Add `c2b_real_source_dry_run.py` CLI with fail-closed preflight | argparse tests |
| 7 | Integration test: production-shaped fixture → pipeline → masked report | pytest |
| 8 | Document operator steps in Gate B runbook addendum (optional doc) | review |
| 9 | **Stop** — request Gate B execution approval (separate from implementation approval) | — |

**Estimated touch:** ~6–8 files, ~400–600 LOC, no migrations, no new dependencies.

---

## 18) Non-goals (explicit)

- Running Gate B dry-run (this plan)
- Reading production rows during planning
- Write-import / Gate D
- Creating staging tenant via script (manual/separate gate)
- Performing backup (operator manual per runbook)
- Changing `consulting_os.db` or Consulting Flask `/dashboard`
- Upgrading live `coreops` DB
- Deploying to production/staging services
- Importing integration/messaging/purchases tables (wave 2+)
- Full 52-table schema fingerprint
- HTTP calls to Core API (even GET) in MVP adapter

---

## 19) Approval gate for minimal implementation

Code changes to real-source path handling are **blocked** until checklist §20 is approved.

Implementation approval covers **adapter code only**, not Gate B execution.

---

## 20) Approval checklist

- [ ] approve real-source adapter minimal implementation
- [ ] approve source path allowlist (`prod_ro_primary` + optional `import_work_copy` pattern)
- [ ] approve backup ID requirement (`--backup-id` mandatory)
- [ ] approve tenant/default_branch dry-run context (required UUIDs, no auto-create)
- [ ] approve masked output format (`--output` outside git, §11 rules)
- [ ] still block actual Gate B dry-run (separate execution approval)
- [ ] still block write-import
- [ ] still block live upgrade/deploy

---

## 21) Risks

| Risk | Mitigation |
|---|---|
| Schema drift between Gate A and Gate B run | Production fingerprint fails closed; re-run Gate A lite if mtime changes |
| Accidental PII in report | `masked_report.py` + `assert_no_raw_pii` + Gate C review |
| Operator runs without backup | `--backup-id` required; runbook attestation |
| Wrong tenant UUID | Document staging-only tenant; future read-only FK check |
| Synthetic tests give false confidence | Production-shaped DDL fixture in tests (not real DB) |
| Path symlink escape | `resolve()` + reject symlinks outside allowlist root |

---

## 22) Final verdict (planning step)

### **READY_FOR_GATE_B_ADAPTER_IMPLEMENTATION**

Gate A preflight passed. Current synthetic-only pipeline is reusable. Blockers are well-defined and addressable with a minimal, bounded code change (§17) without touching live systems.

**Still blocked until separate approvals:**

- Gate B dry-run **execution** (§16)
- Write-import / Gate D
- Live upgrade/deploy

---

**Planning complete. Await §20 checklist approval before any real-source path handling code changes.**
