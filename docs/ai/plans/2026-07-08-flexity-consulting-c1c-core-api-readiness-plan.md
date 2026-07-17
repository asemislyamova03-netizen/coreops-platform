# Implementation Plan: C1c Core API Readiness (Consulting Write-Import Preconditions)

**Дата:** 2026-07-08
**Статус:** waiting for approval (documentation-only)
**Ветка:** `main`
**Режим:** documentation-only — no code, no migrations, no deploy, no import

---

## Task Classification

| Параметр | Значение |
|---|---|
| Project | Flexity |
| Category | documentation_only (план готовки `platform_core` / universal API к write-import) |
| Risk level | medium (docs only); future C1c-code = high (API surface before real writes) |
| Intended scope (this step) | только этот файл: `docs/ai/plans/2026-07-08-flexity-consulting-c1c-core-api-readiness-plan.md` |
| Forbidden scope | любой production code, migrations, deploy, import, Core DB writes, legacy `/dashboard`, `/var/www/consult_app` |
| Required plan type | implementation plan (planning only; отдельный approval до C1c code) |

### Inputs used

- `docs/ai/reports/2026-07-08-flexity-consulting-c2a-synthetic-dry-run-implementation-report.md`
- `docs/ai/plans/2026-07-08-flexity-consulting-c2b-readonly-sqlite-source-adapter-plan.md`
- `docs/ai/reports/2026-07-08-flexity-consulting-c1-core-readiness-implementation-report.md`
- `docs/ai/reviews/2026-07-08-flexity-consulting-core-readiness-review.md`
- `docs/ai/specs/2026-07-08-flexity-consulting-import-batch-summary-contract.md`
- `docs/ai/specs/2026-07-08-flexity-consulting-status-acceptance-policy.md`
- `backend/app/modules/documents/{routes,schemas,models}.py`
- `backend/app/modules/finance/{routes,schemas,models}.py`
- `backend/app/modules/audit/{routes,schemas,service}.py`
- `backend/app/modules/subscriptions/{routes,seed,service}.py`

---

## Goal

Зафиксировать **минимальные gaps Core REST API**, которые нужно закрыть **до любого реального write-import** Consulting-пакета (staging C2c и далее).

Фокус только на partial-зонах из C2a/C2b:

1. documents / contracts API readiness
2. finance / payments / debts API readiness
3. import / audit summary endpoint (если нужен)
4. subscription / package assignment (если нужен для launch)

Не цель C1c: полный ERP-контур, dual-write, production cutover, C2b code, Clinic/Booking/Trailers.

---

## 1) Executive summary

- **C1** закрыл mapping/policy/audit-schema/helpers локально; **запись через REST write path для contracts/payments direction всё ещё partial**.
- **C2a** подтвердил: parties / catalog / work-items / tenants **ready** для REST-shaped payloads; documents и finance payments — **partial**.
- **C2b** (read-only source) **не** ждёт C1c; **C2c write import contracts/payments** — **ждёт**.
- C1c планирует только **минимальный REST write-readiness** для этих partial-зон + решение по summary endpoint и subscription attach.
- Архитектура не меняется: Flexity Core = единственный REST/API target; import не проектируется как direct PostgreSQL inserts.

---

## 2) Current readiness snapshot (after C1 + C2a)

| Area | Status | Evidence | Blocks real write import? |
|---|---|---|---|
| Tenants + `default_branch` | ready (for API create/context) | C2a DTO validate + tenant service | No (must remain in import context) |
| Parties | ready | `PartyCreate` match | No |
| Catalog items | ready | `CatalogItemCreate` match | No |
| Work items / CRM | ready | `WorkItemCreate` match | No |
| Documents / contracts | **partial** | only `POST /documents/generate`; policy helpers without write/import DTO | **Yes** for contract rows |
| Finance payments | **partial** | `POST /finance/payments` exists; **no `direction` on create/model** | **Yes** for faithful INCOME/EXPENSE |
| Finance debts / receivables | **partial / indirect** | receivable = open invoices; no legacy-debt import endpoint | **Yes** if debts in import slice; **deferrable** if debts postponed |
| Import batch summary | **partial** | schema + `build_import_batch_summary` exist; **no REST persist/list** | **Conditional** (see §5) |
| Subscription assign | **mostly ready** | `POST /tenants/{id}/subscription` + plans seed | **No** if pre-assign manual/API before import; billing stays manual |

---

## 3) Gap A — Documents / contracts API

### 3.1 What exists now

| Surface | Status |
|---|---|
| `GET/POST /document-templates` | ready (templates) |
| `GET /documents`, `GET/PATCH /documents/{id}` | list/update status/title |
| `POST /documents/generate` | template render → `DocumentInstance` |
| `assess_legacy_contract_import` / status map helpers | C1 policy layer (not a write API) |
| Model `DocumentInstance` | `party_id`, `work_item_id` nullable, `context_json`, **no dedicated amount column** |

