# Report: M8-D1 MarketingPublishDestination foundation

**Date:** 2026-07-23  
**Worktree:** `.worktrees/marketing-m8b-http-clean`  
**Branch:** `feature/marketing-m8b-http-clean-main`  
**Baseline HEAD (start):** `5249f045f59cb2a877316d10445bf3205d59c8ec`  
**Category:** `universal_module` (Marketing)  
**Slice:** D1 — model + migration + repository + tests only  
**Status:** HQ remediation applied (pre-commit)

## Goal

Add `MarketingPublishDestination` allow-list foundation with HQ-locked lifecycle/validation rules. No HTTP, adapters, dry-run, or execute.

## Classification

| Field | Value |
|---|---|
| Project | Flexity |
| Layer | universal_module |
| Risk | medium (schema + tenant FK; no live publish) |

## Files changed

| Path | Change |
|---|---|
| `backend/app/modules/marketing/enums.py` | Destination status/validation/type enums + helpers |
| `backend/app/modules/marketing/exceptions.py` | Destination validation / not-found / hard-delete (DuplicateError removed) |
| `backend/app/modules/marketing/models.py` | Destination ORM + `identity_locked_at` + composite/tenant RESTRICT FKs; connection UNIQUE `(tenant_id,id)` for FK target |
| `backend/app/modules/marketing/repository.py` | create/get/list/update/lifecycle + metadata boundary |
| `backend/app/modules/marketing/service/publish_destination_validation.py` | Recursive forbidden-key metadata validation |
| `backend/app/modules/marketing/schemas.py` | `PublishDestinationView` (+ `identity_locked_at`) |
| `backend/app/modules/models.py` | Register model |
| `backend/alembic/versions/20260723_0026_marketing_publish_destinations.py` | `0026_mkt_publish_destinations` ← `0025` (remediated in place; no 0027) |
| `backend/tests/test_marketing_publish_destinations_model.py` | Model/repo/lock/FK/metadata tests |
| `backend/tests/test_migration_0026_marketing_publish_destinations.py` | Alembic head/chain smoke |
| `backend/tests/test_marketing_migration.py` | Destination table smoke |
| `backend/tests/test_migration_0025_secret_envelope_versions.py` | Head ancestor assertion (0025 not sole head) |
| `docs/ai/plans/2026-07-23-m8-d-destinations-publish-contract-plan.md` | HQ locks + HQ wording cleanup |
| `docs/ai/reports/2026-07-23-m8-d1-publish-destination-model-implementation-report.md` | This report |

## HQ remediation delta (2026-07-23)

| # | Item | Status |
|---|---|---|
| 1 | Monotonic `identity_locked_at` lock | **Done** — set once on first VALID; UNCHECKED reset / disable / archive do not unlock; `external_id` needs unchecked ∧ lock NULL |
| 2 | Composite FK `(tenant_id, publishing_connection_id)` → connections `(tenant_id, id)` RESTRICT | **Done** — UNIQUE on connections added only in 0026; single-column connection FK removed |
| 3 | Destination `tenant_id` FK RESTRICT (no CASCADE) | **Done** + tenant-delete IntegrityError test |
| 4 | Metadata secret-key boundary (recursive, case-insensitive) | **Done** — create/update paths; values never in errors |
| 5 | Cleanup | **Done** — DuplicateError removed; duplicate connection-only index removed; plan ACTIVE/NOT_VALIDATED → enabled/unchecked wording |

## Intentionally not touched

- HTTP / D2–D4 / adapters / dry-run / execute
- Migrations `0025` and earlier (no 0027)
- Dirty Flexity root / commit / push / deploy

## Migration

| Field | Value |
|---|---|
| revision | `0026_mkt_publish_destinations` |
| down_revision | `0025_secret_envelope_versions` |
| table | `marketing_publish_destinations` |
| connection SoT FK | composite `(tenant_id, publishing_connection_id)` **RESTRICT** |
| tenant FK | **RESTRICT** |
| parent UNIQUE | `uq_marketing_publishing_conn_tenant_id_id` on connections (0026 only) |
| identity lock col | `identity_locked_at` nullable timestamptz |
| partial unique | `(tenant_id, publishing_connection_id, destination_type, external_id) WHERE status <> 'ARCHIVED'` |

## Checks

Scoped pytest + `git diff --check` + alembic single head 0026 (see session).

## Next safe step

**D2** (separate approval): Destination HTTP API + RBAC + redaction — still no dry-run/execute/adapters.

## Stop confirmation

D1 remediation complete in worktree. **No commit. No push. No HTTP. No adapters.**
