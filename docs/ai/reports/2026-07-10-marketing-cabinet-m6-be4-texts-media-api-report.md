# Marketing Cabinet M6-BE4 — Texts & Media API Closeout Report

**Date:** 2026-07-10  
**Branch:** Marketing Cabinet / ContentOps Cabinet  
**Slice:** M6-BE4 — Texts & Media API (local only)  
**Prerequisites:** M6-BE1/BE2 (topics), M6-BE3 (packs)

---

## HQ Summary

### 1. Status

**COMPLETE (local)** — Text upsert API and metadata-only media API implemented with tenant isolation, tests, and pack detail integration.

### 2. Files changed

| File | Action |
|------|--------|
| `backend/app/modules/marketing/service/texts.py` | created |
| `backend/app/modules/marketing/service/media.py` | created |
| `backend/app/modules/marketing/repository.py` | modified — text/media queries |
| `backend/app/modules/marketing/schemas.py` | modified — `PackTextUpsert`, `MediaCreate`, `MediaUpdate` |
| `backend/app/modules/marketing/routes.py` | modified — texts PUT + media CRUD |
| `backend/app/modules/marketing/exceptions.py` | modified — channel/mime errors |
| `backend/app/modules/marketing/enums.py` | modified — `ALLOWED_MEDIA_MIME_TYPES` |
| `backend/app/modules/marketing/service/packs.py` | modified — exclude archived media in detail |
| `backend/tests/test_marketing_texts_media.py` | created — 15 tests |
| `docs/ai/reports/2026-07-10-marketing-cabinet-m6-be4-texts-media-api-report.md` | created |

### 3. Migration changed

**No** — uses existing `0015_marketing_cabinet_mvp` tables.

### 4. Endpoints implemented

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/v1/marketing/packs/{pack_id}/texts` | List texts (existing, now via `MarketingTextService`) |
| `PUT` | `/api/v1/marketing/packs/{pack_id}/texts/{channel}` | Upsert channel text |
| `GET` | `/api/v1/marketing/packs/{pack_id}/media` | List active media metadata |
| `POST` | `/api/v1/marketing/packs/{pack_id}/media` | Attach media metadata |
| `PATCH` | `/api/v1/marketing/media/{asset_id}` | Update media metadata |
| `DELETE` | `/api/v1/marketing/media/{asset_id}` | Soft-archive media (`status=archived`) |

**PATCH for texts:** not implemented — `PUT` is sufficient for MVP upsert.

### 5. Text update behavior

- **Channels:** `telegram`, `instagram`, `threads`, `insights` (enum-validated; invalid → 422)
- **Upsert:** updates existing row from `pack_factory` or creates new row if missing
- **Fields updated:** `text`, `char_count=len(text)`, `version += 1` on update
- **Default status:** `draft` after edit (or explicit `status` in payload)
- **Empty text:** **allowed** (draft packs may have empty channel text)
- **Version note:** first PUT on pack-created rows starts at `version=2` (row already exists at `version=1` from factory)

### 6. Approval reset behavior

**Deferred to M6-BE5.**

Text edits do **not** reset `pack.approval_status` in this slice. Comment left in `MarketingTextService.upsert_pack_text()`.

### 7. Media metadata behavior

- **No file upload** — metadata only (`storage_key`, `public_url`, etc.)
- **POST** creates row with `status=stored`
- **MIME allowlist:** `image/png`, `image/jpeg`, `image/jpg`, `image/webp` → else `409 invalid_mime_type`
- **1080×1080:** optional metadata fields only; no hard validation block
- **DELETE:** soft-archive (`status=archived`); excluded from list and pack detail
- **PATCH:** safe metadata fields only (file_name, mime, storage, urls, dimensions, role, alt_text, status, metadata_json)

### 8. Pack detail updated

`GET /packs/{id}` now reflects:

- Updated `texts[]` after PUT
- Attached `media_assets[]` (non-archived)
- Archived media hidden from detail and `/media` list

### 9. Tenant isolation

- Pack/text/media operations scoped by `tenant_id`
- Cross-tenant pack text PUT → **404** Pack not found
- Cross-tenant media GET/PATCH/DELETE → **404**
- `require_module("marketing")` unchanged on all routes

### 10. Tests added

**`tests/test_marketing_texts_media.py`** (15 tests):

1. update telegram + instagram text  
2. update threads + insights text  
3. unsupported channel → 422  
4. text visible in pack detail  
5. version increment on re-PUT  
6. empty text allowed  
7. cross-tenant text update → 404  
8. media attach metadata  
9. media list  
10. media in pack detail  
11. media PATCH  
12. media DELETE → archived  
13. invalid mime → 409  
14. cross-tenant media denied  
15. module entitlement  

### 11. Tests result

```text
python -m pytest tests/test_marketing_texts_media.py tests/test_marketing_packs.py \
  tests/test_marketing_topics.py tests/test_marketing_migration.py \
  tests/test_modules.py tests/test_parties.py -q

54 passed
```

### 12. Existing regressions

- `test_marketing_packs.py` — **14 passed**
- `test_marketing_topics.py` — **12 passed**
- `test_marketing_migration.py` — **2 passed**
- `test_modules.py` — **5 passed**
- `test_parties.py` — **6 passed**

### 13. What was not touched

- Migration `0015`
- UI / `platform-console`
- Margosya
- Publish / preflight / approval endpoints
- Git export / GitHub Actions
- Object storage / signed URLs / file upload
- `.env`, deploy, staging/production
- Booking / Clinic / Trailers

### 14. Risks

| Risk | Mitigation |
|------|------------|
| No pack `approval_status` reset on text edit | Documented; BE5 will add approval service |
| MIME allowlist may need expansion later | Easy to extend `ALLOWED_MEDIA_MIME_TYPES` |
| Version starts at 2 on first PUT | Expected — factory pre-creates rows at v1 |
| No publish_log side effects on media delete | Safe soft-archive only |

### 15. Next recommended step

**M6-BE5 — Preflight & Approval** (`POST /packs/{id}/preflight`, approve/reject, approval reset on text edit) after HQ approval.

---

## Approval gate

| Gate | Status |
|------|--------|
| M6-BE4 local implementation | ✅ Done |
| HQ review | ⏳ Pending |
| M6-BE5 preflight/approval | ⏳ Next |
