# Implementation Plan: C2b Read-Only SQLite Source Adapter (Planning Only)

**Дата:** 2026-07-08  
**Статус:** waiting for approval (documentation-only)  
**Режим:** planning only — no code, no SQLite access, no data export, no production actions

---

## Task Classification

1. **Project:** Flexity  
2. **Category:** documentation_only  
3. **Risk level:** low (docs only); future C2b-code = medium (PII / live source risk)  
4. **Intended scope (this step):**  
   `docs/ai/plans/2026-07-08-flexity-consulting-c2b-readonly-sqlite-source-adapter-plan.md` only  
5. **Forbidden scope (this step and beyond without new approval):**  
   - production data / `consulting_os.db` reads  
   - SQLite copy/export  
   - Core API writes / Core DB writes  
   - deploy / migrations / service restarts  
   - legacy `/dashboard` or `/var/www/consult_app` changes  
   - dual-write  
6. **Required plan type:** implementation plan (planning-only; no code until C2b adapter implementation is separately approved)

### Inputs used

- `docs/ai/reports/2026-07-08-flexity-consulting-c2a-synthetic-dry-run-implementation-report.md`
- `docs/ai/plans/2026-07-08-flexity-consulting-c2-import-script-plan.md`
- `docs/ai/specs/2026-07-08-flexity-consulting-gate3-migration-mapping-spec.md`
- `docs/ai/research/2026-07-08-flexity-consulting-gate2-data-profiling-report.md`
- `docs/ai/research/2026-07-08-flexity-consulting-current-state-audit-report.md`

---

## Goal

Подготовить безопасный план подключения существующего C2a dry-run pipeline к реальной legacy SQLite БД `consult_app` **только в read-only режиме**, без реализации адаптера, без чтения БД и без записи в Core.

---

## 1. Executive summary

- **C2a** synthetic dry-run **завершён и принят**: pipeline  
  `synthetic source → map/transform → validation → dry-run/no-op REST target → import batch summary` работает локально.
- **C2b (этот документ)** планирует **только** будущий **read-only SQLite source adapter**.  
  Реализация кода и любой доступ к реальной SQLite **не входят** в этот шаг.
- Legacy `/dashboard` (`consult_app`) остаётся **bridge / reference / archive** на переходный период.
- Flexity Core остаётся **единственным REST/API target**. Import никогда не проектируется как direct PostgreSQL inserts.
- В фазе C2b planning: **нет** writes, **нет** imports, **нет** exports, **нет** чтения production DB, **нет** обработки персональных значений.

---

## 2. Source DB access model

| Item | Value / rule |
|---|---|
| Source path (Gate 1) | `/var/www/consult_app/instance/consulting_os.db` |
| App root (Gate 1) | `/var/www/consult_app` |
| Engine | SQLite (legacy single-tenant; `tenant_id` absent) |
| Access mode | **URI read-only** only (e.g. `file:<path>?mode=ro`) |
| Copy / export | **Forbidden by default**; any DB copy needs separate explicit approval |
| Business data dump | Forbidden |
| Personal values in logs/reports | Forbidden (mask / omit) |
| Diagnostics allowed | Aggregate counts, schema hashes, issue codes, synthetic IDs only |
| Backup before later real profiling/import | **Required** — confirm backup ID per runbook before any C2b-dry-run against live source |

### Required operational gates (future, not this doc step)

1. Confirmed backup of source DB + backup ID recorded.  
2. Explicit approval for **C2b adapter implementation**.  
3. Explicit approval for **C2b-dry-run against real source** (separate from implementation).  
4. No production cutover without still later approvals.

---

## 3. Read-only adapter architecture

### 3.1 High-level flow (unchanged from C2a)

```text
[ReadonlySqliteSourceAdapter]  → same legacy-shaped dict domain
        ↓
[mapping / transform (C1 helpers)]
        ↓
[validation layer]
        ↓
[DryRunNoOpTargetAdapter]  ← keep for C2b; REST write client = C2c only
        ↓
[ImportBatchSummary + DryRunValidationReport]
```

Core remains REST/API-shaped payload validation only. **No** Core HTTP writes in C2b.

### 3.2 Components (planned for future C2b-code)

1. **SQLite read-only connection factory**
   - Open via `mode=ro` (and preferably immutable `ro` flags where available).
   - Fail closed if connection is not read-only.
2. **Table readers per domain** (remain aligned with C2a fixture keys):
   - `users`, `clients`, `services`, `orders`, `order_stages`, `order_items`, `contracts`, `payments`
   - Optional later (out of first C2b slice unless approved): acts, suppliers, roles, activity_logs, finance dictionaries.
3. **Row streaming / batching**
   - Cursor / LIMIT-OFFSET or keyset batches.
   - Configurable `max_rows_per_table` for approved local/fixture tests; default unlimited only under approved dry-run.
4. **Field masking for any log path**
   - Names, phones, emails, notes, document text → masked or dropped before logger.
