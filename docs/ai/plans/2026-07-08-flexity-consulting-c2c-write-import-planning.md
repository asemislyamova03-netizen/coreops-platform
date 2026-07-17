# Implementation Plan: C2c Write-Import Planning (Consulting → Flexity Core REST)

**Дата:** 2026-07-08
**Статус:** waiting for approval (documentation-only)
**Ветка:** `main`
**Режим:** planning only — no code, no import, no production, no deploy, no alembic upgrade, no real SQLite access

---

## Task Classification

| Параметр | Значение |
|---|---|
| Project | Flexity |
| Category | documentation_only (future write-import via Core REST) |
| Risk level | low (docs only); future C2c-code / staging write = high |
| Intended scope (this step) | только этот файл: `docs/ai/plans/2026-07-08-flexity-consulting-c2c-write-import-planning.md` |
| Forbidden scope | code, alembic upgrade, deploy, import, export, real SQLite, legacy `/dashboard`, dual-write, production |
| Required plan type | write-import planning (no execution) |

### Inputs used

- `docs/ai/reports/2026-07-08-flexity-consulting-c1c-core-api-readiness-implementation-report.md`
- `docs/ai/reports/2026-07-08-flexity-consulting-c2a-synthetic-dry-run-implementation-report.md`
- `docs/ai/reports/2026-07-08-flexity-consulting-c2b-synthetic-sqlite-adapter-implementation-report.md`
- `docs/ai/plans/2026-07-08-flexity-consulting-c2-import-script-plan.md`
- `docs/ai/specs/2026-07-08-flexity-consulting-gate3-migration-mapping-spec.md`
- Supporting: C1 status/import summary specs, backup/rollback runbook, C1c plan

---

## Goal

Спланировать **будущий write-import path** legacy Consulting (`consult_app`) → Flexity Core **только через Core REST API** после закрытия C1c P0 gaps — **без выполнения** import, migration upgrade, deploy или production cutover в этом шаге.

---

## 1) Executive summary

- **C1c** локально закрыл P0 API gaps: `POST /documents/import` и first-class `Payment.direction` (+ минимальный audit `import.batch.summary` hook). Report accepted.
- **C2a** synthetic dry-run pipeline уже есть: source → map → validate → no-op REST DTO target → import batch summary.
- **C2b** synthetic read-only SQLite adapter + masking/fingerprint уже есть локально; **real-source dry-run** всё ещё требует отдельного approval и не выполнен.
- **C2c (этот документ)** — **только planning** будущего REST write-client / staging write path.
- **Нет** production import, **нет** cutover, **нет** deploy, **нет** alembic upgrade в этом шаге.
- Legacy `/dashboard` (`consult_app`) остаётся read-only bridge/reference до отдельного cutover plan.

---

## 2) Critical migration prerequisite

| Item | Rule |
|---|---|
| Migration file | `backend/alembic/versions/20260708_0013_c1c_payment_direction.py` (`revision = 0013_c1c_payment_direction`) exists **locally** |
| What it adds | `payments.direction` enum-as-string: `incoming` / `outgoing` / `needs_review`, default `incoming` |
| Staging / prod runtime | Before **any** staging or production runtime that creates/loads `Payment` with `direction`, target DB **must** have Alembic upgrade applied |
| Deploy coupling | **Do not deploy** application code that expects `Payment.direction` onto an environment whose DB has not run `0013` |
| Staging upgrade | **Separate explicit approval** required for staging DB migration |
| Production upgrade | **Separate explicit approval** required for production DB migration (not part of C2c planning, not part of C2c-1) |
| Local pytest | Uses `create_all` — does **not** prove staging/prod migration was applied |

### Gate wording (binding)

1. Approval for **C2c code** ≠ approval for **staging alembic upgrade**.
2. Approval for **staging alembic upgrade** ≠ approval for **production alembic upgrade**.
3. Approval for **staging write-import** requires staging already on revision including `0013` (or documented waiver — not recommended).

---

## 3) Target architecture

