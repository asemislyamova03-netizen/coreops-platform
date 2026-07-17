# Booking MVP Domain Extract Manifest

**Date:** 2026-07-17  
**Source (READ ONLY):** `C:/Users/АДМИН/OneDrive/Documents/Flexity` @ `feature/marketing-m8-publish-bridge` `9658a82` (dirty WIP)  
**Target worktree:** `.worktrees/booking-mvp-domain`  
**Branch:** `feature/booking-mvp-domain` from `origin/main` `76773ec`  
**Alembic head on main (baseline):** `0023_mkt_storage_profiles`

## Classification

| Field | Value |
|-------|-------|
| Project | Flexity |
| Category | universal_module (booking industry package domain) |
| Risk | medium (seed entitlement changes; no new migration) |
| Forbidden | dirty root writes; marketing/CRM/branches/process-overlay; wholesale shared seeds/conftest; push/merge/deploy |

## Migrations decision

| Item | Action | Reason |
|------|--------|--------|
| `20250702_0012_phase12_booking_e1.py` | **SKIPPED (already on main)** | Identical SHA256 on dirty and `origin/main`. Revision `0012_booking_e1` already in chain; `0013` revises it. |
| New booking migrations after 0012 | **NONE found** | Dirty root only references booking in 0012 (+ 0013 payment down_revision mention). |
| Renumber to 0024+ | **NOT REQUIRED** | No conflicting new booking revision to land after 0023. |

**Expected Alembic head after extract:** still `0023_mkt_storage_profiles` (single head).

## Copied (verbatim from dirty root)

### Module

- `backend/app/modules/booking/**` (all `.py`; `__pycache__` excluded)

### Tests

- `backend/tests/test_booking_models.py`
- `backend/tests/test_booking_availability.py`
- `backend/tests/test_booking_hold.py`
- `backend/tests/test_booking_seed.py`
- `backend/tests/test_booking_timezone.py`

### Docs

- `docs/booking/**` (6 files)
- `docs/FLEXITY_BOOKING_E1B_CLOSEOUT_REPORT.md`
- `docs/FLEXITY_BOOKING_E1B_IMPLEMENTATION_PLAN.md`
- `docs/FLEXITY_BOOKING_E2_IMPLEMENTATION_PLAN.md`
- `docs/FLEXITY_BOOKING_E2B_CLOSEOUT_REPORT.md`
- `docs/FLEXITY_BOOKING_MVP_AUDIT_AND_PLAN.md`

### Scripts

- `backend/scripts/seed_booking_demo.py`

### Change requests (separable last CR section)

- Appended `CR-2026-07-02-001: Flexity Booking Industry Package` into `docs/ai/CHANGE_REQUESTS.md` (was absent on main)

## Manual hunks (not wholesale seed copies)

### `backend/app/modules/module_registry/seed.py`

- Inserted `booking` module definition between `ai` and `marketing` (marketing already on main).

### `backend/app/modules/subscriptions/seed.py`

- Added 6 booking `FEATURES`
- Added `booking` to business/enterprise `default_modules_json`
- Added business booking feature codes + limits

### `backend/app/modules/models.py`

- Added booking ORM import block **on top of main** (main already had Branch + Process overlay + Marketing). Dirty root `models.py` was **not** copied wholesale (dirty also lacked `ProcessRun`).

### `backend/app/modules/booking/service/__init__.py` (local reconstruct fix)

Dirty root had circular import: `repository` → `service.timezone` → package `__init__` → `availability` → `repository`. Made `__init__.py` import-light (nothing imports the package root). Required for green tests.

## Intentionally skipped

- Dirty `models.py` wholesale
- Dirty `module_registry/seed.py` / `subscriptions/seed.py` wholesale
- `conftest.py`, `test_tenants*`, unrelated CRM/marketing/process-overlay
- `.ai_local/`, credentials, `.env`, other worktrees
- Migration `0012` (already on main, identical)
- Marketing / branches / process-overlay code and migrations
- Any HTTP routes for booking (none present in dirty booking package)

## Verification results

1. **Alembic:** single head `0023_mkt_storage_profiles`. Ephemeral isolated schema in local PG (`PGOPTIONS=search_path`): upgrade head → 9 `booking_*` tables → downgrade -1 → upgrade head. Public `alembic_version` unchanged (`0020_process_overlay_e1b`).
2. **Booking tests:** 39 passed
3. **Regression:** 50 passed (`test_auth`, `test_tenants`, `test_modules`, `test_entitlements`, `test_parties`, `test_health`, `test_catalog`, `test_finance`)
4. **Secret scan:** no hits in staged booking paths
5. **Scope:** no marketing/CRM/process-overlay code copied; `.ephemeral-pg/` local artifact **not** committed
6. **Commit:** local only; **no push**
