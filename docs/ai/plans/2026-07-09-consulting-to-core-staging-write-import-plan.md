# Plan: Consulting -> Core Staging Write-Import (Planning Only)

**Date:** 2026-07-09  
**Status:** planning only (no execution)  
**Scope:** documentation only

---

## 1. Context

- Gate B masked dry-run completed with exit code `0`.
- PII scan: `PASS`.
- No SQLite/Core/live writes were made in Gate B read-only path.
- Masked report path (outside repo):  
  `/home/ubuntu/import_work/reports/consulting_gate_b_dry_run_2026-07-09.json`
- Sanitized report:  
  `docs/ai/reports/2026-07-09-consulting-to-core-gate-b-dry-run-report.md`
- Business decision memo:  
  `docs/ai/decisions/2026-07-09-consulting-import-business-decisions.md`

---

## 2. Approved staging-only policy

- `orders.total_amount` is authoritative for order header.
- Line derived amount (`qty * unit_price`) is stored as metadata/reconciliation.
- Mismatched orders are marked `amount_needs_review`.
- Finance/payment posting for mismatched orders is held.
- Orphan payments are imported as standalone historical payments with:
  - `needs_review`
  - `unlinked_legacy_payment`
  - no auto-link to orders
  - no clean revenue posting
- Null-order contracts are imported standalone with review flag.
- Zero-amount contracts are imported as metadata/doc shell only.
- Missing template fallback: `legacy_unknown_template`.

---

## 3. Staging write-import goal

Goal for future approved execution step:

- Write transformed legacy Consulting data into **isolated staging Core only**.
- Target DB: `coreops_staging_0013`.
- Target revision: `0014_core_branches_baseline`.
- Target tenant: `2507e425-d4bc-432d-8f75-97fb69567de9`.
- Target default branch: `e85d837b-7951-4a61-9d69-d96d58010ced`.
- No live writes.
- No legacy DB writes.

---

## 4. Entities allowed for staging planning

Allowed for future staging write-import design:

- clients/contacts as parties/contacts;
- services/catalog;
- orders/work items;
- order items as metadata/line structure;
- contracts/documents;
- linked payments where link exists;
- orphan payments as standalone historical payments with review flag.

Held / explicitly not auto-posted:

- final accounting posting;
- finance posting for mismatched orders;
- automatic allocation of orphan payments;
- live migration;
- cutover;
- lead routing.

---

## 4.1 Required execution sequence (mandatory)

The following is **required execution sequence** for future staging write-import.
This is not a recommendation. Execution that diverges from this order must fail preflight.

1. import batch / audit context
2. services/catalog
3. clients/parties/contacts
4. orders/work items
5. order items / line metadata
6. contracts/documents
7. linked payments
8. orphan payments as standalone historical payments
9. review flags / audit summary / validation report

---

## 4.2 Conflict policy matrix (mandatory)

Conservative default policy:

- default: skip existing by source reference;
- no destructive overwrite;
- no silent merge;
- update only explicitly safe metadata/review flags;
- fail-closed on ambiguous duplicate source refs;
- fail-closed on tenant/default_branch mismatch;
- fail-closed if source ref points to existing record in another tenant/import batch.