5. **Aggregate-only diagnostics**
   - Counts, NULL rates, status histograms, finance totals — no row dumps.
6. **Schema version / hash check**
   - Compute schema fingerprint (table+column+type signature) and compare to Gate 2 / expected baseline.
   - On mismatch: fail or require explicit override flag (never silent).
7. **Pipeline feed contract**
   - Adapter output **must** match C2a `SyntheticSourceAdapter.load()` shape: `dict[str, list[dict]]` of legacy-shaped rows.
   - Must **not** call mapper/validator internals. Must **not** invent target IDs as truth.

### 3.3 Planned files for future C2b-code (not now)

| Planned path | Role |
|---|---|
| `backend/app/modules/imports_dry_run/sqlite_readonly.py` | Connection + safety asserts |
| `backend/app/modules/imports_dry_run/sqlite_source_adapter.py` | Domain readers → legacy-shaped DTOs |
| `backend/app/modules/imports_dry_run/masking.py` | Log/report masking helpers |
| `backend/app/modules/imports_dry_run/schema_fingerprint.py` | Schema hash check |
| `backend/scripts/c2b_readonly_dry_run.py` | Entry (no-op target; requires flags) |
| `backend/tests/fixtures/consulting_legacy_min.sqlite` | **Synthetic** SQLite fixture (no real PII) |
| `backend/tests/test_imports_sqlite_readonly.py` | Adapter safety + feed tests |

### Files not to touch (C2b-code future)

- `/var/www/consult_app/**`, legacy Flask routes/templates  
- Core production deploy / Nginx / systemd  
- Migrations (unless separately approved)  
- Auth / billing / subscription plan changes  
- Dual-write infrastructure  

---

## 4. Safety controls

| Control | Rule |
|---|---|
| Open DB read-only | Mandatory `mode=ro` URI |
| Fail if write possible | Assert pragma / attempt; abort if writable |
| No write commits | Never `INSERT`/`UPDATE`/`DELETE`/`CREATE`; no write transactions |
| No temp export files with real data | Forbid sidecar CSV/JSON dumps of real rows |
| No raw PII logs | Logger filters + masked serializers |
| No full table dumps | Only aggregates and capped masked samples (if ever approved) |
| Configurable read limit | `max_rows_per_table` for fixture/local tests when later approved |
| Path allowlist | Configured source path only; refuse arbitrary paths without approval |
| Source system label | Always `legacy_consult_app` (never silent synthetic label on real source) |

---

## 5. Data protection rules

- Mask: names, phones, emails, notes, document/body text, addresses.  
- Never write IIN / BIN / passport / sensitive identifiers into markdown reports or CI logs.  
- Never paste raw customer records into AI/chat reports.  
- No screenshots of live data in planning/implementation docs.  
- No sending real DB content outside server / approved local environment.  
- Reports remain aggregate + issue codes + technical synthetic IDs only.  
- Gate 2 remnant: `clients` / `payments` / several finance dictionaries contain personal data — treat all client/payment text fields as sensitive by default.

---

## 6. Adapter output contract

Must be compatible with C2a synthetic source output:

1. **Same internal legacy-shaped DTOs** (keys/fields as in `build_consulting_synthetic_fixture()` / Gate 3 mapping inputs).  
2. **Must not bypass** mapper or validator — only replace the source adapter.  
3. **Preserve source IDs as `external_ref` / metadata only** (e.g. `metadata_json.synthetic_source_id` pattern → `legacy_*_id` / `external_legacy_id`), never as Core primary keys.  
4. **`source_system` = `legacy_consult_app`** for real adapter context (C2a used `consult_app_synthetic`).  
5. Tenant / `default_branch` still come from **import context**, not from SQLite (legacy has no `tenant_id`).  
6. Target remains **Core REST API-shaped payloads** via transform; no-op target in C2b.

---

## 7. Dry-run with real source — future C2b / C2c boundary

| Phase | Scope | Writes | Approval needed |
|---|---|---|---|
| **C2b planning** (this doc) | Documentation only | None | Accepted as planning |
| **C2b-code** | Implement read-only adapter + synthetic SQLite fixture tests | None to Core / legacy | Separate approval |
| **C2b-dry-run** | Real-source read-only dry-run → no-op target → summary | Read SQLite only; **no Core writes** | **Separate** from C2b-code |
| **C2c** | Staging Core **REST** target adapter (write to staging APIs if ready) | Staging API only | Separate; blocked by C1c gaps if write path needs docs/payments fixes |
| **Production cutover** | Live import / switch source of truth | Production | Separate multi-gate approval |

Boundaries:

- C2b never writes to Core.  
- C2c may write only via Core REST to staging after partial API gaps are addressed or explicitly waived.  
- No production cutover before separate approval.  
- No dual-write unless separately designed.

---

## 8. Known Core API gaps from C2a (impact on C2b vs write import)