```text
[legacy consult_app SQLite]  --read-only-->  [source adapter]
                                                    |
                                              [map / transform]
                                                    |
                                              [validation layer]
                                                    |
                    +-------------------------------+-------------------------------+
                    |                               |                               |
           Dry-run / no-op                    Core REST write client         (forbidden)
           (C2a/C2b/C2c-2..)                 (C2c write phases)           direct PG INSERT
                    |                               |
             ImportBatchSummary              Core services → Postgres
             + masked report                 (tenant / branch / audit)
```

Hard rules:

1. **All writes** go through Flexity Core **REST API** (HTTP to Core endpoints).
2. **No** direct PostgreSQL inserts from the import script.
3. **No** bypass of tenant scope, `default_branch` context, validation, or import/audit summary recording.
4. Source side stays **read-only** (`mode=ro`); legacy remains bridge until cutover.
5. Write mode **disabled by default**; explicit flag + approval per environment.
6. Idempotency / `external_ref` strategy must use Core API payloads (documents `context_json`, parties external ids, etc.) — not raw SQL upserts.

### Planned staged entity write order (future)

1. Tenant / `default_branch` readiness (pre-check; create only if approved bootstrap)
2. Users / roles (if in import slice)
3. Parties / contacts
4. Catalog / services
5. Work items / orders / stages / lines
6. Documents / contracts via `/documents/import`
7. Finance payments (with `direction` / `legacy_payment_type`)
8. Import batch summary via audit hook (`record_import_batch_summary_event` or later dedicated API)

Debts: **deferred** per C1c D1 unless separately approved.

---

## 4) Proposed C2c phases

| Phase | Name | What happens | Writes? | Separate approval? |
|---|---|---|---|---|
| **C2c-0** | Staging environment readiness check | Confirm staging Core up, tenant bootstrap path, modules/plan, operator credentials, migration head vs code revision awareness, backup capability | No | Yes (staging ops check) |
| **C2c-1** | Alembic on staging only | Apply `0013_c1c_payment_direction` (and any prior pending heads) on **staging DB only** | Schema only | **Yes — staging migration approval** |
| **C2c-2** | Import script vs synthetic / staging API | Implement/use REST write adapter against synthetic fixtures and/or empty staging tenant; dry-run default; optional tiny write of synthetic rows | Staging API only if write flag approved | Yes (C2c-code + optional synthetic write) |
| **C2c-3** | Real-source dry-run | Read-only real `consulting_os.db` (after backup + path allowlist) → map/validate → **no-op or non-write** report | Source read only; **no Core writes** | **Yes — real-source dry-run** (≠ C2c-2) |
| **C2c-4** | Staging write-import | Controlled/masked dataset or approved limited source slice into staging Core via REST | Staging Core writes | **Yes — staging write-import** |
| **C2c-5** | Client review | Aggregate acceptance (counts, statuses samples, finance totals) without raw PII in shared reports | No new import unless approved delta | Yes (client review gate) |
| **Later** | Production cutover | Own plan: prod migration, prod backup, freeze, write, verify, cutover legacy | Production | Multi-gate; **out of this doc’s execution** |

### Phase dependencies

```text
C2c-0  →  C2c-1 (migration)  →  C2c-2 (script + synthetic/staging API)
                ↘
                 C2c-3 (real-source dry-run)  →  C2c-4 (staging write)  →  C2c-5
                                                                         →  [future prod plan]
```

- C2c-3 must **not** write to Core.
- C2c-4 must not start before C2c-1 success + C2c-3 review (or explicit waiver for synthetic-only write in C2c-2).
- Production never folds into C2c-1…C2c-5 without a new plan.

---

## 5) API readiness checklist

