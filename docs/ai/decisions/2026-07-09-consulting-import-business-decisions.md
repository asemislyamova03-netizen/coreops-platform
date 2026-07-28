# Business Decision Memo — Consulting Import Policy

**Date:** 2026-07-09  
**Status:** draft for business approval  
**Scope:** documentation only — no code, no dry-run, no write-import  
**Related reports:**

- `docs/ai/reports/2026-07-09-consulting-to-core-gate-b-dry-run-report.md`
- `docs/ai/reports/2026-07-09-consulting-to-core-gate-b-masked-report-review.md`

---

## 1. Context

| Field | Value |
|---|---|
| Source system | legacy Consulting OS (SQLite) |
| Target system | Flexity Core (multi-tenant ERP) |
| Current migration stage | after Gate B masked dry-run |
| Dry-run outcome | technical pipeline works; masked JSON produced; PII scan PASS |
| Hard validation errors | 0 |
| Import readiness verdict | `DRY_RUN_BLOCKED` (business/data-quality policy required) |
| Write-import status | **not started** — blocked until this memo approved + technical plan |

**What Gate B proved:**

- Read-only adapter, schema mapping (services, order_items), and no-write target path work.
- Source/backup/staging/live were not modified during dry-run.
- Remaining blockers are **policy decisions**, not schema/runtime failures.

**What is explicitly out of scope for this memo:**

- Running Gate B again
- Staging or live write-import
- Adapter/code changes
- Live deploy or cutover

---

## 2. Decision area A — Amount authority

### Problem

| Metric | Value |
|---|---:|
| Orders with `total_amount` | 38/38 (complete) |
| Line derived amount | `qty * unit_price` per `order_items` row |
| Reconciliation match | 18/38 orders |
| Reconciliation mismatch | 20/38 orders |
| Missing order totals | 0 |

Legacy stores a commercial total at order header level, while line-level `qty * unit_price` does not always reconcile to that header. Import must define which amount is authoritative for Flexity finance and reporting.

### Options

#### A1 — `orders.total_amount` authoritative

- Use order header total as the **primary commercial amount** for the imported work item / order case.
- Line derived totals (`qty * unit_price`) retained as **metadata** and reconciliation fields.
- Mismatched orders flagged `amount_needs_review`.
- **Pros:** aligns with legacy order-level reporting; minimal drift from existing owner-facing totals.
- **Cons:** line-level accounting may not sum to header without manual review.

#### A2 — Line derived total authoritative

- Use `sum(qty * unit_price)` as the commercial amount.
- `orders.total_amount` treated as legacy inconsistent / deprecated field.
- **Pros:** internal consistency at line level.
- **Cons:** changes 20+ order totals vs legacy; high owner/accounting confusion risk.

#### A3 — Contract amount authoritative where contract exists

- Where a contract exists for an order, use `contracts.amount` as primary.
- Order header and line totals secondary.
- **Pros:** contract-centric view for consulting engagements.
- **Cons:** not all orders have contracts; contracts may have null order link (~10); mixed authority across entities.

#### A4 — Conservative hold policy

- Import non-financial order structure (parties, work items, line items, documents).
- **Hold finance/payment posting** for orders with amount reconciliation mismatch until manual review.
- **Pros:** safest path to staging; no silent accounting drift.
- **Cons:** finance module incomplete until review queue cleared.

### Recommendation

**Adopt A1 + A4:**

1. **`orders.total_amount` is authoritative** for order header / work-item commercial amount.
2. **Line derived amounts** (`qty * unit_price`, per-line and per-order sum) stored as metadata and reconciliation counters.
3. Orders in the 20-order mismatch set receive **`amount_needs_review=true`**.
4. **Finance and payment posting** for mismatched orders are **held** until manual review clears them.

### Staging / live acceptability

| Gate | Acceptable under A1+A4? | Condition |
|---|---|---|
| Staging write-import (structure) | **yes** | orders imported with review flags; no automatic finance posting for mismatched set |
| Staging write-import (finance posting) | **partial** | only for the 18 matched orders until review workflow exists |
| Live import | **no** | requires staging validation + explicit live gate |
| Cutover | **no** | blocked |

### Import report requirements (masked/sanitized)

Future write-import and review reports must show (aggregates only, no raw PII):

- `order_total_match_count`, `order_total_mismatch_count`
- count of orders with `amount_needs_review`
- whether finance posting was held per order category
- no raw client names, amounts tied to identifiable rows in repo docs

---

## 3. Decision area B — Orphan payments

### Problem

| Metric | Value |
|---|---:|
| Payments without `order_id` | 57 / 94 |
| `orphan_order` warnings | 57 |
| Headline `total_review_rows` | 57 (= orphan warnings) |
| Hard errors | 0 |

Linked import cannot attach these payments to order/work-item records. A policy is required before any staging write-import.

### Options

#### B1 — Block all orphan payments

- Do not import payments without `order_id` until manually linked in legacy or a mapping file.
- **Pros:** clean linked ledger.
- **Cons:** loses 57 historical payment records in first wave; manual pre-work required.

#### B2 — Import as standalone historical payments

- Import into Flexity with:
  - tenant + default branch context
  - client linkage where `client_id` exists
  - `needs_review=true`
  - source relation status: `unlinked_legacy_payment`
  - preserved legacy external id / source key
