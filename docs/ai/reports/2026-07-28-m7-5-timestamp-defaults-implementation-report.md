# Report: M7.5 Timestamp Defaults Hotfix (local)

**Date:** 2026-07-28  
**Branch:** `fix/marketing-m7-5-timestamp-defaults`  
**Base:** `298bac4d73a1cbd26b390e893977c03d8b976bf7`  
**Worktree:** `.worktrees/m7-5-timestamp-defaults`  
**Verdict:** **M7_5_TIMESTAMP_FIX_READY_FOR_COMMIT**

## Exact root cause

ORM INSERT omitted `created_at`/`updated_at` (model `TimestampMixin.server_default=func.now()`), while Alembic **0027/0028** created those columns as `NOT NULL` **without** PostgreSQL `DEFAULT now()`. Stage → `NotNullViolation` (23502). Guide → 500; Rubric → false `409 marketing_rubric_duplicate` via broad `IntegrityError` catch.

## Affected columns (8)

| Table | Columns |
|---|---|
| `marketing_guides` | `created_at`, `updated_at` |
| `marketing_rubrics` | `created_at`, `updated_at` |
| `marketing_content_plans` | `created_at`, `updated_at` |
| `marketing_content_plan_items` | `created_at`, `updated_at` |

## Migration contract (`0029_mkt_timestamp_defaults`)

- `down_revision`: `0028_mkt_content_plans`
- Upgrade (PostgreSQL only): `ALTER TABLE … ALTER COLUMN … SET DEFAULT now()` for all 8 columns
- Downgrade: `DROP DEFAULT` only — no data/table drops
- SQLite: no-op (local API tests use `create_all`)
- Does **not** change nullability, indexes, FKs, lifecycle, or rows

## Exception mapping

`MarketingRubricService.create_rubric`:

- `marketing_rubric_duplicate` **only** for UniqueViolation / constraint `uq_marketing_rubrics_tenant_code`
- Other `IntegrityError`: `session.rollback()`, safe log (`constraint` + `sqlstate` only), re-raise → internal 500
- No global exception framework; **TimestampMixin not modified**

## Changed files

- `backend/alembic/versions/20260728_0029_mkt_timestamp_defaults.py` (new)
- `backend/app/modules/marketing/service/rubrics.py`
- `backend/tests/test_migration_0027_mkt_guides_rubrics.py` (head → 0029)
- `backend/tests/test_migration_0028_mkt_content_plans.py` (head → 0029)
- `backend/tests/test_migration_0029_mkt_timestamp_defaults.py` (new)
- `backend/tests/test_marketing_m75_timestamp_defaults_pg.py` (new)
- `backend/tests/test_marketing_rubric_integrity_mapping.py` (new)
- `docs/ai/plans/2026-07-28-m7-5-timestamp-defaults-implementation-plan.md`
- `docs/ai/reports/2026-07-28-m7-5-timestamp-defaults-implementation-report.md` (this)

## Tests

- `git diff --check`: clean
- `compileall`: OK
- Targeted suite (migration 0027/0028/0029, integrity mapping, guides/rubrics API, content plans A–D, PG integration): **all passed**
- PG alembic path: Guide/Rubric/Plan/Item create timestamps not null; raw INSERT without timestamps uses DB default; duplicate 409; cross-tenant same code 201

## Security

Security review: **PASS** ([Review](0557923d-eab6-485e-b3c4-0193aef5e1c4#changes)) — no medium+ findings; mapping narrowing improves diagnostics without leaking SQL to clients.

## Stage redeploy requirement

After commit approval:

1. Ship release with this SHA to stage (isolated 298bac4 lineage).
2. Run Alembic upgrade **0028 → 0029** on `coreops_stage` only.
3. Restart stage unit only.
4. Re-run Guide/Rubric create dogfood.
5. Production: **not** until separate HQ approval (prod still on 0026 / `c90e482`).

**Closeout note (2026-07-28):** stage steps 1–4 completed; formal closeout GREEN at `438e39c`. Canonical: `docs/ai/reports/2026-07-28-marketing-m7-5-closeout-report.md`. Production still not promoted.

## Confirmations

- Global `TimestampMixin`: **unchanged** (`git diff` empty for `backend/app/core/models.py`)
- No commit / push / deploy performed
- No UI / M8-D3 changes