| Area | Status after C1c / C2a/C2b | Must verify before C2c-4 |
|---|---|---|
| Tenant + `default_branch` | Ready create path; C2a/C2b readiness checks exist | Staging tenant exists; `default_branch_id` set; import context carries both IDs |
| Users / roles | C1 auth/login + isolation tests | Operator + imported user login/role checklist on staging tenant |
| Parties / contacts | Ready (`PartyCreate`) | Create/list OK tenant-scoped |
| Catalog / services | Ready (`CatalogItemCreate`) | Dictionaries seeded before work items |
| CRM work_items / orders / cases | Ready (`WorkItemCreate` + mapping helpers) | Status/stage mapping acceptance policy frozen |
| Documents import | Ready (`POST /documents/import`) | Null order link + zero amount + external_ref smoke on staging |
| Finance payment direction | Ready in code + local model; **DB needs `0013`** | Staging migrated; direction round-trip; INCOME/EXPENSE mapping |
| Audit / import summary event | Ready: `build_import_batch_summary` + `record_import_batch_summary_event` | Every write batch emits one summary event (no PII) |
| Subscription / package | Existing `POST /tenants/{id}/subscription`; no C1c API change | Plan assigned **before** import (manual/ops); modules parties/crm/catalog/documents/finance enabled |

### Still partial / deferred (do not block planning; block specific writes if in scope)

- Dedicated `/audit/import-batches` REST list API (prefer before production cutover).
- Debt-specific import API (deferred D1).
- Idempotent upsert uniqueness enforcement by `external_ref`.
- Binary signed PDF / full document lifecycle import.

---

## 6) Data protection rules

1. **No raw PII** in logs, markdown reports, chat, or CI artefacts (names, phones, emails, notes, document body text).
2. **No full table dumps** of real source or target.
3. **No real-source write** into Core before real-source dry-run review (C2c-3) and explicit C2c-4 approval.
4. Import logs / summary / error reports: **masked** (reuse C2b `masking.py` patterns).
5. Reports: aggregates, issue codes, technical IDs, synthetic placeholders only.
6. **No copy/export** of `consulting_os.db` without separate approval.
7. Production data access (read or write) requires **separate** approval beyond this planning doc.
8. Staging write should prefer synthetic fixture or explicitly approved reduced/masked dataset when possible.

---

## 7) Validation before write

Mandatory pre-write (and dry-run) checks — align with C1 policy + Gate3 + C2a/C2b pipeline:

| Check | Rule |
|---|---|
| Status mappings | Orders/stages/contracts/payments through frozen matrix; unknown → `needs_review` / review counters |
| Required fields | Reject or quarantine rows missing required Core fields |
| Tenant / `default_branch` | Fail closed if either missing in import context |
| Duplicate handling | Detect collisions (e.g. login); policy: warn/review/skip — do not silent overwrite without approval |
| Orphan handling | Critical orphans (order→client, payment→order where required, etc.) block or quarantine per Gate3 severity |
| Zero contract amount | Allowed with review flag (C1/C1c policy) |
| `contracts.order_id NULL` | Nullable `work_item_id` + link review flag |
| Payment direction | INCOME→incoming, EXPENSE→outgoing, unknown→needs_review; never hide in notes |
| Finance aggregate reconciliation | `source_total` vs mapped/prepared total; fail write batch if mismatch beyond policy |
| Schema fingerprint (real SQLite) | Mismatch fails or requires explicit override flag (C2b) |
| REST DTO validation | Payloads must validate against Core create/import schemas before HTTP write |

Write client must fail closed on validation **errors**; continue-with-review only for documented warning class.

---

## 8) Rollback and recovery

Reference: `docs/ai/runbooks/2026-07-08-flexity-consulting-import-backup-rollback-runbook.md`

| Layer | Requirement before real import (C2c-3 read vs C2c-4/prod write) |
|---|---|
| Source DB | Confirmed backup + backup ID before any real-source access that matters for cutover; mandatory before prod write |
| Target DB | Staging backup before C2c-4; production backup before any prod write (future plan) |
| Import batch summary | Persist via audit hook; record batch id / timestamps / counts |
| Per-entity rollback | Prefer restore target to pre-import snapshot for failed staging/prod wave; document manual reverse only for tiny synthetic tests |
| Bridge fallback | Legacy `/dashboard` remains operational fallback until cutover approval |
| Triggers | Aggregate mismatch, status error rate above threshold, tenant isolation breach, client rejection |

