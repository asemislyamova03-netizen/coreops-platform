# Implementation Plan: M7-D historical-publish API

**Date:** 2026-07-14
**Status:** implemented locally; not deployed
**Product plan:** `docs/ai/plans/2026-07-14-marketing-m7-d-historical-publish-api-plan.md`
**HQ used for this doc:** `APPROVED: historical-publish API planning`
**HQ implementation approval:** `APPROVED: continue historical-publish API implementation`

---

## Goal

Implement `POST /api/v1/marketing/packs/{pack_id}/record-historical-publish` that writes `marketing_publish_logs` and optionally sets `publish_status` to `published` / `partial` without any external publish side effects.

---

## Classification

| Field | Value |
|-------|--------|
| Project | Flexity |
| Category | universal_module (marketing) |
| Risk | medium |
| Migration | **no** (v1) |
| Frontend | **optional / defer** |

---

## Scope

### Files to modify (likely)

| File | Change |
|------|--------|
| `backend/app/modules/marketing/schemas.py` | `HistoricalPublishChannelItem`, `HistoricalPublishRequest`, `HistoricalPublishResponse` |
| `backend/app/modules/marketing/repository.py` | `create_publish_log`, find existing historical log (idempotency) |
| `backend/app/modules/marketing/service/historical_publish.py` | **new** service: validate, insert logs, rollup status, pack metadata summary |
| `backend/app/modules/marketing/routes.py` | register POST route |
| `backend/tests/test_marketing_historical_publish.py` | **new** pytest coverage |

Optional (same PR only if tiny):

| File | Change |
|------|--------|
| `backend/app/modules/marketing/service/packs.py` | expose helper only if needed — prefer dedicated service |

### Files not to touch

- publish live scripts (`scripts/content/publish_*.py`)
- platform-console Publish enablement
- Alembic migrations
- CRM / parties / booking / public_leads
- Margosya-os
- Wave A content packs (read-only evidence later)
- pack approve / reject flows (except ensuring this API does not call them)

---

## Steps

1. ✅ Add request/response schemas (per-channel list, source, evidence_ref, targets, needs_review).
2. ✅ Add repository methods: create log + lookup by idempotency fingerprint.
3. ✅ Implement `MarketingHistoricalPublishService.record(...)`:
   - tenant pack load;
   - refuse if `pack.status == publishing`;
   - for each channel: create or skip;
   - rollup `publish_status` per product plan;
   - set `metadata_json["historical_publish"]` summary;
   - **never** mutate `approval_status` / pack workflow to `published`;
   - **never** import or call outbound publishers.
4. ✅ Wire route under `/marketing/packs/{pack_id}/record-historical-publish`.
5. ✅ Add focused tests (see below).
6. ✅ Run local `pytest` + syntax compilation on touched modules.
7. ⏳ Separate PR (marketing path-scoped). **No deploy** until dedicated HQ.
8. After API live: separate HQ for Wave A marking script/execution.

---

## Tests / checks

| Test | Expect |
|------|--------|
| Create TG+IG historical → targets default | `publish_status=published`, 2 logs, pack `status` unchanged |
| Create TG only + `needs_review=true` | `publish_status=partial`, 1 log |
| Create `insights_site` only | `publish_status=partial`, never `published` |
| Idempotent second call same evidence | `skipped_existing=2`, no duplicate logs |
| Unknown channel rejected | 422 |
| Empty channels rejected | 422 |
| Pack not found / wrong tenant | 404 |
| Pack `status=publishing` | 409 |
| Guard: service does not reference publish_telegram/instagram modules | static import check / code review |

Also: existing marketing approve/preflight tests still green.

---

## Wave A marking plan (after API deploy — separate HQ)

Script (extend or sibling of `scripts/marketing_m7d_content_fill_wave_a.py`):

1. Dry-run print payloads from content-pack evidence.
2. Execute with double flags + tenant `flexity-sales`.
3. Allow-list:

| Group | Action |
|-------|--------|
| 10 strong | TG+IG historical; expect `published` |
| `ai-personal-content-assistant` | TG only + `needs_review=true` → `partial` |
| `1s-erp-novogo-pokoleniya` | `insights_site` only → `partial` |

4. Verify GET pack detail shows logs + status.
5. Confirm no pack became `approval_status=approved` via this path.
6. Confirm publish UI still disabled.

---

## Risks

| Risk | Mitigation |
|------|------------|
| Accidental outbound publish | No publisher imports; no queue_item_id; code review checklist |
| Marking pack workflow `published` by mistake | Explicitly only touch `publish_status` |
| Full `published` for insights-only | Rollup ignores non-target channels |
| Duplicate logs | Idempotency key |
| Dirty-tree CRM files in PR | Path-scoped commit only marketing + tests + docs |

---

## Rollback

- Revert PR.
- Existing historical logs remain (harmless audit).
- Optional ops: leave packs as-is; no schema downgrade.

---

## Approval

**Status:** local implementation complete; no deploy, staging, commit, or push

Do **not** mark Wave A in production until:

```text
APPROVED: execute M7-D historical-publish Wave A marking
```
