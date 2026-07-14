# Implementation Report — Marketing M7-C1 Backend Preflight v2

**Date:** 2026-07-14  
**Project:** Flexity / coreops-platform  
**Gate:** M7-C1 only (backend)  
**HQ approval:** backend implementation only — no FE / deploy / migration  

---

## Status

## ✅ **COMPLETE — LOCAL GREEN**

Backend Preflight v2 rules + additive report shape + tests.  
**Not committed / not deployed** until separate HQ approval.

---

## What changed

### New

| File | Role |
|------|------|
| `backend/app/modules/marketing/service/preflight_rules.py` | Pure helpers: topic context, social length, media missing |

### Updated

| File | Role |
|------|------|
| `backend/app/modules/marketing/service/approval.py` | Wire M7-C1 rules; store report `version=m7-c1` |
| `backend/app/modules/marketing/schemas.py` | `PreflightResponse` v2 fields; pack detail exposes `preflight_report_json` |
| `backend/app/modules/marketing/service/packs.py` | Map `preflight_report_json` on detail |
| `backend/tests/test_marketing_preflight_approval.py` | Happy paths require approved rich topic; M7-C1 cases |
| `docs/ai/plans/2026-07-14-marketing-m7-implementation-plan.md` | Checklist status |
| `docs/ai/plans/2026-07-14-marketing-m7-c-implementation-plan.md` | Checklist progress |

---

## Report v2 shape

Stored in `preflight_report_json` and returned on `POST …/preflight`:

```json
{
  "version": "m7-c1",
  "passed": true,
  "status": "passed|warning|failed",
  "errors": [],
  "blockers": [],
  "warnings": [],
  "checks": [],
  "checklist": [],
  "channel_eligibility": {},
  "topic_context_summary": {},
  "channel_checks": [],
  "media_checks": {}
}
```

Backward compatible: existing `errors` / `warnings` / `checks` retained (`blockers` mirrors `errors`, `checklist` mirrors `checks`).

---

## Blockers implemented

| Code | Rule |
|------|------|
| `topic_missing` | No linked topic (upgrade from soft warning) |
| `topic_not_approved` | Linked topic not approved (M6) |
| `no_publishable_text` | No non-empty channel text (M6) |
| `channel_text_missing` | Missing default channel rows (M6) |
| `pack_metadata_incomplete` | title/slug/planned_date (M6) |
| `media_invalid_mime` | Invalid mime (M6) |
| `context_triple_missing` | audience + pain + CTA all empty |
| `all_texts_too_short` | All non-empty social texts &lt; 20 chars |

---

## Warnings implemented

| Code | Rule |
|------|------|
| `insight_missing` | insight empty |
| `source_ref_missing` | source_ref empty |
| `cta_missing_for_funnel` | funnel in diagnosis/consultation/product_education/objection_handling + CTA empty |
| `media_missing` | no media metadata rows |
| `channel_text_short` | social text present but &lt; 40 chars |
| `notes_missing` | notes empty |
| `topic_planned_date_missing` | topic planned_date empty |
| M6 kept | `insights_text_empty`, `telegram_text_too_long`, `media_not_1080` |

---

## Approval behavior

```text
blockers (errors) → preflight_status=failed, pack=preflight_failed → approve blocked
warnings only → preflight_status=passed, pack=ready_for_approval → approve allowed
```

Unchanged: `approve` still requires `preflight_status == passed`.

---

## Tests run

```bash
python -m pytest backend/tests/test_marketing_preflight_approval.py \
  backend/tests/test_marketing_packs.py \
  backend/tests/test_marketing_topics.py -q
```

**Result:** `52 passed`

---

## Migration

**None.** Alembic stays on `0015`. Uses existing `preflight_report_json`.

---

## Frontend

**Not touched** (M7-C2).

---

## Publish / Margosya

**Untouched.**

---

## Risks / known issues

1. Packs **without topic** now fail preflight (intentional product upgrade — deploy note needed).  
2. Happy-path tests require approved topic + editorial audience/pain/cta.  
3. Thresholds 20 / 40 may need tuning after Асем smoke.  
4. FE still shows raw codes until M7-C2.  
5. Dirty local tree still has unrelated WIP — do not broad-add on commit.

---

## What was not touched

- Frontend / M7-C2  
- Deploy / production / env  
- Alembic / migrations  
- Publish / Margosya / inbound / landing  
- Smoke data cleanup  
- Commit / push  

---

## Next recommended step

1. HQ package review → stage/commit M7-C1 allow-list only.  
2. Then M7-C2 FE Preflight UX.  
3. Deploy + smoke on pack `7ab244ef-…` after merge.