| Entity | Source identity | Conflict behavior | Update allowed? | Fail condition |
|---|---|---|---|---|
| import batch | `source_system + import_batch_id` | fail if exists with different checksum/context | no | duplicate batch id with mismatch |
| services/catalog | `services:<source_id>` | skip existing by source ref | only safe metadata/review fields | source ref bound to another tenant/batch |
| clients/parties | `clients:<source_id>` | skip existing by source ref | safe metadata/review fields only | ambiguous duplicate by source ref |
| contacts | `contacts:<source_id>` | skip existing by source ref | safe metadata/review fields only | parent party tenant mismatch |
| orders/work items | `orders:<source_id>` | skip existing by source ref | `amount_needs_review`/audit metadata only | source ref collision across tenants/batches |
| order items/line metadata | `order_items:<source_id>` | skip existing by source ref | reconciliation/review metadata only | parent order ref mismatch |
| contracts/documents | `contracts:<source_id>` | skip existing by source ref | `null_order_link`/`zero_amount_needs_review` flags only | ambiguous target mapping |
| linked payments | `payments:<source_id>` | skip existing by source ref | review/status metadata only | linked order missing or tenant mismatch |
| orphan standalone payments | `payments:<source_id>` + `unlinked_legacy_payment` | skip existing by source ref | review/status metadata only | attempted auto-link in this mode |
| review flags/audit rows | `import_batch_id + entity + source_ref` | upsert inside batch scope only | yes, safe audit counters/flags | cross-batch or cross-tenant overwrite |

---

## 5. Required technical design (before execution)

Technical design requirements for later implementation:

- Separate write-import entrypoint from dry-run entrypoint.
- Source SQLite access only in read-only mode.
- Target Core adapter restricted to staging-write path only.
- Explicit target safety check (for example `--target-db coreops_staging_0013` and fail-closed on mismatch).
- Staging writes MUST use dedicated env `CONSULTING_STAGING_DATABASE_URL` (never app `DATABASE_URL`).
- On execute, verify `current_database()` matches `--target-db`; missing URL / mismatch / production-like name → fail closed.
- Never print database URL or credentials in logs/errors.
- Clearly separate Gate B dry-run (read-only) from staging write-import plan/execute modes.
- Mandatory flags:
  - `--tenant-id`
  - `--default-branch-id`
  - `--backup-id`
  - `--dry-run-report` (or checksum/reference to Gate B masked report)
- Idempotency key and source external IDs required.
- Duplicate prevention strategy required.
- Transaction strategy required.
- Rollback strategy required.
- Audit log strategy required.
- Import batch ID required.
- No PII in logs.

---

## 6. Idempotency / duplicate prevention

For every imported row preserve source identity:

- source table
- source id
- source import batch

Rerun behavior must prevent duplicate creation for:

- parties
- orders/work items
- payments
- documents/contracts

Unique source reference strategy must be explicit.

Conflict behavior must be defined explicitly (choose and document per entity):

- skip existing; and/or
- update only safe fields; and/or
- fail-closed.

---

## 7. Review flags / metadata

Required review flags / metadata model for future write-import:

- `amount_needs_review`
- `unlinked_legacy_payment`
- `zero_amount_needs_review`
- `template_needs_review`
- `legacy_unknown_template`
- `null_order_link`
- `source_legacy_consulting_os`
- `import_batch_id`

---

## 8. Pre-execution checks (future gate)

Before any staging write-import execution:

- confirm `CONSULTING_STAGING_DATABASE_URL` is set (never fall back to `DATABASE_URL`);
- confirm target DB is `coreops_staging_0013` via `--target-db` AND `SELECT current_database()`;
- confirm target is not live `coreops` / other production-like names;
- confirm Alembic current is `0014_core_branches_baseline`;
- confirm tenant/default branch exist;
- confirm source DB opens read-only;
- confirm backup ID is valid;
- confirm output/import report path is outside repo;
- snapshot staging counts before import;
- optional staging DB backup/snapshot before import;
- confirm no pending write-import report path exists (to avoid overwrite ambiguity).

---

## 9. Execution design (template only, do not run)

`DO NOT RUN WITHOUT SEPARATE STAGING WRITE-IMPORT EXECUTION APPROVAL`

