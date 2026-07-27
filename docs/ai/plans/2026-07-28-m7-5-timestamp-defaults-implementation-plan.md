# Implementation Plan: M7.5 timestamp defaults hotfix

## Goal

Fix stage Guide 500 / Rubric false-duplicate 409 caused by missing PostgreSQL
`now()` defaults on M7.5 tables created by migrations 0027/0028, and narrow
rubric IntegrityError mapping to real unique violations only.

## Classification

- Project: Flexity
- Category: universal_module (marketing)
- Risk: medium (additive migration + exception mapping)
- Base: `origin/main` @ `298bac4`
- Branch: `fix/marketing-m7-5-timestamp-defaults`

## Schema audit (0027/0028 only)

| Table | Column | Model nullable | Model server_default | Model onupdate | Migration 0027/0028 default | Action |
|---|---|---|---|---|---|---|
| marketing_guides | created_at | NO | `func.now()` | — | **empty** | SET DEFAULT now() |
| marketing_guides | updated_at | NO | `func.now()` | `func.now()` | **empty** | SET DEFAULT now() |
| marketing_rubrics | created_at | NO | `func.now()` | — | **empty** | SET DEFAULT now() |
| marketing_rubrics | updated_at | NO | `func.now()` | `func.now()` | **empty** | SET DEFAULT now() |
| marketing_content_plans | created_at | NO | `func.now()` | — | **empty** | SET DEFAULT now() |
| marketing_content_plans | updated_at | NO | `func.now()` | `func.now()` | **empty** | SET DEFAULT now() |
| marketing_content_plan_items | created_at | NO | `func.now()` | — | **empty** | SET DEFAULT now() |
| marketing_content_plan_items | updated_at | NO | `func.now()` | `func.now()` | **empty** | SET DEFAULT now() |

No local model field overrides for these timestamps (all via `TimestampMixin`).
**No TimestampMixin change.**

## Scope

### Files to modify / add

- `backend/alembic/versions/20260728_0029_mkt_timestamp_defaults.py` (new)
- `backend/app/modules/marketing/service/rubrics.py`
- `backend/tests/test_migration_0027_mkt_guides_rubrics.py` (head assert)
- `backend/tests/test_migration_0028_mkt_content_plans.py` (head assert)
- `backend/tests/test_migration_0029_mkt_timestamp_defaults.py` (new)
- `backend/tests/test_marketing_m75_timestamp_defaults_pg.py` (new)
- `backend/tests/test_marketing_rubric_integrity_mapping.py` (new)
- `docs/ai/plans/2026-07-28-m7-5-timestamp-defaults-implementation-plan.md` (this)
- `docs/ai/reports/2026-07-28-m7-5-timestamp-defaults-implementation-report.md` (new)

### Files not to touch

- `backend/app/core/models.py` (TimestampMixin)
- UI / console
- production/stage deploy
- M8-D3
- unrelated modules

## Steps

1. Add migration 0029 (PG-only ALTER SET/DROP DEFAULT).
2. Narrow rubric IntegrityError → duplicate only for UniqueViolation on
   `uq_marketing_rubrics_tenant_code`; rollback; re-raise otherwise.
3. Tests + regression + compileall.
4. Implementation report.

## Tests/checks

- Alembic single head = 0029
- upgrade 0028→0029 defaults present; downgrade drops defaults only
- PG alembic path: Guide/Rubric/ContentPlan/Item create timestamps not null
- Duplicate mapping + non-unique IntegrityError not masked
- M7.5 A–D targeted regression
- `git diff --check`, `compileall`, security review

## Risks

- Stage still needs separate migrate+redeploy after commit approval.
- 0028 latent same bug — covered by 0029.

## Rollback

- Alembic downgrade 0029 (DROP DEFAULT only).
- Revert rubric mapping commit if needed.

## Approval

Status: **approved by HQ** (this message) — implement locally, no commit/push/deploy.