From C2a report:

| Area | Status | Blocks C2b-code / C2b-dry-run? | Blocks C2c / real write import? |
|---|---|---|---|
| Parties / catalog / work-items | ready | No | No |
| Documents / contracts | **partial** (generate-only; no direct import/upsert) | No (mapping+validation still dry-run) | **Yes — needs C1c decision/contract before write import of contracts** |
| Payments / debts / direction | **partial** (no explicit direction on `PaymentCreate`) | No | **Yes — needs C1c finance direction contract before faithful payment write import** |
| Tenant / `default_branch` | readiness validated in C2a | No | Must remain required in context |

**Recommendation:**  
- Start C2b-code **without waiting for C1c** (source adapter + dry-run only).  
- Run **C1c in parallel** (docs import contract + payment direction) so C2c is not blocked later.  
- **Do not** promote C2c write-mode until C1c gaps are closed or explicitly accepted with documented limitations.

---

## 9. Tests required before any real-source run

Must pass **before** approved C2b-dry-run against live `consulting_os.db`:

1. **Synthetic regression** — existing C2a `test_imports_dry_run.py` + status/import summary contracts remain green.  
2. **Read-only connection test** — against **synthetic** SQLite fixture (not production DB).  
3. **No-write assertion test** — attempt/assert that connection rejects writes; pipeline never opens Core DB write session.  
4. **Masking / logging tests** — PII fields never appear in serialized report/log helpers.  
5. **Schema mismatch test** — altered fixture schema fails fingerprint check.  
6. **Batching test** — `max_rows_per_table` / stream batches produce stable counts.  
7. **Source contract test** — adapter output keys match synthetic fixture domains; `source_system=legacy_consult_app`.  
8. **Pipeline integration** — real-adapter feed + no-op target produces `ImportBatchSummary` without Core calls.

---

## 10. Risks

| Risk | Why it matters | Mitigation |
|---|---|---|
| Accidental PII leakage | Real clients/payments contain personal data | Masking, no row dumps, report policy |
| Accidental DB copy/export | Easy to “save a copy for debug” | Explicit forbid + review in QA |
| Schema drift | Live schema ≠ Gate 2 fingerprint | Schema hash gate |
| Source DB lock | SQLite + concurrent Flask traffic | Short RO queries; prefer off-peak; never open write |
| Stale data | Dry-run snapshot aged before cutover | Re-run dry-run near cutover; record run timestamp |
| Bypassing Core REST target | Temptation to SQL-insert into Postgres | Architecture rule: REST/API only; no-op or REST client |
| Treating dry-run as real import | Ops confusion | Explicit labels, no write flags, summary notes |
| Partial docs/payments APIs | C2c false readiness | Parallel C1c; block write import until closed |

---

## 11. Decision checkpoint

| Question | Decision |
|---|---|
| Can **C2b adapter implementation** start safely after this plan is approved? | **Yes**, as **C2b-code only**, against synthetic SQLite fixture first; still **no** production DB access until C2b-dry-run approval. |
| Should **C1c** Core API readiness fixes happen before or in parallel? | **In parallel** with C2b-code. **Required before** C2c write import of contracts/payments (not a blocker for read-only source work). |
| Does **real-source dry-run** need separate approval? | **Yes.** C2b-code approval ≠ C2b-dry-run approval. Backup ID + data-protection checklist required for real-source dry-run. |

### Preconditions before approving C2b-code

- C2a accepted (done).  
- This C2b plan approved.  
- Agreement: Core remains REST/API target; adapter feeds existing pipeline; no dual-write.  
- Test strategy includes synthetic SQLite fixture (no real PII).

### Still deferred

- Any connection to `/var/www/consult_app/instance/consulting_os.db`  
- Any copy/export of that DB  
- C2c staging REST write adapter  
- Production import / cutover  

---

## Scope (this documentation step)

### Files to modify

- `docs/ai/plans/2026-07-08-flexity-consulting-c2b-readonly-sqlite-source-adapter-plan.md` (create)

### Files not to touch

- All production code  
- All legacy Flask code  
- Migrations, env, deploy configs  
- Real SQLite DB  

---

## Steps (already completed by this document)

1. Restate C2a → C2b boundary.  
2. Define read-only access model from Gate 1 path.  
3. Define adapter architecture and output contract.  
4. Define safety, data protection, tests, risks, phase boundaries.  
5. Record decision checkpoint.  
6. **Stop** — wait for approval before C2b-code or any SQLite access.

---

## Tests/checks (this planning step)

- Documentation completeness vs user checklist: yes.  
- No code changes: yes.  
- No SQLite connection / export: yes.  
- No Core/legacy writes: yes.

---

## Rollback

N/A for planning-only doc. To discard: delete or ignore this plan file. No runtime state created.

---

## Approval

**Status: waiting for approval**

Approval required before C2b adapter implementation or any real SQLite access.
