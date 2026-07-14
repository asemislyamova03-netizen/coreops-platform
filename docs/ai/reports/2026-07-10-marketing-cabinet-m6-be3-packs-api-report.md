# Marketing Cabinet M6-BE3 — Packs API Closeout Report

**Date:** 2026-07-10  
**Branch:** Marketing Cabinet / ContentOps Cabinet  
**Slice:** M6-BE3 — Packs API (local only)  
**Prerequisite:** M6-BE1 + M6-BE2 complete

---

## HQ Summary

### 1. Status

**COMPLETE (local)** — Packs API implemented with shared pack factory, detail response, tenant isolation, tests, and reconciliation with `POST /topics/{id}/take`.

### 2. Files changed

| File | Action |
|------|--------|
| `backend/app/modules/marketing/service/slugify.py` | created — shared slug helper |
| `backend/app/modules/marketing/service/pack_factory.py` | created — shared draft pack + texts creation |
| `backend/app/modules/marketing/service/packs.py` | created — Packs service |
| `backend/app/modules/marketing/repository.py` | modified — unified `MarketingRepository` + pack queries |
| `backend/app/modules/marketing/schemas.py` | modified — pack request/response models |
| `backend/app/modules/marketing/routes.py` | modified — pack endpoints |
| `backend/app/modules/marketing/service/topics.py` | modified — `take` uses `pack_factory` |
| `backend/app/modules/marketing/models.py` | modified — pack ↔ media/logs relationships |
| `backend/tests/test_marketing_packs.py` | created — 14 pack API tests |
| `docs/ai/reports/2026-07-10-marketing-cabinet-m6-be3-packs-api-report.md` | created |

### 3. Migration changed

**No** — uses existing `0015_marketing_cabinet_mvp` tables.

### 4. Endpoints implemented

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/v1/marketing/packs` | List packs (tenant-scoped, filters) |
| `POST` | `/api/v1/marketing/packs` | Create draft pack + 4 empty texts |
| `GET` | `/api/v1/marketing/packs/{pack_id}` | Pack detail |
| `PATCH` | `/api/v1/marketing/packs/{pack_id}` | Safe header update |
| `GET` | `/api/v1/marketing/packs/{pack_id}/texts` | Read-only texts list |

**List filters:** `status`, `topic_id`, `planned_date`, `skip`, `limit`  
**Ordering:** `created_at DESC`

### 5. Pack detail response

`PackDetailResponse` includes:

- Pack header: id, tenant_id, slug, pack_dir_name, title, planned_date
- Status fields: `status`, `preflight_status`, `approval_status`, `publish_status`
- Metadata: `source`, `campaign_id`, `plan_item_id`, `channel_config_json`, `legacy_git_path`, `metadata_json`
- Audit: `created_by_user_id`, `created_at`, `updated_at`
- **`topic`**: `TopicSummaryInPack` (id, legacy_topic_id, title, rubric, status) when linked
- **`texts`**: 4 channel rows with text, status, char_count, version
- **`media_assets`**: list (empty until BE4)
- **`publish_logs`**: list (empty until BE6)

### 6. Text rows behavior

- **Create pack** and **`take` topic** both call `create_draft_pack_with_texts()` in `pack_factory.py`
- Default channels: `telegram`, `instagram`, `threads`, `insights`
- If topic has `recommended_channels`, those are used (with validation); otherwise defaults
- Each row: `text=""`, `status=draft`, `char_count=0`, `version=1`
- Unique constraint: one row per `(pack_id, channel)`

### 7. Tenant isolation

- All pack queries filter by `tenant_id`
- Cross-tenant `GET` / `PATCH` → **404** Pack not found
- `topic_id` on create/patch validated in same tenant → foreign topic → **404** Topic not found
- List returns only current tenant packs

### 8. Tests added

**`tests/test_marketing_packs.py`** (14 tests):

1. create pack without topic  
2. create pack with topic  
3. slug uniqueness per tenant (409 `pack_slug_exists`)  
4. create pack creates 4 empty text rows  
5. list packs tenant-scoped  
6. get pack detail includes texts  
7. get pack detail includes topic summary  
8. patch title/source  
9. patch topic same tenant  
10. cross-tenant topic link → 404  
11. cross-tenant pack access → 404  
12. `take` pack visible via Packs API detail  
13. module entitlement on `/packs`  
14. list filters by status/topic_id  

### 9. Tests result

```text
python -m pytest tests/test_marketing_packs.py tests/test_marketing_topics.py \
  tests/test_marketing_migration.py tests/test_modules.py tests/test_parties.py -q

39 passed
```

### 10. Existing regressions

- `test_marketing_topics.py` — **12 passed** (take still works via shared factory)
- `test_marketing_migration.py` — **2 passed**
- `test_modules.py` — **5 passed**
- `test_parties.py` — **6 passed**

### 11. What was not touched

- Migration `0015`
- UI / `platform-console`
- Margosya
- GitHub Actions / git export
- Publish, preflight, approval endpoints
- Text PUT / media upload
- `.env`, deploy, staging/production
- Booking / Clinic / Trailers / public inbound

### 12. Risks

| Risk | Notes |
|------|-------|
| PATCH `status` limited to `draft` / `archived` | Approval/publish states blocked intentionally until BE5/BE6 |
| `PackUpdate.topic_id` cannot unlink (set null) | Not in MVP scope; explicit null handling deferred |
| Detail loads media/logs via relationship + fallback query | Empty lists OK for MVP |
| `take` still returns `TakeTopicPackResponse` (lighter) | Full detail available via `GET /packs/{id}` |

### 13. Next recommended step

**M6-BE4 — Texts & Media API** (`GET/PUT texts`, media register) after HQ approval.

Optional parallel track: **M6-FE1** nav shell once BE3 is reviewed.

---

## Implementation notes

### Shared pack factory

`create_draft_pack_with_texts()` centralizes:

- Draft defaults: `status=draft`, `preflight_status=not_run`, `approval_status=draft`, `publish_status=not_started`
- `pack_dir_name = {planned_date}-{slug}`
- 4 empty text rows

Used by:

- `MarketingPackService.create_pack()`
- `MarketingTopicService.take_topic()`

### PATCH safe fields

Allowed: `title`, `topic_id`, `source`, `status` (only `draft` or `archived`)

Blocked via PATCH: `approved`, `published`, `publishing`, `scheduled`, and direct `approval_status` / `publish_status` / `preflight_status` changes.

### Slug generation

`slugify(title)` when slug omitted; uniqueness enforced per tenant with `409 pack_slug_exists`.

---

## Approval gate

| Gate | Status |
|------|--------|
| M6-BE3 local implementation | ✅ Done |
| HQ review | ⏳ Pending |
| M6-BE4 texts/media | ⏳ Next |
