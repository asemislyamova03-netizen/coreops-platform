# Marketing Cabinet M6-BE1 + M6-BE2 — Closeout Report

**Date:** 2026-07-10  
**Branch:** Marketing Cabinet / ContentOps Cabinet  
**Slice:** M6-BE1 (module skeleton + migration) + M6-BE2 (Topics API)  
**Scope:** local only — no deploy, no Margosya, no UI, no publish bridge

---

## HQ Summary

### 1. Status

**COMPLETE (local)** — Marketing module skeleton, migration `0015_marketing_cabinet_mvp`, Topics API, tests, and module registry wiring implemented and verified locally.

### 2. Files changed

| File | Action |
|------|--------|
| `backend/alembic/versions/20260709_0015_marketing_cabinet_mvp.py` | created |
| `backend/app/modules/marketing/__init__.py` | created |
| `backend/app/modules/marketing/enums.py` | created |
| `backend/app/modules/marketing/models.py` | created |
| `backend/app/modules/marketing/schemas.py` | created |
| `backend/app/modules/marketing/repository.py` | created |
| `backend/app/modules/marketing/exceptions.py` | created |
| `backend/app/modules/marketing/service/__init__.py` | created |
| `backend/app/modules/marketing/service/topics.py` | created |
| `backend/app/modules/marketing/routes.py` | created |
| `backend/app/api/v1/router.py` | modified — include marketing router |
| `backend/app/modules/models.py` | modified — register ORM models |
| `backend/app/modules/module_registry/seed.py` | modified — add `marketing` module |
| `backend/tests/test_marketing_migration.py` | created |
| `backend/tests/test_marketing_topics.py` | created |
| `docs/ai/reports/2026-07-10-marketing-cabinet-m6-be1-be2-report.md` | created |

### 3. Migration created

- **Revision:** `0015_marketing_cabinet_mvp`
- **File:** `backend/alembic/versions/20260709_0015_marketing_cabinet_mvp.py`
- **Revises:** `0014_core_branches_baseline`

### 4. Tables created (schema only)

1. `marketing_content_topics`
2. `marketing_publication_packs`
3. `marketing_publication_texts`
4. `marketing_media_assets`
5. `marketing_publish_logs`
6. `marketing_lead_attribution`

No business logic on packs/media/logs/attribution beyond minimal pack+text creation inside `POST /topics/{id}/take`.

### 5. API endpoints implemented

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/v1/marketing/health` | Module health (BE1) |
| `GET` | `/api/v1/marketing/topics` | List topics |
| `POST` | `/api/v1/marketing/topics` | Create topic |
| `GET` | `/api/v1/marketing/topics/{topic_id}` | Get topic |
| `PATCH` | `/api/v1/marketing/topics/{topic_id}` | Update topic |
| `POST` | `/api/v1/marketing/topics/{topic_id}/take` | Take topic → draft pack + 4 empty texts |
| `POST` | `/api/v1/marketing/topics/{topic_id}/archive` | Archive topic |
| `POST` | `/api/v1/marketing/topics/{topic_id}/mark-used` | Increment `used_count`, set `last_used_at` |

### 6. Tests added

**`tests/test_marketing_migration.py`**
- models registered in metadata
- topic table columns present

**`tests/test_marketing_topics.py`**
- `require_module("marketing")` guard
- health endpoint
- create / list / get / update topic
- archive hides from default list
- mark-used counter + `last_used_at`
- mark-used sets `used` status when not reusable
- take creates draft pack + 4 channel texts
- take requires `approved` status
- duplicate blocked on same topic+date
- cross-tenant isolation (404 on foreign topic)
- marketing in module registry

### 7. Tests result

```text
python -m pytest tests/test_marketing_migration.py tests/test_marketing_topics.py \
  tests/test_modules.py tests/test_parties.py -q

25 passed
```

### 8. Tenant isolation

- All topic queries filter by `tenant_id` from `X-Tenant-ID` / `TenantContext`.
- Cross-tenant `GET` / `PATCH` returns **404** (not found), not data leak.
- Pack/text rows created on take inherit tenant_id from context.

### 9. Module entitlement behavior

- Routes use `Depends(require_module("marketing"))`.
- Module disabled → **403** `Module 'marketing' is not enabled`.
- Registry seed: `marketing` depends on `parties`.
- Enable path: `POST /api/v1/tenants/{id}/modules/parties/enable` then `.../marketing/enable`.

### 10. Existing Core regressions

- `tests/test_modules.py` — **pass**
- `tests/test_parties.py` — **pass**
- No changes to parties/crm/workflows routes.

### 11. What was not touched

- Margosya (`margosya-os`)
- `platform-console/` UI
- GitHub Actions / git export bridge
- Publish endpoints
- Packs/Text/Media/Logs/Attribution REST APIs (beyond take-side-effect)
- `create-core-lead`
- `.env`, production/staging config
- Booking / Clinic / Trailers
- `public_leads.py`

### 12. Risks

| Risk | Mitigation |
|------|------------|
| Migration not applied on staging/prod | Explicit HQ gate before `alembic upgrade` |
| `take` creates packs without BE3 API | Expected; BE3 will expose pack CRUD |
| Partial unique on `legacy_topic_id` allows multiple NULLs | Matches M2/M5 design |
| Alembic downgrade enum drop may differ by DB driver | Local sqlite tests use `create_all`; PG migration test deferred |
| `GET /topics/suggested` deferred to later slice | Not in HQ-approved BE2 endpoint list |

### 13. Next recommended step

**M6-BE3 — Packs API** (`GET/POST/PATCH /marketing/packs`, dashboard aggregates) after HQ approval.

Then **M6-FE1** nav shell when BE2+BE3 are stable.

---

## Implementation notes

### Take topic behavior (M5-aligned)

1. Validates `status == approved` → else `409 topic_not_approved`
2. Duplicate check: non-reusable + used, or existing pack for same `planned_date`
3. Creates `marketing_publication_packs` (draft) + empty `marketing_publication_texts` for channels (topic `recommended_channels` or default 4)
4. Returns `TakeTopicPackResponse` (201) — not full Packs API

### Topic statuses

`draft` | `approved` | `used` | `archived`

Archive excludes topic from default list (`include_archived=true` to show).

### Module registry entry

```python
{
    "code": "marketing",
    "name": "Marketing Cabinet",
    "description": "Content topics, packs, publish workflow",
    "dependencies_json": {"required": ["parties"], "recommended": []},
}
```

---

## Approval gate

| Gate | Status |
|------|--------|
| M6-BE1+BE2 local implementation | ✅ Done |
| HQ review of this report | ⏳ Pending |
| Staging migration | ❌ Not in scope |
| M6-BE3 | ⏳ Next |
