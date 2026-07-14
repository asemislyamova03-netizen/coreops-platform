# Marketing M7-A — Topic taxonomy + rich metadata

**Date:** 2026-07-14
**Project:** Flexity / coreops-platform
**Gate:** M7-A only
**Status:** GREEN (local code complete; not committed; not deployed)

---

## Goal

Give Асем usable topic create/edit with editorial metadata for real content work, without publish/Margosya and without DB migration.

---

## What shipped

### Backend

- New helper: `backend/app/modules/marketing/topic_metadata.py`
  - Keys: `audience`, `pain`, `insight`, `source_ref`, `cta`, `funnel_stage`, `notes`, `planned_date`
  - Create merges explicit flat fields into `metadata_json`
  - Patch merges/clears via `model_fields_set` (empty string clears key)
- `TopicCreate` / `TopicUpdate` / `TopicResponse` accept/return flat editorial fields
- `service/topics.py` maps create/update/response through helpers
- Column `source` unchanged (provenance: `manual` / `console`)
- Editorial reference = `source_ref` inside `metadata_json` only
- Existing list filters (`status`, `rubric`, `search`) unchanged
- Packs / publish / approval untouched

### Frontend

- `marketingTaxonomy.ts` (+ test): rubrics, funnel, priority helpers, payload builders
- `MarketingTopicsPage.tsx`: rich create + **edit** form; list columns (rubric, angle, priority, planned, audience/CTA compact); client filters by rubric/status/priority
- Types extended for optional editorial fields
- Minor CSS: form span / textarea

### Docs

- This report
- Implementation plan checklist updated for M7-A done

---

## Metadata contract

| Field | Storage | Notes |
|-------|---------|--------|
| title, rubric, angle, priority, status | columns | first-class |
| planned_date | `metadata_json.planned_date` | ISO date string; used by Take when present |
| audience, pain, insight, source_ref, cta, funnel_stage, notes | `metadata_json` | flattened on API response |
| source | column | provenance only — not editorial |

API preferred shape: frontend sends flat fields; backend writes into `metadata_json`.

---

## Rubrics (10)

1. Авторская колонка Асем (`asem_column`)
2. Flexity как цифровой организм (`digital_organism`)
3. ERP/CRM будущего (`erp_crm_future`)
4. AI-сотрудники (`ai_employees`)
5. Бизнес-диагностика (`business_diagnosis`)
6. Разбор заявок и продаж (`sales_inbox_review`)
7. Кейсы / путь клиента (`client_journey`)
8. Marketing / ContentOps (`marketing_contentops`)
9. Clinic / Booking / отраслевые модули (`industry_modules`)
10. Founder notes / за кадром (`founder_notes`)

Unknown rubric codes still allowed (soft allow-list / label fallback to raw code).

## Funnel options

`awareness` | `trust` | `diagnosis` | `consultation` | `product_education` | `objection_handling`

## Priority options

UI: `low` / `normal` / `high` → API int `0` / `5` / `10`

---

## Tests run

```text
python -m pytest backend/tests/test_marketing_topics.py backend/tests/test_marketing_packs.py -q
→ 30 passed

npx tsx src/pages/workspace/marketing/marketingTaxonomy.test.ts → ok
npx tsx src/pages/workspace/marketing/marketingLabels.test.ts → ok

VITE_API_BASE_URL=https://flexity.asia/api/v1 npm run build → exit 0
  dist/assets/index-Bt3X7FOi.js
```

Coverage highlights:

- create persists rich metadata + flattened response
- patch updates rich metadata
- legacy M6 create (title/rubric only) still works
- tenant isolation for metadata topics

---

## Migration

**None.** No Alembic change. No schema DDL.

---

## Publish / Margosya

**Not touched.** Disabled paths remain out of scope.

---

## Risks / known issues

1. `planned_date` lives in JSON, not a DB column — list sort by planned date is FE-only / not server-sortable.
2. Priority filter on list is client-side (API has no `priority=` query yet).
3. Soft rubrics: typos in free-text historical rubrics won’t map to RU labels.
4. Clearing editorial fields on PATCH requires sending empty string (or null) for that field — omitted fields leave previous values.
5. Local tree dirty with unrelated WIP — do not stage broadly when committing M7-A later.

---

## Forbidden zones (verified not touched)

- migrations / alembic versions for marketing
- production deploy / env / server / DB writes
- publish/export / Margosya
- CRM, public inbound, landing, Booking/Clinic/Trailers
- billing / subscriptions / tenant conversion

---

## Files changed (M7-A)

**Backend**

- `backend/app/modules/marketing/topic_metadata.py` (new)
- `backend/app/modules/marketing/schemas.py`
- `backend/app/modules/marketing/service/topics.py`
- `backend/tests/test_marketing_topics.py`

**Frontend**

- `platform-console/src/pages/workspace/marketing/marketingTaxonomy.ts` (new)
- `platform-console/src/pages/workspace/marketing/marketingTaxonomy.test.ts` (new)
- `platform-console/src/pages/workspace/marketing/MarketingTopicsPage.tsx`
- `platform-console/src/types/marketing.ts`
- `platform-console/src/index.css`

**Docs**

- `docs/ai/reports/2026-07-14-marketing-m7-a-taxonomy-metadata-report.md` (this file)
- `docs/ai/plans/2026-07-14-marketing-m7-implementation-plan.md` (checklist)

---

## What was not done (intentionally)

- M7-B pack context UI
- M7-C preflight v2
- M7-D 10 operating topics / setup
- M7-E closeout
- Commit / PR / deploy

---

## Next recommended step

1. HQ review of this report + local UI smoke on Topics create/edit (staging or local API).
2. Separate approval for commit/PR of M7-A files only.
3. Then start **M7-B — pack detail context blocks** (docs already planned; no migration).