### 3.2 Why this blocks write import

Legacy `contracts` are **historical instances** (status, amount, optional order link), not fresh generations from a live template.

Using only `/documents/generate`:

- forces inventing/seeding templates + expression of amount/status only via `context`/`rendered_content`;
- cannot cleanly upsert by `external_legacy_id`;
- conflicts with C1 policies (`order_id NULL`, `amount=0`, needs_review) which need first-class import fields, not ad-hoc spam in notes.

### 3.3 Minimal C1c fix options (choose one in C1c-code approval)

| Option | Description | Migration likely? | Recommendation |
|---|---|---|---|
| **A1 (preferred)** | Add `POST /documents/import` (or `POST /documents`) with `DocumentImportCreate`: title, status, party_id, work_item_id nullable, amount (or structured context), external_ref, review flags | Maybe (if amount/external_ref columns); **prefer store amount/external_ref in `context_json` first to avoid migration** | **Primary** |
| **A2** | Extend `DocumentGenerateRequest` + generate path for “import mode” (skip render / accept prefilled body) | Possibly lower | Acceptable if carefully gated |
| **A3** | Waive contract write import in first wave; import CRM only | No | Explicit limitation; contracts stay bridge/legacy until later |

### 3.4 Acceptance criteria (when A1/A2 coded)

1. Create orphan-safe instance with `work_item_id=null` + review flag in payload/context.
2. Persist zero amount with review flag (policy already defined).
3. Set mapped `DocumentStatus` from legacy status without forcing regenerate.
4. Tenant-scoped; no cross-tenant write.
5. Idempotency key or `external_legacy_id` strategy documented (even if stored only in `context_json` for v1).
6. Tests: contract schemas + route happy path + nullable link + zero amount.

### 3.5 Explicitly out of C1c documents scope

- Contract template content migration from legacy.
- EDS / signature production flows for imported history.
- Binary file bulk import of signed PDFs (unless later approved slice).
- Broad documents refactor.

---

## 4) Gap B — Finance / payments / debts API

### 4.1 What exists now

| Surface | Status |
|---|---|
| `POST/GET /finance/payments` | create/list/get |
| `POST /finance/payments/{id}/allocate` | allocate to invoices |
| `POST/GET /finance/invoices`, receivables, summary | invoice-centric AR |
| `PaymentCreate` | amount (>0), currency, date, method, status, reference, notes — **no direction**, **no work_item_id** |
| `map_legacy_payment_type` | helpers only; direction not persisted on Payment model |
| Payment model | no `direction` column |

### 4.2 Why this blocks write import

Gate3 / status policy require:

- `INCOME` → `direction=incoming`, status completed
- `EXPENSE` → `direction=outgoing`, status completed
- unknown → needs_review

Without a first-class direction (or approved surrogate), write import either:

- drops EXPENSE/INCOME distinction, or
- hides it in `notes` (fragile, not queryable, breaks finance aggregates).

**Debts:** Core models AR as invoice balances (`/finance/receivables`), not as legacy free-standing debt rows. Faithful debt import needs either invoice reconstruction or an approved “debt note / unallocated balance” contract — **not present as a dedicated API**.

### 4.3 Minimal C1c fix options

#### Payments direction

| Option | Description | Migration? | Recommendation |
|---|---|---|---|
| **B1 (preferred)** | Add optional `direction` to `PaymentCreate`/`PaymentResponse` + model enum (`incoming` / `outgoing` / `needs_review`) | **Yes** (column) — needs **separate migration approval** | Prefer if migration approval available |
| **B2** | No migration: encode direction in structured `notes` or reserved metadata JSON **only if** Response exposes parsed field + tests lock format | No | Temporary; document limitation |
| **B3** | Import only `INCOME` payments first; queue `EXPENSE` + unknown as review/skip | No | Explicit first-wave limitation |

#### Debts

| Option | Description | Recommendation |
|---|---|---|
| **D1** | Defer debt import; first write wave = payments (± invoices if needed for allocations) | **Default for minimal launch** |
| **D2** | Minimal “open balance” via invoice create + payment allocate mapping | Only if debts in mandatory Gate3 first wave |
| **D3** | New debt entity API | Out of C1c (overbuild) |

### 4.4 Acceptance criteria (payments)

1. Round-trip: create payment with explicit direction (or approved B2 surrogate that API returns).
2. Mapping matrix INSURED: INCOME/EXPENSE/unknown behave per status acceptance policy.
3. List filter by direction (nice-to-have; not mandatory for v1 if documented).
4. Aggregate check still possible: incoming vs outgoing sums for import reconciliation.
5. Tenant isolation tests updated.
6. If B1: migration separately approved and reversible per project rules.