```bash
# TEMPLATE ONLY (NOT EXECUTED IN THIS STEP)
cd /opt/flexity/coreops_staging_0013/runner/backend

PYTHONPATH=/opt/flexity/coreops_staging_0013/runner/backend \
/opt/flexity/envs/coreops/bin/python \
  scripts/c2c_staging_write_import.py \
  --mode staging-write-import \
  --source-db /var/www/consult_app/instance/consulting_os.db \
  --backup-id consulting-gate-b-20260709-0734-asem \
  --tenant-id 2507e425-d4bc-432d-8f75-97fb69567de9 \
  --default-branch-id e85d837b-7951-4a61-9d69-d96d58010ced \
  --target-db coreops_staging_0013 \
  --dry-run-report /home/ubuntu/import_work/reports/consulting_gate_b_dry_run_2026-07-09.json \
  --import-batch-id <TO_BE_GENERATED> \
  --output /home/ubuntu/import_work/reports/consulting_staging_write_import_<ts>.json
```

---

## 10. Post-import validation plan (future execution gate)

After future staging write-import:

- row counts imported by entity;
- no duplicate source references;
- all imported rows have tenant/default_branch context;
- review flag counts match dry-run expectations;
- mismatched order count = `20` or explained;
- orphan standalone payments count = `57` or explained;
- zero-amount contracts count ~`3` or explained;
- missing template fallback count ~`37` or explained;
- staging Core counts before/after;
- no live change;
- PII/log scan pass.

---

## 11. Rollback strategy (plan only)

- Use staging-only transaction rollback where feasible.
- If transaction boundaries are partial, use import-batch-based cleanup strategy.
- Cleanup must rely on stored source references and `import_batch_id`.
- Never modify legacy SQLite.
- Never touch live environment.

### 11.1 Staged rollback runbook (mandatory)

Pre-rollback prerequisites:

- pre-import snapshot/counts must exist;
- `import_batch_id` is mandatory;
- rollback scope limited to target tenant `2507e425-d4bc-432d-8f75-97fb69567de9`;
- rollback uses `import_batch_id` + source refs only.

Rollback criteria:

- **Partial rollback** when failure is isolated to a subset of entities and dependency graph remains consistent.
- **Full rollback** when tenant scope integrity, source-ref integrity, or sequencing integrity is compromised.

Rollback order (reverse of import order):

1. review/audit summary rows
2. orphan payments
3. linked payments
4. documents/contracts
5. order items/metadata
6. orders/work items
7. contacts
8. parties/clients
9. services/catalog (only rows created by this batch)
10. import batch marker

Post-rollback validation:

- counts return to pre-import baseline or are explicitly explained;
- no imported source refs remain for rolled-back batch;
- no orphan imported rows remain;
- live unchanged;
- source SQLite unchanged.

---

## 11.2 Backup artifact immutability (mandatory)

Backup artifact:

- `/home/ubuntu/import_work/backups/consulting_os_readonly_backup_20260709_073425_a474334c.db`

Rules:

- backup is immutable for the import process;
- import runner must not open backup in write mode;
- backup mtime must be checked before and after execution;
- backup must not be copied into repo;
- backup must not be modified, vacuumed, migrated, or re-saved.

---

## 12. Acceptance criteria (planning readiness)

Planning is ready only if:

- technical write adapter design is explicit;
- idempotency is defined;
- rollback is defined;
- review flags are defined;
- no live path is possible by design checks;
- PII/log policy is defined;
- execution command template is prepared but not run.

---

## 13. Non-goals

- no actual write-import in this step;
- no live import;
- no live Alembic upgrade;
- no live DB schema changes;
- no live DB data writes;
- no live backend sync;
- no cutover;
- no `/dashboard` change;
- no lead routing changes;
- no subscription billing changes;
- no production deployment;
- no automatic finance/accounting posting.

---

## 14. Approval gate checklist

- [ ] approve staging write-import adapter implementation
- [ ] approve staging write-import preflight
- [ ] approve staging write-import execution
- [ ] approve rollback strategy
- [ ] approve review flag policy
- [ ] still block live import
- [ ] still block cutover
- [ ] still block `/dashboard` changes

---

## Planning verdict

`READY_FOR_STAGING_WRITE_IMPORT_IMPLEMENTATION_PLAN_REVIEW`