- Do **not** auto-link to orders.
- Do **not** treat as clean revenue posting without review.
- **Pros:** preserves historical cash data; unblocks staging exploration.
- **Cons:** review queue; accounting allocation deferred.

#### B3 — Heuristic auto-matching (client/date/amount)

- Attempt automatic order linkage by fuzzy rules.
- **Pros:** fewer orphan rows.
- **Cons:** high false-link risk; unacceptable for first import without proven rules.

### Recommendation

**Adopt B2 for staging write-import only:**

| Rule | Policy |
|---|---|
| Import orphan payments? | yes, as standalone historical payments |
| Review flag | `needs_review=true` |
| Source relation status | `unlinked_legacy_payment` |
| Auto-link to orders? | **no** |
| Auto revenue posting? | **no** |
| Live import | separate approval after staging review |

### Staging / live acceptability

| Gate | Acceptable under B2? |
|---|---|
| Staging write-import (historical capture) | **yes** |
| Staging finance posting (final) | **no** until review |
| Live import | **no** |
| Cutover | **no** |

---

## 4. Decision area C — Contract and template warnings

### Problems (from masked review)

| Warning | Est. count | Domain |
|---|---:|---|
| `null_order_link` | ~10 | contracts without `order_id` |
| `zero_amount` | ~3 | contracts with `amount = 0` |
| `missing_template_id` | 37 | all `order_stages` lack template |

### Proposed policy

#### C1 — Contracts with null order link

- Import as **standalone historical contracts** when client and contract metadata exist.
- Set `link_needs_review=true`; do not fabricate work-item linkage.
- Document type/status mapped per existing legacy contract rules with review flag where status unknown.

#### C2 — Zero-amount contracts

- Import **metadata / document shell** only.
- Set `zero_amount_needs_review=true`.
- Do **not** create finance obligation or receivable automatically.

#### C3 — Missing template id (order stages)

- **Not a blocker** for historical structure import.
- Apply fallback template/category: `legacy_unknown_template`.
- Set `template_needs_review=true` on affected stages.
- Defer template-dependent document generation until template mapping approved.

---

## 5. Resulting write-import policy proposal

For **future staging write-import planning** (execution still requires separate approval):

### Allowed into staging write-import (first wave)

| Entity | Policy |
|---|---|
| Clients / contacts (parties) | import |
| Services / catalog | import |
| Orders | import with **`orders.total_amount` authoritative** |
| Order items | import with derived line amounts as **metadata** |
| Contracts | import with review flags (`null_order_link`, `zero_amount`) per C1/C2 |
| Payments (linked) | import when `order_id` present and linkage valid |
| Payments (orphan) | import per **B2** — standalone historical, `needs_review` |
| Order stages | import with **C3** fallback template |

### Held / needs review

| Item | Hold reason |
|---|---|
| Finance posting for mismatched orders (20) | A4 hold until manual review |
| Orphan payment final allocation (57) | B2 — not auto-posted |
| Zero-amount contract financial effects (~3) | C2 — no auto obligation |
| Template-dependent document generation (37 stages) | C3 — fallback only |

### Still blocked (no change)

- Live import
- Cutover
- Production lead routing changes
- Automatic finance/accounting posting (without review clearance)
- Deleting or mutating legacy source data
- `/dashboard` changes

---

## 6. Approval checklist

Business owner / product approval required before staging write-import **planning** proceeds:

- [ ] **Approve A1:** `orders.total_amount` authoritative for order header
- [ ] **Approve A4:** hold finance/payment posting for mismatched orders (20)
- [ ] **Approve B2:** import orphan payments as standalone historical payments with `needs_review`
- [ ] **Approve C1:** contract policy for null order links (standalone + `link_needs_review`)
- [ ] **Approve C2:** zero-amount contract policy (metadata shell + `zero_amount_needs_review`)
- [ ] **Approve C3:** missing template fallback (`legacy_unknown_template` + `template_needs_review`)
- [ ] **Still block live import**
- [ ] **Still block cutover**
- [ ] **Still block write-import execution** until technical implementation plan is created and separately approved

---

## 7. Next gate

| If memo approved | Next step |
|---|---|
| All checklist items approved | Create **staging write-import planning doc only** (`docs/ai/plans/...`) — no execution |
| Partial approval | Revise memo; update mapping/report classification where needed |
| Rejected | Return to masked report review / mapping fix planning |

**Hard rule:** no write-import, no staging import execution, no live migration until:

1. This business decision memo is approved, **and**
2. A separate technical write-import implementation plan is approved, **and**
3. A separate write-import execution gate is approved.

---

## 8. Safety statement

- Gate B dry-run **not rerun** in this step.
- Raw `consulting_os.db` **not read**.
- Raw client rows **not read**.
- Raw PII **not printed**.
- No SQLite writes.
- No Core writes/imports.
- Live systems not touched.
- `/dashboard` not changed.
- No adapter/code changes.

---

## 9. Memo verdict

### `READY_FOR_BUSINESS_APPROVAL`

Sufficient masked dry-run evidence exists to decide import policy. Awaiting explicit checklist approval from business owner before staging write-import planning.