### 4.5 Explicitly out of C1c finance scope

- Full accounting ledger.
- Payroll.
- Bank integrations.
- Auto-rebuild of entire legacy finance dictionaries.

---

## 5) Gap C — Import / audit summary endpoint

### 5.1 What exists now

| Surface | Status |
|---|---|
| `ImportBatchSummary` schema | ready (C1) |
| `AuditService.build_import_batch_summary` | ready locally |
| `GET /audit/logs`, data-access, security-events | general audit — **not** import-batch CRUD |
| Persistent `ImportBatch` table / `POST /audit/import-batches` | **missing** |

### 5.2 Is a dedicated endpoint required before write import?

| Decision | When |
|---|---|
| **Required before production write import** | Always need durable operator-visible evidence of batch totals/errors/review |
| **Not required before C2c staging if** | Write client persists summary as one `AuditLog` event with typed `details_json` matching ImportBatchSummary **and** retrieval via existing `GET /audit/logs` is accepted for staging |
| **Required as first-class REST before production cutover** | Prefer `POST/GET /audit/import-batches` (or equivalent) so ops can list batches without scraping generic logs |

### 5.3 Minimal C1c fix options

| Option | Description | Recommendation |
|---|---|---|
| **C1** | Persist via existing audit recorder: action=`import.batch.summary`, details=ImportBatchSummary dump | **OK for staging C2c** if retrieval recipe documented |
| **C2** | Add thin `POST /audit/import-batches` + `GET .../{id}` (+ optional list by tenant) storing JSON in audit or dedicated table | **Preferred before production cutover** |
| **C3** | Summary only in importer process stdout/file | **Reject** for write import acceptance |

### 5.4 Acceptance criteria

1. Summary validates against C1 contract (no PII).
2. Every write-mode batch produces exactly one finished summary.
3. Retrieval documented for ops (endpoint or audit filter).
4. Schema totals rules enforced server-side when POST exists.

---

## 6) Gap D — Subscription / package assignment for launch

### 6.1 What exists now

| Surface | Status |
|---|---|
| `GET /plans` | ready |
| `GET/POST /tenants/{tenant_id}/subscription` | assign by `plan_code` |
| Seed plans | `starter`, `business`, `enterprise` |
| `business` modules | parties, crm, catalog, documents, finance, **booking** |

### 6.2 Does C1c need code for subscriptions?

**No, not as a write-import blocker**, if launch runbook does:

1. Create tenant (+ default_branch).
2. `POST /tenants/{id}/subscription` with an approved plan (`business` or later consulting-specific).
3. Confirm modules/features needed for import targets (documents, finance, crm, parties, catalog).
4. Keep billing/invoicing **manual** (already allowed in readiness review).

### 6.3 Optional follow-ups (not C1c blockers)

| Item | Note |
|---|---|
| Dedicated `consulting` / `consulting_basic` plan | Product packaging; can be CR, not import API gap |
| Strip unused `booking` from consulting entitlement | Prefer package/template later; do not block import |
| Auto-assign subscription inside import script | Forbidden unless separately approved; prefer explicit pre-import step |

### 6.4 Acceptance for launch (ops checklist, no new API)

1. Target tenant has active subscription.
2. Modules `parties`, `crm`, `catalog`, `documents`, `finance` enabled.
3. Import operator has tenant-scoped credentials.
4. No claim of full auto-billing.

---

## 7) Priority matrix for C1c-code (future)

| ID | Gap | Priority for real write import | Migration likely | Can defer behind explicit limitation? |
|---|---|---|---|---|
| A | Documents import/create path | **P0** | Prefer avoid; use `context_json` | Yes only if contracts excluded from wave |
| B | Payment direction on API/model | **P0** | Likely if B1 | Yes via B3 (INCOME-only) with documented skip |
| C | Import summary durability | **P1** staging / **P0** production | Maybe for C2 endpoint | Staging may use audit log event |
| D | Subscription assign | **P2** (ops) | No | Use existing assign API |

---

## 8) Proposed future files (C1c-code only — not now)

> Ничего из этого не меняется в текущем documentation step.

### Likely touch (minimal)

