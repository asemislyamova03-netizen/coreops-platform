# Marketing M7-B — Pack context implementation report

**Date:** 2026-07-14  
**Project:** Flexity / coreops-platform  
**Gate:** M7-B only  
**Status:** GREEN (local code complete; not committed; not deployed)

---

## Goal

Surface source-topic editorial context on Pack Detail for writing, without preflight enforcement or publish/Margosya.

---

## What shipped

### Backend (Option A)

- Expanded `TopicSummaryInPack` with:
  `angle`, `priority`, `audience`, `pain`, `insight`, `source_ref`, `cta`, `funnel_stage`, `notes`, `planned_date`
- `MarketingPackService._topic_summary` maps columns + `extract_editorial_fields(metadata_json)`
- Additive / optional — thin or missing metadata still returns 200

### Frontend

- `marketingPackContext.ts` (+ test): context rows, writing brief, soft completeness
- `MarketingPackDetailPage.tsx`: three panels above tabs
  1. **Контекст темы**
  2. **Бриф для написания**
  3. **Полнота контекста** (display-only; note that M7-C will enforce)
- Link **Редактировать тему** → Topics list (`/marketing/topics`) — no dedicated topic-edit route
- Pack meta label clarified: «Плановая дата пака»
- CSS for marketing pack context panels

### Docs

- This report
- Parent M7 / M7-B implementation plan checklist noted DONE local

---

## Context fields exposed (nested topic)

| Field | Storage |
|-------|---------|
| title, rubric, status, angle, priority | columns |
| audience, pain, insight, source_ref, cta, funnel_stage, notes, planned_date | `metadata_json` flatten |

---

## Completeness behavior

Soft checklist only:

- Аудитория / Боль / Инсайт|источник / CTA / Текст каналов / Медиа  
- Levels: полный / частичный / слабый / не заполнен  
- **Does not** block approval or change preflight (M7-C)

Empty editorial display: **«Не заполнено»**

---

## Tests / build

```text
python -m pytest backend/tests/test_marketing_packs.py backend/tests/test_marketing_topics.py -q
→ 33 passed

npx tsx marketingPackContext.test.ts → ok
npx tsx marketingTaxonomy.test.ts → ok
npx tsx marketingLabels.test.ts → ok

VITE_API_BASE_URL=https://flexity.asia/api/v1 npm run build → exit 0
  dist/assets/index-ELLYr9Ww.js
  dist/assets/index-CayYvMi5.css
```

New backend coverage:

- pack detail with rich topic metadata  
- pack detail with thin topic  
- pack detail without topic  

---

## Migration

**None.**

---

## Publish / Margosya

**Not touched.** Publish tab remains disabled.

---

## Files changed

**Backend**

- `backend/app/modules/marketing/schemas.py`
- `backend/app/modules/marketing/service/packs.py`
- `backend/tests/test_marketing_packs.py`

**Frontend**

- `platform-console/src/types/marketing.ts`
- `platform-console/src/pages/workspace/marketing/MarketingPackDetailPage.tsx`
- `platform-console/src/pages/workspace/marketing/marketingPackContext.ts` (new)
- `platform-console/src/pages/workspace/marketing/marketingPackContext.test.ts` (new)
- `platform-console/src/index.css`

**Docs**

- `docs/ai/reports/2026-07-14-marketing-m7-b-pack-context-report.md` (this file)
- `docs/ai/plans/2026-07-14-marketing-m7-b-implementation-plan.md` (status)

---

## Risks / known issues

1. «Редактировать тему» opens Topics list — cannot deep-link to edit a specific topic (no route).  
2. Nested topic enrichment also appears on pack **list** responses (additive; small).  
3. Soft completeness does not affect workflow — intentional.  
4. Local tree remains dirty with unrelated WIP — stage allow-list only later.

---

## What was not touched

- Alembic / migrations / env / production  
- Preflight v2 / approval rules  
- Publish / Margosya / export  
- Smoke cleanup / DB writes on prod  
- CRM / inbound / landing  

---

## Next recommended step

1. HQ review → stage/commit/PR M7-B only.  
2. Deploy backend allow-list + console (no migration).  
3. Smoke: open pack for M7-A Metadata Smoke Topic (or take topic into pack).  
4. Then **M7-C** preflight v2.
