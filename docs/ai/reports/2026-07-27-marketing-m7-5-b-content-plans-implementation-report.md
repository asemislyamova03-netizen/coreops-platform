# Report: M7.5-B Marketing Content Plan persistence/API

**Date:** 2026-07-27
**Worktree:** `.worktrees/m7-5-b-content-plans`
**Branch:** `feature/marketing-m7-5-b-content-plans`
**Baseline:** `origin/main` @ `787e8ebeb84f0644734080977c8ecf98557398ca`
**Category:** `universal_module` (Marketing Cabinet)
**Slice:** M7.5-B only
**Status:** implemented locally — **not committed** (await HQ)

## HQ contract applied

1. Item API: POST/PATCH/cancel; no hard delete; status not via PATCH.
2. Ordering: `sort_order >= 0`; list order `planned_date, sort_order, created_at, id`.
3. Fingerprint: nullable + partial unique; **not** in B create/PATCH; replay deferred to C.
4. Plan lifecycle: approve / archive; approve requires ≥1 non-cancelled item; drafts→approved atomically; approved immutable except archive.
5. Item lifecycle: create/PATCH/cancel only in draft plan + draft item; cancelled terminal; topic_created not via B.
6. Nested create: header-only POST.
7. Packs: **not** altered (no `plan_item_id`).
8. `line_key` unique per plan (incl. cancelled → no reuse).

## line_key ↔ external_line_key contract (Slice B → C)

| Layer | Name | Notes |
|-------|------|-------|
| Future JSON import (Slice C) + HTTP API (B) | **`line_key`** | Public/stable id within one plan |
| DB column | **`external_line_key`** | `VARCHAR(128) NULL` on `marketing_content_plan_items` |
| Mapping | API/service | Create: `payload.line_key` → `item.external_line_key`; Response: `line_key=item.external_line_key` |
| Uniqueness | Partial unique `(tenant_id, plan_id, external_line_key) WHERE NOT NULL` | Same `line_key` OK across different plans/tenants; cancelled rows keep the key → **no reuse** in the same plan |
| PATCH | Not accepted | `line_key` immutable after create in B |

## Migration

| Item | Value |
|------|-------|
| Revision | `0028_mkt_content_plans` |
| Parent | `0027_mkt_guides_rubrics` |
| Tables | `marketing_content_plans`, `marketing_content_plan_items` |
| Single head | **yes** (`0028`) |
| Packs/topics schema | untouched |

## API contracts (`/api/v1/marketing`)

| Method | Path | RBAC |
|--------|------|------|
| GET | `/content-plans`, `/content-plans/{id}`, `.../items` | `require_module("marketing")` |
| POST/PATCH | `/content-plans`, `/content-plans/{id}` | settings admin |
| POST | `/content-plans/{id}/approve`, `/archive` | settings admin |
| POST/PATCH | `/content-plans/{id}/items`, `.../items/{id}` | settings admin |
| POST | `/content-plans/{id}/items/{id}/cancel` | settings admin |

**Not in B:** import/preview/commit, prompt-export, create-topic, UI.

## Files changed

### New
- `backend/alembic/versions/20260727_0028_mkt_content_plans.py`
- `backend/app/modules/marketing/service/content_plans.py`
- `backend/tests/test_marketing_content_plans_api.py`
- `backend/tests/test_migration_0028_mkt_content_plans.py`
- `docs/ai/reports/2026-07-27-marketing-m7-5-b-content-plans-implementation-report.md`

### Modified
- `backend/app/modules/marketing/{enums,exceptions,models,repository,routes,schemas}.py`
- `backend/app/modules/models.py`
- `backend/tests/test_migration_0027_mkt_guides_rubrics.py`
- `backend/tests/test_marketing_migration.py`

## Tests

| Suite | Result |
|-------|--------|
| content plans API | pass |
| migration 0027/0028 + marketing migration | pass |
| M7.5-A guides/rubrics regression | pass |
| topics regression | pass |
| **Total targeted** | **41 passed** |

## Security verdict

**PASS** ([Security Review](f79591d2-c70d-4308-9a2c-9e87e087632f)) — tenant isolation + settings-admin mutate; no medium+ findings.

## Compatibility evidence

- Guide/Rubric/Topics API tests green.
- No pack model/migration changes.
- `topic_id` always null in B create; no auto topic/pack.
- Existing Cabinet URLs for topics/packs untouched (no FE in B).

## Unresolved / deferred

- Fingerprint replay enforcement → **M7.5-C**.
- `topic_created` / create-topic → **M7.5-D**.
- Plan UI → **M7.5-D**.
- Optional soft unique `(plan, date, title)` not enforced (plan said soft-check optional; not required by HQ B decisions).

## Intentionally not touched

- Dirty root `feature/marketing-m8-publish-bridge`
- M7.5-A worktree
- M7.5-C/D, M8-D3, AI, publish, deploy, commit

## Verdict

**M7_5_B_READY_FOR_COMMIT**