| Path | Purpose |
|---|---|
| `backend/app/modules/documents/schemas.py` | `DocumentImportCreate` / import response fields |
| `backend/app/modules/documents/service.py` | import create path + policy flags |
| `backend/app/modules/documents/routes.py` | `POST /documents` or `/documents/import` |
| `backend/app/modules/finance/schemas.py` | `direction` on PaymentCreate/Response |
| `backend/app/modules/finance/models.py` | direction column (if B1) |
| `backend/app/modules/finance/service.py` | persist/filter direction |
| `backend/app/modules/finance/routes.py` | if query params for direction |
| `backend/app/modules/audit/routes.py` | optional import-batches endpoints |
| `backend/app/modules/audit/service.py` | persist/retrieve batch summary |
| `backend/alembic/versions/*` | **only if B1 or dedicated import-batch table** — separate migration approval |
| `backend/tests/test_documents*.py` / finance / audit | contract + route tests |
| `docs/ai/specs/*` | addendum for import DTO + direction field |

### Forbidden in C1c-code

- Legacy Flask `/dashboard`, `/var/www/consult_app`
- C2b/C2c write client implementation mixed into same PR without approval
- Dual-write
- Production deploy / Nginx / systemd
- Broad accounting / payroll / inventory
- Auth redesign, billing engine redesign
- Clinic / Booking / Trailers scopes

---

## 9) Relation to C2b / C2c

```text
C2b-code / C2b-dry-run  ── parallel to C1c ──►  NO Core writes
C1c-code                ── closes A/B (+ C for prod) ──►  REST write-ready
C2c                     ── staging REST write adapter ──►  BLOCKED until A+B closed or waived
Production write        ── separate gates ──►  needs A+B + durable summary (C) + backup/runbook
```

| Phase | Needs C1c? |
|---|---|
| C2b-code (read-only adapter) | No |
| C2b-dry-run (real SQLite → no-op) | No |
| C2c staging REST writes of contracts/payments | **Yes** (or explicit waivers A3/B3) |
| Production import | **Yes** + durable summary + runbook rehearsal |

---

## 10) Test plan (for future C1c-code)

1. Documents import create: null work_item, zero amount, status mapping, tenant isolation.
2. Payments: direction round-trip; unknown → needs_review; list/create compatibility.
3. If migration B1: alembic up/down on empty test DB (only after migration approval).
4. Import summary: validate schema; POST (if C2) or audit event details parseable.
5. Regression: existing `test_status_mapping_contracts`, `test_import_summary_contract`, documents/finance suites.
6. No production self-test; no real SQLite writes; no deploy.

---

## 11) Risks

| Risk | Mitigation |
|---|---|
| Overbuilding documents generate vs import | Prefer thin import DTO; avoid template rewrite |
| Direction buried in notes only | Prefer B1; if B2, lock format + response field |
| Skipping debts silently | Explicit D1 decision in go/no-go |
| Starting C2c before A/B | Gate: refuse write adapter for those entities |
| Migration creep | Amount/external_ref via `context_json` first; direction migration isolated |
| Treating subscription as import step | Keep pre-import assign_plan ops |

---

## 12) Explicit out of scope (this plan + C1c-code)

- Import script / C2b adapter implementation
- Actual import or export of real data
- Production DB writes / deploy / service restarts
- Dual-write architecture
- Changes to legacy Consulting Flask
- Full accounting / payroll / inventory
- Clinic / Booking / Trailers work
- EDS / government integrations
- Compliance certification claims

---

## Scope (this documentation step)

### Files to modify

- `docs/ai/plans/2026-07-08-flexity-consulting-c1c-core-api-readiness-plan.md` (create)

### Files intentionally not touched

- All backend production code
- All migrations
- All legacy projects
- Deploy / env / secrets
- C2b/C2c code

---

## Steps (completed by this document)

1. Classify task and freeze constraints.
2. Diff C2a partial endpoints against live routes/schemas/models.
3. List minimal API gaps A–D with options and acceptance criteria.
4. Separate staging vs production needs for audit summary and subscriptions.
5. Define future file list and C2b/C2c gates.
6. **Stop** — wait for approval before any C1c code.

---

## Tests/checks (this planning step)

- Documentation-only: yes.
- No code / migrations / deploy / import: yes.
- Focus limited to C2a/C2b partial areas: yes.

---

## Rollback

N/A for documentation. Discard by deleting or ignoring this plan file. No runtime state created.

---

## Decision checkpoint (for approver)

| Question | Proposed answer |
|---|---|
| Can C2b-code proceed without C1c? | **Yes** |
| Must documents import API exist before contract write import? | **Yes** (or waive contracts: A3) |
| Must payment direction be first-class before payment write import? | **Yes** preferred (B1); temporary B2/B3 only with written limitation |
| Must dedicated import-batch endpoint exist before staging write? | **No** if audit-event summary accepted; **Yes** before production cutover preference |
| Must subscription API change in C1c? | **No** — use existing assign + ops checklist |

---

## Approval

**Status: waiting for approval**

Approval required before C1c code implementation.
