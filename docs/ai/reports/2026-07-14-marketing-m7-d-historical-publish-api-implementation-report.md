# Implementation Report — M7-D historical-publish API

**Date:** 2026-07-15
**Status:** local implementation and review-blocker fix complete; not deployed
**HQ:** `APPROVED: continue historical-publish API implementation`

## Delivered

- Added `POST /api/v1/marketing/packs/{pack_id}/record-historical-publish`.
- Added `MarketingHistoricalPublishService`, scoped by the current tenant.
- Records only `marketing_publish_logs` rows with `action="historical_record"` and `status="recorded"`.
- Updates only `pack.publish_status`; pack workflow `status` and `approval_status` remain unchanged.
- Uses tenant-scoped idempotency:
  - `pack_id + channel + source + evidence_ref`;
  - without evidence, `pack_id + channel + source + published_at date`.
- Rollup defaults to Telegram plus Instagram:
  - both recorded → `published`;
  - any missing target, `needs_review`, or insights-only → `partial`;
  - historical rows from earlier API calls are included in the rollup.
- Review blocker fix: historical logs with `metadata_json["needs_review"] == true`
  remain audit rows but do not count as confirmed target-channel coverage.

## Safety boundaries

- No outbound publisher imported or called.
- No Margosya queue/export integration.
- No frontend changes.
- No migration.
- No deploy, production API write, production SQL write, or Wave A marking.
- No change to approval or pack workflow transitions.

## Validation

```text
python -m py_compile app/modules/marketing/schemas.py app/modules/marketing/repository.py app/modules/marketing/service/historical_publish.py app/modules/marketing/routes.py
# passed

python -m pytest tests/test_marketing_historical_publish.py -q
# 12 passed; pre-existing SQLite FK-drop warnings

python -m pytest tests/test_marketing_preflight_approval.py tests/test_marketing_packs.py -q
# 36 passed; pre-existing SQLite FK-drop warnings
```

## Focused coverage

- Telegram + Instagram rollup to `published`.
- Telegram-only and insights-site-only remain `partial`.
- Same evidence is idempotent.
- No-evidence fallback is idempotent for the same published date.
- An existing partial record rolls up after the missing channel is recorded.
- A previous `needs_review=true` target record does not complete a later rollup.
- Instagram-only remains `partial`.
- `pack.status=publishing` returns `409` without writing logs or changing publish status.
- Unknown channel returns `422`.
- Missing or cross-tenant pack returns `404`.
- Workflow and approval statuses remain unchanged.
- Static guard confirms the service has no Margosya or known outbound publisher dependency.

## Changed files

- `backend/app/modules/marketing/schemas.py`
- `backend/app/modules/marketing/repository.py`
- `backend/app/modules/marketing/service/historical_publish.py`
- `backend/app/modules/marketing/routes.py`
- `backend/tests/test_marketing_historical_publish.py`
- `docs/ai/plans/2026-07-14-marketing-m7-d-historical-publish-implementation-plan.md`
- this report

## Next safe step

Repeat the path-scoped code review after the blocker fix. A separate HQ approval remains required before any deploy, and a separate approval remains required before Wave A marking.
