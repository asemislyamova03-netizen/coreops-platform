# Marketing Cabinet M6-BE5 — Preflight & Approval Closeout Report

**Date:** 2026-07-10  
**Branch:** Marketing Cabinet / ContentOps Cabinet  
**Slice:** M6-BE5 — Preflight & Approval API (local only)  
**Prerequisites:** M6-BE1–BE4 complete

---

## HQ Summary

### 1. Status

**COMPLETE (local)** — Preflight checks, approve/reject lifecycle, approval reset on text/media edit, tests, and pack detail status reflection implemented.

### 2. Files changed

| File | Action |
|------|--------|
| `backend/app/modules/marketing/service/approval.py` | created — preflight, approve, reject |
| `backend/app/modules/marketing/service/approval_reset.py` | created — shared reset helper |
| `backend/app/modules/marketing/service/texts.py` | modified — reset on text edit |
| `backend/app/modules/marketing/service/media.py` | modified — reset on media attach/update/archive |
| `backend/app/modules/marketing/schemas.py` | modified — preflight/approve/reject schemas |
| `backend/app/modules/marketing/exceptions.py` | modified — `preflight_not_passed`, invalid state |
| `backend/app/modules/marketing/routes.py` | modified — 3 new endpoints |
| `backend/tests/test_marketing_preflight_approval.py` | created — 11 tests |
| `docs/ai/reports/2026-07-10-marketing-cabinet-m6-be5-preflight-approval-report.md` | created |

### 3. Migration changed

**No** — uses `preflight_report_json`, `preflight_status`, `preflight_at`, `approval_status`, `approved_at`, `approved_by_user_id` from migration `0015`.

### 4. Endpoints implemented

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/v1/marketing/packs/{pack_id}/preflight` | Run MVP preflight checks |
| `POST` | `/api/v1/marketing/packs/{pack_id}/approve` | Approve pack (no publish) |
| `POST` | `/api/v1/marketing/packs/{pack_id}/reject` | Reject pack |

### 5. Preflight behavior

**Allowed pack statuses:** `draft`, `preflight_failed`, `ready_for_approval`, or `draft` + `approval_status=rejected` (re-run after fix).

**Checks (MVP):**

| Check | Severity |
|-------|----------|
| Pack metadata (title, slug, planned_date) | error |
| Text rows exist for 4 channels | error |
| At least one channel has non-empty text | error |
| Per-channel text present | eligibility map |
| Insights empty | warning only |
| Telegram char_count > 4096 | warning |
| Topic not linked | warning |
| Topic linked but not approved | error |
| Media mime invalid | error |
| Media not 1080×1080 | warning only |

**On pass:** `preflight_status=passed`, `status=ready_for_approval`  
**On fail:** `preflight_status=failed`, `status=preflight_failed`  
**Report persisted:** `preflight_report_json`, `preflight_at`

No external API calls, no GHA, no publish.

### 6. Approval behavior

- Requires `preflight_status=passed` and `status=ready_for_approval`
- Sets `approval_status=approved`, `status=approved`, `approved_at`, `approved_by_user_id`
- Before preflight → **409** `preflight_not_passed`
- No publish side effects

### 7. Reject behavior

- Allowed from `ready_for_approval` or `approved`
- Sets `approval_status=rejected`, `status=draft`
- Clears `approved_at` / `approved_by_user_id`
- Optional `reason` stored in `metadata_json.reject_reason`

### 8. Reset-on-edit behavior

`reset_pack_after_content_change()` called from:

- `PUT /packs/{id}/texts/{channel}`
- `POST /packs/{id}/media`
- `PATCH /media/{asset_id}`
- `DELETE /media/{asset_id}` (archive)

**When pack is past pure draft** (preflight passed, ready_for_approval, or approved):

- `approval_status` → `draft`
- `preflight_status` → `not_run`
- `status` → `draft`
- Clears `approved_at`, `approved_by_user_id`, `preflight_at`, `preflight_report_json`

### 9. Pack detail status reflection

`GET /packs/{id}` returns updated `status`, `preflight_status`, `approval_status`, `approved_at`, `approved_by_user_id`, and persisted `preflight_report_json` via detail fields.

### 10. Tenant isolation

Cross-tenant preflight/approve/reject → **404** Pack not found. `require_module("marketing")` enforced.

### 11. Tests added

**`tests/test_marketing_preflight_approval.py`** (11 tests):

1. preflight empty pack fails  
2. preflight with telegram passes  
3. preflight multiple channels passes  
4. preflight cross-tenant 404  
5. approve before preflight fails  
6. approve after preflight succeeds  
7. reject works  
8. text edit after approve resets  
9. media edit after approve resets  
10. pack detail reflects statuses  
11. module entitlement on preflight  

### 12. Tests result

```text
python -m pytest tests/test_marketing_preflight_approval.py \
  tests/test_marketing_texts_media.py tests/test_marketing_packs.py \
  tests/test_marketing_topics.py tests/test_marketing_migration.py \
  tests/test_modules.py tests/test_parties.py -q

65 passed
```

### 13. Existing regressions

- `test_marketing_texts_media.py` — **15 passed**
- `test_marketing_packs.py` — **14 passed**
- `test_marketing_topics.py` — **12 passed**
- `test_marketing_migration.py` — **2 passed**
- `test_modules.py` — **5 passed**
- `test_parties.py` — **6 passed**

### 14. What was not touched

- Migration `0015`
- UI / `platform-console`
- Margosya
- Publish endpoint / git export / GitHub Actions
- Object storage / file upload
- External channel token checks
- `.env`, deploy, staging/production
- Booking / Clinic / Trailers

### 15. Risks

| Risk | Notes |
|------|-------|
| Instagram/telegram not required individually | BE5 uses "at least one channel" per HQ scope (M4 stricter checks deferred) |
| No `rejected_at` column | Reason stored in `metadata_json` |
| Reset on media attach after approve | By design — any content change invalidates approval |
| Preflight re-run from `approved` blocked | Must reset via text edit or reject first |

### 16. Next recommended step

**M6-BE6 — Publish logs + git export bridge** (or **M6-FE1** nav shell if HQ prefers UI after BE5) after HQ approval.

---

## State machine (implemented)

```text
draft
  → POST /preflight (pass) → ready_for_approval + preflight_status=passed
  → POST /preflight (fail) → preflight_failed + preflight_status=failed
ready_for_approval
  → POST /approve → approved
  → POST /reject → draft + approval_status=rejected
approved
  → POST /reject → draft + approval_status=rejected
  → text/media edit → draft + approval_status=draft + preflight_status=not_run
```

---

## Approval gate

| Gate | Status |
|------|--------|
| M6-BE5 local implementation | ✅ Done |
| HQ review | ⏳ Pending |
| M6-BE6 publish/git export | ⏳ Next |