Operational must-haves for C2c-4+:

1. Freeze further batches on trigger.
2. Capture batch id + environment.
3. Restore target from backup point.
4. Post-rollback verification summary (aggregates only).
5. Do not “patch forward” in production without new approval.

---

## 9) Explicit out of scope

- Production import / cutover
- Production deploy / Nginx / systemd / service restart
- Production Alembic upgrade
- Staging or any alembic upgrade **without** its own approval (C2c-1 is planned, not approved by this doc alone)
- Legacy `/dashboard` rewrite or dual-write
- Direct PostgreSQL loaders
- Full accounting / payroll / taxes / inventory expansion
- Clinic / Booking / Trailers scopes
- Debt API build-out
- Subscription product redesign
- Compliance / certification claims
- This planning step itself writing any code or touching real DB

---

## 10) Decision checkpoint

| Question | Answer |
|---|---|
| Is **C2c implementation** (REST write client code) safe **now**? | **Not until** this plan is approved **and** a separate **C2c-code** approval is granted. Planning ≠ code. |
| Is **staging migration** approval required first? | **Yes**, before any staging runtime that persists `Payment.direction`. Prefer C2c-1 before C2c-2 write attempts on staging. |
| Is **real-source dry-run** approval required before any write of real data? | **Yes.** C2c-3 approval required before C2c-4 with real-source-derived rows. Synthetic-only staging writes (C2c-2) may proceed earlier under their own approval but never replace real-source dry-run. |
| Can production cutover start under this plan? | **No.** Needs a separate production plan and multi-gate approvals. |
| Remaining Core API blockers for planning? | None for P0 docs/payments direction locally; operational blockers are migration upgrade on target envs + durable ops checklist. |

### Preconditions before approving C2c-code

- This C2c planning doc accepted.
- Agreement: REST-only writes; no direct PG.
- Awareness of `0013` migration gate.
- C2a/C2b local dry-run baseline remains green.
- Masking + no-PII report policy accepted.

### Still deferred until later approvals

- Staging alembic upgrade (C2c-1)
- Real SQLite path allowlist / backup ID for C2c-3
- Staging write-import (C2c-4)
- Client review (C2c-5)
- Production migration / import / cutover

---

## Scope (this documentation step)

### Files to modify

- `docs/ai/plans/2026-07-08-flexity-consulting-c2c-write-import-planning.md` (create)

### Files intentionally not touched

- All backend code
- All alembic applications
- All legacy projects
- Env / deploy / secrets
- Real SQLite DB

---

## Steps (completed by this document)

1. Restate C1c + C2a/C2b baseline.
2. Lock migration prerequisite for `Payment.direction`.
3. Define REST-only target architecture.
4. Split C2c-0…C2c-5 + future production boundary.
5. Checklist API readiness, validation, data protection, rollback.
6. Decision checkpoint.
7. **Stop** — wait for approvals before code or any DB action.

---

## Tests/checks (this planning step)

- Documentation completeness vs required sections: yes.
- No code / alembic / import / deploy / SQLite access: yes.

---

## Risks (planning awareness)

| Risk | Mitigation |
|---|---|
| Deploy without `0013` | Coupled gate: migration before app that requires direction |
| Skipping real-source dry-run | Hard phase order C2c-3 → C2c-4 |
| Treating planning as write approval | Explicit approval lines below |
| PII leakage on first real-source run | Masking + backup + aggregate-only reports |
| Dual-write temptation | Architecture forbid + review |
| Confusing audit hook with full import-batches API | Documented as staging-ok / prod preference later |

---

## Rollback

N/A for planning-only doc. Discard by deleting/ignoring this file. No runtime state created.

---

## Approval

**Status: waiting for approval**

Approval required before C2c code, staging migration, real-source dry-run, write-import, deploy, or production action.
